"""Servicio HTTP del especialista Riesgo solar (radiación): POST /predecir, GET /salud, GET /info.

Arranque:  uvicorn api_solar:app --host 0.0.0.0 --port 8000
"""

from modelo_solar import CARPETA_ARTEFACTOS, DEFINICION

from comun.especialista.api import crear_app

app = crear_app(DEFINICION, CARPETA_ARTEFACTOS)
