#!/usr/bin/env bash
# Arranca la DEMO en una sola máquina con respuestas grabadas de ejecuciones reales.
#   ./arrancar_demo.sh          con Docker: docker compose up --build
#   ./arrancar_demo.sh local    sin Docker: mismos servicios en procesos locales
# Interfaz: http://localhost:8100/   (la pantalla avisa: "Demo en una sola máquina")
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/.." && pwd)"

if [ "${1:-}" != "local" ] && command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  cd "$AQUI" && exec docker compose up --build
fi

echo "Arranque local (sin Docker) con respuestas guardadas."
LOGS="${LOGS:-/tmp/astro-demo}"
mkdir -p "$LOGS" "$AQUI/datos"
if [ -f "$LOGS/pids" ]; then xargs -r kill < "$LOGS/pids" 2>/dev/null || true; rm -f "$LOGS/pids"; sleep 1; fi

( cd "$RAIZ/laptop3-orquestador" && RESPUESTAS_GUARDADAS="$AQUI/respuestas-guardadas.json" \
    PYTHONPATH="$RAIZ:$RAIZ/laptop3-orquestador" exec python3 -m uvicorn orquestador.principal:crear_app \
    --factory --host 127.0.0.1 --port 8300 > "$LOGS/orquestador.log" 2>&1 ) &
echo $! >> "$LOGS/pids"

( cd "$RAIZ/laptop1-backend-frontend" && URL_ORQUESTADOR="http://127.0.0.1:8300" \
    RUTA_BD="$AQUI/datos/astro_medico.db" \
    PYTHONPATH="$RAIZ:$RAIZ/laptop1-backend-frontend:$RAIZ/laptop3-orquestador" exec python3 -m uvicorn \
    backend.principal:crear_app --factory --host 0.0.0.0 --port 8100 > "$LOGS/backend.log" 2>&1 ) &
echo $! >> "$LOGS/pids"

echo "Listo en http://localhost:8100/  (logs en $LOGS/)"
echo "Detener: kill \$(cat $LOGS/pids)"
