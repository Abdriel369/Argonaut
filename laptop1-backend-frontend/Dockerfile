# Laptop 1 · backend + frontend. Contexto de construcción: la raíz del repositorio.
# Lleva una COPIA del motor de reglas (laptop3 orquestador/reglas/protocolos) para el respaldo local.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY laptop1-backend-frontend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY comun /app/comun
COPY contratos /app/contratos
COPY laptop1-backend-frontend/backend /app/laptop1-backend-frontend/backend
COPY laptop1-backend-frontend/frontend /app/laptop1-backend-frontend/frontend
COPY laptop3-orquestador/orquestador /app/laptop3-orquestador/orquestador
COPY laptop3-orquestador/reglas /app/laptop3-orquestador/reglas
COPY laptop3-orquestador/protocolos /app/laptop3-orquestador/protocolos
ENV PYTHONPATH=/app:/app/laptop1-backend-frontend:/app/laptop3-orquestador \
    DIR_FRONTEND=/app/laptop1-backend-frontend/frontend \
    RUTA_BD=/datos/astro_medico.db
WORKDIR /app/laptop1-backend-frontend
EXPOSE 8100
CMD ["uvicorn", "backend.principal:crear_app", "--factory", "--host", "0.0.0.0", "--port", "8100"]
