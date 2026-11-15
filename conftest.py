"""Rutas de importación para ejecutar TODAS las pruebas desde la raíz con `pytest`.

Cada laptop tiene su carpeta; aquí se añaden al camino de Python lo mismo que
hace cada imagen Docker con PYTHONPATH.
"""

import os
import shutil
import sys
import uuid
from pathlib import Path

import pytest

# En Windows, el driver de esta máquina hace fallar XGBoost al finalizar el
# proceso cuando detecta CUDA. Las pruebas usan CPU para ser deterministas; el
# runtime normal sigue con USAR_GPU=auto y no se toca. Se puede sobrescribir.
if sys.platform == "win32":
    os.environ.setdefault("USAR_GPU", "no")

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


@pytest.fixture
def ruta_temporal():
    """Carpeta temporal dentro del proyecto.

    En el sandbox de Windows, pytest crea sus temporales con un descriptor de
    seguridad restrictivo que luego no puede leer ni borrar. Esta carpeta usa los
    permisos heredados del proyecto y se limpia al terminar.
    """
    base = RAIZ / ".tmp" / "pruebas"
    base.mkdir(parents=True, exist_ok=True)
    ruta = base / uuid.uuid4().hex
    ruta.mkdir()
    try:
        yield ruta
    finally:
        shutil.rmtree(ruta, ignore_errors=True)
