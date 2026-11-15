# Laptop 1 · backend + interfaz

Laptop 1 es la puerta de entrada del astronauta: sirve la interfaz web, guarda los datos y llama al
orquestador de la Laptop 3. **Datos 100 % simulados.** Prototipo, no es diagnóstico médico.

## Qué hace
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
```bash
cp .env.example .env     # IP_LAPTOP1, IP_LAPTOP2, IP_LAPTOP3 reales
docker compose up --build
```
Interfaz: `http://IP_LAPTOP1:8100/`

## Variables (`.env`)
| Variable | Para qué |
|---|---|
| `IP_LAPTOP1/2/3` | IP fija de cada laptop en el router |
| `PUERTO_BACKEND` | Puerto de la interfaz (8100) |
| `PUERTO_ORQUESTADOR` | Puerto del orquestador en la Laptop 3 (8300) |
| `TIEMPO_MAX_ORQUESTADOR_S` | Espera máxima por el orquestador (8 s) |
| `REINTENTOS_ORQUESTADOR` | Reintentos antes del respaldo local (2) |

## Estructura
- `backend/`: API (`principal.py`), servicio (`servicio.py`), cálculo puro (`calculo.py`), validación de
  sensores (`sensores.py`), persistencia (`bd.py`), cliente del orquestador (`cliente_orquestador.py`), pruebas.
- `frontend/`: HTML, CSS y JavaScript sin compilar. Tipografías locales en `fuentes/` (SIL OFL 1.1).
  Ningún recurso remoto.

## Probar la conexión con la Laptop 3
```bash
python3 ../scripts/verificar_red.py --desde laptop1
```
