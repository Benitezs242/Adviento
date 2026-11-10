#!/usr/bin/env python3
"""Servidor web para la alerta del calendario de Adviento.

Combina la interfaz HTML con un backend mínimo para iniciar el monitor y
servir el estado a la página web.
"""

import json
import os
import threading
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "8080"))
ACCESS_KEY = os.environ.get("ACCESS_KEY", "").strip()
STATE_FILE = HERE / "estado_adviento.json"
MONITOR_SCRIPT = HERE / "monitor_adviento.py"

INDEX_HTML = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#09090b">
<title>Alerta Calendario de Adviento</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root { 
    --bg: #09090b; 
    --card: #18181b; 
    --card-border: #27272a;
    --text: #fafafa; 
    --muted: #a1a1aa; 
    --primary: #8b5cf6;
    --primary-hover: #7c3aed;
    --ok: #10b981; 
    --ok-bg: rgba(16, 185, 129, 0.12);
    --warn: #f59e0b; 
    --bad: #ef4444; 
    --bad-bg: rgba(239, 68, 68, 0.15);
  }
  
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  
  body { 
    margin: 0; 
    background: var(--bg); 
    color: var(--text); 
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    padding: max(20px, env(safe-area-inset-top)) 16px 40px; 
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .container {
    width: 100%;
    max-width: 480px;
  }

  header {
    text-align: center;
    margin-bottom: 24px;
    padding-top: 10px;
  }

  h1 { 
    font-size: 1.5rem; 
    font-weight: 800;
    margin: 0 0 6px; 
    letter-spacing: -0.025em;
    background: linear-gradient(135deg, #fff 30%, #a1a1aa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  
  .sub { 
    color: var(--muted); 
    font-size: 0.875rem; 
    font-weight: 500;
  }

  .state { 
    border-radius: 20px; 
    padding: 24px 20px; 
    text-align: center; 
    font-weight: 700; 
    font-size: 1.25rem; 
    background: var(--card); 
    border: 1px solid var(--card-border);
    margin-bottom: 16px; 
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
  }
  
  .state small { 
    display: block; 
    font-weight: 500; 
    font-size: 0.875rem; 
    color: var(--muted); 
    margin-top: 8px; 
    line-height: 1.4;
  }
  
  .state.ok { 
    background: var(--ok-bg); 
    border-color: rgba(16, 185, 129, 0.3);
    color: var(--ok); 
  } 
  
  .state.wait { 
    background: var(--card); 
  }

  button { 
    width: 100%; 
    font-family: inherit;
    font-size: 1rem; 
    padding: 16px; 
    border-radius: 16px; 
    border: 0; 
    font-weight: 700; 
    margin-bottom: 12px; 
    cursor: pointer;
    transition: transform 0.1s ease, background 0.2s ease;
  }

  button:active { transform: scale(0.98); }

  #arm { 
    background: linear-gradient(135deg, #9333ea 0%, var(--primary) 100%); 
    color: white; 
    box-shadow: 0 4px 14px rgba(139, 92, 246, 0.4);
  } 
  
  #arm.on { 
    background: var(--card); 
    color: var(--muted); 
    border: 1px solid var(--card-border);
    box-shadow: none;
  }
  
  #stop { 
    background: var(--bad-bg); 
    color: #fca5a5; 
    border: 1px solid rgba(239, 68, 68, 0.3);
    display: none; 
  }

  .cta { 
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center; 
    background: #fff; 
    color: #09090b; 
    font-weight: 800; 
    font-size: 1.1rem;
    padding: 18px 16px; 
    border-radius: 16px; 
    margin-bottom: 16px; 
    text-decoration: none; 
    box-shadow: 0 0 0 3px var(--ok), 0 8px 20px rgba(16, 185, 129, 0.3);
    animation: pulse-cta 2s infinite;
  }

  @keyframes pulse-cta {
    0% { transform: scale(1); }
    50% { transform: scale(1.02); }
    100% { transform: scale(1); }
  }

  .cta[hidden], .storelink[hidden], .err[hidden] { display: none !important; }

  .storelink { 
    display: block; 
    text-align: center; 
    color: #c084fc; 
    font-size: 0.9rem; 
    font-weight: 600;
    margin: 8px 0 20px; 
    text-decoration: none;
  }
  
  .storelink:hover { text-decoration: underline; }

  h2 { 
    font-size: 0.85rem; 
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 24px 0 10px; 
    color: var(--muted); 
    font-weight: 700;
  }

  .list { 
    background: var(--card); 
    border: 1px solid var(--card-border);
    border-radius: 16px; 
    padding: 4px 16px; 
    margin-bottom: 16px; 
  }
  
  .item { 
    padding: 14px 0; 
    border-bottom: 1px solid var(--card-border); 
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }
  
  .item:last-child { border-bottom: 0; }
  
  .item a { 
    color: var(--text); 
    text-decoration: none; 
    font-weight: 600;
    font-size: 0.95rem;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }
  
  .item a:hover { color: #c084fc; }
  
  .tag { 
    font-size: 0.75rem; 
    font-weight: 700;
    padding: 4px 10px; 
    border-radius: 999px; 
    white-space: nowrap;
  }
  
  .tag.y { background: var(--ok-bg); color: var(--ok); border: 1px solid rgba(16, 185, 129, 0.2); } 
  .tag.n { background: rgba(255, 255, 255, 0.05); color: var(--muted); }

  .ev { 
    font-size: 0.85rem; 
    padding: 12px 0; 
    border-bottom: 1px solid var(--card-border); 
    white-space: pre-wrap; 
    word-break: break-word; 
    line-height: 1.4;
  }
  
  .ev:last-child { border-bottom: 0; }
  .ev time { color: var(--muted); display: block; font-size: 0.75rem; margin-bottom: 2px; }

  .err { 
    background: var(--bad-bg);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #fca5a5; 
    padding: 12px 16px;
    border-radius: 12px;
    font-size: 0.85rem; 
    margin-bottom: 16px; 
    font-weight: 500;
  }

  .note { 
    color: var(--muted); 
    font-size: 0.78rem; 
    line-height: 1.5; 
    text-align: center;
    margin-top: 16px;
    padding: 0 10px;
  }

  body.alarm { animation: flash 0.6s infinite alternate; }
  @keyframes flash { from { background: var(--bg); } to { background: #7f1d1d; } }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🎄 Vigilante de Adviento</h1>
    <div class="sub" id="meta">Conectando con el sistema…</div>
  </header>

  <button id="arm">🔔 Activar alertas (toca una vez)</button>
  <button id="stop">🔕 Silenciar alarma</button>

  <div class="state wait" id="state">Analizando tienda<small>Comprobando disponibilidad del producto...</small></div>
  
  <a class="cta" id="cta" hidden target="_blank" rel="noopener"></a>
  <div class="err" id="err" hidden></div>

  <a class="storelink" id="storelink" hidden target="_blank" rel="noopener">🌐 Visitar la tienda oficial ↗</a>

  <h2>Productos monitoreados</h2>
  <div class="list" id="items"><div class="item">—</div></div>

  <h2>Historial de avisos</h2>
  <div class="list" id="events"><div class="ev">Sin registros recientes.</div></div>

  <p class="note">Mantén esta pestaña abierta y la pantalla encendida para asegurar que las alertas sonoras y de vibración funcionen correctamente.</p>
</div>

<script>
(function () {
  var K = new URLSearchParams(location.search).get('k') || '';
  var lastId = null, armed = false, ctx = null, beepTimer = null, wake = null, prevAvail = null;
  var $ = function (id) { return document.getElementById(id); };

  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : null; }

  function beep() {
    if (!ctx) return;
    try {
      var o = ctx.createOscillator(), g = ctx.createGain();
      o.type = 'square'; o.frequency.value = 880;
      g.gain.value = 0.25;
      o.connect(g); g.connect(ctx.destination);
      o.start(); o.stop(ctx.currentTime + 0.35);
    } catch (e) {}
  }
  
  function startAlarm() {
    if (beepTimer) return;
    document.body.classList.add('alarm');
    stop.style.display = 'block';
    beep(); if (navigator.vibrate) navigator.vibrate([400, 150, 400]);
    beepTimer = setInterval(function () {
      beep(); if (navigator.vibrate) navigator.vibrate([400, 150, 400]);
    }, 1300);
  }
  
  function stopAlarm() {
    clearInterval(beepTimer); beepTimer = null;
    document.body.classList.remove('alarm');
    stop.style.display = 'none';
    if (navigator.vibrate) navigator.vibrate(0);
  }
  
  stop.onclick = stopAlarm;

  async function requestWake() {
    try { if ('wakeLock' in navigator) wake = await navigator.wakeLock.request('screen'); } catch (e) {}
  }
  
  document.addEventListener('visibilitychange', function () {
    if (armed && document.visibilityState === 'visible') requestWake();
  });

  async function startServices() {
    try {
      var r = await fetch('/api/start?k=' + encodeURIComponent(K), { cache: 'no-store' });
      var d = await r.json();
      if (r.status === 403) {
        meta.textContent = 'Acceso denegado: clave incorrecta';
        return false;
      }
      if (d && d.status === 'started') {
        meta.textContent = 'Servicios iniciados · comprobando tienda...';
        return true;
      }
      if (d && d.status === 'running') {
        meta.textContent = 'Servicios ya activos · comprobando tienda...';
        return true;
      }
      meta.textContent = d && d.message ? d.message : 'Servicios en espera';
      return false;
    } catch (e) {
      meta.textContent = 'No se pudo iniciar el servicio';
      return false;
    }
  }

  arm.onclick = async function () {
    try { ctx = ctx || new (window.AudioContext || window.webkitAudioContext)(); await ctx.resume(); } catch (e) {}
    var started = await startServices();
    if (!started) return;
    armed = true;
    this.textContent = '✨ Alertas activas y protegiendo';
    this.className = 'on';
    beep();
    try { if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission(); } catch (e) {}
    requestWake();
  };

  function notifyOS(text) {
    try {
      if ('Notification' in window && Notification.permission === 'granted') new Notification('🎄 Calendario de Adviento', { body: text });
    } catch (e) {}
  }

  function render(d) {
    meta.textContent = (d.store || '') + ' · Última verificación: ' + (d.checked_at || '—');
    var avail = d.items.filter(function (i) { return i.available; });
    var st = state;
    
    if (avail.length) {
      st.className = 'state ok';
      st.firstChild.nodeValue = '¡PRODUCTO DISPONIBLE!';
      st.querySelector('small').textContent = avail.map(function (i) { return i.title; }).join(' · ');
    } else {
      st.className = 'state wait';
      st.firstChild.nodeValue = 'Buscando lanzamiento...';
      st.querySelector('small').textContent = d.items.length ? 'Se encontraron ' + d.items.length + ' productos relacionados, pero aún sin stock.' : 'Monitoreando la tienda en busca de novedades.';
    }

    var cta = cta, main = avail.filter(function (i) { return /adviento|advent/i.test(i.title); })[0] || avail[0];
    var mainUrl = main ? safeUrl(main.url) : null;
    if (mainUrl) { 
      cta.href = mainUrl; 
      cta.innerHTML = '🛒 &nbsp; COMPRAR AHORA: ' + main.title; 
      cta.hidden = false; 
    } else { 
      cta.hidden = true; 
    }

    var sl = storelink, storeUrl = safeUrl(d.store);
    if (storeUrl) { sl.href = storeUrl; sl.hidden = false; }

    if (prevAvail === false && avail.length && armed) startAlarm();
    prevAvail = avail.length > 0;

    var err = err; 
    err.hidden = !d.error; 
    err.textContent = d.error ? 'Aviso de conexión: ' + d.error : '';

    var box = items; 
    box.textContent = '';
    if (!d.items.length) { 
      var e = document.createElement('div'); 
      e.className = 'item'; 
      e.style.color = 'var(--muted)';
      e.textContent = 'Sin coincidencias activas por ahora.'; 
      box.appendChild(e); 
    }
    
    d.items.forEach(function (i) {
      var row = document.createElement('div'); 
      row.className = 'item';
      var url = safeUrl(i.url), el;
      if (url) { 
        el = document.createElement('a'); 
        el.href = url; 
        el.target = '_blank'; 
        el.rel = 'noopener'; 
      } else { 
        el = document.createElement('span'); 
      }
      el.textContent = i.title; 
      row.appendChild(el);
      
      var tag = document.createElement('span'); 
      tag.className = 'tag ' + (i.available ? 'y' : 'n');
      tag.textContent = i.available ? 'Disponible' : 'Agotado'; 
      row.appendChild(tag);
      box.appendChild(row);
    });

    var evBox = events; 
    evBox.textContent = '';
    if (!d.events.length) { 
      var n = document.createElement('div'); 
      n.className = 'ev'; 
      n.style.color = 'var(--muted)';
      n.textContent = 'Sin eventos registrados todavía.'; 
      evBox.appendChild(n); 
    }
    
    d.events.slice().reverse().forEach(function (ev) {
      var row = document.createElement('div'); 
      row.className = 'ev';
      var t = document.createElement('time'); 
      t.textContent = ev.time; 
      row.appendChild(t);
      row.appendChild(document.createTextNode(ev.text));
      evBox.appendChild(row);
    });
  }

  function handleNew(d) {
    var maxId = d.events.length ? d.events[d.events.length - 1].id : 0;
    if (lastId === null) { lastId = maxId; return; }
    var fresh = d.events.filter(function (e) { return e.id > lastId; });
    lastId = maxId;
    if (!fresh.length) return;
    var important = fresh.filter(function (e) { return !/^✅|^🟢/.test(e.text); });
    if (!important.length) return;
    notifyOS(important[important.length - 1].text);
    if (armed) startAlarm();
  }

  async function poll() {
    try {
      var r = await fetch('/api/status?k=' + encodeURIComponent(K), { cache: 'no-store' });
      if (r.status === 403) { meta.textContent = 'Acceso denegado: clave incorrecta'; return; }
      var d = await r.json();
      render(d); handleNew(d);
    } catch (e) {
      meta.textContent = 'Reconectando con el servidor...';
    }
  }
  poll(); setInterval(poll, 10000);
})();
</script>
</body>
</html>
"""

_MONITOR_THREAD = None


def run_monitor_loop():
    """Ejecuta el monitor en un hilo dentro del mismo proceso web."""
    try:
        import monitor_adviento
        monitor_adviento.run_forever()
    except Exception as exc:  # pragma: no cover - fallback defensivo
        print(f"Monitor en segundo plano falló: {exc}", flush=True)


def build_status_payload():
    """Devuelve el estado mínimo para la web y al usuario."""
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {
                    "store": "https://www.maquillajetrendyshop.com",
                    "checked_at": checked_at,
                    "items": data.get("items", []),
                    "events": data.get("events", []),
                    "error": None,
                }
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        pass

    return {
        "store": "https://www.maquillajetrendyshop.com",
        "checked_at": checked_at,
        "items": [],
        "events": [],
        "error": None,
    }


def start_monitor_service():
    """Lanza el monitor del calendario en un hilo del mismo proceso."""
    global _MONITOR_THREAD
    if _MONITOR_THREAD is not None and _MONITOR_THREAD.is_alive():
        return {"status": "running", "message": "El servicio ya estaba activo."}

    try:
        _MONITOR_THREAD = threading.Thread(
            target=run_monitor_loop,
            name="alerta-monitor",
            daemon=True,
        )
        _MONITOR_THREAD.start()
        return {"status": "started", "message": "Servicios iniciados correctamente."}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/start":
            if ACCESS_KEY and urllib.parse.parse_qs(parsed.query).get("k", [""])[0] != ACCESS_KEY:
                self.send_response(403)
                self.send_json({"status": "denied", "message": "Clave incorrecta"})
                return
            data = start_monitor_service()
            self.send_response(200 if data.get("status") != "error" else 500)
            self.send_json(data)
            return

        if parsed.path == "/api/status":
            if ACCESS_KEY and urllib.parse.parse_qs(parsed.query).get("k", [""])[0] != ACCESS_KEY:
                self.send_response(403)
                self.send_json({"status": "denied", "message": "Clave incorrecta"})
                return
            self.send_json(build_status_payload())
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(INDEX_HTML.encode("utf-8"))

    def send_json(self, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main():
    start_monitor_service()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), WebHandler)
    print(f"Servidor web activo en http://127.0.0.1:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Detenido.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
