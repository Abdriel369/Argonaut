"""Servicio HTTP del especialista Sueño: POST /predecir, GET /salud, GET /info.

Arranque:  uvicorn api_sueno:app --host 0.0.0.0 --port 8000
"""

from modelo_sueno import CARPETA_ARTEFACTOS, DEFINICION

from comun.especialista.api import crear_app

app = crear_app(DEFINICION, CARPETA_ARTEFACTOS)
