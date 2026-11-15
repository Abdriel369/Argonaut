"""Índice de preparación, orden de la vista de tripulación y degradación."""

import asyncio

import pila
from backend import aptitud
from backend.ajustes import Ajustes

CONFIG = Ajustes.desde_entorno().tripulacion["preparacion"]
PERFIL = {"plan": {"ejercicio_min": 100.0}}
BASE = {"sueno_h": 7.0}
NIVELES = {
    "sueno_h": "verde", "animo": "amarillo", "estres": "naranja",
    "ejercicio_min": "verde", "fc_reposo": "verde", "hrv": "verde",
}


def registros_completos(dia=5):
    return {
        d: {"sueno_h": 7.0, "animo": 4.0, "estres": 30.0, "ejercicio_min": 100.0,
            "fc_reposo": 60.0, "hrv": 55.0}
        for d in range(1, dia + 1)
    }


def test_la_formula_del_anexo_b_da_el_resultado_exacto():
    resultado = aptitud.calcular_preparacion(
        PERFIL, 5, registros_completos(), NIVELES, BASE, "verde", 0, CONFIG)
    assert resultado["preparacion_pct"] == 92
    assert resultado["desglose"] == {
        "indicadores": 80.8, "plan": 100.0, "seguridad": 100.0, "datos": 100.0,
    }
    assert resultado["estado"] == "ok"
    assert resultado["cobertura"] == 1.0


def test_los_topes_por_alerta_naranja_y_roja_se_aplican():
    naranja = aptitud.calcular_preparacion(
        PERFIL, 5, registros_completos(), NIVELES, BASE, "naranja", 0, CONFIG)
    rojo = aptitud.calcular_preparacion(
        PERFIL, 5, registros_completos(), NIVELES, BASE, "rojo", 0, CONFIG)
    assert naranja["preparacion_pct"] == 70
    assert rojo["preparacion_pct"] == 45


def test_sin_cobertura_suficiente_el_indice_es_none_y_no_cero():
    resultado = aptitud.calcular_preparacion(
        PERFIL, 5, registros_completos(2), NIVELES, BASE, "verde", 0, CONFIG)
    assert resultado["preparacion_pct"] is None
    assert resultado["estado"] == "sin_datos_suficientes"
    assert resultado["cobertura"] == 0.4


def test_con_mas_de_dos_indicadores_principales_sin_dato_el_indice_es_none():
    registros = registros_completos()
    registros[5] = {"sueno_h": 7.0, "animo": 4.0}
    resultado = aptitud.calcular_preparacion(
        PERFIL, 5, registros, NIVELES, BASE, "verde", 0, CONFIG)
    assert resultado["preparacion_pct"] is None
    assert resultado["faltantes_principales"] == 4


def test_el_orden_desempata_por_cobertura_y_luego_por_nombre():
    filas = [
        {"id": "A", "nombre": "Zeta", "preparacion_pct": 70, "cobertura": 1.0},
        {"id": "B", "nombre": "Alfa", "preparacion_pct": 70, "cobertura": 1.0},
        {"id": "C", "nombre": "Beta", "preparacion_pct": 70, "cobertura": 0.8},
        {"id": "D", "nombre": "Sin datos", "preparacion_pct": None, "cobertura": 1.0},
        {"id": "E", "nombre": "Mejor", "preparacion_pct": 90, "cobertura": 0.6},
    ]
    orden = [f["id"] for f in aptitud.ordenar_filas(filas)]
    assert orden == ["E", "B", "A", "C", "D"]


def test_la_vista_general_funciona_con_el_orquestador_caido():
    async def caso():
        app = pila.crear_pila(laptop3_apagada=True)
        async with pila.navegador(app) as nav:
            respuesta = await nav.get("/api/tripulacion?dia=5")
            return respuesta.status_code, respuesta.json()

    codigo, datos = asyncio.run(caso())
    assert codigo == 200
    assert datos["degradado"] is True
    assert len(datos["astronautas"]) == 6


def test_cambiar_el_astronauta_activo_cambia_el_tablero_principal():
    async def caso():
        app = pila.crear_pila(laptop3_apagada=True)
        async with pila.navegador(app) as nav:
            respuesta = await nav.post("/api/tripulacion/activo", json={"astronauta_id": "AST-02"})
            estado = await nav.get("/api/estado")
            return respuesta.status_code, respuesta.json(), estado.json()

    codigo, cambiado, estado = asyncio.run(caso())
    assert codigo == 200
    assert cambiado["astronauta_id"] == "AST-02"
    assert estado["astronauta"]["id"] == "AST-02"
    assert estado["astronauta_activo"] == "AST-02"


def test_hana_sin_datos_no_se_ordena_como_un_cero():
    app = pila.crear_pila(laptop3_apagada=True)
    datos = asyncio.run(app.state.servicio.tripulacion(5))
    fila = next(f for f in datos["astronautas"] if f["id"] == "AST-05")
    assert fila["preparacion_pct"] is None
    assert fila["estado"] == "sin_datos_suficientes"
    assert fila["posicion"] is None
    assert fila["tendencia"] == "sin_dato"
    assert datos["astronautas"][-1]["id"] == "AST-05"


def test_un_astronauta_que_falla_no_impide_ver_a_los_demas(monkeypatch):
    app = pila.crear_pila(laptop3_apagada=True)
    servicio = app.state.servicio
    original = servicio._resumen_astronauta

    def fallo(astronauta_id, dia):
        if astronauta_id == "AST-03":
            raise RuntimeError("fallo simulado de un astronauta")
        return original(astronauta_id, dia)

    monkeypatch.setattr(servicio, "_resumen_astronauta", fallo)
    datos = asyncio.run(servicio.tripulacion(5))
    assert len(datos["astronautas"]) == 6
    por_id = {fila["id"]: fila for fila in datos["astronautas"]}
    assert por_id["AST-03"]["estado"] == "error"
    assert sum(1 for fila in datos["astronautas"] if fila["estado"] == "error") == 1
    assert por_id["AST-01"]["estado"] == "ok"
