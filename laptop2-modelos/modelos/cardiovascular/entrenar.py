"""Entrena el especialista Cardiovascular con datos sintéticos y guarda el artefacto versionado.

Uso (desde esta carpeta):  python entrenar.py
Reproducible: la semilla está fija en el generador de datos.
"""

import json

from modelo_cardio import CARPETA_ARTEFACTOS, DEFINICION

from comun.especialista import entrenar
from comun.especialista.dispositivo import detectar_dispositivo

if __name__ == "__main__":
    dispositivo = detectar_dispositivo() if DEFINICION.tipo == "boosting" else "cpu"
    metricas = entrenar(DEFINICION, CARPETA_ARTEFACTOS, dispositivo)
    print(json.dumps(metricas, indent=2, ensure_ascii=False))
