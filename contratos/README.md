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

**Datos sospechosos (campo opcional).** Cuando la validación de sensores de la Laptop 1 aparta una lectura,
`entrada_orquestador` lleva ese indicador como `null` y añade `sensores_sospechosos` con el motivo. El campo solo
se envía cuando hay alguno, así que un mensaje normal es idéntico al de antes. `resultado_final` devuelve
`sensores_sospechosos` con un aviso por cada uno. Los mensajes sin ese campo siguen siendo válidos.

Ejemplos en `ejemplos/`. Pruebas en `pruebas/`. La validación está en `comun/contratos.py`.
