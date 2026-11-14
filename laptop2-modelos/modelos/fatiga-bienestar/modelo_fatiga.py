"""Especialista: Fatiga y bienestar (Laptop 2).

Combina sueño, ánimo, estrés, variabilidad del pulso (HRV), ejercicio, ingesta y cohesión
del equipo (aislamiento y confinamiento) para estimar el riesgo de fatiga.

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

import generador_fatiga as generador  # noqa: E402
from comun.especialista import Definicion  # noqa: E402
from comun.especialista.datos import (  # noqa: E402,F401
    desviacion_pct, irregularidad, media_ultimos, pct_del_plan, valor,
)

CARPETA_ARTEFACTOS = AQUI / "artefactos"


def extraer(datos: dict) -> dict:
    """Toma de la consulta solo lo que este modelo necesita (None = sin dato)."""
    return {
        "sueno_h": valor(datos, "sueno_h"),
        "sueno_media_3d": media_ultimos(datos, "sueno_h", 3),
        "animo": valor(datos, "animo"),
        "estres": valor(datos, "estres"),
        "hrv_desv_pct": desviacion_pct(datos, "hrv"),
        "ejercicio_pct_plan": pct_del_plan(datos, "ejercicio_min"),
        "ingesta_pct": valor(datos, "ingesta_pct"),
        "cohesion_equipo": valor(datos, "cohesion_equipo"),
        "tiempo_reaccion_ms": valor(datos, "tiempo_reaccion_ms"),
    }


DEFINICION = Definicion(
    nombre="fatiga-bienestar",
    titulo="Fatiga y bienestar",
    riesgo_que_estima="fatiga y desgaste emocional",
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
        "Ánimo, estrés y cohesión son respuestas subjetivas; en datos reales tienen sesgos que aquí no existen.",
        "El aislamiento prolongado de una misión real no está representado en datos de una semana simulada.",
        "La confianza es una heurística, no una probabilidad calibrada.",
    ),
)
