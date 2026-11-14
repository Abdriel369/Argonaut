"""Gateway de la Laptop 2: único punto de entrada a los 3 modelos especialistas.

  POST /consultar  reparte la consulta a los especialistas pedidos, en paralelo,
                   con un tiempo máximo por modelo, y devuelve lo que haya respondido
                   marcando los que fallaron.
  GET  /salud      estado del gateway y de cada modelo
  GET  /info       ficha de cada modelo (versión, métricas, limitaciones)

Arranque:  uvicorn gateway.principal:crear_app --factory --host 0.0.0.0 --port 8200
"""

import asyncio
import os
import time

import httpx
from fastapi import FastAPI, HTTPException

from comun import AVISO
from comun.contratos import ErrorContrato, validar
from comun.registro import configurar_logs

# Nombre del especialista -> variable de entorno con su dirección dentro de la Laptop 2.
VARIABLES_URL = {
    "sueno": ("URL_MODELO_SUENO", "http://127.0.0.1:8210"),
    "fatiga-bienestar": ("URL_MODELO_FATIGA", "http://127.0.0.1:8220"),
    "cardiovascular": ("URL_MODELO_CARDIO", "http://127.0.0.1:8230"),
}


def urls_desde_entorno() -> dict:
    return {nombre: os.environ.get(variable, defecto).rstrip("/")
            for nombre, (variable, defecto) in VARIABLES_URL.items()}


def crear_app(urls: dict | None = None, transportes: dict | None = None,
              tiempo_max_s: float | None = None) -> FastAPI:
    """'transportes' permite conectar los modelos en proceso durante las pruebas."""
    log = configurar_logs("gateway")
    urls = urls or urls_desde_entorno()
    transportes = transportes or {}
    tiempo_max_s = tiempo_max_s or float(os.environ.get("TIEMPO_MAX_MODELO_S", "3"))
    app = FastAPI(title="Gateway de modelos · Laptop 2", version="1.0.0")

    def http(nombre: str, tiempo: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transportes.get(nombre),
                                 timeout=httpx.Timeout(tiempo, connect=min(tiempo, 2.0)))

    def motivo(error: Exception) -> str:
        if isinstance(error, httpx.TimeoutException):
            return f"no respondió en {tiempo_max_s:g} s"
        if isinstance(error, httpx.ConnectError):
            return "no se pudo conectar con el modelo"
        if isinstance(error, httpx.HTTPStatusError):
            return f"el modelo respondió con error {error.response.status_code}"
        if isinstance(error, ErrorContrato):
            return "el modelo respondió fuera de contrato"
        return f"fallo: {type(error).__name__}"

    async def preguntar(nombre: str, consulta_id: str, datos: dict):
        """Devuelve (nombre, respuesta, None) o (nombre, None, motivo del fallo)."""
        consulta = {"consulta_id": consulta_id, "especialista": nombre, "datos": datos}
        try:
            async with http(nombre, tiempo_max_s) as cliente:
                respuesta = await cliente.post(f"{urls[nombre]}/predecir", json=consulta)
                respuesta.raise_for_status()
                return nombre, validar("respuesta_especialista", respuesta.json()), None
        except Exception as error:
            log.warning("Modelo %s: %s", nombre, motivo(error))
            return nombre, None, motivo(error)

    async def salud_modelo(nombre: str):
        try:
            async with http(nombre, 1.5) as cliente:
                respuesta = await cliente.get(f"{urls[nombre]}/salud")
                respuesta.raise_for_status()
                cuerpo = respuesta.json()
            return nombre, {"ok": True, "detalle": "ok", "version": cuerpo.get("version_modelo"),
                            "dispositivo": cuerpo.get("dispositivo")}
        except Exception as error:
            return nombre, {"ok": False, "detalle": motivo(error)}

    @app.post("/consultar")
    async def consultar(consulta: dict):
        inicio = time.perf_counter()
        try:
            validar("consulta_gateway", consulta)
        except ErrorContrato as error:
            raise HTTPException(status_code=422, detail=str(error))
        resultados = await asyncio.gather(*[
            preguntar(nombre, consulta["consulta_id"], consulta["datos"])
            for nombre in consulta["especialistas"]
        ])
        salida = {
            "consulta_id": consulta["consulta_id"],
            "respuestas": [respuesta for _, respuesta, _ in resultados if respuesta is not None],
            "fallidos": [{"especialista": nombre, "motivo": fallo}
                         for nombre, respuesta, fallo in resultados if respuesta is None],
        }
        validar("respuesta_gateway", salida)
        log.info("consulta=%s respondieron=%d fallaron=%d (%.0f ms)", consulta["consulta_id"],
                 len(salida["respuestas"]), len(salida["fallidos"]), 1000 * (time.perf_counter() - inicio))
        return salida

    @app.get("/salud")
    async def salud():
        modelos = dict(await asyncio.gather(*[salud_modelo(nombre) for nombre in urls]))
        todos = all(m["ok"] for m in modelos.values())
        return {"estado": "ok" if todos else "parcial", "servicio": "gateway", "modelos": modelos}

    @app.get("/info")
    async def info():
        fichas = {}
        for nombre in urls:
            try:
                async with http(nombre, 2.0) as cliente:
                    fichas[nombre] = (await cliente.get(f"{urls[nombre]}/info")).json()
            except Exception as error:
                fichas[nombre] = {"error": motivo(error)}
        return {"aviso": AVISO, "modelos": fichas}

    return app
