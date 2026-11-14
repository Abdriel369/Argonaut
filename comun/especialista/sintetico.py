"""Piezas comunes de los generadores de datos sintéticos.

Los datos NO vienen de astronautas ni de pacientes: se sortean dentro de rangos
de referencia públicos y se etiquetan con una regla de riesgo escrita a mano
(documentada en SUPUESTOS.md de cada laptop). Con la misma semilla salen siempre
los mismos datos.
"""

import argparse
import csv

import numpy as np


def mezcla(rng, n, minimo, maximo, centro, dispersion, fraccion_uniforme=0.35):
    """Valores entre minimo y maximo.

    La mayoría se concentra cerca de 'centro' (situación habitual) y una parte se
    reparte por todo el rango, para que el modelo también vea situaciones raras.
    """
    normales = rng.normal(centro, dispersion, n)
    uniformes = rng.uniform(minimo, maximo, n)
    valores = np.where(rng.random(n) < fraccion_uniforme, uniformes, normales)
    return np.clip(valores, minimo, maximo)


def etiquetar(rng, logit):
    """Etiqueta 1 = 'riesgo elevado', sorteada con probabilidad sigmoide(logit).

    El sorteo añade ruido a propósito: ningún modelo debe poder acertar el 100 %.
    """
    probabilidad = 1.0 / (1.0 + np.exp(-np.asarray(logit)))
    return (rng.random(len(probabilidad)) < probabilidad).astype(int)


def positivo(valores):
    """max(0, x) elemento a elemento."""
    return np.maximum(0.0, valores)


def cli(variables, generar, semilla_por_defecto):
    """Uso: python generador_x.py --n 1000 --salida muestra.csv"""
    parser = argparse.ArgumentParser(description="Genera una muestra de datos sintéticos (CSV).")
    parser.add_argument("--n", type=int, default=1000)
    parser.add_argument("--semilla", type=int, default=semilla_por_defecto)
    parser.add_argument("--salida", default="muestra.csv")
    argumentos = parser.parse_args()
    X, y = generar(argumentos.n, argumentos.semilla)
    with open(argumentos.salida, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow([v.nombre for v in variables] + ["riesgo_elevado"])
        for fila, etiqueta in zip(X, y):
            escritor.writerow([round(float(v), 3) for v in fila] + [int(etiqueta)])
    print(f"{argumentos.n} filas sintéticas en {argumentos.salida} "
          f"(semilla {argumentos.semilla}, {100 * y.mean():.1f} % con riesgo elevado)")
