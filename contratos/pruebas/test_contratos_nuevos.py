"""Contratos nuevos del reloj y de la vista de tripulación."""

import json

import pytest

from comun.contratos import NOMBRES, ErrorContrato, carpeta_contratos, errores, validar

CARPETA = carpeta_contratos()
NUEVOS = ("lectura_reloj", "respuesta_lectura_reloj", "respuesta_lote_reloj", "estado_reloj",
          "tripulacion", "detalle_tripulacion")


def ejemplo(nombre: str) -> dict:
    return json.loads((CARPETA / "ejemplos" / f"{nombre}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("nombre", NUEVOS)
def test_los_esquemas_nuevos_estan_registrados(nombre):
    assert nombre in NOMBRES
    assert (CARPETA / f"{nombre}.schema.json").is_file()


@pytest.mark.parametrize("nombre", NUEVOS)
def test_los_ejemplos_nuevos_cumplen_su_contrato(nombre):
    assert errores(nombre, ejemplo(nombre)) == []


def test_una_lectura_sin_lectura_id_se_rechaza():
    datos = ejemplo("lectura_reloj")
    del datos["lectura_id"]
    with pytest.raises(ErrorContrato, match="lectura_id"):
        validar("lectura_reloj", datos)


def test_un_astronauta_desconocido_se_rechaza():
    datos = ejemplo("lectura_reloj")
    datos["astronauta_id"] = "AST-99"
    assert errores("lectura_reloj", datos)


def test_un_indicador_no_numerico_se_rechaza():
    datos = ejemplo("lectura_reloj")
    datos["indicadores"]["sueno_h"] = "mucho"
    assert errores("lectura_reloj", datos)


def test_un_origen_desconocido_se_rechaza():
    datos = ejemplo("lectura_reloj")
    datos["origen"] = "movil-nativo"
    assert errores("lectura_reloj", datos)


def test_el_estado_del_reloj_admite_proyeccion_sin_datos():
    datos = ejemplo("estado_reloj")
    datos["proyeccion"] = [{
        "indicador": "sueno_h", "valor_24h": None, "direccion": "sin_dato",
        "pendiente": None, "dias_para_base": None,
        "metodo": "regresión lineal simple, últimos 7 días",
        "aviso": "Proyección heurística.", "puntos": 0,
    }]
    assert errores("estado_reloj", datos) == []


def test_la_vista_de_tripulacion_acepta_una_fila_sin_datos():
    datos = ejemplo("tripulacion")
    fila = datos["astronautas"][0]
    fila["preparacion_pct"] = None
    fila["desglose"] = None
    fila["estado"] = "sin_datos_suficientes"
    assert errores("tripulacion", datos) == []
