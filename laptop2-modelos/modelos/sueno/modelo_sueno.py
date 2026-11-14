"""Especialista: Sueño (Laptop 2).

Estima el riesgo por falta o irregularidad de sueño: horas dormidas, deuda de varios días,
ritmo circadiano (16 amaneceres al día en órbita), luz, ejercicio y estrés.

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

import generador_sueno as generador  # noqa: E402
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
        "irregularidad_h": irregularidad(datos, "sueno_h"),
        "desfase_circadiano_h": valor(datos, "desfase_circadiano_h"),
        "luz_brillante_min": valor(datos, "luz_brillante_min"),
        "ejercicio_min": valor(datos, "ejercicio_min"),
        "estres": valor(datos, "estres"),
    }


DEFINICION = Definicion(
    nombre="sueno",
    titulo="Sueño",
    riesgo_que_estima="problemas por falta o desorden de sueño",
    version="1.0.0",
    tipo="logistica",
    laptop="Laptop 2",
    variables=generador.VARIABLES,
    generar=generador.generar,
    extraer=extraer,
    hiperparametros={"C": 1.0},
    n_muestras=20000,
    semilla=generador.SEMILLA,
    auc_minimo=0.78,
    limitaciones=(
        "Entrenado solo con datos sintéticos: aprende una regla escrita a mano, no fisiología real.",
        "Los rangos vienen de estudios en Tierra y de resúmenes públicos de vuelos; no representan por completo el espacio.",
        "El desfase circadiano y la luz son valores simulados; en una estación real vendrían de sensores y horarios.",
        "Modelo lineal: no capta combinaciones complejas entre factores.",
    ),
)
