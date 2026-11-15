# Laptop 1 · backend + interfaz

Laptop 1 es la puerta de entrada del astronauta: sirve la interfaz web, guarda los datos y llama al
orquestador de la Laptop 3. **Datos 100 % simulados.** Prototipo, no es diagnóstico médico.

## Qué hace
- **Seis astronautas simulados y deterministas.** AST-01 conserva su perfil y su guion actuales
  (`backend/config/perfil.toml`, `backend/config/guion_7_dias.toml`). Los otros cinco viven en
  `backend/config/tripulacion.toml` con su propia línea base, plan y guion. La base SQLite tiene clave
  compuesta `(astronauta_id, dia)` y migra automáticamente una base antigua (con copia previa) asignando
  las filas existentes a AST-01.
- **Vista de tripulación (Crew)** en la página principal: cabecera de equipo, filas ordenadas por el índice
  de preparación, filtros, cobertura, tendencia, sparkline y detalle individual con alertas, junta,
  protocolo y calidad del dato.
- **Índice de preparación (Readiness)** calculado solo con reglas locales, con desglose de indicadores,
  plan, seguridad y datos. `Model risk` se muestra aparte y no entra en el índice. Fórmula y límites en
  [`SUPUESTOS_TRIPULACION.md`](SUPUESTOS_TRIPULACION.md).
- **Reloj web simulado en `/reloj/`**: cinco pantallas, lecturas simuladas o editables, envío idempotente,
  alertas y pasos de protocolo, proyección heurística a 24 h y cola offline en `localStorage`.
- **Guion de 7 días** (`backend/config/guion_7_dias.toml`), determinista. Sueño y ánimo decaen, el sistema avisa,
  la astronauta sigue el protocolo y se recupera.
- **Línea base** del perfil simulado "Cdte. Lucía Ferrer" (`backend/config/perfil.toml`). Se recalibra con los dos
  primeros días de adaptación.
- **Validación de sensores** (`backend/sensores.py`, límites en `backend/config/sensores.toml`): corre antes de las
  reglas y de los modelos. Tres chequeos por indicador: rango posible, cambio brusco y valor congelado. Un dato que
  falla queda como "dato sospechoso": no se usa en ningún cálculo, llega a los modelos como dato faltante y la
  pantalla pide revisar el equipo. No cambia el nivel. Supuestos y límites de ejemplo en [`SUPUESTOS.md`](SUPUESTOS.md).
- **Persistencia** en SQLite: registros, evaluaciones, alertas, respuestas de modelos e informes. Exportación a CSV.
- **Modo degradado:** si la Laptop 3 no responde tras los reintentos, evalúa con su copia local del motor de reglas.
- **Controles de demo:** día de misión, reproducir la semana, evento solar, sensor defectuoso (valor imposible, salto
  brusco o valor congelado en el sensor de pulso), enlace con la Tierra, caída de la Laptop 2, reiniciar.

## Arrancar
Con Docker:
```bash
cp .env.example .env     # IP_LAPTOP1, IP_LAPTOP2, IP_LAPTOP3 reales
docker compose up --build
```
Interfaz: `http://IP_LAPTOP1:8100/`. Reloj: `http://IP_LAPTOP1:8100/reloj/`.

En Windows, sin Docker ni bash, desde la raíz del repositorio:
```powershell
.\scripts\arrancar_local.ps1          # siete procesos en 127.0.0.1
.\scripts\arrancar_local.ps1 parar
```

## Variables (`.env`)
| Variable | Para qué |
|---|---|
| `IP_LAPTOP1/2/3` | IP fija de cada laptop en el router |
| `PUERTO_BACKEND` | Puerto de la interfaz (8100) |
| `PUERTO_ORQUESTADOR` | Puerto del orquestador en la Laptop 3 (8300) |
| `URL_ORQUESTADOR` | URL completa del orquestador (`http://IP_LAPTOP3:8300`) |
| `RUTA_BD` | Ruta del SQLite (por defecto `backend/datos/astro_medico.db`) |
| `DIR_FRONTEND` | Carpeta de la interfaz (por defecto `frontend/`) |
| `TIEMPO_MAX_ORQUESTADOR_S` | Espera máxima por el orquestador (8 s) |
| `REINTENTOS_ORQUESTADOR` | Reintentos antes del respaldo local (2) |
| `USAR_GPU` | `auto` (defecto) o `no` para forzar CPU en los modelos |

## Estructura
- `backend/`: API (`principal.py`), servicio (`servicio.py`), cálculo puro (`calculo.py`), índice de
  preparación (`aptitud.py`), validación de sensores (`sensores.py`), persistencia (`bd.py`), cliente del
  orquestador (`cliente_orquestador.py`), pruebas.
- `backend/config/`: `perfil.toml` y `guion_7_dias.toml` (AST-01), `tripulacion.toml` (los seis perfiles
  y los pesos del índice), `indicadores.toml` (catálogo, rangos y paso), `sensores.toml`.
- `frontend/`: HTML, CSS y JavaScript sin compilar. La página principal incluye la sección **Crew**; el
  reloj vive en `frontend/reloj/` (`index.html`, `reloj.css`, `reloj.js`, `cola.js` y sus pruebas Node).
  Tipografías locales en `fuentes/` (SIL OFL 1.1). Ningún recurso remoto.

## Endpoints nuevos

| Ruta | Para qué |
|---|---|
| `GET /api/tripulacion?dia=N` | Vista general: equipo + filas ordenadas. Solo reglas locales. |
| `GET /api/tripulacion/{astronauta_id}?dia=N` | Detalle; orquestador con 4 s y respaldo local indicado. |
| `POST /api/tripulacion/activo` | `{"astronauta_id": "AST-02"}` cambia el astronauta del tablero. |
| `POST /api/reloj/lectura` | Lectura o lote; valida, aplica al día actual, reevalúa y devuelve estado compacto. Idempotente por `lectura_id`. |
| `GET /api/reloj/estado?astronauta_id=AST-01` | Estado compacto del reloj (contrato `estado_reloj`). |
| `GET /reloj/` | Pantalla del reloj; `/reloj` redirige con 307. |

Los contratos están en `../contratos/`: `lectura_reloj`, `respuesta_lectura_reloj`, `estado_reloj`,
`tripulacion` y `detalle_tripulacion`. El CSV añade `astronauta_id`; los informes y la cola de envío
se filtran por astronauta.

## Probar la conexión con la Laptop 3
```bash
python3 ../scripts/verificar_red.py --desde laptop1
```

## Pruebas
Desde la raíz:
```bash
python -m pytest
node frontend/reloj/pruebas/cola.script.mjs   # lógica pura de la cola offline
```
En Windows las pruebas fuerzan `USAR_GPU=no` porque el driver de la máquina de desarrollo hace fallar
XGBoost al cerrar; el funcionamiento normal sigue usando `USAR_GPU=auto`.
