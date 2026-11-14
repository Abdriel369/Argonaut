# Supuestos de los datos sintéticos (Laptop 2)

Ningún dato viene de astronautas ni de pacientes. Se sortean dentro de rangos de referencia y se etiquetan
con una regla de riesgo escrita a mano. Con la misma semilla salen siempre los mismos datos.

Regla general: la mayoría de los valores se concentra cerca de un centro típico (distribución normal) y
una parte (35 %) se reparte por todo el rango, para que el modelo vea también casos raros.
La etiqueta se sortea con probabilidad `sigmoide(regla)`, así que ningún modelo puede acertar el 100 %.

## Sueño (`generador_sueno.py`, semilla 20261)
| Variable | Rango | Referencia | Fuente del rango |
|---|---|---|---|
| Horas de sueño de anoche | 3.0–9.5 h | 7.2 h (línea base) | Rangos de sueño en tierra y resúmenes públicos de vuelos |
| Sueño medio de 3 días | 3.5–9.0 h | 7.2 h | idem |
| Irregularidad de la semana | 0–2.5 h | 0.3 h | Supuesto propio |
| Desfase del reloj interno | 0–6 h | 0.5 h | 16 amaneceres al día en órbita (dato del reto) |
| Luz brillante por la mañana | 0–180 min | 70 min | Supuesto propio |
| Ejercicio | 0–240 min | 120 min | Plan de contramedidas en la ISS |
| Estrés | 0–100 | 30 | Escala propia |

Supuesto clave: la regla es lineal en estas variables (ver `logit_riesgo`); por eso una regresión logística la recupera.

## Fatiga y bienestar (`generador_fatiga.py`, semilla 20262)
Incluye sueño, ánimo (1–5), estrés, variabilidad del pulso frente a la base, ejercicio frente al plan,
comida (30–120 % del plan), cohesión del equipo (1–5) y tiempo de reacción (200–600 ms).
Supuesto clave: **interacción** sueño × estrés (dormir poco pesa más con estrés alto), por eso se usa gradient boosting.

## Cardiovascular (`generador_cardio.py`, semilla 20263)
Incluye pulso en reposo frente a la base, variabilidad, SpO2 (85–100 %), presión sistólica (90–180 mmHg,
módulo externo opcional), sueño medio, ejercicio y día de misión.
Supuesto clave: el efecto del **desplazamiento de fluidos** es mayor en los primeros días (término exponencial en el día de misión).

## Límites de estos supuestos
- Las reglas de etiquetado son supuestos propios, con pesos de ejemplo. No son fisiología validada.
- Los rangos vienen de referencias públicas, pero no se han verificado con datos de misión reales.
- Métricas (AUC, exactitud, sensibilidad) miden si el modelo recupera la regla sintética, no su validez clínica.
