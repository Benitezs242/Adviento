# Poner la alerta en internet (un solo enlace para ella)

Tú lo subes una vez. Ella solo abre el enlace, toca **Activar alertas** y deja la página abierta. No hay que configurar variables ni claves.

## Paso 1. Subir la carpeta a GitHub

1. Crea un repositorio **privado** nuevo.
2. Sube todos los archivos de esta carpeta (`Dockerfile`, `monitor_adviento.py`, `web_alerta.py`, `render.yaml`, etc.).

## Paso 2A. Render (tiene plan gratis, con una limitación)

1. En render.com: **New +** → **Blueprint** → conecta tu GitHub y elige el repositorio.
2. Render lee `render.yaml` y crea el servicio. Espera a que termine de desplegar.
3. Copia la dirección del servicio (algo como `https://alerta-calendario.onrender.com`). Ese es el enlace para ella.

Limitación del plan gratis: según la documentación de Render, el servicio se suspende tras 15 minutos sin tráfico y tarda cerca de un minuto en despertar. Mientras ella tenga la página abierta, el celular consulta al servidor cada 10 segundos y lo mantiene despierto.

## Paso 2B. Railway (siempre encendido, de pago)

1. En railway.com: **New Project** → **Deploy from GitHub repo** → elige el repositorio (detecta el `Dockerfile`).
2. En **Settings → Networking**, genera un dominio público.
3. Ese dominio es el enlace para ella.

Según la documentación de Railway, el plan Hobby cuesta 5 USD al mes. Revisa el precio vigente.

## Paso 3. Lo que le dices a ella

"Abre este enlace, toca el botón morado **Activar alertas** una vez, y deja la pantalla encendida con la página abierta."

## Comprobar que funciona

Abre `https://TU-DIRECCION/api/status`. Si ves `"error": null` y una hora en `checked_at`, el servidor logró leer la tienda. Si `error` trae un mensaje, pásamelo.

## Privacidad

La página solo muestra datos públicos de la tienda, así que no lleva clave. Si prefieres que no la abra cualquiera con el enlace, agrega la variable `ACCESS_KEY` en el panel del hosting y usa `https://TU-DIRECCION/?k=TU_CLAVE`.
