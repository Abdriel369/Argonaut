# Supuestos del índice de preparación y de la proyección

> Prototipo con datos simulados. **No es una evaluación médica** ni una decisión
> de aptitud para volar. Es una herramienta de demo para comparar perfiles.

## Dónde vive

- Fórmula: `laptop1-backend-frontend/backend/aptitud.py`.
- Pesos, topes y lista de indicadores principales:
  `laptop1-backend-frontend/backend/config/tripulacion.toml`, sección `[preparacion]`.
- Perfiles y guiones de los seis astronautas: el mismo archivo, secciones
  `[astronautas.AST-0N]`. AST-01 conserva `perfil.toml` y `guion_7_dias.toml`.
- Proyección: `laptop1-backend-frontend/backend/calculo.py`,
  `proyeccion_lineal()`.

## Índice de preparación (Readiness)

Para el astronauta `a` en el día `d`:

```
cobertura = días_con_datos / d

C_indicadores = media del puntaje de los indicadores principales con dato
  verde 100 · amarillo 60 · naranja 25 · rojo 0
  principales: sueno_h, animo, estres, ejercicio_min, fc_reposo, hrv

C_plan = 100 × (0.40 × min(1, sueño / base_sueño)
              + 0.30 × min(1, ejercicio / plan_ejercicio)
              + 0.30 × min(1, ingesta / 100))

C_seguridad = 100 × (1 − riesgo del peor nivel de las reglas)
  verde 0.00 · amarillo 0.25 · naranja 0.55 · rojo 0.85

C_datos = 100 × (0.70 × cobertura + 0.30 × (1 − min(1, sospechosos_hoy / 3)))

preparacion = 0.40 × C_indicadores
            + 0.25 × C_plan
            + 0.20 × C_seguridad
            + 0.15 × C_datos
```

Topes:

- alerta roja → `min(preparacion, 45)`;
- alerta naranja → `min(preparacion, 70)`;
- `cobertura < 0.5` → `preparacion_pct = null`, estado
  `sin_datos_suficientes`;
- más de 2 de los 6 principales sin dato → también `null`.

Si falta un término de `C_plan`, se usa el promedio ponderado de los términos
disponibles y los pesos se renormalizan. No se inventa el valor que falta.

### Decisiones y límites

- **Solo reglas locales.** El índice no espera al orquestador ni a los modelos.
  Así es rápido, comparable y reproducible.
- **Model risk va aparte.** Es el máximo riesgo de los especialistas con
  confianza ≥ 0.60. Se muestra en el detalle y en la fila solo si ya existe una
  evaluación guardada; nunca entra en `preparacion_pct`. Si no se consultaron
  modelos, la tabla muestra `—`.
- **Nunca un cero engañoso.** Una fila sin datos suficientes va al final, con la
  etiqueta `Not enough data` y `posicion = null`.
- **Redondeo.** La tabla muestra enteros; el desglose puede mostrar un decimal.
- **Los pesos y topes son cortes de diseño propio**, no probabilidades
  calibradas ni valores clínicos. Si se cambian, hay que actualizar este archivo
  y la ayuda de la interfaz.
- **El ranking no excluye a nadie.** Es una comparación de demo entre perfiles
  simulados.

## Proyección heurística a 24 h

Para `sueno_h`, `fc_reposo`, `hrv` y `estres`:

1. Se toman hasta los últimos 7 valores válidos (se ignoran `null` y los datos
   sospechosos).
2. Se ajusta una recta por mínimos cuadrados usando el día de misión como `x`.
3. Se calcula el valor esperado en `último_día + 1`.
4. Se recorta al rango físico del catálogo (`indicadores.toml`).
5. `direccion` es `sube`, `baja` o `estable` según la pendiente y un umbral
   pequeño basado en los decimales del indicador.
6. `dias_para_base` solo se informa si el cruce con la línea base cae en el
   horizonte (14 días) y en la dirección de la pendiente.
7. Con menos de 3 puntos válidos, `valor_24h` es `null` y el reloj muestra
   **Not enough data to project**.

La proyección es una **heurística de demo**, no un modelo predictivo ni un
pronóstico médico. El texto que la acompaña lo dice.

## Tripulación simulada

- AST-01: Cdte. Lucía Ferrer. Guion actual sin cambios.
- AST-02: Mateo Ríos. Perfil fuerte; pico de estrés el día 5.
- AST-03: Aisha Ndiaye. Sueño y ánimo bajan; naranja hacia el día 5; se recupera.
- AST-04: Tomás Vega. Estable en verde; lectura imposible de pulso el día 3
  (la capa de sensores la aparta y no cambia el nivel).
- AST-05: Hana Sato. Solo se siembran los días 1–2; el resto queda sin registro
  para mostrar `Not enough data`.
- AST-06: Diego Salas. Poco ejercicio y poca ingesta; rojo o naranja varios días.

Los nombres son ficticios. Los valores son deterministas: el mismo día y la
misma semilla dan siempre el mismo resultado.

## Lo que no se afirma

- No se dice que nadie esté "apto", "no apto", "sano" o "enfermo".
- No se diagnostica, no se recetan dosis y no se predice riesgo de muerte.
- No hay datos reales, ni dispositivos reales, ni Bluetooth.
- La cobertura y los datos sospechosos son de ejemplo; no sustituyen una
  revisión del equipo médico.
