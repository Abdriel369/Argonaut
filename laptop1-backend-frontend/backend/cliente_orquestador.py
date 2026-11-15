"""Cliente HTTP hacia el orquestador (Laptop 3), con tiempo máximo, reintentos y respaldo.

Tolerancia a fallos: si la Laptop 3 no responde tras los reintentos, la Laptop 1
evalúa con el MISMO motor de reglas en local (sin especialistas) y lo indica.
"""

import asyncio
import logging

import httpx

from comun.contratos import ErrorContrato, validar
from orquestador import nucleo
from orquestador.clientes import ClienteNulo

log = logging.getLogger("backend.orquestador")


class ClienteOrquestador:
    def __init__(self, url: str, tiempo_max_s: float = 8.0, reintentos: int = 2, transporte=None):
        self.url = url.rstrip("/")
        self.tiempo_max_s = tiempo_max_s
        self.reintentos = reintentos
        self._transporte = transporte            # solo para pruebas en proceso
        self._config_local = nucleo.cargar_configuracion()

    def _http(self, tiempo: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transporte,
                                 timeout=httpx.Timeout(tiempo, connect=min(tiempo, 2.0)))

    async def evaluar(self, entrada: dict, tiempo_max_s: float | None = None,
                      reintentos: int | None = None) -> tuple[dict, dict]:
        """Devuelve (resultado_final, info de conexión). Nunca lanza por fallos de red.

        ``tiempo_max_s`` y ``reintentos`` permiten un camino corto (por ejemplo, el
        detalle de un astronauta: 4 s y sin reintentos) sin tocar la configuración
        del flujo principal.
        """
        validar("entrada_orquestador", entrada)
        tiempo = self.tiempo_max_s if tiempo_max_s is None else float(tiempo_max_s)
        intentos_totales = self.reintentos if reintentos is None else max(0, int(reintentos))
        ultimo_error = ""
        for intento in range(1, intentos_totales + 2):
            try:
                async with self._http(tiempo) as http:
                    respuesta = await http.post(f"{self.url}/evaluar", json=entrada)
                    respuesta.raise_for_status()
                    resultado = validar("resultado_final", respuesta.json())
                return resultado, {"ok": True, "detalle": "ok", "intentos": intento}
            except (httpx.HTTPError, ErrorContrato, ValueError) as error:
                ultimo_error = type(error).__name__
                log.warning("Orquestador: intento %d de %d falló (%s)", intento, intentos_totales + 1, ultimo_error)
                if intento <= intentos_totales:
                    await asyncio.sleep(0.3 * intento)   # espera corta antes de reintentar

        # Respaldo local: mismas reglas, sin junta de especialistas.
        log.error("Orquestador no disponible; se evalúa con las reglas locales de la Laptop 1.")
        resultado = await nucleo.evaluar(
            entrada, ClienteNulo("orquestador (Laptop 3) no disponible"),
            self._config_local, origen="respaldo-local")
        return resultado, {"ok": False, "detalle": f"sin respuesta ({ultimo_error})",
                           "intentos": intentos_totales + 1}

    async def red(self) -> dict:
        """Estado de las tres laptops y del modelo solar, visto desde la Laptop 1."""
        estado = {
            "laptop1": {"ok": True, "detalle": "backend y frontend"},
            "laptop3": {"ok": False, "detalle": ""},
            "laptop2": {"ok": False, "detalle": "desconocido: la Laptop 3 no responde",
                        "simulada": False, "modelos": {}},
            "modelo_solar": {"ok": False, "detalle": "desconocido: la Laptop 3 no responde"},
            "respuestas_guardadas": False,
        }
        try:
            async with self._http(6.0) as http:
                respuesta = await http.get(f"{self.url}/red")
                respuesta.raise_for_status()
                cuerpo = respuesta.json()
            estado["laptop3"] = {"ok": True, "detalle": "orquestador"}
            estado["laptop2"] = cuerpo["gateway"]
            estado["modelo_solar"] = cuerpo["modelo_solar"]
            estado["respuestas_guardadas"] = bool(cuerpo.get("respuestas_guardadas"))
        except (httpx.HTTPError, ValueError, KeyError) as error:
            estado["laptop3"]["detalle"] = f"sin respuesta ({type(error).__name__})"
        return estado

    async def caida_laptop2(self, activa: bool) -> bool:
        """Pide al orquestador simular la caída de la Laptop 2. Devuelve True si lo aceptó."""
        try:
            async with self._http(3.0) as http:
                respuesta = await http.post(f"{self.url}/demo/caida-laptop2", json={"activa": activa})
                respuesta.raise_for_status()
            return True
        except httpx.HTTPError:
            return False
