"""Entrypoint único de la demo de Argonaut para Render.

Un solo proceso, un solo contenedor y un solo servicio:

  * El backend (FastAPI) sirve la interfaz web y la API en el mismo puerto.
  * El orquestador (reglas, junta de especialistas, protocolos, informe) se
    monta EN PROCESO como aplicación ASGI.
  * Las llamadas del backend al orquestador usan ``httpx.ASGITransport``: no se
    abren sockets, no hay un segundo servicio y no se depende de ninguna IP.
  * Los especialistas responden desde ``respuestas-guardadas.json`` con
    ``ClienteGuardado`` (88 respuestas de ejecuciones reales). No se cargan
    modelos de IA: la demo no necesita xgboost, sklearn ni GPU.

Variables de entorno relevantes (las fija el Dockerfile con valores por defecto):

  RUTA_BD               SQLite temporal, por ejemplo /tmp/astro_medico.db
  RESPUESTAS_GUARDADAS  ruta del JSON con las respuestas grabadas
  PORT                  puerto que asigna Render (lo usa uvicorn)
  URL_ORQUESTADOR       solo una URL simbólica: el transporte es en proceso
"""

import logging
import os
from pathlib import Path

import httpx

from backend.ajustes import Ajustes
from backend.principal import crear_app as crear_backend
from comun.registro import configurar_logs
from orquestador.clientes import ClienteNulo
from orquestador.principal import cliente_desde_entorno
from orquestador.principal import crear_app as crear_orquestador

log = logging.getLogger("render")

# La imagen copia el JSON a /app; en el repositorio vive en modo-demo-sin-laptops/.
RUTAS_GUARDADAS = (
    Path("/app/respuestas-guardadas.json"),
    Path(__file__).resolve().parents[2] / "modo-demo-sin-laptops" / "respuestas-guardadas.json",
)


def _ruta_respuestas_guardadas() -> str:
    """Ruta del JSON de respuestas grabadas, sin obligar a definir la variable."""
    indicada = os.environ.get("RESPUESTAS_GUARDADAS", "").strip()
    if indicada:
        return indicada
    for candidata in RUTAS_GUARDADAS:
        if candidata.is_file():
            return str(candidata)
    return ""


def crear_app():
    """Construye la aplicación integrada: backend + orquestador en la misma app.

    Se puede llamar desde las pruebas; el módulo también expone ``app`` para
    ``uvicorn app:app``.
    """
    # Un solo formato de log para el servicio integrado (backend + orquestador).
    configurar_logs("demo")

    # httpx exige una URL absoluta aunque el transporte sea ASGI y no haya red.
    os.environ.setdefault("URL_ORQUESTADOR", "http://orquestador.interno")

    ruta_guardadas = _ruta_respuestas_guardadas()
    if ruta_guardadas:
        os.environ["RESPUESTAS_GUARDADAS"] = ruta_guardadas
    try:
        cliente_especialistas = cliente_desde_entorno()
    except (OSError, ValueError, KeyError) as error:
        # La demo no se cae si falta la grabación: sigue con reglas y modo degradado.
        log.error("No se pudo leer la grabación de especialistas (%s): %s", ruta_guardadas, error)
        cliente_especialistas = ClienteNulo("respuestas guardadas no disponibles")

    orquestador = crear_orquestador(cliente=cliente_especialistas)
    transporte = httpx.ASGITransport(app=orquestador)

    ajustes = Ajustes.desde_entorno()
    app = crear_backend(ajustes=ajustes, transporte_orquestador=transporte)

    # Útil para /salud, para depurar y para las pruebas de integración.
    app.state.orquestador = orquestador
    app.state.especialistas = cliente_especialistas

    log.info(
        "Demo integrada lista: orquestador en proceso, respuestas_guardadas=%s, "
        "especialistas=%s, bd=%s, frontend=%s",
        bool(getattr(cliente_especialistas, "respuestas_guardadas", False)),
        type(cliente_especialistas).__name__,
        ajustes.ruta_bd,
        ajustes.dir_frontend,
    )
    return app


app = crear_app()
