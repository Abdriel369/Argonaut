"""Modo demo sin las tres laptops: la historia debe verse igual que con los modelos reales."""

import asyncio
from pathlib import Path

import pytest

import pila
from orquestador.clientes import ClienteGuardado

ARCHIVO = Path(__file__).resolve().parents[1] / "respuestas-guardadas.json"
HISTORIA = ["verde", "verde", "amarillo", "naranja", "rojo", "amarillo", "verde"]   # ver test_integracion.py


@pytest.fixture
def cliente_guardado():
    if not ARCHIVO.exists():
        pytest.fail("Falta respuestas-guardadas.json: ejecuta modo-demo-sin-laptops/grabar_respuestas.py")
    return ClienteGuardado(ARCHIVO)


def _recorrer(cliente, caida=False):
    async def principal():
        app = pila.crear_pila(cliente_especialistas=cliente)
        async with pila.navegador(app) as nav:
            if caida:
                await nav.post("/api/demo/caida-laptop2", json={"activa": True})
            resultados = []
            for dia in range(1, 8):
                resultados.append((await nav.post("/api/demo/dia", json={"dia": dia})).json()["resultado"])
            return resultados
    return asyncio.run(principal())


def test_la_historia_se_reproduce_con_respuestas_guardadas(cliente_guardado):
    resultados = _recorrer(cliente_guardado)
    assert [r["nivel_global"] for r in resultados] == HISTORIA
    for r in resultados:
        assert r["respuestas_guardadas"] is True
        for miembro in r["junta"]:
            assert "guardada" not in (miembro["motivo"] or ""), (r["dia_mision"], miembro)


def test_con_la_laptop2_apagada_la_demo_sigue_con_el_modelo_solar(cliente_guardado):
    resultados = _recorrer(cliente_guardado, caida=True)
    dia5 = resultados[4]
    assert dia5["modo"] == "degradado"
    estados = {m["especialista"]: m["estado"] for m in dia5["junta"]}
    assert estados["riesgo-solar"] == "respondio"


def test_sensor_defectuoso_en_modo_demo_deja_sin_respuesta_guardada_y_siguen_las_reglas(cliente_guardado):
    # Un dato sospechoso cambia lo que reciben los especialistas: ese estado no está grabado.
    async def principal():
        app = pila.crear_pila(cliente_especialistas=cliente_guardado)
        async with pila.navegador(app) as nav:
            antes = (await nav.post("/api/demo/dia", json={"dia": 5})).json()["resultado"]
            despues = (await nav.post("/api/demo/sensor-defectuoso", json={"activo": True})).json()["resultado"]
            reparado = (await nav.post("/api/demo/sensor-defectuoso", json={"activo": False})).json()["resultado"]
            return antes, despues, reparado
    antes, despues, reparado = asyncio.run(principal())

    assert antes["modo"] == "completo" and antes["nivel_global"] == "rojo"
    # Los especialistas consultados quedan como no disponibles, con el motivo a la vista.
    consultados = [m for m in despues["junta"] if m["estado"] != "no_convocado"]
    assert consultados, "el día 5 las reglas convocan a la junta"
    for miembro in consultados:
        assert miembro["estado"] == "no_disponible", miembro["especialista"]
        assert "no hay respuesta guardada" in miembro["motivo"]
    assert despues["modo"] == "degradado" and despues["respuestas_guardadas"] is True
    # Las reglas siguen funcionando: el rojo de fatiga se mantiene y el aviso del sensor aparece.
    assert despues["nivel_global"] == "rojo"
    assert "FATIGA" in despues["reglas_activadas"]
    assert despues["sensores_sospechosos"][0]["indicador"] == "fc_reposo"
    assert despues["semaforo_indicadores"]["fc_reposo"]["nivel"] == "sospechoso"
    # Al reparar el sensor, los datos vuelven a ser los grabados.
    assert reparado["modo"] == "completo" and reparado["sensores_sospechosos"] == []
    assert reparado["nivel_global"] == "rojo"


def test_un_dato_a_mano_no_grabado_deja_al_especialista_no_disponible_y_siguen_las_reglas(cliente_guardado):
    async def principal():
        app = pila.crear_pila(cliente_especialistas=cliente_guardado)
        async with pila.navegador(app) as nav:
            await nav.post("/api/demo/dia", json={"dia": 3})
            return (await nav.post("/api/registro", json={"indicadores": {"sueno_h": 3.0}})).json()["resultado"]
    r = asyncio.run(principal())
    estados = {m["especialista"]: m for m in r["junta"]}
    assert estados["sueno"]["estado"] == "no_disponible"
    assert "no hay respuesta guardada" in estados["sueno"]["motivo"]
    assert r["modo"] == "degradado"
    assert "SUENO_BAJO" in r["reglas_activadas"] and r["nivel_global"] in ("naranja", "rojo")
