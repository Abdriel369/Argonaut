#!/usr/bin/env bash
# Arranca TODO en esta máquina sin Docker (útil para desarrollar y depurar).
# Los 7 servicios reales, cada uno en su puerto, hablando por HTTP en 127.0.0.1.
#   ./scripts/arrancar_local.sh          arranca y deja los logs en /tmp/astro-medico/
#   ./scripts/arrancar_local.sh parar    detiene todo
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
LOGS="${LOGS:-/tmp/astro-medico}"
mkdir -p "$LOGS"

parar() {
  if [ -f "$LOGS/pids" ]; then
    xargs -r kill < "$LOGS/pids" 2>/dev/null || true
    rm -f "$LOGS/pids"
  fi
}
if [ "${1:-}" = "parar" ]; then parar; echo "Servicios detenidos."; exit 0; fi
parar
sleep 1   # da tiempo a que se liberen los puertos

lanzar() {  # nombre, carpeta de trabajo, PYTHONPATH, objetivo uvicorn, puerto, [--factory]
  local nombre="$1" carpeta="$2" rutas="$3" objetivo="$4" puerto="$5" extra="${6:-}"
  # 'exec' hace que el PID guardado sea el del propio servicio (así "parar" lo detiene de verdad).
  ( cd "$carpeta" && PYTHONPATH="$rutas" exec python3 -m uvicorn "$objetivo" $extra \
      --host 0.0.0.0 --port "$puerto" ) > "$LOGS/$nombre.log" 2>&1 &
  echo $! >> "$LOGS/pids"
}

L1="$RAIZ/laptop1-backend-frontend"; L2="$RAIZ/laptop2-modelos"; L3="$RAIZ/laptop3-orquestador"
DATOS="$L2/datos-sinteticos"

# Laptop 2: tres modelos + gateway
lanzar modelo-sueno  "$L2/modelos/sueno"            "$RAIZ:$DATOS:$L2/modelos/sueno"            api_sueno:app  8210
lanzar modelo-fatiga "$L2/modelos/fatiga-bienestar" "$RAIZ:$DATOS:$L2/modelos/fatiga-bienestar" api_fatiga:app 8220
lanzar modelo-cardio "$L2/modelos/cardiovascular"   "$RAIZ:$DATOS:$L2/modelos/cardiovascular"   api_cardio:app 8230
lanzar gateway       "$L2"                          "$RAIZ:$L2"   gateway.principal:crear_app 8200 --factory
# Laptop 3: modelo solar + orquestador
lanzar modelo-solar  "$L3/modelos/riesgo-solar"     "$RAIZ:$L3/modelos/riesgo-solar" api_solar:app 8310
URL_GATEWAY="http://127.0.0.1:8200" URL_MODELO_SOLAR="http://127.0.0.1:8310" \
  lanzar orquestador "$L3" "$RAIZ:$L3" orquestador.principal:crear_app 8300 --factory
# Laptop 1: backend + frontend
URL_ORQUESTADOR="http://127.0.0.1:8300" RUTA_BD="${RUTA_BD:-$LOGS/astro_medico.db}" \
  lanzar backend "$L1" "$RAIZ:$L1:$L3" backend.principal:crear_app 8100 --factory

echo "Servicios arrancando. Logs en $LOGS/. Interfaz: http://127.0.0.1:8100/"
