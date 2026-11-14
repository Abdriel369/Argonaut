"""Especialista: Riesgo solar (radiación) (Laptop 3).

El especialista más pesado (más datos y más árboles). Combina tasa de dosis, dosis acumulada,
evento solar simulado y señales del cuerpo (pulso, temperatura, SpO2). Vive en la Laptop 3.

Modelo entrenado con datos SINTÉTICOS. No diagnostica: estima riesgo.
"""

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def _raiz_repo(inicio: Path) -> Path:
    """Sube por las carpetas hasta encontrar la que contiene comun/ (raíz del monorepo)."""
    return next(p for p in inicio.parents if (p / "comun").is_dir())
for _ruta in (_raiz_repo(AQUI), AQUI):   # raíz del repo (comun/) y generador de datos
    if str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

import generador_solar as generador  # noqa: E402
from comun.especialista import Definicion  # noqa: E402
from comun.especialista.datos import (  # noqa: E402,F401
    desviacion_pct, irregularidad, media_ultimos, pct_del_plan, valor,
)

CARPETA_ARTEFACTOS = AQUI / "artefactos"


def extraer(datos: dict) -> dict:
    """Toma de la consulta solo lo que este modelo necesita (None = sin dato)."""
    contexto = datos.get("contexto") or {}
    dosis = contexto.get("dosis_acumulada")
    evento = contexto.get("evento_solar")
    return {
        "tasa_dosis_usv_h": valor(datos, "tasa_dosis_usv_h"),
        "dosis_acumulada_msv": float(dosis) if isinstance(dosis, (int, float)) else None,
        "evento_solar": float(bool(evento)) if evento is not None else None,
        "fc_desv_pct": desviacion_pct(datos, "fc_reposo"),
        "temperatura": valor(datos, "temperatura"),
        "spo2": valor(datos, "spo2"),
    }


DEFINICION = Definicion(
    nombre="riesgo-solar",
    titulo="Riesgo solar (radiación)",
    riesgo_que_estima="exposición a radiación",
    version="1.0.0",
    tipo="boosting",
    laptop="Laptop 3",
    variables=generador.VARIABLES,
    generar=generador.generar,
    extraer=extraer,
    hiperparametros={"rondas": 400, "max_depth": 5, "eta": 0.05, "subsample": 0.8, "colsample_bytree": 0.9, "min_child_weight": 30},
    n_muestras=60000,
    semilla=generador.SEMILLA,
    auc_minimo=0.8,
    limitaciones=(
        "Entrenado solo con datos sintéticos: aprende una regla escrita a mano, no radiobiología real.",
        "El evento solar es simulado; no hay pronóstico de clima espacial ni dosímetro real.",
        "No distingue tipos de radiación ni blindaje del módulo.",
        "Las señales del cuerpo no miden daño por radiación; solo acompañan la estimación de riesgo.",
    ),
)
