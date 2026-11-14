# Laptop 2 · modelos especialistas y gateway. Una sola imagen; cada servicio cambia el comando.
# Contexto de construcción: la raíz del repositorio.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY laptop2-modelos/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY comun /app/comun
COPY contratos /app/contratos
COPY laptop2-modelos /app/laptop2-modelos
WORKDIR /app/laptop2-modelos
