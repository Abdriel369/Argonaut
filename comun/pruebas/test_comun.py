"""Piezas comunes: niveles de alerta y selección de dispositivo."""

from comun.especialista.dispositivo import detectar_dispositivo
from comun.niveles import maximo, nivel_por_riesgo, subir


def test_maximo_devuelve_el_nivel_mas_grave():
    assert maximo("verde", "naranja", "amarillo") == "naranja"
    assert maximo() == "verde"


def test_subir_no_pasa_de_rojo():
    assert subir("rojo") == "rojo"
    assert subir("amarillo") == "naranja"


def test_cortes_de_riesgo():
    assert nivel_por_riesgo(0.10) == "verde"
    assert nivel_por_riesgo(0.20) == "amarillo"
    assert nivel_por_riesgo(0.50) == "naranja"
    assert nivel_por_riesgo(0.80) == "rojo"


def test_usar_gpu_no_fuerza_cpu(monkeypatch):
    monkeypatch.setenv("USAR_GPU", "no")
    assert detectar_dispositivo() == "cpu"
