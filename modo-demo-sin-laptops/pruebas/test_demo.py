"""Modo demo sin las tres laptops: la historia debe verse igual que con los modelos reales."""

import asyncio
from pathlib import Path

import pytest

import pila
from orquestador.clientes import ClienteGuardado

ARCHIVO = Path(__file__).resolve().parents[1] / "respuestas-guardadas.json"
HISTORIA = ["verde", "verde", "amarillo", "amarillo", "rojo", "amarillo", "verde"]


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
