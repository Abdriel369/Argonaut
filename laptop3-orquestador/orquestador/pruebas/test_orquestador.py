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


# --------------------------------------------------------------------------
# Datos sospechosos: un sensor que parece fallar
# --------------------------------------------------------------------------

def test_un_dato_sospechoso_genera_un_aviso_claro_y_no_cambia_el_nivel():
    limpio = asyncio.run(evaluar(entrada(1), ClienteNulo(), CFG))
    r = asyncio.run(evaluar(entrada(1, sensor={1: {"fc_reposo": 250.0}}), ClienteNulo(), CFG))
    validar("resultado_final", r)
    assert limpio["sensores_sospechosos"] == []
    aviso = r["sensores_sospechosos"][0]
    assert aviso["aviso"] == ("El sensor de pulso en reposo parece fallar: marca 250 lpm, un valor que no es "
                              "posible. Revisa el equipo y vuelve a medir. Mientras tanto ese dato no se usa.")
    assert r["nivel_global"] == limpio["nivel_global"] == "verde"
    assert r["alertas"] == [] and r["informe_cirujano"] is None
    assert r["explicacion_global"].endswith("Hay 1 dato sospechoso: revisa el equipo.")


def test_cada_motivo_tiene_su_aviso():
    casos = {
        "cambio_brusco": {5: {"fc_reposo": 128.0}},
        "valor_congelado": {2: {"fc_reposo": 64.0}, 3: {"fc_reposo": 64.0}, 4: {"fc_reposo": 64.0}, 5: {"fc_reposo": 64.0}},
    }
    textos = {}
    for motivo, sensor in casos.items():
        r = asyncio.run(evaluar(entrada(5, sensor=sensor), ClienteNulo(), CFG))
        aviso = r["sensores_sospechosos"][0]
        assert aviso["motivo"] == motivo
        textos[motivo] = aviso["aviso"]
    assert "pasó de 69 a 128 lpm de una lectura a la siguiente" in textos["cambio_brusco"]
    assert "lleva 4 días marcando exactamente 64 lpm" in textos["valor_congelado"]


def test_el_especialista_al_que_le_falta_el_dato_no_sube_la_alerta():
    alertas = _alerta_sueno("amarillo")
    respuesta = {**_respuesta("sueno", "rojo", 0.9), "datos_faltantes": ["sueno_h"]}
    con_voto = fusionar(alertas, {"sueno": respuesta}, CFG.orquestador)
    sin_voto = fusionar(alertas, {"sueno": respuesta}, CFG.orquestador, sin_voto={"sueno"})
    assert con_voto[0]["nivel"] == "naranja"
    assert sin_voto[0]["nivel"] == "amarillo" and sin_voto[0]["elevada_por"] == []
    assert sin_voto[0]["especialistas_consultados"] == ["sueno"], "su opinión se sigue mostrando"
    # Tampoco crea una señal temprana por su cuenta.
    assert fusionar([], {"cardiovascular": {**_respuesta("cardiovascular", "rojo", 0.9)}}, CFG.orquestador,
                    sin_voto={"cardiovascular"}) == []
