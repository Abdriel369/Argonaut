# syntax=docker/dockerfile:1
# Argonaut · Station Doctor — imagen única para la demo en Render.
#
# Un solo contenedor y un solo proceso: backend + orquestador en la misma app
# (ver deploy/render/app.py). No instala dependencias de IA: los especialistas
# responden desde respuestas-guardadas.json.

FROM python:3.12-slim

# --- Entorno ---------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app:/app/laptop1-backend-frontend:/app/laptop3-orquestador \
    RUTA_BD=/tmp/astro_medico.db \
    RESPUESTAS_GUARDADAS=/app/respuestas-guardadas.json \
    PORT=8100

WORKDIR /app

# --- Dependencias (solo runtime) -------------------------------------------
COPY deploy/render/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

# --- Código indispensable --------------------------------------------------
# Rutas relativas al contexto de build (la raíz del repositorio).
COPY comun ./comun
COPY contratos ./contratos
COPY laptop1-backend-frontend/backend ./laptop1-backend-frontend/backend
COPY laptop1-backend-frontend/frontend ./laptop1-backend-frontend/frontend
COPY laptop3-orquestador/orquestador ./laptop3-orquestador/orquestador
COPY laptop3-orquestador/reglas ./laptop3-orquestador/reglas
COPY laptop3-orquestador/protocolos ./laptop3-orquestador/protocolos
COPY modo-demo-sin-laptops/respuestas-guardadas.json ./respuestas-guardadas.json
COPY deploy/render/app.py ./deploy/render/app.py

# --- Usuario sin privilegios ----------------------------------------------
# /tmp sigue siendo escribible: ahí vive la SQLite temporal.
RUN useradd --create-home --uid 10001 demo \
    && chown -R demo:demo /app
USER demo

EXPOSE 8100

# Render detiene el contenedor con SIGTERM: `exec` deja a uvicorn como PID 1
# para que reciba la señal y cierre las conexiones de forma ordenada.
STOPSIGNAL SIGTERM
CMD ["sh", "-c", "exec python -m uvicorn app:app --app-dir /app/deploy/render --host 0.0.0.0 --port ${PORT:-8100} --proxy-headers --forwarded-allow-ips='*'"]
