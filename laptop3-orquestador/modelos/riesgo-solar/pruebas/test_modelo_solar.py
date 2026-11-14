"""Especialista de RIESGO SOLAR (Laptop 3): métricas, contrato, API y reproducibilidad."""

import numpy as np

import generador_solar as generador
from api_solar import app
from comun.especialista.verificacion import comprobar_api, comprobar_modelo
from fabrica import entrada
from modelo_solar import CARPETA_ARTEFACTOS, DEFINICION

DATOS = entrada(2, evento=True)


def test_metricas_contrato_y_datos_incompletos():
    comprobar_modelo(DEFINICION, CARPETA_ARTEFACTOS, DATOS)


def test_api_http():
    comprobar_api(app, DEFINICION, DATOS)


def test_con_tormenta_solar_sube_el_riesgo():
    from comun.especialista.nucleo import ModeloEspecialista
    modelo = ModeloEspecialista(DEFINICION, CARPETA_ARTEFACTOS, dispositivo="cpu")
    tranquilo = modelo.predecir(entrada(2))["riesgo"]
    tormenta = modelo.predecir(DATOS)["riesgo"]
    assert tormenta > tranquilo


def test_los_datos_sinteticos_son_reproducibles():
    X1, y1 = generador.generar(500, generador.SEMILLA)
    X2, y2 = generador.generar(500, generador.SEMILLA)
    assert np.array_equal(X1, X2) and np.array_equal(y1, y2)
