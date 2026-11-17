#!/bin/sh
# Arranca las dos interfaces en el contenedor `uis` (CMD de uis/Dockerfile):
#   - website en el puerto 3000;
#   - backoffice en el puerto 3001.
# Cada línea de salida lleva el prefijo de su aplicación. SIGTERM y SIGINT (docker compose stop o
# Ctrl+C) se reenvían a las dos. Si una se cae, se detiene la otra y el script termina con error,
# para que Docker marque el contenedor como caído en lugar de dejar una sola aplicación en marcha.
set -u

cd "$(dirname "$0")"

# Lanza `next dev` en una aplicación y escribe su salida con prefijo. La salida pasa por un FIFO para
# que $! sea el PID de Next.js (y no el del filtro), y así poder enviarle las señales.
# Con el sondeo activo (NEXT_WATCH_POLL_INTERVAL_MS), Turbopack avisa con "watch error ... NotFound"
# por cada ruta que vigila por si llega a existir (src/, .config, .next-internal...). Es inofensivo y
# solo aparece con sondeo, así que se descartan esas líneas; cualquier otro error se muestra.
# Uso: start_app <nombre> <puerto>; deja el PID en la variable APP_PID.
start_app() {
  name=$1
  port=$2
  fifo="/tmp/$name.fifo"
  rm -f "$fifo"
  mkfifo "$fifo"
  awk -v prefix="[$name] " '
    /watch error \(.*kind: NotFound/ { next }
    { print prefix $0; fflush() }
  ' < "$fifo" &
  (cd "$name" && exec ./node_modules/.bin/next dev -H 0.0.0.0 -p "$port") > "$fifo" 2>&1 &
  APP_PID=$!
}

# Espera solo a los dos `next dev`, no a los filtros: si Next.js muere de golpe, su proceso hijo puede
# dejar el FIFO abierto y el filtro no terminaría. Al salir este script (PID 1), Docker cierra el resto.
stop_all() {
  kill -TERM "$WEBSITE_PID" "$BACKOFFICE_PID" 2>/dev/null
  wait "$WEBSITE_PID" "$BACKOFFICE_PID" 2>/dev/null
}

start_app website 3000
WEBSITE_PID=$APP_PID
start_app backoffice 3001
BACKOFFICE_PID=$APP_PID

trap 'stop_all; exit 0' TERM INT

# Espera mientras las dos sigan vivas.
while kill -0 "$WEBSITE_PID" 2>/dev/null && kill -0 "$BACKOFFICE_PID" 2>/dev/null; do
  sleep 1
done

echo "[start.sh] Una de las aplicaciones se ha detenido; se detiene también la otra." >&2
stop_all
exit 1
