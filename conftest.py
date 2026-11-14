"""Rutas de importación para ejecutar TODAS las pruebas desde la raíz con `pytest`.

Cada laptop tiene su carpeta; aquí se añaden al camino de Python lo mismo que
hace cada imagen Docker con PYTHONPATH.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

RUTAS = [
    RAIZ,                                                        # comun/, contratos/
    RAIZ / "pruebas-integracion",                                # pila.py, fabrica.py
    RAIZ / "laptop1-backend-frontend",                           # backend/
    RAIZ / "laptop2-modelos",                                    # gateway/
    RAIZ / "laptop2-modelos" / "datos-sinteticos",
    RAIZ / "laptop2-modelos" / "modelos" / "sueno",
    RAIZ / "laptop2-modelos" / "modelos" / "fatiga-bienestar",
    RAIZ / "laptop2-modelos" / "modelos" / "cardiovascular",
    RAIZ / "laptop3-orquestador",                                # orquestador/, reglas/, protocolos/
    RAIZ / "laptop3-orquestador" / "modelos" / "riesgo-solar",
    RAIZ / "modo-demo-sin-laptops",
]
for ruta in RUTAS:
    if str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))
