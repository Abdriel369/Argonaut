"""Monta las tres "laptops" dentro de un solo proceso de Python, sin red.

Cada servicio es la aplicación real; solo se sustituye el cable (HTTP) por un
transporte en memoria. Sirve para las pruebas de integración y para grabar las
respuestas del modo demo.
"""

import httpx

import api_cardio
import api_fatiga
import api_solar
import api_sueno
from backend.ajustes import Ajustes
from backend.principal import crear_app as crear_backend
from gateway.principal import crear_app as crear_gateway
from orquestador.clientes import ClienteHTTP
from orquestador.principal import crear_app as crear_orquestador


def _sin_conexion(peticion: httpx.Request):
    """Simula una laptop apagada: nadie contesta en esa dirección."""
    raise httpx.ConnectError("Laptop apagada (simulación de prueba)", request=peticion)


def crear_gateway_en_proceso(modelos_caidos=()):
    """Gateway real conectado a los tres modelos reales de la Laptop 2."""
    aplicaciones = {"sueno": api_sueno.app, "fatiga-bienestar": api_fatiga.app,
                    "cardiovascular": api_cardio.app}
    transportes = {
        nombre: (httpx.MockTransport(_sin_conexion) if nombre in modelos_caidos
                 else httpx.ASGITransport(app=aplicacion))
        for nombre, aplicacion in aplicaciones.items()
    }
    return crear_gateway(urls={nombre: f"http://modelo-{nombre}" for nombre in aplicaciones},
                         transportes=transportes)


def crear_cliente_especialistas(laptop2_apagada=False, solar_apagado=False, modelos_caidos=(),
                                clase=ClienteHTTP):
    """Cliente del orquestador hacia el gateway (Laptop 2) y el modelo solar (Laptop 3)."""
    return clase(
        url_gateway="http://laptop2-gateway", url_solar="http://modelo-solar",
        transporte_gateway=(httpx.MockTransport(_sin_conexion) if laptop2_apagada
                            else httpx.ASGITransport(app=crear_gateway_en_proceso(modelos_caidos))),
        transporte_solar=(httpx.MockTransport(_sin_conexion) if solar_apagado
                          else httpx.ASGITransport(app=api_solar.app)),
    )


def crear_pila(laptop2_apagada=False, laptop3_apagada=False, solar_apagado=False,
               modelos_caidos=(), cliente_especialistas=None):
    """Devuelve la aplicación del backend con toda la pila conectada detrás."""
    cliente = cliente_especialistas or crear_cliente_especialistas(laptop2_apagada, solar_apagado, modelos_caidos)
    orquestador = crear_orquestador(cliente=cliente)
    ajustes = Ajustes.desde_entorno()
    ajustes.ruta_bd = ":memory:"
    ajustes.url_orquestador = "http://laptop3-orquestador"
    ajustes.reintentos_orquestador = 0 if laptop3_apagada else 1
    transporte = (httpx.MockTransport(_sin_conexion) if laptop3_apagada
                  else httpx.ASGITransport(app=orquestador))
    return crear_backend(ajustes, transporte_orquestador=transporte)


def navegador(app) -> httpx.AsyncClient:
    """Cliente HTTP que habla con el backend como lo haría la interfaz web."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://laptop1", timeout=30)
