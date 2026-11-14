"""Contratos JSON: los esquemas son válidos y los mensajes incorrectos se rechazan."""

import json

import pytest
from jsonschema import Draft202012Validator

from comun.contratos import NOMBRES, ErrorContrato, carpeta_contratos, errores, validar

CARPETA = carpeta_contratos()


def ejemplo(nombre: str) -> dict:
    return json.loads((CARPETA / "ejemplos" / f"{nombre}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("nombre", NOMBRES)
def test_cada_esquema_es_json_schema_valido(nombre):
    esquema = json.loads((CARPETA / f"{nombre}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(esquema)


@pytest.mark.parametrize("nombre", ["entrada_orquestador", "consulta_especialista", "respuesta_especialista"])
def test_los_ejemplos_cumplen_su_contrato(nombre):
    assert errores(nombre, ejemplo(nombre)) == []


def test_entrada_sin_astronauta_se_rechaza():
    entrada = ejemplo("entrada_orquestador")
    del entrada["astronauta_id"]
    with pytest.raises(ErrorContrato, match="astronauta_id"):
        validar("entrada_orquestador", entrada)


def test_riesgo_fuera_de_rango_se_rechaza():
    respuesta = ejemplo("respuesta_especialista")
    respuesta["riesgo"] = 1.4
    assert errores("respuesta_especialista", respuesta)


def test_los_datos_de_entrenamiento_deben_ser_sinteticos():
    respuesta = ejemplo("respuesta_especialista")
    respuesta["datos_entrenamiento"] = "reales"
    assert errores("respuesta_especialista", respuesta)


def test_especialista_desconocido_se_rechaza():
    consulta = ejemplo("consulta_especialista")
    consulta["especialista"] = "inmunologico"   # línea futura: no está implementada
    assert errores("consulta_especialista", consulta)
