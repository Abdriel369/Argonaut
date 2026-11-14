"""Pruebas comunes de los cuatro especialistas: métricas, contrato, datos incompletos y API HTTP.

Cada modelo tiene su carpeta 'pruebas/' con llamadas a estas funciones.
"""

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from comun import AVISO
from comun.contratos import validar
from comun.especialista.nucleo import Definicion, ModeloEspecialista, ruta_metricas, ruta_modelo


def comprobar_modelo(definicion: Definicion, carpeta: Path, datos: dict) -> None:
    carpeta = Path(carpeta)
    modelo = ModeloEspecialista(definicion, carpeta, dispositivo="cpu")

    metricas = json.loads(ruta_metricas(definicion, carpeta).read_text(encoding="utf-8"))
    assert metricas["auc"] >= definicion.auc_minimo, f"AUC {metricas['auc']} por debajo del mínimo"
    assert metricas["datos_entrenamiento"] == "sintéticos"
    huella = hashlib.sha256(ruta_modelo(definicion, carpeta).read_bytes()).hexdigest()
    assert metricas["sha256_modelo"] == huella, "El artefacto guardado no coincide con sus métricas"

    respuesta = {"consulta_id": "prueba", **modelo.predecir(datos)}
    validar("respuesta_especialista", respuesta)
    assert respuesta["factores"], "Debe explicar su predicción con factores"
    assert 0.0 <= respuesta["riesgo"] <= 1.0
    assert modelo.predecir(datos) == modelo.predecir(datos), "La predicción debe ser determinista"

    vacio = {"dia_mision": 5, "indicadores": {}, "tendencias_7d": {}, "linea_base": {}, "plan": {}, "contexto": {}}
    pobre = {"consulta_id": "prueba", **modelo.predecir(vacio)}
    validar("respuesta_especialista", pobre)
    assert pobre["datos_faltantes"], "Con datos vacíos debe listar lo que falta"
    assert pobre["confianza"] < respuesta["confianza"], "Con datos faltantes la confianza debe bajar"


def comprobar_api(app, definicion: Definicion, datos: dict) -> None:
    cliente = TestClient(app)

    salud = cliente.get("/salud").json()
    assert salud["estado"] == "ok" and salud["version_modelo"] == definicion.version

    info = cliente.get("/info").json()
    assert info["aviso"] == AVISO
    assert info["datos_entrenamiento"] == "sintéticos"
    assert len(info["limitaciones"]) >= 2, "Debe documentar sus limitaciones"

    consulta = {"consulta_id": "prueba-api", "especialista": definicion.nombre, "datos": datos}
    correcta = cliente.post("/predecir", json=consulta)
    assert correcta.status_code == 200, correcta.text
    validar("respuesta_especialista", correcta.json())

    otro = "riesgo-solar" if definicion.nombre != "riesgo-solar" else "sueno"
    assert cliente.post("/predecir", json={**consulta, "especialista": otro}).status_code == 422
    assert cliente.post("/predecir", json={"consulta_id": "x"}).status_code == 422
