"""Orquestador: enrutamiento por tabla, fusión (las reglas mandan) y modo degradado."""

import asyncio

from comun.contratos import validar
from fabrica import entrada
from orquestador.clientes import ClienteNulo
from orquestador.nucleo import cargar_configuracion, enrutar, evaluar, fusionar

CFG = cargar_configuracion()


def _respuesta(nombre: str, nivel: str, confianza: float) -> dict:
    return {
        "especialista": nombre, "nivel": nivel, "confianza": confianza, "riesgo": 0.6,
        "factores": [{"indicador": "sueno_h", "aporte": 0.9, "etiqueta": "Sueño", "frase": "dormiste poco anoche"}],
        "explicacion_corta": "x", "version_modelo": "1.0.0", "datos_entrenamiento": "sintéticos",
    }


def _alerta_sueno(nivel: str) -> list:
    return [{"id": "SUENO_BAJO", "origen": "indicador", "titulo": "Sueño", "nivel": nivel,
             "indicadores_implicados": ["sueno_h"], "hechos": ["h"], "consecuencia": "c", "protocolo_id": "sueno"}]


def test_la_tabla_de_rutas_decide_a_quien_consultar():
    convocados = enrutar(["sueno_h:bajo"], CFG.orquestador)
    assert set(convocados) == {"sueno", "fatiga-bienestar"}
    assert enrutar([], CFG.orquestador) == {}


def test_un_especialista_solo_puede_subir_un_escalon():
    alertas = _alerta_sueno("amarillo")
    subio = fusionar(alertas, {"sueno": _respuesta("sueno", "rojo", 0.9)}, CFG.orquestador)
    assert subio[0]["nivel"] == "naranja"
    assert subio[0]["elevada_por"] == ["sueno"]


def test_un_especialista_nunca_baja_una_alerta_de_las_reglas():
    alertas = _alerta_sueno("amarillo")
    bajo = fusionar(alertas, {"sueno": _respuesta("sueno", "verde", 0.9)}, CFG.orquestador)
    assert bajo[0]["nivel"] == "amarillo"


def test_con_poca_confianza_la_opinion_no_cambia_el_nivel():
    alertas = _alerta_sueno("amarillo")
    poca = fusionar(alertas, {"sueno": _respuesta("sueno", "rojo", 0.3)}, CFG.orquestador)
    assert poca[0]["nivel"] == "amarillo"


def test_un_especialista_puede_avisar_sin_que_las_reglas_vean_nada():
    resultado = fusionar([], {"cardiovascular": _respuesta("cardiovascular", "rojo", 0.9)}, CFG.orquestador)
    assert resultado[0]["id"] == "SENAL_CARDIOVASCULAR"
    assert resultado[0]["nivel"] == "amarillo"


def test_sin_especialistas_la_demo_sigue_con_las_reglas_y_lo_indica():
    r = asyncio.run(evaluar(entrada(5), ClienteNulo(), CFG))
    assert r["modo"] == "degradado"
    assert "riesgo-solar" in r["especialistas_no_disponibles"]
    assert r["nivel_global"] == "rojo"
    validar("resultado_final", r)
