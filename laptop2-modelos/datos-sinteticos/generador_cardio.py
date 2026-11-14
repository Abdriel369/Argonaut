"""Datos sintéticos del especialista CARDIOVASCULAR (reproducibles, semilla fija).

Rangos y supuestos documentados en SUPUESTOS.md.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # raíz del repo (comun/)

from comun.especialista import Variable  # noqa: E402
from comun.especialista.sintetico import cli, etiquetar, mezcla, positivo  # noqa: E402

SEMILLA = 20263

VARIABLES = (
    Variable("fc_desv_pct", "Pulso en reposo frente a tu normal", -15.0, 50.0, 0.0,
             "tu pulso en reposo está más alto que tu normal", "tu pulso en reposo está tranquilo", "%", 1),
    Variable("hrv_desv_pct", "Variabilidad del pulso frente a tu normal", -60.0, 30.0, 0.0,
             "la variabilidad de tu pulso es buena", "la variabilidad de tu pulso bajó", "%", -1),
    Variable("spo2", "Oxigenación", 85.0, 100.0, 98.0,
             "tu oxigenación es buena", "tu oxigenación está baja", "%", -1),
    Variable("presion_sistolica", "Presión arterial (módulo externo)", 90.0, 180.0, 118.0,
             "tu presión está alta", "tu presión está normal", "mmHg", 1),
    Variable("sueno_media_3d", "Sueño medio de 3 días", 3.5, 9.0, 7.2,
             "llevas varios días durmiendo bien", "llevas varios días durmiendo poco", "h", -1),
    Variable("ejercicio_pct_plan", "Ejercicio frente al plan", 0.0, 200.0, 100.0,
             "cumpliste tu ejercicio", "hiciste poco ejercicio", "%", -1),
    Variable("dia_mision", "Día de misión", 1.0, 180.0, 30.0,
             "llevas tiempo en microgravedad",
             "tu cuerpo aún se adapta: en microgravedad los líquidos suben hacia el pecho y la cabeza",
             "días", -1),
)


def logit_riesgo(fc_desv_pct, hrv_desv_pct, spo2, presion_sistolica, sueno_media_3d,
                 ejercicio_pct_plan, dia_mision):
    """Regla de riesgo de sobrecarga cardiovascular (pesos de ejemplo, supuestos propios)."""
    return (
        -2.60
        + 0.090 * positivo(fc_desv_pct)             # pulso en reposo por encima de tu normal
        + 0.030 * positivo(-hrv_desv_pct)           # variabilidad por debajo de tu normal
        + 0.50 * positivo(96.0 - spo2)              # oxigenación baja
        + 0.030 * positivo(presion_sistolica - 125.0)
        + 0.25 * positivo(6.5 - sueno_media_3d)     # dormir poco carga al corazón
        + 0.010 * positivo(70.0 - ejercicio_pct_plan)   # desacondicionamiento
        + 0.25 * np.exp(-(dia_mision - 1.0) / 3.0)  # desplazamiento de fluidos: pesa los primeros días
    )


def generar(n: int, semilla: int = SEMILLA):
    rng = np.random.default_rng(semilla)
    fc = mezcla(rng, n, -15.0, 50.0, 2.0, 7.0)
    hrv = mezcla(rng, n, -60.0, 30.0, -3.0, 12.0)
    spo2 = mezcla(rng, n, 85.0, 100.0, 97.5, 1.0, fraccion_uniforme=0.2)
    presion = mezcla(rng, n, 90.0, 180.0, 119.0, 9.0)
    media_3d = mezcla(rng, n, 3.5, 9.0, 7.0, 0.9)
    ejercicio = mezcla(rng, n, 0.0, 200.0, 98.0, 22.0)
    # Días de misión: muchos casos al principio (cuando más cambia el cuerpo).
    dia = np.clip(np.round(rng.exponential(25.0, n)) + 1.0, 1.0, 180.0)
    X = np.column_stack([fc, hrv, spo2, presion, media_3d, ejercicio, dia])
    y = etiquetar(rng, logit_riesgo(*X.T))
    return X, y


if __name__ == "__main__":
    cli(VARIABLES, generar, SEMILLA)
