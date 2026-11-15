"""API del backend (Laptop 1) y servidor de la interfaz web.

Arranque:  uvicorn backend.principal:crear_app --factory --host 0.0.0.0 --port 8100
La interfaz se abre en http://IP_LAPTOP1:8100/ desde la laptop o el celular.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from backend.ajustes import Ajustes
from backend.bd import BaseDatos
from backend.cliente_orquestador import ClienteOrquestador
from backend.servicio import ErrorDatos, Servicio
from comun import AVISO
from comun.registro import configurar_logs


def crear_app(ajustes: Ajustes | None = None, transporte_orquestador=None) -> FastAPI:
    """'transporte_orquestador' permite conectar el orquestador en proceso durante las pruebas."""
    configurar_logs("backend")
    ajustes = ajustes or Ajustes.desde_entorno()
    cliente = ClienteOrquestador(ajustes.url_orquestador, ajustes.tiempo_max_orquestador_s,
                                 ajustes.reintentos_orquestador, transporte_orquestador)
    servicio = Servicio(ajustes, BaseDatos(ajustes.ruta_bd), cliente)
    app = FastAPI(title="Médico de estación · backend", version="1.0.0")
    app.state.servicio = servicio

    async def protegido(corrutina):
        """Convierte un dato rechazado en un 422 con mensaje sencillo."""
        try:
            return await corrutina
        except ErrorDatos as error:
            raise HTTPException(status_code=422, detail=str(error))

    @app.get("/salud")
    def salud():
        return {"estado": "ok", "servicio": "backend", "version": app.version, "aviso": AVISO}

    # ---- lectura ----------------------------------------------------------
    @app.get("/api/estado")
    async def estado(astronauta_id: str | None = None):
        return await protegido(servicio.estado(astronauta_id))

    @app.get("/api/red")
    async def red():
        return await cliente.red()

    @app.get("/api/historial")
    def historial(astronauta_id: str | None = None):
        return {"historial": servicio.bd.historial(
            servicio.dia_actual, astronauta_id or servicio.astronauta_activo)}

    @app.get("/api/informes")
    def informes(astronauta_id: str | None = None):
        return {"informes": servicio._informes(
            servicio.dia_actual, astronauta_id or servicio.astronauta_activo)}

    @app.get("/api/exportar.csv", response_class=PlainTextResponse)
    def exportar(astronauta_id: str | None = None):
        return PlainTextResponse(
            servicio.exportar_csv(astronauta_id), media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="astro-medico-historial.csv"'})

    # ---- vista de tripulación ---------------------------------------------
    @app.get("/api/tripulacion")
    async def tripulacion(dia: int | None = None):
        return await protegido(servicio.tripulacion(dia))

    @app.post("/api/tripulacion/activo")
    async def tripulacion_activo(cuerpo: dict):
        astronauta_id = cuerpo.get("astronauta_id")
        if not astronauta_id:
            raise HTTPException(status_code=422, detail="Falta astronauta_id.")
        return await protegido(servicio.cambiar_activo(str(astronauta_id)))

    @app.get("/api/tripulacion/{astronauta_id}")
    async def tripulacion_detalle(astronauta_id: str, dia: int | None = None):
        return await protegido(servicio.detalle_tripulacion(astronauta_id, dia))

    # ---- reloj inteligente (simulación web) -------------------------------
    @app.get("/api/reloj/estado")
    async def reloj_estado(astronauta_id: str | None = None):
        return await protegido(servicio.estado_reloj(
            astronauta_id or servicio.astronauta_activo))

    @app.post("/api/reloj/lectura")
    async def reloj_lectura(cuerpo: dict):
        return await protegido(servicio.registrar_lectura_reloj(cuerpo))

    # ---- entrada de datos -------------------------------------------------
    @app.post("/api/registro")
    async def registro(cuerpo: dict):
        return await protegido(servicio.registrar_manual(
            cuerpo.get("indicadores") or {}, cuerpo.get("astronauta_id")))

    @app.post("/api/checkin/animo")
    async def checkin_animo(cuerpo: dict):
        return await protegido(servicio.checkin_animo(cuerpo.get("valor"), cuerpo.get("astronauta_id")))

    @app.post("/api/checkin/reaccion")
    async def checkin_reaccion(cuerpo: dict):
        return await protegido(servicio.checkin_reaccion(
            cuerpo.get("tiempos_ms"), cuerpo.get("astronauta_id")))

    @app.post("/api/checkin/equipo")
    async def checkin_equipo(cuerpo: dict):
        return await protegido(servicio.checkin_equipo(cuerpo, cuerpo.get("astronauta_id")))

    @app.post("/api/protocolo/paso")
    def protocolo_paso(cuerpo: dict):
        if not cuerpo.get("alerta_id") or not cuerpo.get("paso_id"):
            raise HTTPException(status_code=422, detail="Faltan alerta_id o paso_id.")
        return servicio.marcar_paso(str(cuerpo["alerta_id"]), str(cuerpo["paso_id"]),
                                    bool(cuerpo.get("hecho")), cuerpo.get("astronauta_id"))

    @app.post("/api/reevaluar")
    async def reevaluar():
        return await servicio.reevaluar()

    # ---- panel de demo ----------------------------------------------------
    @app.post("/api/demo/dia")
    async def demo_dia(cuerpo: dict):
        return await protegido(servicio.fijar_dia(cuerpo.get("dia")))

    @app.post("/api/demo/evento-solar")
    async def demo_evento_solar(cuerpo: dict):
        return await servicio.evento_solar(bool(cuerpo.get("activo", True)))

    @app.post("/api/demo/sensor-defectuoso")
    async def demo_sensor_defectuoso(cuerpo: dict):
        """{"activo": true|false, "tipo": "imposible"|"salto"|"congelado", "indicador": opcional}"""
        return await protegido(servicio.sensor_defectuoso(
            bool(cuerpo.get("activo", True)), cuerpo.get("tipo") or "imposible", cuerpo.get("indicador")))

    @app.post("/api/demo/caida-laptop2")
    async def demo_caida_laptop2(cuerpo: dict):
        return await protegido(servicio.caida_laptop2(bool(cuerpo.get("activa"))))

    @app.post("/api/demo/enlace-tierra")
    async def demo_enlace_tierra():
        return await servicio.enlace_tierra()

    @app.post("/api/demo/reiniciar")
    async def demo_reiniciar():
        return await servicio.reiniciar()

    # ---- interfaz web (archivos locales, sin CDN) --------------------------
    @app.get("/reloj", include_in_schema=False)
    def reloj_sin_barra():
        """StaticFiles(html=True) sirve /reloj/; esta ruta evita un 404 sin la barra."""
        return RedirectResponse(url="/reloj/")

    if ajustes.dir_frontend.is_dir():
        app.mount("/", StaticFiles(directory=ajustes.dir_frontend, html=True), name="frontend")

    return app
