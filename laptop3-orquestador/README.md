# Laptop 3 · orquestador y modelo de riesgo solar

El **orquestador** es la junta médica: las reglas detectan el riesgo, una tabla decide a qué especialistas consultar,
los especialistas opinan, y el orquestador combina todo en una explicación sencilla con protocolo y escalamiento.
El modelo de **riesgo solar** (el más pesado) vive en su propio contenedor, en esta laptop.

**Datos simulados.** Prototipo, no es diagnóstico médico.

## Cómo decide
1. **Reglas en tres niveles** (`reglas/motor.py`, configuración en `reglas/config/umbrales.toml`):
   - por indicador contra la línea base, con persistencia (varios días seguidos fuera de rango suben un escalón);
   - por combinación: FATIGA, AISLAMIENTO, PÉRDIDA MUSCULAR Y ÓSEA, RADIACIÓN, CARDIOVASCULAR, ENERGÍA BAJA;
   - por contexto de misión: ventana de adaptación (días 1-2, umbrales más tolerantes), dosis acumulada.
2. **Enrutamiento por tabla** (`orquestador/config/orquestador.toml`): señal → especialistas. Es una tabla, no un modelo,
   para que sea fiable y explicable.
3. **Consulta** en paralelo: al gateway de la Laptop 2 (sueño, fatiga y bienestar, cardiovascular) y al modelo solar local.
4. **Fusión:** las reglas mandan. Un especialista puede **subir** una alerta un escalón con confianza suficiente;
   nunca la baja. También puede avisar cuando las reglas no ven nada (señal temprana, en amarillo).
5. **Síntesis:** explicación en lenguaje sencillo, protocolo, escalamiento (verde, amarillo, naranja, rojo) e informe
   para el cirujano de vuelo (naranja o superior).

**Datos sospechosos.** Si la entrada trae `sensores_sospechosos` (lecturas que la validación de sensores de la
Laptop 1 apartó), las reglas excluyen esos indicadores y su semáforo queda en "sospechoso". Un sensor roto no activa
ninguna regla y las alertas de otras señales no cambian. El resultado lleva un aviso por cada dato ("El sensor de
pulso en reposo parece fallar... Revisa el equipo") y la lista de reglas que hoy se evalúan sin él. El aviso no cambia
el nivel. Ese día, el especialista al que le falta el dato opina pero no sube alertas
(`sin_voto_con_dato_sospechoso` en `orquestador/config/orquestador.toml`).

**Fuentes de los umbrales.** Cada bloque de `reglas/config/umbrales.toml` lleva un campo `fuente`. El detalle está en
`FUENTES.md`, en la raíz del repositorio.

**Modo degradado:** si el gateway no responde a tiempo, el orquestador sigue con las reglas y el modelo solar local,
marca `modo: "degradado"` y lista los especialistas no disponibles.

## Arrancar
```bash
cp .env.example .env
docker compose up --build
```
Servicios: `orquestador` (puerto 8300) y `modelo-solar` (puerto interno 8310).

## Endpoints del orquestador
- `POST /evaluar`: entrada del orquestador → resultado final (contrato `resultado_final`).
- `GET /red`: estado del gateway de la Laptop 2 y del modelo solar, para el indicador de la interfaz.
- `POST /demo/caida-laptop2`: simula la caída de la Laptop 2 (interruptor del panel de demo).
- `GET /info`, `GET /salud`.

## Modelo de riesgo solar
`modelos/riesgo-solar/`: gradient boosting con 60 000 muestras sintéticas. Combina tasa de dosis, dosis acumulada,
evento solar y señales del cuerpo. Supuestos en `modelos/riesgo-solar/SUPUESTOS.md`.
Reentrenar: `cd modelos/riesgo-solar && python entrenar.py`.

## Probar la conexión con el gateway
```bash
python3 ../scripts/verificar_red.py --desde laptop3
```
