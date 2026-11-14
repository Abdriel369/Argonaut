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

Ejemplos en `ejemplos/`. Pruebas en `pruebas/`. La validación está en `comun/contratos.py`.
