"""Integración: la historia completa de la demo y los modos de fallo, con todas las piezas reales."""

import asyncio
import re
from pathlib import Path

import pila

FRONTEND = Path(__file__).resolve().parents[1] / "laptop1-backend-frontend" / "frontend"
HISTORIA = ["verde", "verde", "amarillo", "amarillo", "rojo", "amarillo", "verde"]


async def recorrer_semana(app):
    async with pila.navegador(app) as nav:
        niveles, ultimo = [], None
        for dia in range(1, 8):
            ultimo = (await nav.post("/api/demo/dia", json={"dia": dia})).json()
            niveles.append(ultimo["resultado"]["nivel_global"])
        return niveles, ultimo


def test_la_historia_completa_de_la_demo():
    niveles, ultimo = asyncio.run(recorrer_semana(pila.crear_pila()))
    assert niveles == HISTORIA
    assert ultimo["resultado"]["modo"] == "completo"


def test_con_la_laptop2_apagada_sigue_respondiendo_y_lo_indica():
    async def caso():
        app = pila.crear_pila(laptop2_apagada=True)
        async with pila.navegador(app) as nav:
            return (await nav.post("/api/demo/dia", json={"dia": 5})).json()["resultado"]
    r = asyncio.run(caso())
    assert r["modo"] == "degradado"
    assert r["nivel_global"] == "rojo"
    estados = {m["especialista"]: m["estado"] for m in r["junta"]}
    assert estados["riesgo-solar"] == "respondio"


def test_un_solo_modelo_caido_no_tumba_a_los_demas():
    async def caso():
        app = pila.crear_pila(modelos_caidos=("sueno",))
        async with pila.navegador(app) as nav:
            return (await nav.post("/api/demo/dia", json={"dia": 3})).json()["resultado"]
    r = asyncio.run(caso())
    estados = {m["especialista"]: m["estado"] for m in r["junta"]}
    assert estados["sueno"] == "no_disponible"
    assert estados["fatiga-bienestar"] == "respondio"
    assert r["modo"] == "degradado"


def test_la_interfaz_no_usa_recursos_remotos():
    archivos = [*FRONTEND.rglob("*.html"), *FRONTEND.rglob("*.css"), *FRONTEND.rglob("*.js")]
    assert archivos, "No se encontró la interfaz"
    for ruta in archivos:
        texto = ruta.read_text(encoding="utf-8")
        assert not re.search(r"""(src|href|url)\s*[=(]\s*["']?https?://""", texto), ruta
