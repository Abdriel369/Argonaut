"""Servicio HTTP del especialista Cardiovascular: POST /predecir, GET /salud, GET /info.

Arranque:  uvicorn api_cardio:app --host 0.0.0.0 --port 8000
"""

from modelo_cardio import CARPETA_ARTEFACTOS, DEFINICION

from comun.especialista.api import crear_app

app = crear_app(DEFINICION, CARPETA_ARTEFACTOS)
