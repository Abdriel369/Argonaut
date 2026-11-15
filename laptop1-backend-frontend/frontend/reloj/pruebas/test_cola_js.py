"""Pruebas de la lógica JavaScript pura (cola offline y vistas) con Node.

Si Node no está instalado, se saltan: el resto de la suite sigue funcionando.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

AQUI = Path(__file__).resolve().parent
NODE = shutil.which("node")


def correr(script: str) -> str:
    resultado = subprocess.run(
        [NODE, str(AQUI / script)], capture_output=True, text=True, timeout=60,
        cwd=str(AQUI),
    )
    assert resultado.returncode == 0, resultado.stderr or resultado.stdout
    return resultado.stdout


@pytest.mark.skipif(NODE is None, reason="Node no está instalado")
def test_la_cola_offline_del_reloj_pasa_sus_comprobaciones():
    salida = correr("cola.script.mjs")
    assert "todas las comprobaciones pasaron" in salida


@pytest.mark.skipif(NODE is None, reason="Node no está instalado")
def test_las_vistas_de_tripulacion_renderizan_sin_errores():
    salida = correr("vistas.script.mjs")
    assert "renderizan sin errores" in salida
