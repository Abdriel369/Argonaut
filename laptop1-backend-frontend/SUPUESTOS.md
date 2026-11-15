# Supuestos de la validación de sensores (Laptop 1)

> **Prototipo con datos simulados. No es una herramienta de diagnóstico médico.**

La validación de sensores corre **antes** del motor de reglas y de los modelos. Código:
`backend/sensores.py`. Límites: `backend/config/sensores.toml`.

**Todos los límites son valores de ejemplo, elegidos por el equipo. No vienen de ninguna norma ni de la ficha
de un sensor real: FUENTE POR CITAR.** Antes de cualquier uso serio hay que sustituirlos por los rangos del
equipo médico y de cada sensor.

## Qué hace

Cada lectura pasa tres chequeos. Si falla uno, queda como **dato sospechoso**:

1. El valor **no se usa**: no entra en la línea base, en las tendencias, en las reglas ni en los modelos.
   Tampoco se sustituye por otro valor. El sistema no inventa datos.
2. A los modelos les llega como dato faltante y lo anotan en `datos_faltantes`.
3. La pantalla muestra un aviso claro, por ejemplo: "El sensor de pulso en reposo parece fallar: marca 250 lpm,
   un valor que no es posible. Revisa el equipo y vuelve a medir."
4. El aviso **no cambia el nivel**. Es un aviso de equipo, no una alerta de salud.

| Chequeo | Qué mira | Clave en `sensores.toml` |
|---|---|---|
| (a) Rango posible | El valor está fuera de lo que el cuerpo o el sensor pueden dar | `minimo`, `maximo` |
| (b) Cambio brusco | La lectura se aleja demasiado de la última lectura válida | `cambio_maximo` |
| (c) Valor congelado | Lleva demasiados días seguidos marcando exactamente lo mismo | `dias_congelado` |

## Límites de ejemplo

| Indicador | Rango posible | Cambio máximo por día | Días congelado |
|---|---|---|---|
| Pulso en reposo | 30–200 lpm | 35 lpm | 4 |
| Variabilidad del pulso (HRV) | 5–200 ms | 45 ms | 4 |
| Temperatura | 32–43 °C | 4 °C | 5 |
| Sueño | 0–24 h | no se aplica | 5 |
| Oxigenación (SpO2) | 50–100 % | no se aplica | no se aplica |
| Ánimo | 1–5 | no se aplica | no se aplica |
| Estrés | 0–100 | no se aplica | no se aplica |
| Ejercicio | 0–600 min | no se aplica | no se aplica |
| Comida | 0–300 % del plan | no se aplica | no se aplica |
| Radiación ahora | 0 µSv/h o más, sin máximo | no se aplica | no se aplica |
| Señales de apoyo (reloj interno, luz, cohesión, reacción, presión, glucosa) | igual que el catálogo | no se aplica | no se aplica |

## Supuestos y por qué

- **Una lectura por día.** El prototipo guarda un valor diario por indicador. "Cambio entre lecturas" significa
  de un día al siguiente y "congelado" se cuenta en días. Con sensores reales, que miden cada pocos segundos,
  estos límites se expresarían por minuto y habría que volver a elegirlos.
- **El rango del sensor es igual o más amplio que el del catálogo** (`indicadores.toml`). Así un dato que el
  backend acepta a mano nunca se marca por rango. Hay una prueba que lo comprueba.
- **Un dato ingresado a mano no pasa los chequeos (b) y (c).** Lo confirmó una persona. Esto da la salida
  natural del aviso: revisar el equipo, medir de nuevo y anotar el valor a mano. Ese valor confirmado sirve
  además de referencia para las siguientes lecturas del sensor.
- **El cambio brusco se compara con dos referencias:** la última lectura válida del sensor y el último dato
  válido de cualquier origen. Solo es sospechosa si se aleja de las dos. Evita marcar una lectura normal
  después de un dato a mano muy distinto.
- **Sin chequeo de cambio brusco donde un cambio rápido es justo lo que hay que ver:**
  - Oxigenación: una caída rápida es una emergencia real. El protocolo de oxigenación ya empieza por
    recolocar el sensor y volver a medir.
  - Radiación: en una tormenta solar la tasa sube mucho en poco tiempo. Tampoco tiene máximo.
  - Sueño, ejercicio, comida, ánimo y estrés: cambian mucho de un día a otro de forma normal.
- **Sin chequeo de valor congelado donde repetir el valor es normal:** oxigenación (resolución de 1 %), ánimo
  (escala de 1 a 5), ejercicio y comida (cumplir el plan exacto), y radiación (el guion simulado usa una tasa
  constante de 21 µSv/h, así que el chequeo daría un falso positivo todos los días).
- **El límite de cambio de la temperatura es amplio (4 °C)** para no ocultar una fiebre real, que puede subir
  rápido.

## Riesgos de estos supuestos

- **Un límite demasiado estricto oculta un cambio real.** Si el pulso de verdad sube 40 lpm de un día a otro,
  la lectura queda como sospechosa hasta que una persona la confirma a mano. Por eso el aviso pide siempre
  revisar el equipo y volver a medir, y se repite cada día mientras dure.
- **Un sensor trabado en un valor creíble no se detecta hasta el día 4 o 5.** Antes de eso es indistinguible
  de un valor estable. Solo un segundo sensor o una medición a mano lo descubrirían antes.
- **El chequeo no distingue un sensor roto de una persona muy enferma en el borde del rango.** Los rangos son
  amplios a propósito para que esto solo ocurra con valores imposibles.

## Qué pasa con las alertas

- **Un sensor roto no puede dar nivel rojo por sí solo.** El dato se aparta antes de las reglas, así que no
  activa ninguna. Las pruebas lo comprueban para cada día del guion y cada indicador.
- **No baja una alerta que depende de otras señales.** Una alerta que no usa ese indicador sigue igual.
- **Sí desaparece la alerta que necesitaba ese dato.** Ejemplo del día 5: sin el pulso no se puede afirmar
  "señales de sobrecarga del corazón"; queda la alerta de variabilidad del pulso, que sí tiene dato. El aviso
  lista las reglas que hoy se evalúan sin ese dato.
- **El especialista al que le falta el dato opina, pero ese día no cambia el nivel.** Ver la nota siguiente.

## Nota sobre la confianza de los modelos

La idea de partida era que un dato faltante bajara la confianza del modelo y que así dejara de subir alertas.
En las pruebas no siempre ocurre: al faltarle el pulso, el modelo cardiovascular lo rellena con un valor sano,
su riesgo se aleja de 0.5 y su confianza (una heurística) **sube**. El día 5 pasa de 0.66 a 0.71 y el día 4 de
0.73 a 0.79.

Los modelos no se tocaron. La protección está en el orquestador
(`sin_voto_con_dato_sospechoso = true` en `laptop3-orquestador/orquestador/config/orquestador.toml`): si hoy
hay un dato sospechoso y a un especialista le faltan datos, su opinión se muestra pero no sube una alerta ni
crea una señal temprana. La regla es conservadora: también deja sin voto a un especialista al que le falte un
dato por otro motivo ese mismo día.

## Simulación del panel de demo

El botón "Simular sensor defectuoso" hace fallar el sensor de pulso en el día actual:

| Tipo | Qué marca el sensor | Chequeo que lo detecta |
|---|---|---|
| Valor imposible | 250 lpm (máximo posible × 1.25) | (a) rango |
| Salto brusco | lectura del día anterior + 60 lpm (cambio máximo × 1.7) | (b) cambio brusco. Necesita un día anterior |
| Valor congelado | el mismo valor durante 4 días, hasta hoy | (c) congelado. Necesita 4 días de misión |

El fallo queda ligado al día en que se activa, igual que el evento solar. Un dato ingresado a mano ese día
tiene prioridad sobre el sensor simulado.
