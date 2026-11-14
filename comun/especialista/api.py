"""API HTTP común de los especialistas: POST /predecir, GET /salud, GET /info."""

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException

from comun import AVISO
from comun.contratos import ErrorContrato, validar
from comun.especialista.nucleo import Definicion, ModeloEspecialista
from comun.registro import configurar_logs


def crear_app(definicion: Definicion, carpeta_artefactos: Path) -> FastAPI:
    """Crea el servicio de un especialista. El modelo se carga una sola vez al arrancar."""
    log = configurar_logs(f"modelo-{definicion.nombre}")
    modelo = ModeloEspecialista(definicion, carpeta_artefactos)
    log.info("Modelo %s v%s listo en %s", definicion.nombre, definicion.version, modelo.dispositivo)

    app = FastAPI(title=f"Especialista: {definicion.titulo}", version=definicion.version)
    app.state.modelo = modelo

    @app.get("/salud")
    def salud():
        return {
            "estado": "ok",
            "servicio": f"modelo-{definicion.nombre}",
            "version_modelo": definicion.version,
            "dispositivo": modelo.dispositivo,
        }

    @app.get("/info")
    def info():
        return {**modelo.info(), "aviso": AVISO}

    @app.post("/predecir")
    def predecir(consulta: dict):
        inicio = time.perf_counter()
        try:
            validar("consulta_especialista", consulta)
        except ErrorContrato as error:
            raise HTTPException(status_code=422, detail=str(error))
        if consulta["especialista"] != definicion.nombre:
            raise HTTPException(
                status_code=422,
                detail=f"Esta consulta es para '{consulta['especialista']}', no para '{definicion.nombre}'.",
            )
        respuesta = {"consulta_id": consulta["consulta_id"], **modelo.predecir(consulta["datos"])}
        validar("respuesta_especialista", respuesta)   # nunca devolvemos algo fuera de contrato
        log.info("consulta=%s riesgo=%.2f nivel=%s (%.0f ms)", consulta["consulta_id"],
                 respuesta["riesgo"], respuesta["nivel"], 1000 * (time.perf_counter() - inicio))
        return respuesta

    return app
