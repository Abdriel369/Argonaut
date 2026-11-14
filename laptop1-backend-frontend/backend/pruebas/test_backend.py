"""Backend: guion, línea base, validación de datos, protocolos, informes y controles de demo."""

import asyncio

import pytest

import pila
from backend import calculo
from backend.ajustes import Ajustes


def correr_con_app(funcion, **kwargs):
    async def principal():
        app = pila.crear_pila(**kwargs)
        async with pila.navegador(app) as nav:
            return await funcion(nav)
    return asyncio.run(principal())


def test_el_dia_critico_genera_informe_pendiente():
    async def caso(nav):
        return (await nav.post("/api/demo/dia", json={"dia": 5})).json()
    e = correr_con_app(caso)
    assert e["resultado"]["nivel_global"] == "rojo"
    assert e["informes"] and e["informes"][0]["estado"] == "pendiente"
    assert e["musculo_hueso"]["es_estimacion"] is True


def test_un_dato_fuera_de_rango_se_rechaza():
    async def caso(nav):
        r = await nav.post("/api/registro", json={"indicadores": {"spo2": 150}})
        return r.status_code, r.json()
    codigo, cuerpo = correr_con_app(caso)
    assert codigo == 422
    assert "entre 70" in cuerpo["detail"]


def test_la_linea_base_se_recalibra_tras_la_adaptacion():
    perfil = Ajustes.desde_entorno().perfil
    registros = {1: {"sueno_h": 6.0}, 2: {"sueno_h": 6.0}}
    assert calculo.linea_base(perfil, 2, registros)["sueno_h"] == 7.2
    assert calculo.linea_base(perfil, 3, registros)["sueno_h"] == 6.6


def test_la_exposicion_musculo_hueso_baja_con_el_ejercicio():
    sin_ejercicio = calculo.exposicion_musculo_hueso({d: {"ejercicio_min": 0} for d in (1, 2, 3)}, 3, 120, 0.8)
    con_plan = calculo.exposicion_musculo_hueso({d: {"ejercicio_min": 120} for d in (1, 2, 3)}, 3, 120, 0.8)
    assert sin_ejercicio["porcentaje"] == 100
    assert con_plan["porcentaje"] == 20


def test_la_prueba_de_reaccion_exige_tres_respuestas():
    async def caso(nav):
        return (await nav.post("/api/checkin/reaccion", json={"tiempos_ms": [300, 320]})).status_code
    assert correr_con_app(caso) == 422


def test_un_paso_de_protocolo_aparece_en_el_informe():
    async def caso(nav):
        await nav.post("/api/demo/dia", json={"dia": 5})
        await nav.post("/api/protocolo/paso", json={"alerta_id": "FATIGA", "paso_id": "f1", "hecho": True})
        return (await nav.get("/api/informes")).json()
    acciones = correr_con_app(caso)["informes"][0]["contenido"]["acciones_tomadas"]
    assert acciones and acciones[0]["alerta"] == "FATIGA"
    assert "Detén" in acciones[0]["paso"]


def test_el_enlace_con_la_tierra_envia_la_cola_una_sola_vez():
    async def caso(nav):
        await nav.post("/api/demo/dia", json={"dia": 5})
        primero = (await nav.post("/api/demo/enlace-tierra")).json()
        segundo = (await nav.post("/api/demo/enlace-tierra")).json()
        return primero, segundo
    primero, segundo = correr_con_app(caso)
    assert primero["ultimo_enlace"]["enviados"] == 1
    assert segundo["ultimo_enlace"]["enviados"] == 0
    assert primero["informes"][0]["estado"] == "enviado"


def test_el_evento_solar_suma_12_msv_a_la_dosis():
    async def caso(nav):
        await nav.post("/api/demo/dia", json={"dia": 5})
        antes = (await nav.get("/api/estado")).json()["indicadores"]["dosis_acumulada_msv"]
        despues = (await nav.post("/api/demo/evento-solar", json={"activo": True})).json()
        return antes, despues["indicadores"]["dosis_acumulada_msv"]
    antes, despues = correr_con_app(caso)
    assert abs((despues - antes) - 12.0) < 0.01


def test_la_caida_de_la_laptop2_pasa_a_modo_degradado():
    async def caso(nav):
        await nav.post("/api/demo/caida-laptop2", json={"activa": True})
        return (await nav.post("/api/demo/dia", json={"dia": 5})).json()["resultado"]
    r = correr_con_app(caso)
    assert r["modo"] == "degradado"
    estados = {m["especialista"]: m["estado"] for m in r["junta"]}
    assert estados["sueno"] == "no_disponible"
    assert estados["riesgo-solar"] == "respondio"


def test_sin_laptop3_el_backend_evalua_con_su_respaldo_local():
    async def caso(nav):
        e = (await nav.post("/api/demo/dia", json={"dia": 5})).json()
        return e
    e = correr_con_app(caso, laptop3_apagada=True)
    assert e["resultado"]["origen"] == "respaldo-local"
    assert e["resultado"]["modo"] == "degradado"
    assert e["resultado"]["nivel_global"] == "rojo"
    assert e["conexion_orquestador"]["ok"] is False


def test_la_exportacion_csv_tiene_una_fila_por_dia_evaluado():
    async def caso(nav):
        await nav.post("/api/demo/dia", json={"dia": 5})
        return (await nav.get("/api/exportar.csv")).text
    texto = correr_con_app(caso)
    assert "dia_mision" in texto
    filas = [linea for linea in texto.splitlines() if linea[:1].isdigit()]
    assert len(filas) == 5


@pytest.mark.parametrize("ruta", ["/api/estado", "/api/red", "/api/historial", "/api/informes"])
def test_las_lecturas_responden_sin_error(ruta):
    async def caso(nav):
        return (await nav.get(ruta)).status_code
    assert correr_con_app(caso) == 200
