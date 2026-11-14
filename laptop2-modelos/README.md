# Laptop 2 · modelos especialistas y gateway

Tres modelos pequeños, cada uno con su API y su contenedor, detrás de un **gateway** que es el único
punto de entrada visible desde la Laptop 3. **Datos sintéticos.** No es diagnóstico.

| Especialista | Qué estima | Modelo | Puerto interno |
|---|---|---|---|
| Sueño | Riesgo por falta o desorden de sueño (incluye el reloj circadiano) | Regresión logística | 8210 |
| Fatiga y bienestar | Fatiga, ánimo, estrés, HRV, ejercicio, comida, cohesión | Gradient boosting (XGBoost) | 8220 |
| Cardiovascular | Sobrecarga del corazón; desplazamiento de fluidos en microgravedad | Gradient boosting (XGBoost) | 8230 |

Líneas futuras (solo documentadas, no implementadas): músculo-hueso e inmunológico.

## Arrancar
```bash
cp .env.example .env
docker compose up --build
```

## Cada modelo
- Genera su propio conjunto sintético con semilla fija (`datos-sinteticos/`). Supuestos: `datos-sinteticos/SUPUESTOS.md`.
- Entrega **factores** que explican la predicción, no solo un número.
- Versionado: `modelos/<nombre>/artefactos/modelo-<nombre>-v1.0.0.*` y sus métricas.
- API: `POST /predecir`, `GET /salud`, `GET /info` (incluye métricas y limitaciones).
- Pruebas en `modelos/<nombre>/pruebas/`.

Reentrenar (desde la carpeta del modelo): `python entrenar.py`.

## Gateway
`POST /consultar` reparte la consulta en paralelo, con tiempo máximo por modelo (`TIEMPO_MAX_MODELO_S`, 3 s).
Devuelve lo que respondió y marca en `fallidos` los que no. `GET /salud` indica el estado de cada modelo.

## GPU
`USAR_GPU=auto` (por defecto) usa CUDA en XGBoost si detecta una GPU NVIDIA; si no, CPU. El modelo lineal
siempre corre en CPU. Para usar GPU en Docker, ver el bloque comentado de la Laptop 3.

## Probar la conexión
```bash
python3 ../scripts/verificar_red.py --desde laptop3   # desde la Laptop 3, hacia el gateway
```
