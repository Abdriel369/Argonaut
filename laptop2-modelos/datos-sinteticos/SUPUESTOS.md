# Supuestos de los datos sintéticos (Laptop 2)

Ningún dato viene de astronautas ni de pacientes. Se sortean dentro de rangos de referencia y se etiquetan
con una regla de riesgo escrita a mano. Con la misma semilla salen siempre los mismos datos.

Regla general: la mayoría de los valores se concentra cerca de un centro típico (distribución normal) y
una parte (35 %) se reparte por todo el rango, para que el modelo vea también casos raros.
La etiqueta se sortea con probabilidad `sigmoide(regla)`, así que ningún modelo puede acertar el 100 %.

## Sueño (`generador_sueno.py`, semilla 20261, versión 1.1.0)

**Qué cambió respecto a la 1.0.0.** Antes las siete variables se sorteaban de forma independiente,
se recortaban en los bordes y la referencia de cada una no coincidía con sus datos. Ahora:

1. **Orden causal.** Primero estrés, ejercicio, luz y desfase del reloj; después irregularidad, sueño
   de anoche y sueño de 3 días, que dependen de lo anterior.
2. **Dependencias explícitas** (medias por fila, con ruido propio):

| Relación | Efecto supuesto | Correlación resultante |
|---|---|---|
| Estrés → sueño de anoche | −0.012 h por punto de estrés por encima de 30 | sueño–estrés ≈ −0.29 |
| Ejercicio → sueño de anoche | +0.003 h por minuto por encima de 115 | sueño–ejercicio ≈ +0.22 |
| Irregularidad → sueño de anoche | −0.30 h por hora de irregularidad | sueño–irregularidad ≈ −0.13 |
| Luz → sueño de anoche | +0.008 h por minuto por encima de 63 | — |
| Desfase del reloj → irregularidad | sube con el desfase | desfase–irregularidad ≈ +0.26 |
| Estrés → ejercicio | un poco menos ejercicio con más estrés | — |
| Ejercicio → luz brillante | más luz en días con más actividad al aire libre | luz–ejercicio ≈ +0.15 |
| Sueño de anoche + hábito → sueño de 3 días | 60 % anoche, 40 % hábito personal | — |

3. **Sin recortes.** Las variables acotadas usan Beta (y normal truncada para el sueño); no hay masas
   puntuales en 0 ni en el máximo. Una parte de los días (8–10 %) viene de una cola de casos difíciles.
4. **Referencias = medianas de la población sintética**, no valores a ojo: sueño 7.0 h, sueño de 3 días 7.0 h,
   irregularidad 0.3 h, desfase 0.5 h, luz 54 min, ejercicio 109 min, estrés 29.
5. **Prevalencia de riesgo ≈ 12 %** (antes 16.5 %). Se obtuvo ajustando la intersección de la regla a
   −3.374 por bisección con la semilla y el tamaño por defecto. Es un supuesto de diseño: no es una medición.

| Variable | Rango | Referencia (mediana) | Fuente del rango |
|---|---|---|---|
| Horas de sueño de anoche | 3.0–9.5 h | 7.0 h | Supuesto propio, **por verificar** con datos de sueño en tierra y de misión |
| Sueño medio de 3 días | 3.5–9.0 h | 7.0 h | idem |
| Irregularidad de la semana | 0–2.5 h | 0.3 h | Supuesto propio |
| Desfase del reloj interno | 0–6 h | 0.5 h | Supuesto propio. El texto anterior citaba "16 amaneceres al día en órbita (dato del reto)"; **no se ha confirmado en el texto del reto** |
| Luz brillante por la mañana | 0–180 min | 54 min | Supuesto propio |
| Ejercicio | 0–240 min | 109 min | Supuesto propio; compararlo con el plan de contramedidas de la ISS, **por verificar** |
| Estrés | 0–100 | 29 | Escala propia |

**Regla de etiquetado.** Sigue siendo lineal y con los mismos pesos que la 1.0.0 (ver `logit_riesgo`).
Por eso una regresión logística es la clase de modelo adecuada: puede recuperarla. Lo que cambia es la
distribución de las variables que la alimentan.

**Resultados de la 1.1.0 (modelo `modelo-sueno-v1.1.0`, medidos sobre la partición de prueba):**

| Métrica | 1.0.0 | 1.1.0 | Lectura |
|---|---|---|---|
| AUC (mínimo 0.78) | 0.850 | 0.822 | Baja un poco: los datos son más coherentes y algo menos separables |
| Prevalencia | 0.165 | 0.122 | Objetivo de diseño |
| Brier | 0.101 | 0.087 | No es comparable directamente: depende de la prevalencia |
| Skill score (1 − Brier / p(1−p)) | ≈ 0.27 | ≈ 0.18 | Comparable entre prevalencias; baja, con la misma regla |
| Error de calibración esperado | — | 0.011 | Por deciles, predicho ≈ observado en todos los tramos |
| Sensibilidad con corte 0.5 | 0.36 | 0.18 | El producto no usa 0.5: usa los cortes 0.20 / 0.50 / 0.75 |

**Efecto en la demo.** El riesgo de sueño sube en los días de la historia (día 3: 0.25 → 0.31; día 4: 0.42 → 0.52).
El día 4 cruza 0.50 con confianza 0.62 y la fusión sube la alerta de FATIGA a naranja. Por eso la historia
esperada cambió a verde, verde, amarillo, **naranja**, rojo, amarillo, verde. Esto se aceptó de forma explícita;
no se ajustó la calibración para conservar la historia anterior.

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
