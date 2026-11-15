# PROMPT · Reloj inteligente + vista de tripulación

> Pega este documento completo como instrucción para el agente de IA que va a trabajar en el repositorio.
> Está escrito para el proyecto **Argonaut** (médico de estación, NASA Space Apps 2026). Si el agente no
> tiene el repositorio en su contexto, debe pedir que se lo adjunten antes de escribir código.

---

## 0. Tu papel y las reglas de oro

Actúa como **ingeniero de software senior full-stack** con experiencia en FastAPI, SQLite, JavaScript sin
frameworks y diseño de interfaces accesibles. Vas a ampliar un prototipo que ya funciona; no vas a reescribirlo.

Reglas de oro:

1. **El repositorio manda.** Si este prompt contradice el código, gana el código. Anota la diferencia y
   propón el ajuste antes de romper algo.
2. **No rompas lo que ya funciona.** La suite actual (91 funciones de prueba; el número exacto lo da pytest)
   debe seguir pasando. El guion de 7 días de AST-01, sus niveles esperados y los umbrales no se tocan.
3. **Nada de datos reales ni afirmaciones médicas.** Todo es simulado. No se diagnostica, no se recetan
   dosis, no se dice que alguien es "apto para volar". El índice nuevo es una herramienta de demo.
4. **Todo local.** Sin CDN, sin fuentes remotas, sin analítica, sin servicios externos. La interfaz actual
   ya cumple eso y la nueva también debe cumplirlo.
5. **Entrega por fases y verifica.** Después de cada fase: pruebas, arranque local y una comprobación manual
   en el navegador. No dejes la demo a medias entre fases.

Antes de escribir una línea:

- `git status` y `git log --oneline -5` para ver el estado.
- Lee los archivos de la sección 1.
- Ejecuta la suite y guarda el resultado base.
- Escribe un `PLAN.md` corto con las fases y los criterios de aceptación de la sección 9.

Si trabajas en Windows (el entorno de desarrollo actual), los scripts `.sh` no corren de forma nativa:
usa `python -m pytest` y `python -m uvicorn` directamente, o añade `scripts/arrancar_local.ps1` con los
mismos siete procesos. No exijas bash para probar.

---

## 1. Contexto obligatorio del repositorio

Léelos en este orden. No supongas su contenido.

**Raíz y documentación**
- `README.md` — mapa de las tres laptops, flujo, límites y estado de verificación.
- `FUENTES.md` — de dónde sale cada umbral. No añadas cifras nuevas sin fuente o sin marcarlas como
  "corte de diseño propio".
- `contratos/README.md` — quién envía qué a quién.

**Laptop 1 (backend + interfaz)**
- `laptop1-backend-frontend/README.md`
- `backend/principal.py` — API y montaje de la interfaz.
- `backend/servicio.py` — guion, validación de sensores, línea base, evaluación, informes, demo.
- `backend/bd.py` — esquema SQLite (claves por día; aquí está el cambio grande).
- `backend/calculo.py` — línea base, tendencias, desviaciones, exposición músculo-hueso.
- `backend/sensores.py` — datos sospechosos; corre antes de reglas y modelos.
- `backend/ajustes.py` — variables de entorno y configuración.
- `backend/config/perfil.toml`, `guion_7_dias.toml`, `indicadores.toml`, `sensores.toml`
- `frontend/index.html`, `js/app.js`, `js/vistas.js`, `js/util.js`, `js/i18n.js`, `css/estilos.css`
- `backend/pruebas/test_backend.py`, `test_sensores.py`

**Laptop 2 y Laptop 3**
- `laptop2-modelos/gateway/principal.py`
- `laptop3-orquestador/orquestador/nucleo.py`, `clientes.py`, `sintesis.py`, `informe.py`, `principal.py`
- `laptop3-orquestador/reglas/motor.py`, `reglas/config/umbrales.toml`
- `laptop3-orquestador/orquestador/config/orquestador.toml`
- `laptop3-orquestador/protocolos/protocolos.toml`
- `comun/contratos.py`, `comun/niveles.py`, `comun/especialista/nucleo.py`

**Pruebas e integración**
- `conftest.py`, `pytest.ini`
- `pruebas-integracion/test_integracion.py`, `pila.py`, `fabrica.py`
- `modo-demo-sin-laptops/README.md`, `respuestas-guardadas.json`, `pruebas/test_demo.py`

**Comandos de referencia**
```bash
pip install -r laptop2-modelos/requirements.txt pytest
python -m pytest
./scripts/arrancar_local.sh          # Linux/macOS
./modo-demo-sin-laptops/arrancar_demo.sh local
```

---

## 2. Qué hay que construir

Dos entregables que comparten datos y contratos:

### A. La página del reloj (`/reloj/`)
Una **aplicación web que simula el reloj inteligente** de un astronauta. No es una app nativa ni usa
Bluetooth real: es una pantalla de reloj en el navegador, con datos simulados, que:

- **Recolecta** las lecturas del astronauta (sueño, ánimo, estrés, ejercicio, pulso, HRV, SpO2, temperatura,
  comida) y las **envía** al backend.
- **Recibe** el nivel de riesgo, las alertas y la siguiente acción del protocolo.
- Muestra **monitoreo** (estado de hoy) y **predicción** (riesgo estimado por los modelos + proyección
  heurística de tendencia).
- Funciona **sin conexión**: guarda las lecturas en el dispositivo y las reenvía al volver la red.

### B. La vista de tripulación en la página principal
Una sección nueva (y una ruta de detalle) que muestra:

- **Datos generales de toda la tripulación**: quién está en cada nivel, cuántos verdes/amarillos/naranjas/rojos,
  promedio del índice, cobertura de datos, día de misión.
- **Comparación en porcentajes**: un índice de preparación (readiness) por astronauta, ordenado, con desglose
  visible y una explicación de cómo se calcula.
- **Detalle individual** al hacer clic: indicadores, tendencia de 7 días, alertas, junta de especialistas,
  protocolo y calidad de los datos de ese astronauta.
- Todo con datos simulados y sin afirmar que es una evaluación médica.

La idea de producto: el reloj es el dispositivo del astronauta; la página principal es el tablero del comandante
(o del equipo médico) que ve a toda la tripulación y puede bajar al detalle de una persona.

---

## 3. Decisiones ya tomadas (cámbialas solo con justificación)

1. **Idioma de la interfaz nueva: inglés**, igual que la interfaz actual (`index.html`, `app.js`, `vistas.js`
   están en inglés desde el último commit). Los textos que el backend devuelve en español se traducen en
   `frontend/js/i18n.js`, como ya se hace. Añade ahí las cadenas nuevas. No traduzcas el backend.
   Si el equipo decide demostrar en español, es un cambio solo de cadenas; la lógica no cambia.
2. **Seis astronautas.** AST-01 (Cdte. Lucía Ferrer) conserva **exactamente** su perfil, su guion y sus niveles
   actuales. Los otros cinco son ficticios, con perfiles y guiones deterministas (ver Anexo A).
3. **El índice de preparación se calcula con las reglas locales**, no con los modelos, para que sea rápido,
   comparable y reproducible. La opinión de los modelos se muestra aparte y **no** entra en el índice.
   Fórmula exacta en el Anexo B.
4. **El reloj es una simulación web**, no un dispositivo real. Debe decirlo en pantalla. Los botones de
   "medir" generan valores simulados con semilla fija y ruido pequeño alrededor de la línea base; la persona
   también puede escribirlos o corregirlos.
5. **La predicción no es un modelo nuevo.** Es (a) el riesgo de los especialistas que ya existen y (b) una
   proyección lineal simple sobre los últimos días, marcada como heurística. No inventes un modelo de IA nuevo.
6. **Sin dependencias nuevas de frontend.** HTML, CSS y JavaScript con módulos ES, como ahora.
   En Python, usa la pila existente (FastAPI, httpx, jsonschema, numpy, scikit-learn/XGBoost) y la
   biblioteca estándar. Si crees que necesitas algo más, justifícalo y pide permiso.
7. **La compatibilidad es requisito.** Las rutas y contratos actuales siguen funcionando; los nuevos campos
   son opcionales o tienen valor por defecto `AST-01`.

---

## 4. Alcance A · Página del reloj

### 4.1 Ruta y estructura

- Archivo: `laptop1-backend-frontend/frontend/reloj/index.html`, con `reloj.css` y `reloj.js` en la misma
  carpeta o en `frontend/js/reloj.js`.
- La interfaz se monta con `StaticFiles(..., html=True)` en `/`. Comprueba que `/reloj/` sirve el
  `index.html`; si `/reloj` sin barra no redirige, añade una ruta explícita en `backend/principal.py`
  antes del montaje. La barra de navegación principal debe tener un enlace "Watch" que abra `/reloj/`.
- Usa rutas relativas desde `/reloj/` (`../css/estilos.css`, `../js/util.js`) y comprueba que no haya 404.
- Sin build, sin framework, sin CDN. Reutiliza las variables CSS de `estilos.css`:
  `--noche`, `--vidrio`, `--borde`, `--tinta`, `--acento`, `--verde`, `--amarillo`, `--naranja`, `--rojo`,
  `--sin-dato`, `--texto`, `--cifras`, `--radio`, `--toque`.
- Reutiliza `frontend/js/util.js` (`esc`, `icono`, `insignia`, `TEXTO_NIVEL`) para los niveles y los iconos.
  Cada nivel debe tener **forma + texto + color**, nunca solo color.
- La pantalla debe verse bien en una ventana de 320×320 px (marco de reloj redondeado en escritorio) y
  ocupar el ancho completo en un teléfono. Objetivos táctiles de al menos 44×44 px.

### 4.2 Pantallas del reloj

Cinco pantallas, navegables con puntos o botones inferiores. Una sola idea por pantalla.

1. **Today** (inicio)
   - Nombre y rol del astronauta, día de misión, hora local.
   - Píldora de conexión: `Station online` / `Offline · N saved` / `Degraded`.
   - Nivel global grande: icono + palabra (`Normal`, `Attention`, `Alert`, `Critical`) + porcentaje de riesgo.
   - "What to do now": la primera acción pendiente del protocolo de la alerta principal.
   - Botón `Done` (marca el paso) y botón `See all`.
   - Pie permanente y visible: `Simulated data. Not a medical diagnosis.`

2. **Measure**
   - Campos agrupados: sueño, ánimo, estrés, ejercicio, pulso, HRV, SpO2, temperatura, comida.
   - Cada campo con unidad, rango permitido y paso, tomados de `indicadores.toml` (no los escribas a mano).
   - Botón `Measure now`: rellena pulso, HRV, SpO2 y temperatura con una lectura simulada plausible
     (ruido pequeño y determinista alrededor de la línea base). Marca el campo como "simulated".
   - Botón `Send`: envía el lote. Muestra `Sending…`, `Saved on watch` o `Sent`.
   - Si el backend rechaza un valor, muestra el mensaje exacto y deja corregirlo; no pierdas lo escrito.

3. **Alert**
   - Alerta principal: título, nivel, causa en lenguaje sencillo y consecuencia.
   - Pasos del protocolo con casillas; el paso marcado se envía a `POST /api/protocolo/paso`.
   - Botón `Remind me in 15 min` (cuenta atrás local, sin servidor).
   - Si no hay alertas: `All clear` con la explicación global.

4. **Trend**
   - Tres mini-gráficas de 7 días: sueño, pulso en reposo y HRV (o los que el backend marque como
     `principales`).
   - Debajo, la proyección a 24 h: "If this continues…" con el valor estimado y la dirección.
   - Etiqueta: `Heuristic projection from the last days. Not a diagnosis.`

5. **My watch**
   - Astronauta emparejado (selector solo en modo demo; ver 6.2).
   - Batería y señal simuladas, última sincronización, lecturas en cola, botón `Sync now`.
   - Botón `Open full dashboard` (vuelve a `/`).
   - Nota de simulación y versión.

### 4.3 Captura y envío

- Los valores se mapean **solo** a indicadores existentes del catálogo. No inventes indicadores nuevos.
- Respeta `editable` de `indicadores.toml`: el reloj no puede escribir `dosis_acumulada_msv`,
  `cohesion_equipo`, `tiempo_reaccion_ms`, presión ni glucosa.
- Cada lectura lleva: `lectura_id` (UUID del cliente), `astronauta_id`, `capturado_en` (ISO 8601),
  `origen` (`"reloj-simulado"`), `indicadores` (solo los enviados).
- El envío es **idempotente**: reenviar el mismo `lectura_id` no duplica ni vuelve a evaluar dos veces.
- Después de un envío correcto, el reloj refresca su estado con la respuesta compacta; no vuelve a pedir
  `/api/estado` completo.

### 4.4 Recepción de alertas y sugerencias

- El reloj hace `GET /api/reloj/estado?astronauta_id=...` cada 5 s, y **pausa** el sondeo cuando la
  pestaña está oculta (`document.visibilityState`). Al volver, refresca una vez.
- La respuesta es compacta (ver Anexo D). No llames a `/api/estado` desde el reloj: es pesada.
- Si el reloj está sin conexión, muestra el último estado cacheado con la marca `Offline` y la hora.
- Una alerta nueva debe anunciarse con `aria-live="polite"` y un cambio visual; nada de solo vibración.
- El reloj **sugiere**, no ordena: textos como "Next step" o "Suggested action", nunca "You must".

### 4.5 Modo sin conexión

- Cola en `localStorage`, una por astronauta, con un máximo razonable (por ejemplo 20 lecturas).
- Al enviar: si falla la red, guarda la lectura y muestra `Saved on watch`.
- Reintento con backoff exponencial (1 s, 2 s, 4 s… máximo 30 s) y al evento `online`.
- Si el servidor responde 4xx (dato inválido), **no** reintentes para siempre: marca la lectura como
  `needs review`, muéstrala en "My watch" y permite corregirla o descartarla.
- Si hay varias lecturas del mismo día, el servidor aplica la última y conserva el histórico de
  evaluaciones; no borres datos en silencio.
- La cola debe sobrevivir a recargar la página.

### 4.6 Predicción y tendencia

El backend calcula la proyección; el reloj solo la pinta. Para `sueno_h`, `fc_reposo`, `hrv` y `estres`:

- Toma hasta los últimos 7 valores válidos (ignora `null` y sospechosos).
- Ajusta una recta por mínimos cuadrados con el índice del día como `x`.
- Devuelve: `valor_24h`, `direccion` (`sube`/`baja`/`estable`), `pendiente`, `dias_para_base` (si la
  pendiente se acerca a la línea base y el cruce cae en un horizonte razonable; si no, `null`),
  `metodo` (`"regresión lineal simple, últimos 7 días"`) y `aviso`.
- Si hay menos de 3 puntos válidos, devuelve `null` y el reloj muestra `Not enough data to project`.
- Redondea con los decimales del catálogo y nunca proyectes fuera del rango físico del indicador.
- El texto siempre dice que es una proyección heurística, no un pronóstico médico.

---

## 5. Alcance B · Vista de tripulación en la página principal

### 5.1 Datos y datos generales

La vista debe mostrar, para el día seleccionado:

- **Cabecera de equipo**: día de misión, número de astronautas, reparto por nivel (verde/amarillo/naranja/rojo),
  promedio del índice de preparación, mejor y menor índice, indicador más débil del equipo y cobertura
  media de datos.
- **Tarjetas o tabla por astronauta**: posición, nombre, rol, nivel (icono + texto), índice de preparación
  en porcentaje con barra, cobertura de datos, tendencia (flecha) y una sparkline de 7 días.
- **Filtros**: `All`, `With alerts` (amarillo o peor), `Incomplete data`. Orden por índice descendente;
  desempate por cobertura y luego por nombre.
- **Detalle individual** al hacer clic: panel o modal con indicadores, tendencia, alertas, junta de
  especialistas, protocolo, datos sospechosos y una nota de calidad. Debe ser claro si el detalle viene
  del orquestador (con modelos) o del respaldo local (solo reglas).
- Un botón de ayuda `How is this calculated?` que abre el desglose de la fórmula y sus límites.

No inventes fotos ni avatares remotos: usa iniciales o un icono local.

### 5.2 Índice de preparación (porcentaje)

- Clave interna: `preparacion_pct` (0–100, entero). Etiqueta UI: `Readiness`.
- Se calcula con las **reglas locales** para los seis astronautas: rápido, comparable y reproducible.
- Fórmula, pesos, topes y caso "sin datos suficientes": **Anexo B**. Los pesos viven en configuración
  (`backend/config/tripulacion.toml` o `aptitud.toml`), no en el código.
- Muestra siempre el **desglose**: indicadores, plan, seguridad y calidad de datos, cada uno en porcentaje
  y con su peso.
- Muestra aparte `Model risk` (máximo riesgo de los especialistas, si está disponible) y aclara que **no**
  entra en el índice. En la tabla general se muestra `—` cuando no se consultaron modelos para ese
  astronauta.
- Si `cobertura < 0.5`, `preparacion_pct = null` y la fila dice `Not enough data`; no la ordenes como si
  tuviera un cero. Si el equipo quiere una posición, ponla al final y con la etiqueta, nunca un 0 engañoso.
- Redondeo: entero. No muestres decimales en la tabla; el desglose puede mostrarlos.

### 5.3 Lenguaje y ética del ranking

- No uses "apto", "no apto", "enfermo", "sano", "capacidad médica" ni "riesgo de muerte".
- Usa `Readiness`, `Indicators`, `Plan adherence`, `Safety`, `Data quality`, `Team view`.
- Nota visible: `Prototype readiness index built from simulated data. It is not a medical evaluation or a
  fitness-for-duty decision.`
- El ranking es una herramienta de demo para comparar; no debe usarse para excluir a nadie.
- Si un astronauta tiene datos incompletos, dilo antes que su porcentaje.

---

## 6. Backend y datos

### 6.1 Multiastronauta

Hoy el sistema es de un solo astronauta y la base está indexada por día. Hay que ampliarlo sin romper
AST-01:

- Añade `astronauta_id` a registros, evaluaciones, alertas, respuestas de modelos, pasos de protocolo y
  check-ins. Clave primaria compuesta `(astronauta_id, dia)`.
- Conserva firmas compatibles con valor por defecto `"AST-01"` en `bd.py` y `servicio.py` para no tener que
  tocar todas las llamadas existentes de golpe.
- Migración automática al arrancar: si detectas el esquema viejo, migra las filas a `"AST-01"`. Si la
  migración no es viable, crea una base nueva **solo** después de copiar la anterior y documenta que el
  historial de demo se reinicia una vez. Nunca borres la base sin copia.
- `_cargar_guion()` debe sembrar los seis astronautas; `reiniciar()` debe reiniciarlos a todos y volver al
  día 1.
- El astronauta "activo" (el que muestra el tablero principal) se guarda en estado y por defecto es
  `AST-01`. Cambiarlo es una acción de demo. El reloj puede emparejarse con cualquier astronauta del
  roster; no está limitado al activo.
- Valida el `astronauta_id` contra el roster: desconocido → 422 con mensaje claro, nunca 500.

### 6.2 Endpoints nuevos (puedes ajustar nombres si documentas el contrato)

- `GET /api/tripulacion?dia=N`
  Devuelve roster + datos generales + filas ordenadas. Solo reglas locales; no llama al orquestador.
- `GET /api/tripulacion/{astronauta_id}?dia=N`
  Detalle individual. Intenta el orquestador (evaluación completa con especialistas) con timeout ≤4 s;
  si no responde, cae al respaldo local y lo indica con `origen: "respaldo-local"`. No reutilices los
  8 s × 3 intentos del flujo principal para un clic de detalle.
- `POST /api/tripulacion/activo` `{ "astronauta_id": "AST-02" }`
  Cambia el astronauta que muestra el tablero principal (solo demo). Devuelve el estado nuevo.
- `POST /api/reloj/lectura`
  Recibe una lectura o un lote pequeño, valida, aplica al día actual de ese astronauta, reevalúa y
  devuelve el estado compacto del reloj. Idempotente por `lectura_id`.
- `GET /api/reloj/estado?astronauta_id=AST-01`
  Estado compacto para el reloj (Anexo D), para cualquier astronauta del roster. Si no hay evaluación
  guardada de ese astronauta/día, calcula una (orquestador con timeout corto; si no, reglas locales).
- `GET /api/reloj/cola` no hace falta: la cola vive en el cliente. Si añades endpoints de diagnóstico,
  documéntalos y no los enlaces desde la interfaz.

Todos los endpoints nuevos validan entrada y salida con `comun.contratos.validar`.

### 6.3 Contratos

- Añade esquemas en `contratos/`: `lectura_reloj.schema.json`, `estado_reloj.schema.json`,
  `tripulacion.schema.json` (o `respuesta_tripulacion.schema.json`).
- Actualiza `comun/contratos.py` (`NOMBRES`), `contratos/README.md`, `contratos/ejemplos/` y
  `contratos/pruebas/test_contratos.py`.
- Los contratos existentes no cambian de forma incompatible. Si añades campos, que sean opcionales o con
  `default`.
- `resultado_final` puede ganar `astronauta_id` opcional; no lo hagas obligatorio para no romper la demo
  guardada.

### 6.4 Persistencia y exportación

- El CSV (`/api/exportar.csv`) debe incluir la columna `astronauta_id` y seguir funcionando con el
  astronauta activo si no se pide otro.
- Los informes para el cirujano de vuelo deben llevar el astronauta y no mezclar tripulantes.
- La cola de informes pendientes y el enlace con la Tierra se mantienen por astronauta.
- Guarda los `lectura_id` aplicados en una tabla (o en `estado`) para que la idempotencia sobreviva a un
  reinicio del backend; no la dejes solo en memoria.

### 6.5 Rendimiento y degradación

- La vista de tripulación debe responder en menos de **3 s** con caché caliente. Cachea el resultado por
  `(astronauta_id, dia, hash de los datos)` con TTL de 30–60 s; invalida al cambiar datos o de día.
- La vista general usa el motor de reglas local (`reglas.evaluar`), no seis llamadas al orquestador.
  Si decides enriquecer con modelos, hazlo en paralelo, con timeout de 2.5 s y resultados parciales;
  nunca bloquees la tabla entera por un astronauta.
- Reutiliza `servicio.construir_entrada` (parametrizado por astronauta) para armar la entrada; no
  dupliques el cálculo de línea base, desviaciones y tendencias.
- El reloj no debe provocar una evaluación completa en cada sondeo de 5 s: sirve el último resultado
  guardado y reevalúa solo cuando llega una lectura o cuando se marca un paso.
- Si el orquestador está caído, la vista general sigue funcionando con reglas y muestra `Degraded`.
  Si la Laptop 2 está caída, el detalle individual lo indica.
- Nada de `asyncio.gather` sin control de errores: un astronauta que falla no tumba a los demás.

### 6.6 Seguridad y robustez

- Valida números con `calculo.es_numero` (nada de `bool`), límites del catálogo y `astronauta_id` del roster.
- Rechaza indicadores desconocidos o no editables con 422 y mensaje en lenguaje sencillo.
- No concatenes SQL con datos del usuario; usa parámetros.
- No registres en logs datos personales innecesarios; los ids y los valores bastan.
- Los endpoints nuevos no deben permitir escribir en días pasados; el reloj solo escribe el día actual
  del astronauta con el que está emparejado.

---

## 7. Restricciones técnicas y de producto

- **No cambies** los umbrales de `umbrales.toml`, los protocolos, los artefactos de los modelos, el guion de
  AST-01 ni los niveles esperados de la demo.
- **No añadas** servicios, contenedores, bases de datos externas ni dependencias de frontend.
- **No uses** `localStorage` para datos sensibles reales; aquí es una demo con datos simulados.
- **No rompas** la exportación CSV, el enlace con la Tierra, el evento solar, el sensor defectuoso ni el
  botón de reinicio.
- **Accesibilidad**: etiquetas `label`, `aria-live` para alertas y estados, foco visible, navegación con
  teclado, contraste suficiente, `prefers-reduced-motion`, nada de solo color.
- **Responsive**: el reloj a 320×320 y en teléfono; la vista de tripulación en una columna en móvil y en
  tabla/tarjetas en escritorio.
- **Determinismo**: los seis astronautas deben dar los mismos valores para el mismo día y la misma semilla.
- **Estilo del repo**: comentarios y docstrings en español, nombres de variables en español cuando el
  archivo ya lo hace; textos de UI en inglés y centralizados.
- **Documentación**: actualiza `README.md` (mapa, cómo abrir `/reloj/`, vista de tripulación), `contratos/README.md`,
  `laptop1-backend-frontend/README.md` y añade `SUPUESTOS.md` para el índice y la proyección. Si añades
  variables de entorno, actualiza `.env.example`.

---

## 8. Pruebas exigidas

Añade pruebas nuevas; no borres ni debilites las existentes. Como mínimo:

**Contratos**
1. Los esquemas nuevos son JSON Schema válidos.
2. Los ejemplos nuevos cumplen su contrato.
3. Un `lectura_id` que falta o un `astronauta_id` desconocido se rechazan.
4. Un indicador desconocido o no editable se rechaza.
5. Un valor fuera de rango se rechaza con 422 y mensaje claro.

**Reloj / backend**
6. Una lectura del reloj actualiza solo a ese astronauta; los demás no cambian.
7. Reenviar el mismo `lectura_id` no duplica ni reevalúa dos veces (idempotencia).
8. Una lectura del reloj respeta la validación de sensores: un valor imposible no activa reglas y genera aviso.
9. `GET /api/reloj/estado` cumple el contrato y no llama al orquestador en cada consulta.
10. La proyección devuelve `null` con menos de 3 puntos y valores razonables con una serie fija.

**Tripulación / índice**
11. La fórmula del Anexo B da el resultado exacto con un fixture fijo (desglose incluido).
12. Los topes por alerta roja/naranja se aplican.
13. `cobertura < 0.5` produce `preparacion_pct = null` y la fila no se ordena como cero.
14. El desempate por cobertura y nombre funciona.
15. La vista general funciona con el orquestador caído (reglas locales) y lo indica.
16. Un astronauta que falla no impide ver a los demás.

**Compatibilidad e interfaz**
17. Las 91 pruebas actuales siguen pasando.
18. La historia de 7 días de AST-01 da los mismos niveles.
19. `test_la_interfaz_no_usa_recursos_remotos` (ya recorre todo `frontend/`) sigue pasando con
    `reloj/index.html`, `reloj.css` y `reloj.js`.
20. La migración de la base conserva el historial de AST-01 (o lo documenta si se recrea).

**Manual (descríbelo en el reporte)**
21. Abrir `/reloj/`, medir, enviar, ver alerta, marcar un paso y comprobar que aparece en el informe.
22. Poner el navegador en offline, enviar, recargar, volver a online y comprobar que se sincroniza una sola vez.
23. Abrir la vista de tripulación, ordenar, filtrar, entrar al detalle de dos astronautas y volver.
24. Reiniciar la demo y comprobar que vuelve al día 1 con los seis astronautas.

Si no hay un runner de JavaScript, extrae la lógica pura de la cola y la proyección a módulos que se puedan
probar con Node (`node --test`) o con un script pequeño; documenta el comando. No dejes lógica crítica sin
prueba solo porque es JS.

---

## 9. Criterios de aceptación (definición de terminado)

- [ ] `python -m pytest` pasa completo desde la raíz.
- [ ] `/` sigue funcionando igual para AST-01 y muestra la sección **Crew**.
- [ ] `/reloj/` funciona en escritorio y en móvil, sin errores de consola ni 404.
- [ ] El reloj envía lecturas, recibe alertas y marca pasos del protocolo.
- [ ] La cola offline funciona y es idempotente.
- [ ] La vista de tripulación muestra los seis, ordenados por `preparacion_pct`, con desglose y detalle.
- [ ] Los estados degradados (sin Laptop 2, sin Laptop 3) se ven y no rompen la página.
- [ ] No hay recursos remotos ni afirmaciones médicas.
- [ ] La documentación y `.env.example` están al día.
- [ ] El reporte final explica qué cambió, cómo probarlo y qué límites quedan.

---

## 10. Entregables y forma de reportar

1. Código y pruebas en el repositorio, con commits pequeños y mensajes claros.
2. `PLAN.md` con las fases y su estado.
3. `DEMO_RELOJ.md` con un guion de demo de 2–3 minutos: qué abrir, qué pulsar, qué debe verse.
4. Al terminar, un reporte con:
   - archivos creados y modificados;
   - decisiones tomadas y su porqué;
   - resultados de las pruebas (número exacto);
   - cómo arrancar en local (Windows y Linux/macOS);
   - límites conocidos y lo que no se pudo verificar.
5. No hagas commit de bases de datos generadas, artefactos temporales, capturas ni secretos.

---

## Anexo A · Tripulación simulada (puedes ajustar nombres y valores, no el reparto de casos)

| ID | Nombre | Rol | Perfil de la semana | Para qué sirve en la demo |
|---|---|---|---|---|
| AST-01 | Cdte. Lucía Ferrer | Comandante | El guion actual: verde, verde, amarillo, naranja, rojo, amarillo, verde | Historia principal; no se toca |
| AST-02 | Mateo Ríos | Piloto | Rinde alto; duerme y entrena bien; un pico de estrés el día 5 | Mejor índice; comparación |
| AST-03 | Aisha Ndiaye | Ingeniera de vuelo | Sueño y ánimo bajan; naranja hacia el día 5; se recupera | Curva descendente y recuperación |
| AST-04 | Tomás Vega | Oficial médico | Estable en verde; un sensor sospechoso el día 3 | Mostrar datos sospechosos sin romper el nivel |
| AST-05 | Hana Sato | Científica | Faltan días de registro (cobertura baja) | "Not enough data", no un cero |
| AST-06 | Diego Salas | Especialista de misión | Poco ejercicio y poca ingesta; rojo o naranja varios días | Peor índice; alertas de energía y músculo |

Reglas:

- Los seis tienen línea base pre-vuelo propia y plan de ejercicio propio.
- Los guiones son listas de 7 valores o se generan con semilla fija; el mismo día siempre da lo mismo.
- AST-01 conserva `perfil.toml` y `guion_7_dias.toml` actuales, sin cambios de valores.
- Para AST-05, define días sin registro y no los siembres; el resto del sistema ya trata `None` como
  "sin dato".
- Los nombres son ficticios; no uses personas reales ni datos personales.

---

## Anexo B · Fórmula del índice de preparación

Para el astronauta `a` en el día `d`:

```
cobertura = días_con_datos / d

C_indicadores = media de puntaje(indicador) para los indicadores principales con dato
  puntaje: verde 100 · amarillo 60 · naranja 25 · rojo 0
  principales: sueno_h, animo, estres, ejercicio_min, fc_reposo, hrv

C_plan = 100 × (0.40 × min(1, sueno_h / base_sueno)
              + 0.30 × min(1, ejercicio_min / plan_ejercicio)
              + 0.30 × min(1, ingesta_pct / 100))

C_seguridad = 100 × (1 − riesgo_reglas)
  riesgo_reglas = { verde: 0.00, amarillo: 0.25, naranja: 0.55, rojo: 0.85 }[peor nivel de las reglas]

C_datos = 100 × (0.70 × cobertura + 0.30 × (1 − min(1, sospechosos_hoy / 3)))

preparacion = 0.40 × C_indicadores
            + 0.25 × C_plan
            + 0.20 × C_seguridad
            + 0.15 × C_datos

si hay alerta roja:   preparacion = min(preparacion, 45)
si hay alerta naranja: preparacion = min(preparacion, 70)
si cobertura < 0.5:   preparacion = null, estado = "sin_datos_suficientes"
```

Notas:

- `sospechosos_hoy` es el número de datos marcados como sospechosos ese día para ese astronauta.
- Si faltan más de 2 de los 6 indicadores principales en el día, `preparacion = null` y
  `estado = "sin_datos_suficientes"`.
- Si falta un término de `C_plan` (sueño, ejercicio o ingesta), usa el promedio de los términos
  disponibles; no inventes el valor que falta.
- `Model risk` se muestra aparte: máximo `riesgo` de los especialistas con `confianza >= 0.60`. No entra
  en `preparacion`.
- Los pesos y los topes viven en configuración; si los cambias, actualiza este anexo y la UI.
- El índice es una **heurística de demo**, no una probabilidad calibrada ni una evaluación médica.

---

## Anexo C · Endpoints existentes que debes reutilizar

Laptop 1:

```text
GET  /api/estado
GET  /api/red
GET  /api/historial
GET  /api/informes
GET  /api/exportar.csv
POST /api/registro                    {"indicadores": {...}}
POST /api/checkin/animo               {"valor": 1..5}
POST /api/checkin/reaccion            {"tiempos_ms": [...]}
POST /api/checkin/equipo              {"comunicacion":1..5,"conflictos":1..5,"carga":1..5}
POST /api/protocolo/paso              {"alerta_id":"...","paso_id":"...","hecho":true}
POST /api/reevaluar
POST /api/demo/dia                    {"dia": 1..7}
POST /api/demo/evento-solar           {"activo": true|false}
POST /api/demo/sensor-defectuoso      {"activo":true,"tipo":"imposible|salto|congelado"}
POST /api/demo/caida-laptop2          {"activa": true|false}
POST /api/demo/enlace-tierra
POST /api/demo/reiniciar
```

Laptop 3:
```text
POST /evaluar                         entrada_orquestador -> resultado_final
GET  /red
GET  /info
POST /demo/caida-laptop2
```

No dupliques lógica que ya existe en `servicio.py` o `reglas/motor.py`: reutilízala.

---

## Anexo D · Payloads de ejemplo

`POST /api/reloj/lectura`

```json
{
  "lectura_id": "8d1f3c2a-7b44-4f0e-9a51-2c6d8e1b7a30",
  "astronauta_id": "AST-01",
  "capturado_en": "2026-11-15T16:05:00Z",
  "origen": "reloj-simulado",
  "indicadores": {
    "sueno_h": 6.8,
    "animo": 4,
    "estres": 38,
    "ejercicio_min": 110,
    "fc_reposo": 64,
    "hrv": 50,
    "spo2": 98,
    "temperatura": 36.6
  }
}
```

Respuesta:

```json
{
  "aceptado": true,
  "lectura_id": "8d1f3c2a-7b44-4f0e-9a51-2c6d8e1b7a30",
  "astronauta_id": "AST-01",
  "dia_mision": 6,
  "nivel_global": "amarillo",
  "estado_reloj": { "...": "mismo objeto que GET /api/reloj/estado" }
}
```

`GET /api/reloj/estado?astronauta_id=AST-01`

```json
{
  "astronauta": {"id": "AST-01", "nombre": "Cdte. Lucía Ferrer", "rol": "Comandante"},
  "dia_mision": 6,
  "actualizado": "2026-11-15T16:05:03Z",
  "conexion": {"orquestador": true, "modelos": true, "modo": "completo"},
  "nivel_global": "amarillo",
  "riesgo_pct": 42,
  "explicacion": "You are sleeping less than usual.",
  "alerta_principal": {
    "id": "SUENO_BAJO",
    "titulo": "You are sleeping less than usual",
    "nivel": "amarillo",
    "causa": "You slept 6.8 h (your normal is 7.1 h)...",
    "protocolo_id": "sueno",
    "siguiente_paso": {"id": "s1", "texto": "Finish demanding tasks 2 hours before bed."}
  },
  "alertas": [],
  "tendencia": {"sueno_h": [7.1, 6.4, 5.6, 5.2, 5.0, 6.8], "fc_reposo": [], "hrv": []},
  "proyeccion": [
    {
      "indicador": "sueno_h",
      "valor_24h": 6.9,
      "direccion": "sube",
      "pendiente": 0.21,
      "dias_para_base": 1,
      "metodo": "regresión lineal simple, últimos 7 días",
      "aviso": "Heuristic projection. Not a diagnosis."
    }
  ],
  "datos_sospechosos": [],
  "aviso": "Simulated-data prototype. Not a medical diagnostic tool."
}
```

`GET /api/tripulacion?dia=5`

```json
{
  "dia_mision": 5,
  "equipo": {
    "total": 6,
    "niveles": {"verde": 2, "amarillo": 2, "naranja": 1, "rojo": 1},
    "promedio_preparacion": 61,
    "mejor": "AST-02",
    "menor": "AST-06",
    "cobertura_media": 0.83,
    "indicador_mas_debil": "sueno_h"
  },
  "astronautas": [
    {
      "id": "AST-02",
      "nombre": "Mateo Ríos",
      "rol": "Piloto",
      "nivel": "verde",
      "preparacion_pct": 84,
      "desglose": {"indicadores": 88, "plan": 91, "seguridad": 100, "datos": 100},
      "cobertura": 1.0,
      "tendencia": "estable",
      "riesgo_modelos_pct": null,
      "estado": "ok"
    }
  ],
  "aviso": "Simulated-data prototype. Not a medical evaluation."
}
```

En la tabla general, `riesgo_modelos_pct` es `null` cuando no se consultaron modelos para ese astronauta
(lo normal: la vista general es solo reglas). La UI muestra `—`, no un cero.

---

## Anexo E · Orden de implementación recomendado

1. **Fase 0** — reconocimiento, plan y suite base.
2. **Fase 1** — multiastronauta y migración; contratos nuevos; pruebas de aislamiento.
3. **Fase 2** — endpoints de tripulación + índice + vista general; pruebas de fórmula y degradación.
4. **Fase 3** — endpoints del reloj + proyección; pruebas de ingesta e idempotencia.
5. **Fase 4** — página `/reloj/` y cola offline; pruebas manuales y de recursos remotos.
6. **Fase 5** — documentación, demo y limpieza.

En cada fase: `pytest`, arranque local, comprobación en el navegador y actualización de `PLAN.md`.

---

## Anexo F · Lo que NO debes hacer

- No convertir esto en una app móvil nativa ni en un sistema con login real.
- No añadir datos médicos reales, nombres de astronautas reales ni afirmaciones clínicas.
- No usar frameworks de frontend, CDN, Tailwind, React, Vue ni build steps.
- No cambiar los umbrales, protocolos, modelos entrenados ni el guion de AST-01 para "que cuadre".
- No hacer que el reloj llame a `/api/estado` completo cada 5 segundos.
- No llamar al orquestador seis veces para pintar la tabla general.
- No ordenar a alguien como "0 %" cuando en realidad le faltan datos.
- No ocultar los estados degradados ni los datos sospechosos.
- No implementes notificaciones push, service workers ni ejecución en segundo plano real; el sondeo y la
  cola local bastan para la demo.
- No dejar la demo sin una forma de reiniciar a los seis astronautas al día 1.
