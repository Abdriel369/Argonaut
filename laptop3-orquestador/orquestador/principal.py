"""Servicio HTTP del orquestador (Laptop 3).

  POST /evaluar            entrada_orquestador -> resultado_final
  GET  /salud              healthcheck
  GET  /red                estado del gateway de la Laptop 2 y del modelo solar
  POST /demo/caida-laptop2 {"activa": true|false}  simula que la Laptop 2 se cae
  GET  /info               reglas, umbrales y tabla de enrutamiento vigentes

Arranque:  uvicorn orquestador.principal:crear_app --factory --host 0.0.0.0 --port 8300
"""

import os

from fastapi import FastAPI, HTTPException

from comun import AVISO
from comun.contratos import ErrorContrato
from comun.registro import configurar_logs
from orquestador import nucleo
from orquestador.clientes import ClienteGuardado, ClienteHTTP


def cliente_desde_entorno():
    """Lee las direcciones del archivo .env (nada de IP escritas en el código)."""
    guardadas = os.environ.get("RESPUESTAS_GUARDADAS", "").strip()
    if guardadas:
        return ClienteGuardado(guardadas)
    tiempo_modelo = float(os.environ.get("TIEMPO_MAX_MODELO_S", "3"))
    return ClienteHTTP(
        url_gateway=os.environ.get("URL_GATEWAY", "http://127.0.0.1:8200"),
        url_solar=os.environ.get("URL_MODELO_SOLAR", "http://127.0.0.1:8310"),
        # El gateway espera hasta TIEMPO_MAX_MODELO_S por modelo; le damos un margen.
        tiempo_gateway_s=tiempo_modelo + 1.5,
        tiempo_solar_s=tiempo_modelo,
    )


def crear_app(cliente=None, config=None) -> FastAPI:
    log = configurar_logs("orquestador")
    cliente = cliente or cliente_desde_entorno()
    config = config or nucleo.cargar_configuracion()
    app = FastAPI(title="Orquestador · junta médica de modelos", version="1.0.0")
    app.state.cliente = cliente

    @app.get("/salud")
    def salud():
        return {"estado": "ok", "servicio": "orquestador", "version": app.version,
                "respuestas_guardadas": cliente.respuestas_guardadas,
                "caida_laptop2_simulada": cliente.simular_caida_l2}

    @app.get("/red")
    async def red():
        return await cliente.estado_red()

    @app.post("/evaluar")
    async def evaluar(entrada: dict):
        try:
            return await nucleo.evaluar(entrada, cliente, config)
        except ErrorContrato as error:
            raise HTTPException(status_code=422, detail=str(error))

    @app.post("/demo/caida-laptop2")
    def caida_laptop2(cuerpo: dict):
        cliente.simular_caida_l2 = bool(cuerpo.get("activa"))
        log.info("Caída simulada de la Laptop 2: %s", cliente.simular_caida_l2)
        return {"caida_laptop2_simulada": cliente.simular_caida_l2}

    @app.get("/info")
    def info():
        return {"aviso": AVISO, "umbrales": config.reglas, "enrutamiento": config.orquestador["rutas"],
                "especialistas": config.orquestador["especialistas"],
                "escalamiento": config.orquestador["escalamiento"]}

    return app
