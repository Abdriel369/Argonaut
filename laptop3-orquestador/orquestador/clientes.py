"""Clientes con los que el orquestador habla con los especialistas.

- ClienteHTTP:     el real. Gateway de la Laptop 2 por HTTP + modelo solar local.
- ClienteGuardado: modo demo en una sola máquina, con respuestas grabadas de ejecuciones reales.
- ClienteNulo:     ningún especialista (respaldo de la Laptop 1 cuando no hay orquestador).

Todos devuelven lo mismo: (respuestas por especialista, fallidos por especialista).
Ningún fallo de red lanza excepción hacia arriba: se convierte en "no disponible".
"""

import asyncio
import hashlib
import json
import logging
from pathlib import Path

import httpx

from comun.contratos import ErrorContrato, validar

log = logging.getLogger("orquestador.clientes")

ESPECIALISTAS_LAPTOP2 = ("sueno", "fatiga-bienestar", "cardiovascular")
ESPECIALISTA_LOCAL = "riesgo-solar"


def _motivo(error: Exception) -> str:
    """Motivo corto y legible de un fallo de red."""
    if isinstance(error, httpx.TimeoutException):
        return "no respondió a tiempo"
    if isinstance(error, httpx.ConnectError):
        return "no se pudo conectar"
    if isinstance(error, httpx.HTTPStatusError):
        return f"respondió con error {error.response.status_code}"
    if isinstance(error, ErrorContrato):
        return "respondió fuera de contrato"
    return f"fallo: {type(error).__name__}"


class ClienteHTTP:
    """Consulta al gateway de la Laptop 2 y al modelo solar local, en paralelo."""

    respuestas_guardadas = False

    def __init__(self, url_gateway: str, url_solar: str, tiempo_gateway_s: float = 4.5,
                 tiempo_solar_s: float = 3.0, tiempo_salud_s: float = 1.5,
                 transporte_gateway=None, transporte_solar=None):
        self.url_gateway = url_gateway.rstrip("/")
        self.url_solar = url_solar.rstrip("/")
        self.tiempo_gateway_s = tiempo_gateway_s
        self.tiempo_solar_s = tiempo_solar_s
        self.tiempo_salud_s = tiempo_salud_s
        self._transporte_gateway = transporte_gateway   # solo para pruebas en proceso
        self._transporte_solar = transporte_solar
        self.simular_caida_l2 = False                   # interruptor de la demo

    def _http(self, transporte, tiempo: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transporte, timeout=httpx.Timeout(tiempo, connect=min(tiempo, 2.0)))

    async def gateway_disponible(self) -> tuple[bool, str]:
        if self.simular_caida_l2:
            return False, "caída simulada desde el panel de demo"
        try:
            async with self._http(self._transporte_gateway, self.tiempo_salud_s) as http:
                respuesta = await http.get(f"{self.url_gateway}/salud")
                respuesta.raise_for_status()
            return True, "ok"
        except Exception as error:
            return False, _motivo(error)

    async def _consultar_gateway(self, consulta_id: str, especialistas: list, datos: dict, estado_l2):
        if not especialistas:
            return {}, {}
        # estado_l2 = (disponible, motivo) si el orquestador ya comprobó la salud del gateway.
        disponible, motivo = estado_l2 if estado_l2 is not None else await self.gateway_disponible()
        if not disponible:
            return {}, {nombre: f"Laptop 2 no disponible ({motivo})" for nombre in especialistas}
        consulta = validar("consulta_gateway",
                           {"consulta_id": consulta_id, "especialistas": especialistas, "datos": datos})
        try:
            async with self._http(self._transporte_gateway, self.tiempo_gateway_s) as http:
                respuesta = await http.post(f"{self.url_gateway}/consultar", json=consulta)
                respuesta.raise_for_status()
                cuerpo = validar("respuesta_gateway", respuesta.json())
        except Exception as error:
            log.warning("Gateway Laptop 2: %s", _motivo(error))
            return {}, {nombre: f"Laptop 2 {_motivo(error)}" for nombre in especialistas}
        respuestas, fallidos = {}, {f["especialista"]: f["motivo"] for f in cuerpo["fallidos"]}
        for item in cuerpo["respuestas"]:
            try:
                validar("respuesta_especialista", item)
                respuestas[item["especialista"]] = item
            except ErrorContrato as error:
                fallidos[item.get("especialista", "desconocido")] = _motivo(error)
        for nombre in especialistas:
            if nombre not in respuestas and nombre not in fallidos:
                fallidos[nombre] = "sin respuesta del gateway"
        return respuestas, fallidos

    async def _consultar_solar(self, consulta_id: str, datos: dict):
        consulta = {"consulta_id": consulta_id, "especialista": ESPECIALISTA_LOCAL, "datos": datos}
        try:
            async with self._http(self._transporte_solar, self.tiempo_solar_s) as http:
                respuesta = await http.post(f"{self.url_solar}/predecir", json=consulta)
                respuesta.raise_for_status()
                return {ESPECIALISTA_LOCAL: validar("respuesta_especialista", respuesta.json())}, {}
        except Exception as error:
            log.warning("Modelo solar local: %s", _motivo(error))
            return {}, {ESPECIALISTA_LOCAL: f"modelo solar {_motivo(error)}"}

    async def consultar(self, consulta_id: str, especialistas: list, datos: dict, estado_l2=None):
        de_laptop2 = [e for e in especialistas if e in ESPECIALISTAS_LAPTOP2]
        tareas = [self._consultar_gateway(consulta_id, de_laptop2, datos, estado_l2)]
        if ESPECIALISTA_LOCAL in especialistas:
            tareas.append(self._consultar_solar(consulta_id, datos))
        respuestas, fallidos = {}, {}
        for parcial_ok, parcial_mal in await asyncio.gather(*tareas):
            respuestas.update(parcial_ok)
            fallidos.update(parcial_mal)
        return respuestas, fallidos

    async def estado_red(self) -> dict:
        """Healthchecks para el indicador de estado de la interfaz."""
        estado = {
            "gateway": {"ok": False, "detalle": "", "simulada": self.simular_caida_l2, "modelos": {}},
            "modelo_solar": {"ok": False, "detalle": ""},
            "respuestas_guardadas": False,
        }
        if self.simular_caida_l2:
            estado["gateway"]["detalle"] = "caída simulada desde el panel de demo"
        else:
            try:
                async with self._http(self._transporte_gateway, self.tiempo_salud_s + 2.0) as http:
                    respuesta = await http.get(f"{self.url_gateway}/salud")
                    respuesta.raise_for_status()
                    cuerpo = respuesta.json()
                estado["gateway"].update(ok=True, detalle="ok", modelos=cuerpo.get("modelos", {}))
            except Exception as error:
                estado["gateway"]["detalle"] = _motivo(error)
        try:
            async with self._http(self._transporte_solar, self.tiempo_salud_s) as http:
                respuesta = await http.get(f"{self.url_solar}/salud")
                respuesta.raise_for_status()
                cuerpo = respuesta.json()
            estado["modelo_solar"].update(ok=True, detalle="ok", version=cuerpo.get("version_modelo"),
                                          dispositivo=cuerpo.get("dispositivo"))
        except Exception as error:
            estado["modelo_solar"]["detalle"] = _motivo(error)
        return estado


def clave_guardada(especialista: str, datos: dict) -> str:
    """Huella estable de una consulta: mismo especialista + mismos datos -> misma clave."""
    def redondear(objeto):
        if isinstance(objeto, float):
            return round(objeto, 4)
        if isinstance(objeto, dict):
            return {k: redondear(v) for k, v in sorted(objeto.items())}
        if isinstance(objeto, list):
            return [redondear(v) for v in objeto]
        return objeto
    canonico = json.dumps(redondear(datos), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(f"{especialista}|{canonico}".encode("utf-8")).hexdigest()[:20]


class ClienteGuardado:
    """Responde con resultados grabados de ejecuciones reales (modo demo sin las 3 laptops).

    Si llegan datos que no estaban en la grabación (por ejemplo un registro manual),
    ese especialista se marca como no disponible y el sistema sigue con las reglas.
    """

    respuestas_guardadas = True

    def __init__(self, ruta: Path):
        contenido = json.loads(Path(ruta).read_text(encoding="utf-8"))
        self.respuestas = contenido["respuestas"]
        self.meta = contenido.get("meta", {})
        self.simular_caida_l2 = False

    async def gateway_disponible(self) -> tuple[bool, str]:
        if self.simular_caida_l2:
            return False, "caída simulada desde el panel de demo"
        return True, "respuestas guardadas"

    async def consultar(self, consulta_id: str, especialistas: list, datos: dict, estado_l2=None):
        respuestas, fallidos = {}, {}
        for nombre in especialistas:
            if nombre in ESPECIALISTAS_LAPTOP2 and self.simular_caida_l2:
                fallidos[nombre] = "Laptop 2 no disponible (caída simulada desde el panel de demo)"
                continue
            guardada = self.respuestas.get(clave_guardada(nombre, datos))
            if guardada is None:
                fallidos[nombre] = "no hay respuesta guardada para estos datos (modo demo)"
                continue
            respuestas[nombre] = {**guardada, "consulta_id": consulta_id, "respuesta_guardada": True}
        return respuestas, fallidos

    async def estado_red(self) -> dict:
        ok_l2 = not self.simular_caida_l2
        detalle = "respuestas guardadas" if ok_l2 else "caída simulada desde el panel de demo"
        return {
            "gateway": {
                "ok": ok_l2, "detalle": detalle, "simulada": self.simular_caida_l2,
                "modelos": {n: {"ok": ok_l2, "detalle": detalle} for n in ESPECIALISTAS_LAPTOP2},
            },
            "modelo_solar": {"ok": True, "detalle": "respuestas guardadas"},
            "respuestas_guardadas": True,
        }


class ClienteNulo:
    """Sin especialistas: solo reglas. Lo usa la Laptop 1 como último respaldo."""

    respuestas_guardadas = False
    simular_caida_l2 = False

    def __init__(self, motivo: str = "orquestador no disponible"):
        self.motivo = motivo

    async def gateway_disponible(self) -> tuple[bool, str]:
        return False, self.motivo

    async def consultar(self, consulta_id: str, especialistas: list, datos: dict, estado_l2=None):
        return {}, {nombre: self.motivo for nombre in especialistas}

    async def estado_red(self) -> dict:
        return {"gateway": {"ok": False, "detalle": self.motivo, "simulada": False, "modelos": {}},
                "modelo_solar": {"ok": False, "detalle": self.motivo}, "respuestas_guardadas": False}
