#!/usr/bin/env python3
"""
Lógica del vigilante del calendario de adviento (Trendy Shop, VTEX; también Shopify).

Lo usa web_alerta.py. Revisa el catálogo y detecta cuando:
  - aparece un producto nuevo que coincide con las palabras clave
  - un producto pasa de agotado a disponible (o se agota)
  - cambia el precio de un producto
  - un producto desaparece del catálogo

Solo usa la librería estándar de Python.

También se puede correr solo, para ver los avisos en la consola:
  python3 monitor_adviento.py          # en bucle, cada 5 minutos
  python3 monitor_adviento.py --once   # una sola revisión
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def load_dotenv(path):
    """Carga KEY=VALUE de un .env sin pisar variables ya definidas."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


load_dotenv(os.path.join(HERE, ".env"))

STORE_URL = os.environ.get("STORE_URL", "https://www.maquillajetrendyshop.com").rstrip("/")
PLATFORM = os.environ.get("PLATFORM", "auto").lower()  # auto | vtex | shopify
KEYWORDS = [
    k.strip().lower()
    for k in os.environ.get("KEYWORDS", "adviento,advent,calendario").split(",")
    if k.strip()
]
INTERVAL = max(120, int(os.environ.get("CHECK_EVERY_SECONDS", "300")))
STATE_FILE = os.environ.get("STATE_FILE", os.path.join(HERE, "estado_adviento.json"))
FAILS_BEFORE_ALERT = 6  # revisiones seguidas con error antes de avisar que la tienda no responde
USER_AGENT = "Mozilla/5.0 (compatible; VigilanteAdviento/3.0; uso personal)"


def http_get(url, timeout=25):
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def text_matches(*parts):
    haystack = " ".join(p for p in parts if p).lower()
    return any(k in haystack for k in KEYWORDS)


# ---------------------------------------------------------------- Shopify

def fetch_shopify():
    raw, page = [], 1
    while True:
        data = json.loads(http_get(f"{STORE_URL}/products.json?limit=250&page={page}"))
        if "products" not in data:
            raise ValueError("Respuesta sin 'products'")
        batch = data["products"]
        if not batch:
            break
        raw.extend(batch)
        if len(batch) < 250:
            break
        page += 1
        time.sleep(1)

    items = []
    for p in raw:
        tags = p.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        if not text_matches(p.get("title"), p.get("handle"), p.get("product_type"), " ".join(tags)):
            continue
        variants = p.get("variants", [])
        items.append(
            {
                "id": str(p["id"]),
                "title": p.get("title", ""),
                "url": f"{STORE_URL}/products/{p.get('handle', '')}",
                "available": any(v.get("available") for v in variants),
                "price": variants[0].get("price") if variants else "?",
                "release": "",
            }
        )
    return items


# ------------------------------------------------------------------- VTEX

def _vtex_normalize(products):
    items = {}
    for p in products:
        if not isinstance(p, dict) or "productId" not in p:
            continue
        categories = " ".join(p.get("categories", []) or [])
        if not text_matches(p.get("productName"), p.get("linkText"), categories):
            continue
        available, prices = False, []
        for it in p.get("items", []) or []:
            for seller in it.get("sellers", []) or []:
                offer = seller.get("commertialOffer", {}) or {}
                if offer.get("IsAvailable") or (offer.get("AvailableQuantity") or 0) > 0:
                    available = True
                if offer.get("Price"):
                    prices.append(offer["Price"])
        pid = str(p["productId"])
        items[pid] = {
            "id": pid,
            "title": p.get("productName", ""),
            "url": p.get("link") or f"{STORE_URL}/{p.get('linkText', '')}/p",
            "available": available,
            "price": min(prices) if prices else "?",
            "release": (p.get("releaseDate") or "")[:10],
        }
    return items


def fetch_vtex():
    found, classic_ok = {}, False
    for kw in KEYWORDS:
        url = (
            f"{STORE_URL}/api/catalog_system/pub/products/search"
            f"?ft={urllib.parse.quote(kw)}&_from=0&_to=49"
        )
        try:
            data = json.loads(http_get(url))
            if isinstance(data, list):
                classic_ok = True
                found.update(_vtex_normalize(data))
        except (urllib.error.URLError, ValueError):
            pass
        time.sleep(1)

    if not classic_ok:  # respaldo: búsqueda inteligente de VTEX
        for kw in KEYWORDS:
            url = (
                f"{STORE_URL}/api/io/_v/api/intelligent-search/product_search/"
                f"?query={urllib.parse.quote(kw)}&count=50&page=1"
            )
            data = json.loads(http_get(url))
            found.update(_vtex_normalize(data.get("products", [])))
            time.sleep(1)
    return list(found.values())


def fetch_items():
    if PLATFORM == "shopify":
        return fetch_shopify()
    if PLATFORM == "vtex":
        return fetch_vtex()
    try:  # auto: la web de Trendy es VTEX, pero se prueba Shopify primero
        return fetch_shopify()
    except (urllib.error.URLError, ValueError):
        return fetch_vtex()


# ------------------------------------------------------------ Estado/avisos

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATE_FILE)
    except OSError as e:  # si el disco es de solo lectura, se sigue en memoria
        print(f"No se pudo guardar el estado: {e}", flush=True)


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def notify(text):
    """Muestra el aviso en consola. web_alerta.py lo engancha para mostrarlo en la página."""
    print(f"[{now()}] [ALERTA] {text}", flush=True)
    return True


def fmt_price(p):
    return f"${p:,.0f}".replace(",", ".") if isinstance(p, (int, float)) else f"${p}"


# El estado también se guarda en memoria: si el archivo no persiste (hosting gratis),
# no se pierde entre revisiones.
_MEMORY_STATE = {"value": None}


def check_once():
    current = {item["id"]: item for item in fetch_items()}
    previous = _MEMORY_STATE["value"]
    if previous is None:
        previous = load_state()

    if previous is None:  # primera vez: línea base
        lines = [
            f"- {i['title']} ({'DISPONIBLE' if i['available'] else 'no disponible'})"
            for i in list(current.values())[:10]
        ]
        resumen = "\n".join(lines) if lines else "- (ninguno todavía)"
        notify(
            f"✅ Vigilante activo en {STORE_URL}\n"
            f"Palabras clave: {', '.join(KEYWORDS)}\n"
            f"Coinciden {len(current)} producto(s):\n{resumen}"
        )
        _MEMORY_STATE["value"] = current
        save_state(current)
        return current

    for pid, item in current.items():
        old = previous.get(pid)
        rel = f"\nLanzamiento: {item['release']}" if item.get("release") else ""
        if old is None:
            if item["available"]:
                notify(f"🎄 ¡NUEVO y DISPONIBLE!: {item['title']} ({fmt_price(item['price'])}){rel}\n{item['url']}")
            else:
                notify(f"👀 Apareció un producto nuevo (aún no disponible): {item['title']}{rel}\n{item['url']}")
            continue
        if item["available"] and not old.get("available"):
            notify(f"🛒 ¡YA SE PUEDE COMPRAR!: {item['title']} ({fmt_price(item['price'])})\n{item['url']}")
        elif not item["available"] and old.get("available"):
            notify(f"⛔ Se agotó o dejó de estar disponible: {item['title']}\n{item['url']}")
        if item["price"] != old.get("price"):
            notify(
                f"💲 Cambió el precio de {item['title']}: "
                f"{fmt_price(old.get('price'))} → {fmt_price(item['price'])}\n{item['url']}"
            )

    for pid, old in previous.items():
        if pid not in current:
            notify(f"🫥 Ya no aparece en la búsqueda: {old['title']}")

    _MEMORY_STATE["value"] = current
    save_state(current)
    return current


def run_forever():
    print(f"[{now()}] Vigilando {STORE_URL} cada {INTERVAL}s. Palabras clave: {KEYWORDS}", flush=True)
    while True:
        try:
            check_once()
        except Exception as e:
            print(f"[{now()}] Error en la revisión: {e}", flush=True)
        time.sleep(INTERVAL)


def main():
    if "--once" in sys.argv[1:]:
        try:
            check_once()
        except (urllib.error.URLError, ValueError) as e:
            sys.exit(f"No se pudo leer el catálogo de la tienda: {e}")
        return
    try:
        run_forever()
    except KeyboardInterrupt:
        print("\nDetenido.")


if __name__ == "__main__":
    main()
