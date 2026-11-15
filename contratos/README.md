# Contratos JSON

Esquemas compartidos por las tres laptops. Todos los servicios validan lo que reciben y lo que devuelven.
Cada servicio expone `GET /salud` y los modelos devuelven su `version_modelo`.

| Esquema | Quién lo envía → quién lo recibe |
|---|---|
| `entrada_orquestador` | Laptop 1 backend → Laptop 3 orquestador |
| `consulta_especialista` | Orquestador → cada modelo (vía gateway o local) |
| `respuesta_especialista` | Modelo → orquestador |
| `consulta_gateway` / `respuesta_gateway` | Orquestador → gateway de la Laptop 2 (y su respuesta, con fallidos) |
| `resultado_final` | Orquestador → Laptop 1 backend |
| `lectura_reloj` | Reloj web (`/reloj/`) → Laptop 1 |
| `respuesta_lectura_reloj` | Laptop 1 → reloj web (tras aplicar una lectura) |
| `respuesta_lote_reloj` | Laptop 1 → reloj web (tras aplicar un lote pequeño) |
| `estado_reloj` | Laptop 1 → reloj web (estado compacto, sondeo cada 5 s) |
| `tripulacion` | Laptop 1 → página principal (vista general de la tripulación) |
| `detalle_tripulacion` | Laptop 1 → página principal (detalle individual) |

**Multiastronauta.** Todos los mensajes nuevos llevan `astronauta_id`. Las
rutas y contratos antiguos siguen funcionando: si el campo falta, la Laptop 1
usa `AST-01`. `resultado_final` gana `astronauta_id` **opcional**; no es
obligatorio para no romper las respuestas guardadas de la demo.

**Reloj e idempotencia.** `lectura_reloj` exige `lectura_id` (UUID del cliente),
`astronauta_id`, `capturado_en`, `origen` y un objeto `indicadores` con solo los
indicadores enviados. Reenviar el mismo `lectura_id` devuelve
`repetida: true` sin duplicar ni reevaluar. El estado compacto incluye
`campos` (unidad, rango y paso del catálogo), `linea_base`, `roster` y
`proyeccion` heurística. `sin_datos: true` indica que el astronauta no tiene
lecturas ese día: el reloj lo muestra como "No data", no como un verde.

**Datos sospechosos (campo opcional).** Cuando la validación de sensores de la Laptop 1 aparta una lectura,
`entrada_orquestador` lleva ese indicador como `null` y añade `sensores_sospechosos` con el motivo. El campo solo
se envía cuando hay alguno, así que un mensaje normal es idéntico al de antes. `resultado_final` devuelve
`sensores_sospechosos` con un aviso por cada uno. Los mensajes sin ese campo siguen siendo válidos.

Ejemplos en `ejemplos/`. Pruebas en `pruebas/`. La validación está en `comun/contratos.py`.
