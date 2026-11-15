"""Reloj simulado: ingesta, idempotencia, aislamiento, sensores y proyección."""

import asyncio
import uuid

import pila
from backend import calculo
from backend.bd import BaseDatos


def lectura(astronauta_id="AST-01", indicadores=None, lectura_id=None):
    return {
        "lectura_id": lectura_id or str(uuid.uuid4()),
        "astronauta_id": astronauta_id,
        "capturado_en": "2026-11-15T16:05:00Z",
        "origen": "reloj-simulado",
        "indicadores": indicadores or {"sueno_h": 6.8, "animo": 4, "estres": 38},
    }


def test_una_lectura_actualiza_solo_a_su_astronauta():
    async def caso():
        app = pila.crear_pila(laptop3_apagada=True)
        async with pila.navegador(app) as nav:
            await nav.post("/api/demo/dia", json={"dia": 5})
            antes = (await nav.get("/api/reloj/estado?astronauta_id=AST-02")).json()
            respuesta = await nav.post("/api/reloj/lectura", json=lectura())
            despues = (await nav.get("/api/reloj/estado?astronauta_id=AST-02")).json()
            return respuesta.status_code, respuesta.json(), antes, despues

    codigo, cuerpo, antes, despues = asyncio.run(caso())
    assert codigo == 200 and cuerpo["aceptado"] is True
    assert antes["indicadores"] == despues["indicadores"]


def test_reenviar_el_mismo_lectura_id_no_duplica_ni_reevalua():
    async def caso():
        app = pila.crear_pila(laptop3_apagada=True)
        servicio = app.state.servicio
        identificador = str(uuid.uuid4())
        async with pila.navegador(app) as nav:
            primera = await nav.post("/api/reloj/lectura", json=lectura(lectura_id=identificador))
            segunda = await nav.post("/api/reloj/lectura", json=lectura(lectura_id=identificador))
            filas = servicio.bd.consultar(
                "SELECT COUNT(*) AS n FROM lecturas_reloj WHERE lectura_id = ?", (identificador,))
            return primera.json(), segunda.json(), filas[0]["n"]

    primera, segunda, filas = asyncio.run(caso())
    assert primera["aceptado"] is True and primera["repetida"] is False
    assert segunda["aceptado"] is True and segunda["repetida"] is True
    assert filas == 1


def test_un_astronauta_sin_datos_muestra_sin_datos_y_no_un_verde():
    async def caso():
        app = pila.crear_pila(laptop3_apagada=True)
        async with pila.navegador(app) as nav:
            await nav.post("/api/demo/dia", json={"dia": 5})
            return (await nav.get("/api/reloj/estado?astronauta_id=AST-05")).json()

    estado = asyncio.run(caso())
    assert estado["sin_datos"] is True
    assert estado["alerta_principal"] is None
    assert all(v is None for v in estado["indicadores"].values())


def test_la_idempotencia_del_reloj_sobrevive_a_un_reinicio(ruta_temporal):
    ruta = str(ruta_temporal / "reloj.db")
    primera = BaseDatos(ruta)
    primera.guardar_lectura("lectura-persistente", "AST-01", 3, "2026-11-15T16:05:00Z",
                            {"sueno_h": 6.8})
    segunda = BaseDatos(ruta)
    guardada = segunda.lectura_guardada("lectura-persistente")
    assert guardada is not None
    assert guardada["astronauta_id"] == "AST-01"
    assert guardada["dia"] == 3
    assert guardada["indicadores"] == {"sueno_h": 6.8}


def test_un_lote_pequeno_se_aplica_y_cumple_su_contrato():
    async def caso():
        app = pila.crear_pila(laptop3_apagada=True)
        async with pila.navegador(app) as nav:
            lote = {"lecturas": [
                lectura(indicadores={"sueno_h": 7.0}),
                lectura(indicadores={"fc_reposo": 61}),
            ]}
            respuesta = await nav.post("/api/reloj/lectura", json=lote)
            return respuesta.status_code, respuesta.json()

    codigo, cuerpo = asyncio.run(caso())
    assert codigo == 200
    assert cuerpo["aceptado"] is True
    assert len(cuerpo["resultados"]) == 2
    assert all(r["aceptado"] is True for r in cuerpo["resultados"])


def test_un_valor_fuera_del_catalogo_se_rechaza_y_no_cambia_el_estado():
    async def caso():
        app = pila.crear_pila(laptop3_apagada=True)
        async with pila.navegador(app) as nav:
            antes = (await nav.get("/api/reloj/estado?astronauta_id=AST-01")).json()
            respuesta = await nav.post(
                "/api/reloj/lectura", json=lectura(indicadores={"fc_reposo": 250}))
            despues = (await nav.get("/api/reloj/estado?astronauta_id=AST-01")).json()
            return respuesta.status_code, respuesta.json(), antes, despues

    codigo, cuerpo, antes, despues = asyncio.run(caso())
    assert codigo == 422
    assert "30 y 200" in cuerpo["detail"]
    assert antes["indicadores"] == despues["indicadores"]


def test_un_valor_sospechoso_no_activa_reglas_y_genera_aviso():
    async def caso():
        app = pila.crear_pila(laptop3_apagada=True)
        async with pila.navegador(app) as nav:
            await nav.post("/api/demo/dia", json={"dia": 2})
            # El día 1 el pulso fue 62: 200 es un salto imposible para el sensor.
            respuesta = await nav.post(
                "/api/reloj/lectura", json=lectura(indicadores={"fc_reposo": 200}))
            return respuesta.json()["estado_reloj"]

    estado = asyncio.run(caso())
    assert [s["indicador"] for s in estado["datos_sospechosos"]] == ["fc_reposo"]
    assert estado["datos_sospechosos"][0]["motivo"] == "cambio_brusco"
    assert estado["nivel_global"] == "verde"
    assert all(alerta["id"] != "FC_ALTA" for alerta in estado["alertas"])


def test_el_estado_del_reloj_no_llama_al_orquestador_en_cada_consulta():
    async def caso():
        app = pila.crear_pila(laptop3_apagada=True)
        servicio = app.state.servicio
        original = servicio.cliente.evaluar
        llamadas = []

        async def contar(*args, **kwargs):
            llamadas.append(1)
            return await original(*args, **kwargs)

        servicio.cliente.evaluar = contar
        async with pila.navegador(app) as nav:
            primera = await nav.get("/api/reloj/estado?astronauta_id=AST-03")
            segunda = await nav.get("/api/reloj/estado?astronauta_id=AST-03")
            return primera.status_code, segunda.status_code, len(llamadas)

    primera, segunda, llamadas = asyncio.run(caso())
    assert primera == 200 and segunda == 200
    # La primera consulta calcula y guarda; la segunda sirve lo guardado.
    assert llamadas == 1


def test_la_proyeccion_devuelve_none_con_menos_de_tres_puntos():
    assert calculo.proyeccion_lineal([7.0, None, 6.5], [1, 2, 3]) is None
    assert calculo.proyeccion_lineal([], []) is None


def test_la_proyeccion_da_valores_razonables_con_una_serie_fija():
    serie = [7.1, 6.9, 6.7, 6.5, 6.3]
    dias = [1, 2, 3, 4, 5]
    proyecto = calculo.proyeccion_lineal(
        serie, dias, decimales=1, minimo=0.0, maximo=14.0, linea_base=7.1)
    assert proyecto["valor_24h"] == 6.1
    assert proyecto["direccion"] == "baja"
    assert proyecto["pendiente"] == -0.2
    assert proyecto["dias_para_base"] is None

    subiendo = calculo.proyeccion_lineal(
        [6.0, 6.2, 6.4, 6.6, 6.8], dias, decimales=1, minimo=0.0, maximo=14.0, linea_base=7.0)
    assert subiendo["valor_24h"] == 7.0
    assert subiendo["direccion"] == "sube"
    assert subiendo["dias_para_base"] == 1


def test_la_proyeccion_nunca_sale_del_rango_fisico():
    proyecto = calculo.proyeccion_lineal(
        [1.0, 2.0, 3.0], [1, 2, 3], decimales=0, minimo=0.0, maximo=10.0)
    assert 0.0 <= proyecto["valor_24h"] <= 10.0
