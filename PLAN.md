# PLAN · Reloj inteligente + vista de tripulación

> Prototipo con datos simulados. No es una herramienta de diagnóstico médico.

Estado de las fases del encargo. La suite base se midió antes de tocar código:
**254 pruebas pasando** (`python -m pytest -q`). Al cerrar este plan: **304**.

## Fase 0 · Reconocimiento y base

- [x] `git status` y `git log --oneline -5`.
- [x] Lectura de README, FUENTES, contratos y backend de la Laptop 1.
- [x] Suite base: 254 pruebas. Se guardó la salida en `.tmp/pytest_base.log`.
- [x] `PLAN.md` con fases y criterios de aceptación.
- [x] Entorno Windows: los artefactos JSON se normalizaron a LF (sus hashes se
      calculan sobre los bytes) y las pruebas fuerzan CPU en Windows porque el
      driver de esta máquina hace fallar XGBoost al finalizar con CUDA.

## Fase 1 · Multiastronauta y migración

- [x] `astronauta_id` en registros, evaluaciones, alertas, respuestas de modelos,
      informes, pasos de protocolo y check-ins. Clave compuesta `(astronauta_id, dia)`.
- [x] Migración automática con copia previa (`*.pre-multiautonauta-*.bak`); las filas
      antiguas pasan a AST-01.
- [x] Seis perfiles/guiones deterministas en `backend/config/tripulacion.toml`.
      AST-01 conserva `perfil.toml` y `guion_7_dias.toml` sin cambios.
- [x] `reiniciar()` vuelve al día 1 con los seis; `_sembrar_faltantes()` añade los
      cinco nuevos a una base migrada sin borrar el historial de AST-01.
- [x] Pruebas de aislamiento, migración e idempotencia.

## Fase 2 · Tripulación e índice

- [x] `GET /api/tripulacion?dia=N` con cabecera de equipo, filas ordenadas y caché de 30 s.
- [x] `GET /api/tripulacion/{astronauta_id}?dia=N` con orquestador (4 s, sin reintentos)
      y respaldo local indicado en `origen`.
- [x] `POST /api/tripulacion/activo`.
- [x] Fórmula del Anexo B en `backend/aptitud.py`; pesos y topes en configuración.
- [x] Desglose visible, `Model risk` aparte y `null` cuando no hay datos suficientes.
- [x] Filtros, detalle y ayuda "How is this calculated?" en la página principal.
- [x] Pruebas de fórmula exacta, topes, cobertura baja, desempate y degradación.

## Fase 3 · Reloj y proyección

- [x] `POST /api/reloj/lectura` (una lectura o lote), validación contra catálogo,
      idempotencia persistente en `lecturas_reloj` y respuesta compacta.
- [x] `GET /api/reloj/estado?astronauta_id=...` sin llamar al orquestador en cada sondeo.
- [x] Proyección lineal en `calculo.proyeccion_lineal` (mínimos cuadrados, 3 puntos
      mínimos, límites físicos, `dias_para_base` opcional).
- [x] Pruebas de aislamiento, idempotencia, sensores sospechosos y proyección.

## Fase 4 · Interfaz

- [x] Sección **Crew** en `/` con cabecera, filtros, tabla/tarjetas, detalle y ayuda.
- [x] Página `/reloj/` con cinco pantallas, 320 px de ancho, táctil y sin CDN.
- [x] Cola offline en `localStorage` por astronauta, backoff 1–30 s, `needs review`.
- [x] Enlace **Watch** en la navegación y enlace de vuelta al tablero.
- [x] Lógica pura de la cola en `backend/../frontend/reloj/cola.js` y pruebas Node.
- [x] Pruebas de rutas `/reloj/` y de que la interfaz no usa recursos remotos.

## Fase 5 · Documentación y demo

- [x] `README.md`, `laptop1-backend-frontend/README.md`, `contratos/README.md`.
- [x] `SUPUESTOS_TRIPULACION.md` (índice y proyección).
- [x] `DEMO_RELOJ.md`.
- [x] `scripts/arrancar_local.ps1` con los siete procesos.
- [x] `.gitignore` para temporales y respaldos de migración.

## Criterios de aceptación

- [x] `python -m pytest` pasa completo desde la raíz.
- [x] `/` sigue funcionando para AST-01 y muestra la sección Crew.
- [x] `/reloj/` se sirve por la misma aplicación; `/reloj` redirige.
- [x] El reloj envía lecturas, recibe alertas y marca pasos del protocolo.
- [x] La cola offline e idempotencia están cubiertas por pruebas.
- [x] La vista de tripulación muestra los seis, ordenados por preparación.
- [x] Los estados degradados se ven y no rompen la página.
- [x] No hay recursos remotos ni afirmaciones médicas.
- [x] Documentación y `.env.example` al día.
- [x] Comprobación visual con Chrome headless: `/` y `/reloj/` a 1280 px y a
      390/360 px emulados; la tabla Crew carga, el detalle de AST-03 se abre y no
      hay desbordamiento horizontal.
- [ ] El ciclo offline completo con DevTools (offline → recargar → online) no se
      automatizó; la lógica pura y la API sí están cubiertas por Node y pytest.

## Riesgos conocidos

- La demo de la cola offline necesita navegador; el sandbox de este entorno no
  permite abrirlo. Las piezas puras y las rutas sí están probadas.
- El guion de AST-05 no siembra los días 3–7: es intencional para mostrar
  "Not enough data". Al enviar una lectura del reloj en uno de esos días, la
  cobertura sube porque la persona empieza a registrar.
- El índice es una heurística de demo, no una probabilidad calibrada.
