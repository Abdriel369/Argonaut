"""Especialista: Cardiovascular (Laptop 2).

Combina pulso en reposo, HRV, SpO2, presión arterial (solo si hay módulo externo), sueño y
ejercicio, considerando el desplazamiento de fluidos por microgravedad de los primeros días.

Modelo entrenado con datos SINTÉTICOS. No diagnostica: estima riesgo.
"""

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def _raiz_repo(inicio: Path) -> Path:
    """Sube por las carpetas hasta encontrar la que contiene comun/ (raíz del monorepo)."""
    return next(p for p in inicio.parents if (p / "comun").is_dir())
for _ruta in (_raiz_repo(AQUI), AQUI.parents[1] / "datos-sinteticos"):   # raíz del repo (comun/) y generador de datos
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

import generador_cardio as generador  # noqa: E402
from comun.especialista import Definicion  # noqa: E402
from comun.especialista.datos import (  # noqa: E402,F401
    desviacion_pct, irregularidad, media_ultimos, pct_del_plan, valor,
)

CARPETA_ARTEFACTOS = AQUI / "artefactos"


def extraer(datos: dict) -> dict:
    """Toma de la consulta solo lo que este modelo necesita (None = sin dato)."""
    return {
        "fc_desv_pct": desviacion_pct(datos, "fc_reposo"),
        "hrv_desv_pct": desviacion_pct(datos, "hrv"),
        "spo2": valor(datos, "spo2"),
        # Opcional: sin módulo externo de presión llega None y el modelo lo imputa.
        "presion_sistolica": valor(datos, "presion_sistolica"),
        "sueno_media_3d": media_ultimos(datos, "sueno_h", 3),
        "ejercicio_pct_plan": pct_del_plan(datos, "ejercicio_min"),
        "dia_mision": float(datos["dia_mision"]) if isinstance(datos.get("dia_mision"), (int, float)) else None,
    }


DEFINICION = Definicion(
    nombre="cardiovascular",
    titulo="Cardiovascular",
    riesgo_que_estima="sobrecarga del corazón y la circulación",
    version="1.0.0",
    tipo="boosting",
    laptop="Laptop 2",
    variables=generador.VARIABLES,
    generar=generador.generar,
    extraer=extraer,
    hiperparametros={"rondas": 160, "max_depth": 3, "eta": 0.08, "subsample": 0.8, "min_child_weight": 20},
    n_muestras=20000,
    semilla=generador.SEMILLA,
    auc_minimo=0.78,
    limitaciones=(
        "Entrenado solo con datos sintéticos: aprende una regla escrita a mano, no fisiología real.",
        "La presión arterial no se mide de forma fiable sin equipo dedicado; aquí es un dato simulado y opcional.",
        "El efecto del desplazamiento de fluidos se resume en un solo término; la realidad es más compleja.",
        "No detecta arritmias ni ningún problema concreto: solo estima riesgo general.",
    ),
)
