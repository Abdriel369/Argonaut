"""Datos sintéticos del especialista de RIESGO SOLAR / radiación (reproducibles, semilla fija).

Rangos y supuestos documentados en SUPUESTOS.md (esta misma carpeta).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))   # raíz del repo (comun/)

from comun.especialista import Variable  # noqa: E402
from comun.especialista.sintetico import cli, etiquetar, mezcla, positivo  # noqa: E402

SEMILLA = 20264

VARIABLES = (
    Variable("tasa_dosis_usv_h", "Radiación que llega ahora", 5.0, 2000.0, 20.0,
             "la radiación que llega ahora es más alta de lo normal", "la radiación actual es la habitual",
             "µSv/h", 1),
    Variable("dosis_acumulada_msv", "Radiación acumulada en la misión", 0.0, 400.0, 20.0,
             "ya acumulas bastante radiación en la misión", "tu radiación acumulada es baja", "mSv", 1),
    Variable("evento_solar", "Tormenta solar en curso", 0.0, 1.0, 0.0,
             "hay una tormenta solar en curso", "no hay tormenta solar", "sí/no", 1),
    Variable("fc_desv_pct", "Pulso en reposo frente a tu normal", -15.0, 50.0, 0.0,
             "tu pulso está más alto que tu normal", "tu pulso está tranquilo", "%", 1),
    Variable("temperatura", "Temperatura corporal", 35.5, 39.5, 36.6,
             "tu temperatura está elevada", "tu temperatura es normal", "°C", 1),
    Variable("spo2", "Oxigenación", 85.0, 100.0, 98.0,
             "tu oxigenación es buena", "tu oxigenación está baja", "%", -1),
)


def logit_riesgo(tasa_dosis_usv_h, dosis_acumulada_msv, evento_solar, fc_desv_pct, temperatura, spo2):
    """Regla de riesgo por radiación (pesos de ejemplo, supuestos propios).

    Las señales del cuerpo (pulso, temperatura) solo pesan cuando hay exposición
    real: tormenta solar o tasa de dosis alta. Esa interacción es la razón de usar
    gradient boosting.
    """
    expuesto = ((evento_solar > 0.5) | (tasa_dosis_usv_h > 100.0)).astype(float)
    return (
        -3.00
        + 1.40 * np.log10(np.maximum(tasa_dosis_usv_h, 5.0) / 20.0)   # la tasa pesa en escala logarítmica
        + 1.80 * (evento_solar > 0.5)
        + 0.012 * dosis_acumulada_msv
        + expuesto * (0.060 * positivo(fc_desv_pct) + 1.50 * positivo(temperatura - 37.0))
        + 0.30 * positivo(96.0 - spo2)
    )


def generar(n: int, semilla: int = SEMILLA):
    rng = np.random.default_rng(semilla)
    evento = (rng.random(n) < 0.25).astype(float)
    # Sin tormenta: tasa habitual (decenas de µSv/h). Con tormenta: de 100 a 2000 µSv/h.
    tasa_normal = np.clip(np.exp(rng.normal(np.log(22.0), 0.45, n)), 5.0, 2000.0)
    tasa_evento = np.exp(rng.uniform(np.log(100.0), np.log(2000.0), n))
    # Un 10 % de los casos sin tormenta declarada tiene tasa alta (sensor adelantado al aviso).
    tasa_rara = np.exp(rng.uniform(np.log(5.0), np.log(2000.0), n))
    tasa = np.where(evento > 0.5, tasa_evento, np.where(rng.random(n) < 0.10, tasa_rara, tasa_normal))
    dosis = np.clip(rng.exponential(45.0, n), 0.0, 400.0)
    fc = mezcla(rng, n, -15.0, 50.0, 2.0, 7.0)
    temperatura = mezcla(rng, n, 35.5, 39.5, 36.7, 0.3, fraccion_uniforme=0.25)
    spo2 = mezcla(rng, n, 85.0, 100.0, 97.5, 1.0, fraccion_uniforme=0.2)
    X = np.column_stack([tasa, dosis, evento, fc, temperatura, spo2])
    y = etiquetar(rng, logit_riesgo(*X.T))
    return X, y


if __name__ == "__main__":
    cli(VARIABLES, generar, SEMILLA)
