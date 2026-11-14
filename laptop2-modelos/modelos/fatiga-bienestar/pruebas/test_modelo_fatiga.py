"""Especialista de FATIGA Y BIENESTAR: métricas, contrato, API y reproducibilidad."""

import numpy as np

import generador_fatiga as generador
from api_fatiga import app
from comun.especialista.verificacion import comprobar_api, comprobar_modelo
from fabrica import entrada
from modelo_fatiga import CARPETA_ARTEFACTOS, DEFINICION

DATOS = entrada(5)


def test_metricas_contrato_y_datos_incompletos():
    comprobar_modelo(DEFINICION, CARPETA_ARTEFACTOS, DATOS)


def test_api_http():
    comprobar_api(app, DEFINICION, DATOS)


def test_los_datos_sinteticos_son_reproducibles():
    X1, y1 = generador.generar(500, generador.SEMILLA)
    X2, y2 = generador.generar(500, generador.SEMILLA)
    assert np.array_equal(X1, X2) and np.array_equal(y1, y2)
