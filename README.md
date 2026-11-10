# Alerta del calendario de adviento (Trendy Shop)

Una página web para abrir en el celular. Revisa la tienda cada minuto y, cuando el calendario aparece o se puede comprar, suena, vibra, parpadea en rojo y muestra un botón grande que lleva directo al producto.

Para publicarla en internet, sigue `DESPLEGAR.md`.

## Probarla en tu computador

```bash
python3 web_alerta.py
```

Abre `http://localhost:8080` en el navegador. No necesita instalar nada más (solo Python 3).

## Uso en el celular

1. Abrir el enlace.
2. Tocar **Activar alertas** una vez (los navegadores no dejan sonar sin ese toque).
3. Dejar la página abierta y la pantalla encendida.

Si el celular se bloquea o cambia de app, el navegador puede pausar la página. En iPhone no vibra.

## Ajustes opcionales (variables o archivo `.env`)

- `KEYWORDS`: palabras que busca. Por defecto `adviento,advent,calendario`. Si "calendario" trae productos que no son el de adviento, usa `KEYWORDS=adviento,advent`.
- `WEB_CHECK_SECONDS`: cada cuánto revisa la tienda (por defecto 60, mínimo 30).
- `ACCESS_KEY`: si la pones, la página solo abre con `/?k=TU_CLAVE`.
