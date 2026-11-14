"""Datos sintéticos del especialista de SUEÑO (reproducibles, semilla fija).

Qué representa cada variable, de dónde sale su rango y qué supuestos se hicieron:
ver SUPUESTOS.md en esta misma carpeta.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # raíz del repo (comun/)

from comun.especialista import Variable  # noqa: E402
from comun.especialista.sintetico import cli, etiquetar, mezcla  # noqa: E402

SEMILLA = 20261

VARIABLES = (
    Variable("sueno_h", "Horas de sueño de anoche", 3.0, 9.5, 7.2,
             "dormiste más de lo habitual", "dormiste poco anoche", "h", -1),
    Variable("sueno_media_3d", "Sueño medio de 3 días", 3.5, 9.0, 7.2,
             "llevas varios días durmiendo bien", "llevas varios días durmiendo poco", "h", -1),
    Variable("irregularidad_h", "Irregularidad del sueño en la semana", 0.0, 2.5, 0.3,
             "tus horas de sueño cambian mucho de un día a otro", "tu horario de sueño es regular", "h", 1),
    Variable("desfase_circadiano_h", "Desfase del reloj interno", 0.0, 6.0, 0.5,
             "tu reloj interno está desajustado (16 amaneceres al día en órbita)",
             "tu reloj interno está bien ajustado", "h", 1),
    Variable("luz_brillante_min", "Minutos de luz brillante en tu 'mañana'", 0.0, 180.0, 70.0,
             "recibiste buena luz por la mañana", "recibiste poca luz brillante por la mañana", "min", -1),
    Variable("ejercicio_min", "Ejercicio del día", 0.0, 240.0, 120.0,
             "hiciste bastante ejercicio", "hiciste poco ejercicio", "min", -1),
    Variable("estres", "Estrés percibido", 0.0, 100.0, 30.0,
             "tu estrés está alto", "tu estrés está bajo", "0-100", 1),
)


def logit_riesgo(sueno_h, sueno_media_3d, irregularidad_h, desfase_circadiano_h,
                 luz_brillante_min, ejercicio_min, estres):
    """Regla de riesgo con la que se etiquetan los datos (pesos de ejemplo, supuestos propios).

    Es lineal a propósito: así una regresión logística puede recuperarla y cada
    peso se puede leer y discutir.
    """
    return (
        -3.75
        + 0.50 * (7.0 - sueno_h)             # menos horas anoche -> más riesgo
        + 0.40 * (7.0 - sueno_media_3d)      # deuda de sueño acumulada
        + 0.60 * irregularidad_h             # horarios cambiantes
        + 0.45 * desfase_circadiano_h        # reloj interno desajustado
        - 0.012 * (luz_brillante_min - 60.0)  # la luz brillante ayuda a ajustar el reloj
        + 0.015 * (estres - 30.0)            # el estrés empeora el sueño
        - 0.003 * (ejercicio_min - 120.0)    # el ejercicio ayuda un poco
    )


def generar(n: int, semilla: int = SEMILLA):
    """Devuelve (X, y): X con las columnas de VARIABLES e y = 1 si 'riesgo elevado'."""
    rng = np.random.default_rng(semilla)
    sueno = mezcla(rng, n, 3.0, 9.5, 7.0, 1.0)
    # El sueño de 3 días se parece al de anoche, con algo de variación.
    media_3d = np.clip(sueno + rng.normal(0.0, 0.6, n), 3.5, 9.0)
    irregularidad = mezcla(rng, n, 0.0, 2.5, 0.45, 0.35)
    desfase = mezcla(rng, n, 0.0, 6.0, 0.9, 0.9)
    luz = mezcla(rng, n, 0.0, 180.0, 65.0, 30.0)
    ejercicio = mezcla(rng, n, 0.0, 240.0, 115.0, 40.0)
    estres = mezcla(rng, n, 0.0, 100.0, 35.0, 18.0)
    X = np.column_stack([sueno, media_3d, irregularidad, desfase, luz, ejercicio, estres])
    y = etiquetar(rng, logit_riesgo(*X.T))
    return X, y


if __name__ == "__main__":
    cli(VARIABLES, generar, SEMILLA)
