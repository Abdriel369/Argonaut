# Médico de estación · prototipo para NASA Space Apps Challenge 2026

> **Prototipo con datos simulados. No es una herramienta de diagnóstico médico.**

Reto: *Create Health Monitoring Software for Astronauts on Space Missions* (dificultad intermedia).

**Lema de la demo:** *A 20 minutos de la Tierra, el médico de la estación ya sabe qué hacer.*

Un asistente que vive **dentro** de la estación. Con 20 minutos de retraso no se puede esperar a la Tierra,
así que mide, interpreta y orienta por sí solo. No diagnostica: avisa por **riesgo** y recomienda acciones.
Un orquestador de reglas detecta un posible riesgo, consulta a cuatro modelos especialistas
(sueño, fatiga y bienestar, cardiovascular y riesgo solar) y explica el resultado en lenguaje sencillo
con un protocolo paso a paso y un informe para el cirujano de vuelo.

## Mapa de laptops

| Laptop | Qué corre | Carpeta | Puerto |
|---|---|---|---|
| 1 | Backend (API, SQLite, guion, línea base), interfaz web | `laptop1-backend-frontend/` | 8100 |
| 2 | Gateway + 3 modelos (sueño, fatiga y bienestar, cardiovascular) | `laptop2-modelos/` | 8200 (gateway) |
| 3 | Orquestador (reglas, junta, síntesis) + modelo de riesgo solar | `laptop3-orquestador/` | 8300 (orquestador), 8310 (solar) |

Las tres laptops están en un router propio con IP fija. Cada una corre su propio `docker compose`
y se comunican por HTTP usando las IP de su archivo `.env`. Nada de IP va escrito en el código.

```
Laptop 1 ──HTTP──▶ Laptop 3 orquestador ──HTTP──▶ Laptop 2 gateway ──▶ sueño · fatiga · cardio
 (tablero)          │  reglas → tabla de rutas         (reparte, 3 s por modelo)
                    └──local──▶ riesgo solar (GPU si hay)
 Si la Laptop 2 no responde: MODO DEGRADADO (reglas + solar) y la pantalla lo indica.
 Si la Laptop 3 no responde: la Laptop 1 evalúa con su copia local de las reglas.
```

## Cómo arrancar

En cada laptop, con Docker:

```bash
cd laptop2-modelos        # y luego laptop3-orquestador, laptop1-backend-frontend
cp .env.example .env      # ajustar IP_LAPTOP1/2/3 reales del router
docker compose up --build
```

Orden recomendado: Laptop 2, luego Laptop 3, luego Laptop 1. Interfaz: `http://IP_LAPTOP1:8100/`
(se abre igual desde el celular).

Verificar la red desde cada laptop (no necesita Docker ni internet):

```bash
python3 scripts/verificar_red.py --desde laptop1   # Laptop 1 → Laptop 3 y lo que ve de la 2
python3 scripts/verificar_red.py --desde laptop3   # Laptop 3 → gateway y cada modelo de la 2
```

**Sin las tres laptops (para jueces):** `modo-demo-sin-laptops/arrancar_demo.sh`
(con Docker, o `local` sin Docker). Usa respuestas de modelos grabadas de ejecuciones reales, y la
pantalla lo avisa en todo momento.

**Desarrollo local en una sola máquina** (siete procesos reales, en puertos de 127.0.0.1):
`scripts/arrancar_local.sh` y `scripts/arrancar_local.sh parar`.

## Pruebas

```bash
pip install -r laptop2-modelos/requirements.txt pytest
python3 -m pytest          # desde la raíz (ver el número exacto en la salida)
```

Qué cubren:
- **Contratos:** cada esquema JSON es válido; mensajes incorrectos se rechazan.
- **Reglas:** cada día del guion da el nivel esperado (verde, verde, amarillo, amarillo, rojo, amarillo, verde);
  ventana de adaptación; persistencia; datos faltantes sin romper nada.
- **Orquestador:** enrutamiento por tabla; un especialista solo sube un escalón (nunca baja la regla);
  modo degradado sin especialistas.
- **Cada modelo** (4): AUC mínimo, integridad del artefacto (hash), contrato de salida, factores explicativos,
  comportamiento con datos incompletos, determinismo, API (`/salud`, `/info`, `/predecir`) y reproducibilidad de los datos sintéticos.
- **Backend:** validación de datos, recalibración de la línea base, exposición musculo-hueso, protocolos en el informe,
  enlace con la Tierra, evento solar, caídas y respaldo local.
- **Integración:** la historia completa de 7 días; Laptop 2 apagada; un solo modelo caído; la interfaz sin recursos remotos.
- **Modo demo:** la historia se reproduce igual con respuestas guardadas.

## Datos, supuestos y umbrales

- **Todos los datos son simulados.** Los modelos se entrenan con datos sintéticos generados dentro de rangos
  de referencia públicos (NASA HRP, CSA). Cada generador tiene semilla fija y su documentación de supuestos:
  `laptop2-modelos/datos-sinteticos/SUPUESTOS.md` y `laptop3-orquestador/modelos/riesgo-solar/SUPUESTOS.md`.
- **Las métricas miden que el modelo aprendió la regla sintética**, no su validez clínica.
- Los umbrales y pesos viven en archivos de configuración con comentarios. Son **valores de ejemplo**.
  Antes de cualquier uso serio hay que sustituirlos y citar la fuente.

| Umbral | Valor de ejemplo | Dónde | Fuente sugerida (**por verificar**; no se han comprobado) |
|---|---|---|---|
| Sueño bajo la base | 1 h amarillo, 2.5 h naranja, 3.5 h rojo; persistencia 3 días | `reglas/config/umbrales.toml` | NASA HRP, riesgo de sueño y fatiga |
| Ánimo bajo | 2 puntos (escala 1-5); persistencia 3 días | idem | NASA HRP, salud conductual |
| Estrés alto | 20 / 35 / 55 puntos sobre la base (0-100) | idem | Escala propia del prototipo |
| Ejercicio bajo | 30 % y 50 % bajo el plan; 5 días | idem | Contramedidas de ejercicio en la ISS |
| Pulso en reposo alto | +15 % / +25 % / +40 % | idem | Valores de referencia de NASA HRP |
| HRV baja | −20 % / −35 % / −50 % | idem | Valores de referencia de NASA HRP |
| SpO2 baja | 3 / 5 / 8 puntos bajo la base | idem | Valor de referencia (aprox. 95 %) |
| Temperatura elevada | +0.8 / +1.3 / +2.0 °C | idem | Valor de referencia |
| Comida baja | menos del 75 % del plan (y 60 % en combinación) | idem | NASA HRP, nutrición |
| Radiación ahora | 60 / 200 / 1000 µSv/h | idem | NASA-STD-3001 vol. 1 |
| Radiación acumulada | 50 / 150 / 250 mSv | idem | NASA-STD-3001 vol. 1, límites de exposición |
| Corte de riesgo a nivel | 0.20 / 0.50 / 0.75 | `comun/especialista/nucleo.py` | Escala propia del prototipo |
| Tiempo máximo por modelo | 3 s | `.env` de Laptop 2 y 3 | Diseño del sistema |
| Ventana de adaptación | 2 días, umbrales ×1.5 | `reglas/config/umbrales.toml` | NASA HRP, duración de la adaptación inicial |

Las fuentes de la tabla son pistas para buscar, no citas verificadas. Antes de presentarlas, abrir cada documento y confirmar la cifra. Documentos sugeridos: NASA-STD-3001 (volúmenes 1 y 2); informes de evidencia del NASA Human
Research Program por riesgo; páginas públicas de salud en el espacio de la Agencia Espacial Canadiense (CSA).

## Limitaciones (honestas)

- **No es un diagnóstico.** Avisa por riesgo y recomienda acciones; no sustituye al equipo médico.
- **Datos simulados y sintéticos.** Los rangos son de referencia; los datos de la Tierra y los sintéticos no representan
  por completo el espacio.
- **Presión arterial y glucosa:** no son fiables sin equipo dedicado. Son módulos externos opcionales con datos simulados.
- **Músculo y hueso:** solo es una *exposición estimada* a partir de los días de misión y el ejercicio cumplido. No es una medición.
- **Sistema inmune:** línea futura. Requiere sangre, saliva y orina; no se simula.
- **Radiación:** el evento solar es simulado. No hay pronóstico de clima espacial ni dosímetro real.
- **Confianza:** es una heurística, no una probabilidad calibrada.
- **Protocolos:** son texto de ejemplo, sin dosis de medicamentos. Un protocolo real lo define el equipo médico de la misión.

## Estado de la verificación

- Verificado aquí: todas las pruebas pasan; la historia de 7 días da los niveles del guion; la demo local
  (`arrancar_demo.sh local`) funciona de extremo a extremo; los `docker-compose.yml` tienen sintaxis válida.
- **No verificado aquí:** la construcción de las imágenes Docker y el arranque con `docker compose`. El entorno de
  desarrollo no tiene daemon de Docker. Los Dockerfile siguen la misma estructura de carpetas que usan las pruebas.
- **Por hacer en el sitio:** probar con las tres laptops reales en el router; ajustar IP y puerto en cada `.env`;
  elegir si se usa GPU NVIDIA (ver el bloque comentado de `laptop3-orquestador/docker-compose.yml`).

## Estructura del repositorio

```
contratos/                  esquemas JSON compartidos + ejemplos + pruebas
comun/                      validación, niveles, base de los especialistas, verificación compartida
laptop1-backend-frontend/   backend, frontend (sin CDN), configuración del perfil y del guion
laptop2-modelos/            gateway, 3 modelos, datos sintéticos y supuestos
laptop3-orquestador/        orquestador, reglas, protocolos, modelo de riesgo solar
modo-demo-sin-laptops/      demo en una sola máquina con respuestas grabadas
pruebas-integracion/        pila en memoria, fábrica de entradas, pruebas de integración
scripts/                    verificación de red y arranque local
```

Licencias de las tipografías (SIL OFL 1.1): `laptop1-backend-frontend/frontend/fuentes/`.
