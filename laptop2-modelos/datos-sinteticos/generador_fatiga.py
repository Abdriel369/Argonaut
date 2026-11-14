"""Datos sintéticos del especialista de FATIGA Y BIENESTAR (reproducibles, semilla fija).

Rangos y supuestos documentados en SUPUESTOS.md.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # raíz del repo (comun/)

from comun.especialista import Variable  # noqa: E402
from comun.especialista.sintetico import cli, etiquetar, mezcla, positivo  # noqa: E402

SEMILLA = 20262

VARIABLES = (
    Variable("sueno_h", "Horas de sueño de anoche", 3.0, 9.5, 7.2,
             "dormiste bien anoche", "dormiste poco anoche", "h", -1),
    Variable("sueno_media_3d", "Sueño medio de 3 días", 3.5, 9.0, 7.2,
             "llevas varios días durmiendo bien", "llevas varios días durmiendo poco", "h", -1),
    Variable("animo", "Ánimo", 1.0, 5.0, 4.0,
             "tu ánimo está bien", "tu ánimo está bajo", "1-5", -1),
    Variable("estres", "Estrés percibido", 0.0, 100.0, 30.0,
             "tu estrés está alto", "tu estrés está bajo", "0-100", 1),
    Variable("hrv_desv_pct", "Variabilidad del pulso frente a tu normal", -60.0, 30.0, 0.0,
             "tu cuerpo se está recuperando bien", "tu cuerpo muestra señales de poca recuperación", "%", -1),
    Variable("ejercicio_pct_plan", "Ejercicio frente al plan", 0.0, 200.0, 100.0,
             "entrenaste más de lo planeado", "entrenaste menos de lo planeado", "%", 0),
    Variable("ingesta_pct", "Comida frente a lo planeado", 30.0, 120.0, 100.0,
             "comiste lo planeado", "comiste menos de lo planeado", "%", -1),
    Variable("cohesion_equipo", "Cohesión del equipo", 1.0, 5.0, 4.2,
             "el equipo se siente unido", "el equipo se siente distante", "1-5", -1),
    Variable("tiempo_reaccion_ms", "Tiempo de reacción", 200.0, 600.0, 270.0,
             "tus reflejos están más lentos", "tus reflejos están rápidos", "ms", 1),
)


def logit_riesgo(sueno_h, sueno_media_3d, animo, estres, hrv_desv_pct, ejercicio_pct_plan,
                 ingesta_pct, cohesion_equipo, tiempo_reaccion_ms):
    """Regla de riesgo de fatiga (pesos de ejemplo, supuestos propios).

    Incluye una interacción: dormir poco pesa más cuando además hay estrés alto.
    Por eso se usa gradient boosting y no un modelo lineal.
    """
    deuda_sueno = positivo(7.0 - sueno_media_3d)
    return (
        -3.88
        + 0.50 * (7.0 - sueno_media_3d)
        + 0.30 * (7.0 - sueno_h)
        + 0.45 * (4.0 - animo)
        + 0.022 * (estres - 30.0)
        + 0.018 * positivo(-hrv_desv_pct)                 # HRV por debajo de tu normal
        + 0.008 * np.abs(ejercicio_pct_plan - 100.0)      # sobrecarga o sedentarismo
        + 0.020 * positivo(90.0 - ingesta_pct)            # comer poco
        + 0.35 * positivo(3.5 - cohesion_equipo)          # aislamiento y confinamiento
        + 0.006 * positivo(tiempo_reaccion_ms - 280.0)    # reflejos lentos
        + 0.15 * deuda_sueno * positivo((estres - 40.0) / 20.0)   # interacción sueño x estrés
    )


def generar(n: int, semilla: int = SEMILLA):
    rng = np.random.default_rng(semilla)
    sueno = mezcla(rng, n, 3.0, 9.5, 7.0, 1.0)
    media_3d = np.clip(sueno + rng.normal(0.0, 0.6, n), 3.5, 9.0)
    animo = np.clip(np.round(mezcla(rng, n, 1.0, 5.0, 3.8, 0.9)), 1.0, 5.0)
    estres = mezcla(rng, n, 0.0, 100.0, 35.0, 18.0)
    hrv = mezcla(rng, n, -60.0, 30.0, -3.0, 12.0)
    ejercicio = mezcla(rng, n, 0.0, 200.0, 98.0, 22.0)
    ingesta = mezcla(rng, n, 30.0, 120.0, 95.0, 9.0)
    cohesion = mezcla(rng, n, 1.0, 5.0, 4.0, 0.6)
    reaccion = mezcla(rng, n, 200.0, 600.0, 285.0, 35.0)
    X = np.column_stack([sueno, media_3d, animo, estres, hrv, ejercicio, ingesta, cohesion, reaccion])
    y = etiquetar(rng, logit_riesgo(*X.T))
    return X, y


if __name__ == "__main__":
    cli(VARIABLES, generar, SEMILLA)
