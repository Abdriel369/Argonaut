"""Servicio HTTP del especialista Fatiga y bienestar: POST /predecir, GET /salud, GET /info.

Arranque:  uvicorn api_fatiga:app --host 0.0.0.0 --port 8000
"""

from modelo_fatiga import CARPETA_ARTEFACTOS, DEFINICION

from comun.especialista.api import crear_app

app = crear_app(DEFINICION, CARPETA_ARTEFACTOS)
