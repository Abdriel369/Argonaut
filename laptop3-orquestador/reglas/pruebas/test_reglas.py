"""Motor de reglas: el guion de 7 días, la ventana de adaptación y los datos faltantes."""

import pytest

from fabrica import entrada
from reglas import cargar_config, evaluar

CFG = cargar_config()

# Lo que debe verse en la demo (acceptance: días 1-2 verde, 3 y 4 amarillo, 5 crítico, 6 mejora, 7 verde).
NIVELES_GUION = ["verde", "verde", "amarillo", "amarillo", "rojo", "amarillo", "verde"]


@pytest.mark.parametrize("dia,esperado", list(enumerate(NIVELES_GUION, start=1)))
def test_cada_dia_del_guion_da_el_nivel_esperado(dia, esperado):
    assert evaluar(entrada(dia), CFG)["nivel"] == esperado


def test_dia_5_activa_fatiga_con_el_ademas_del_animo():
    r = evaluar(entrada(5), CFG)
    assert "FATIGA" in r["reglas_activadas"]
    assert [a for a in r["alertas"] if a["id"] == "FATIGA"][0]["nivel"] == "rojo"


def test_ventana_de_adaptacion_es_mas_tolerante():
    # Dos días de adaptación: una caída de 1.3 h no alerta; en el día 3 ya alerta.
    dos = evaluar(entrada(2, sobre={2: {"sueno_h": 5.9}}), CFG)
    assert dos["ventana_adaptacion"] is True
    assert dos["semaforo"]["sueno_h"]["nivel"] == "verde"
    tres = evaluar(entrada(3, sobre={3: {"sueno_h": 5.9}}), CFG)
    assert tres["ventana_adaptacion"] is False
    assert tres["semaforo"]["sueno_h"]["nivel"] == "amarillo"


def test_persistencia_sube_un_escalon_tras_varios_dias():
    # Día 5: la caída de sueño lleva 3 días seguidos fuera de rango -> de amarillo a naranja.
    r = evaluar(entrada(5), CFG)
    assert r["semaforo"]["sueno_h"]["nivel"] == "naranja"
    assert r["semaforo"]["sueno_h"]["sube_por_persistencia"] is True


def test_evento_solar_activa_radiacion():
    r = evaluar(entrada(2, evento=True), CFG)
    assert "RADIACION" in r["reglas_activadas"]
    assert r["nivel"] in ("naranja", "rojo")


def test_un_dato_sin_registro_no_rompe_la_evaluacion():
    r = evaluar(entrada(4, sobre={4: {"spo2": None}}), CFG)
    assert r["semaforo"]["spo2"]["nivel"] == "sin_dato"
    assert r["semaforo"]["spo2"]["valor"] is None


def test_el_texto_de_cada_alerta_explica_el_hecho():
    r = evaluar(entrada(5), CFG)
    for alerta in r["alertas"]:
        assert alerta["hechos"], alerta["id"]
        assert alerta["consecuencia"], alerta["id"]
