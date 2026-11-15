"""Integración: la historia completa de la demo y los modos de fallo, con todas las piezas reales."""

import asyncio
import re
from pathlib import Path

import pila

FRONTEND = Path(__file__).resolve().parents[1] / "laptop1-backend-frontend" / "frontend"
# Versión 1.1.0 del especialista de sueño: el día 4 sube a naranja (sueño con riesgo 0.52 y
# confianza 0.62 eleva la alerta de FATIGA). Ver SUPUESTOS.md y README.
HISTORIA = ["verde", "verde", "amarillo", "naranja", "rojo", "amarillo", "verde"]


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


def test_la_historia_no_cambia_y_no_marca_ningun_dato_sospechoso():
    async def caso():
        async with pila.navegador(pila.crear_pila()) as nav:
            dias = [(await nav.post("/api/demo/dia", json={"dia": dia})).json() for dia in range(1, 8)]
        return dias
    dias = asyncio.run(caso())
    assert [d["resultado"]["nivel_global"] for d in dias] == HISTORIA
    for d in dias:
        assert d["sensores_sospechosos"] == [] and d["resultado"]["sensores_sospechosos"] == []
        assert all(m.get("opinion_limitada") in (None, False) for m in d["resultado"]["junta"])


def test_sensor_defectuoso_en_el_dia_critico_no_baja_el_rojo_ni_pide_a_los_modelos_el_dato():
    async def caso():
        async with pila.navegador(pila.crear_pila()) as nav:
            await nav.post("/api/demo/dia", json={"dia": 5})
            return (await nav.post("/api/demo/sensor-defectuoso", json={"activo": True, "tipo": "salto"})).json()
    e = asyncio.run(caso())
    r = e["resultado"]
    assert r["nivel_global"] == "rojo" and r["modo"] == "completo"
    assert r["sensores_sospechosos"][0]["motivo"] == "cambio_brusco"
    cardio = next(m for m in r["junta"] if m["especialista"] == "cardiovascular")
    assert "fc_desv_pct" in cardio["respuesta"]["datos_faltantes"]


def test_sensor_defectuoso_con_la_laptop3_apagada_lo_cubre_el_respaldo_local():
    # La copia local de las reglas en la Laptop 1 también aparta el dato y avisa.
    async def caso():
        async with pila.navegador(pila.crear_pila(laptop3_apagada=True)) as nav:
            await nav.post("/api/demo/dia", json={"dia": 5})
            return (await nav.post("/api/demo/sensor-defectuoso", json={"activo": True})).json()
    r = asyncio.run(caso())["resultado"]
    assert r["origen"] == "respaldo-local"
    assert r["nivel_global"] == "rojo"
    assert r["semaforo_indicadores"]["fc_reposo"]["nivel"] == "sospechoso"
    assert "El sensor de pulso en reposo parece fallar" in r["sensores_sospechosos"][0]["aviso"]
