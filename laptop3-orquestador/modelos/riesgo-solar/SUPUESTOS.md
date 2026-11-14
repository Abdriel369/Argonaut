# Supuestos del modelo de riesgo solar (Laptop 3)

Datos sintéticos (semilla 20264, 60 000 muestras). Generador: `generador_solar.py`.

| Variable | Rango simulado | Supuesto |
|---|---|---|
| Tasa de dosis ahora | 5–2000 µSv/h | Sin tormenta: lognormal alrededor de 22 µSv/h (tasa habitual). Con tormenta: de 100 a 2000 µSv/h. El 10 % de los casos sin tormenta tiene tasa alta, para que el modelo no dependa solo del aviso. |
| Dosis acumulada | 0–400 mSv | Exponencial de media 45 mSv. Referencia: alrededor de 0.5 mSv/día con tasa baja. |
| Evento solar | sí/no | Ocurre en el 25 % de los casos. Simulado, sin pronóstico real. |
| Pulso en reposo frente a la base | −15 % a +50 % | Señal del cuerpo, solo pesa cuando hay exposición (tormenta o tasa > 100 µSv/h). |
| Temperatura | 35.5–39.5 °C | Idem. |
| SpO2 | 85–100 % | Idem. |

## Regla de etiquetado
Logit con: término logarítmico de la tasa de dosis, bonificación por tormenta, término lineal de la dosis
acumulada y, solo en exposición, pulso y temperatura. La interacción es la razón de usar gradient boosting.

## Límites
- No hay radiobiología ni blindaje del módulo: el modelo estima riesgo a partir de la tasa y la dosis simuladas.
- El evento solar es simulado; no hay pronóstico de clima espacial ni dosímetro real.
- Los umbrales de dosis de las reglas (NASA-STD-3001) deben citarse y verificarse antes de cualquier uso serio.
