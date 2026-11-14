"""Datos sintéticos del especialista de SUEÑO (reproducibles, semilla fija).

Qué representa cada variable, de dónde sale su rango y qué supuestos se hicieron:
ver SUPUESTOS.md en esta misma carpeta.

Versión 1.1.0 (datos más realistas): las variables ya no son independientes. El estrés
y el ejercicio afectan al sueño de anoche antes de que la regla de riesgo actúe; el
desfase del reloj y la irregularidad van juntos; y los valores se generan con
distribuciones acotadas (Beta y normal truncada), sin recortar en los bordes.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # raíz del repo (comun/)

from comun.especialista import Variable  # noqa: E402
from comun.especialista.sintetico import cli, etiquetar  # noqa: E402

SEMILLA = 20261

# Intersección calibrada para que la prevalencia de riesgo sea ≈ 12 % con la semilla y el tamaño
# por defecto (20 000 muestras). Se obtuvo con bisección; ver SUPUESTOS.md.
INTERCEPTO = -3.374
PREVALENCIA_OBJETIVO = 0.12

# "referencia" = mediana de la población sintética (antes eran valores a ojo, desalineados).
VARIABLES = (
    Variable("sueno_h", "Horas de sueño de anoche", 3.0, 9.5, 7.0,
             "dormiste más de lo habitual", "dormiste poco anoche", "h", -1),
    Variable("sueno_media_3d", "Sueño medio de 3 días", 3.5, 9.0, 7.0,
             "llevas varios días durmiendo bien", "llevas varios días durmiendo poco", "h", -1),
    Variable("irregularidad_h", "Irregularidad del sueño en la semana", 0.0, 2.5, 0.3,
             "tus horas de sueño cambian mucho de un día a otro", "tu horario de sueño es regular", "h", 1),
    Variable("desfase_circadiano_h", "Desfase del reloj interno", 0.0, 6.0, 0.5,
             "tu reloj interno está desajustado (16 amaneceres al día en órbita)",
             "tu reloj interno está bien ajustado", "h", 1),
    Variable("luz_brillante_min", "Minutos de luz brillante en tu 'mañana'", 0.0, 180.0, 54.0,
             "recibiste buena luz por la mañana", "recibiste poca luz brillante por la mañana", "min", -1),
    Variable("ejercicio_min", "Ejercicio del día", 0.0, 240.0, 109.0,
             "hiciste bastante ejercicio", "hiciste poco ejercicio", "min", -1),
    Variable("estres", "Estrés percibido", 0.0, 100.0, 29.0,
             "tu estrés está alto", "tu estrés está bajo", "0-100", 1),
)


def logit_riesgo(sueno_h, sueno_media_3d, irregularidad_h, desfase_circadiano_h,
                 luz_brillante_min, ejercicio_min, estres):
    """Regla de riesgo con la que se etiquetan los datos (pesos de ejemplo, supuestos propios).

    Es lineal a propósito: así una regresión logística puede recuperarla y cada
    peso se puede leer y discutir. Los pesos no cambian respecto a la versión 1.0.0;
    lo que cambia es cómo se generan las variables que la alimentan.
    """
    return (
        INTERCEPTO
        + 0.50 * (7.0 - sueno_h)             # menos horas anoche -> más riesgo
        + 0.40 * (7.0 - sueno_media_3d)      # deuda de sueño acumulada
        + 0.60 * irregularidad_h             # horarios cambiantes
        + 0.45 * desfase_circadiano_h        # reloj interno desajustado
        - 0.012 * (luz_brillante_min - 60.0)  # la luz brillante ayuda a ajustar el reloj
        + 0.015 * (estres - 30.0)            # el estrés empeora el sueño
        - 0.003 * (ejercicio_min - 120.0)    # el ejercicio ayuda un poco
    )


# --------------------------------------------------------------------------
# Muestreo con distribuciones acotadas (sin recortar en los bordes)
# --------------------------------------------------------------------------

def _fraccion_mezclada(rng, media, k, prob_cola, media_cola, k_cola):
    """Fracción en [0, 1] con Beta. Una parte de las filas (prob_cola) viene de una
    distribución de casos difíciles: así hay colas, pero sin masas puntuales en los bordes.
    'media' puede ser un vector: una media por fila (así se generan dependencias)."""
    n = len(media)
    en_cola = rng.random(n) < prob_cola
    m = np.clip(np.where(en_cola, media_cola, media), 0.03, 0.97)
    kk = np.where(en_cola, k_cola, k)
    return rng.beta(m * kk, (1.0 - m) * kk)


def _normal_truncada(rng, mu, sd, minimo, maximo):
    """Normal con 'mu' por fila, rechazando lo que cae fuera del rango (sin recortar)."""
    x = rng.normal(mu, sd)
    malos = (x < minimo) | (x > maximo)
    while malos.any():
        x[malos] = rng.normal(np.asarray(mu)[malos] if np.ndim(mu) else mu, sd, malos.sum())
        malos = (x < minimo) | (x > maximo)
    return x


def generar(n: int, semilla: int = SEMILLA):
    """Devuelve (X, y): X con las columnas de VARIABLES e y = 1 si 'riesgo elevado'.

    El orden de generación importa: primero lo que es causa común (estrés, ejercicio, luz,
    reloj) y después lo que depende de eso (sueño, irregularidad, sueño de 3 días).
    """
    rng = np.random.default_rng(semilla)

    # 1) Estrés: fracción de la escala 0-100, con cola de días difíciles.
    f_estres = _fraccion_mezclada(rng, np.full(n, 0.30), 5, 0.08, 0.70, 3)
    estres = f_estres * 100.0

    # 2) Ejercicio: un poco menos cuando hay más estrés.
    f_ejercicio = _fraccion_mezclada(rng, 0.48 - 0.15 * (f_estres - 0.30), 6, 0.08, 0.15, 3)
    ejercicio = f_ejercicio * 240.0

    # 3) Luz brillante por la mañana: sale más en días con más actividad al aire libre.
    f_luz = _fraccion_mezclada(rng, 0.35 + 0.15 * (f_ejercicio - 0.48), 5, 0.08, 0.10, 3)
    luz = f_luz * 180.0

    # 4) Desfase del reloj interno: la mayoría pequeño, con cola.
    f_desfase = _fraccion_mezclada(rng, np.full(n, 0.13), 4, 0.10, 0.40, 2)
    desfase = f_desfase * 6.0

    # 5) Irregularidad del horario: sube con el desfase del reloj.
    f_irregularidad = _fraccion_mezclada(rng, 0.15 + 0.30 * (f_desfase - 0.13), 4, 0.08, 0.45, 2)
    irregularidad = f_irregularidad * 2.5

    # 6) Sueño de anoche: baja con estrés e irregularidad; sube con ejercicio y luz.
    mu_sueno = (7.1 - 0.012 * (estres - 30.0) + 0.003 * (ejercicio - 115.0)
                - 0.30 * (irregularidad - 0.37) + 0.008 * (luz - 63.0))
    sueno = _normal_truncada(rng, mu_sueno, 0.9, 3.0, 9.5)

    # 7) Sueño de 3 días: mezcla del de anoche con el hábito personal del día.
    habito = _normal_truncada(rng, np.full(n, 7.1), 0.5, 3.5, 9.0)
    media_3d = _normal_truncada(rng, 0.6 * sueno + 0.4 * habito, 0.25, 3.5, 9.0)

    X = np.column_stack([sueno, media_3d, irregularidad, desfase, luz, ejercicio, estres])
    y = etiquetar(rng, logit_riesgo(*X.T))
    return X, y


if __name__ == "__main__":
    cli(VARIABLES, generar, SEMILLA)
