# Especialista de sueño · v1.1.0

Estima el riesgo por falta o desorden de sueño a partir de horas dormidas, sueño de tres días, irregularidad
del horario, desfase del reloj interno, luz de la mañana, ejercicio y estrés. **Entrenado solo con datos
sintéticos. No diagnostica: estima un riesgo entre 0 y 1 y explica los factores que más pesan.**

Prototipo, no es diagnóstico médico.

## Qué cambió en la 1.1.0

- Los datos sintéticos ahora tienen dependencias causales (el estrés y el ejercicio afectan al sueño antes de la
  etiqueta; la irregularidad va con el desfase del reloj) y no se recortan en los bordes.
- Las referencias de cada variable son las medianas de la población sintética.
- La prevalencia de riesgo bajó de 16.5 % a 12 %.
- La regla de etiquetado no cambió. Los detalles, supuestos y resultados están en
  `laptop2-modelos/datos-sinteticos/SUPUESTOS.md`.

## Resultados

| Métrica | Valor 1.1.0 | Nota |
|---|---|---|
| AUC | 0.822 | Mínimo exigido 0.78 |
| Brier | 0.087 | Depende de la prevalencia |
| Error de calibración esperado | 0.011 | Por deciles, predicho ≈ observado |
| Prevalencia en los datos | 0.12 | Supuesto de diseño |

Los valores son los de `artefactos/metricas-sueno-v1.1.0.json`, generados por `entrenar.py`. No se editan a mano.

## Efecto en la historia de la demo

El día 4 de la historia sube de amarillo a naranja: el riesgo de sueño (0.52) con confianza 0.62 eleva la
alerta de FATIGA. La historia esperada en las pruebas es ahora verde, verde, amarillo, naranja, rojo, amarillo, verde.

## Qué NO debe afirmarse en la presentación

- Que el modelo está validado con datos de astronautas o de misión. No lo está.
- Que la regla de riesgo refleja la fisiología real del sueño. Es una regla escrita a mano con pesos de ejemplo.
- Que los rangos, las dependencias o la prevalencia son mediciones. Son supuestos documentados, pendientes de verificar.
- Que el AUC o el Brier miden la calidad clínica. Miden si el modelo recupera la regla sintética.
- Que la sensibilidad con corte 0.5 (0.18) dice algo del producto. El producto usa los cortes 0.20 / 0.50 / 0.75.

## Limitaciones

- Modelo lineal: no capta combinaciones complejas entre factores.
- Los datos son de un corte transversal: cada fila es independiente, sin serie diaria.
- El desfase circadiano y la luz son simulados; en una estación vendrían de sensores y horarios.

## Reentrenar

```bash
cd laptop2-modelos/modelos/sueno
python entrenar.py
```

Reproducible: la misma semilla da los mismos datos, el mismo modelo y el mismo hash.
