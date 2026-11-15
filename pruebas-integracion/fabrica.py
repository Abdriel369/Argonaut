"""Entradas del orquestador construidas con el MISMO código que usa el backend.

Así las pruebas de reglas y modelos parten de exactamente lo que recibiría el
orquestador durante la demo, sin copiar cifras a mano.
"""

from backend.ajustes import Ajustes
from backend.bd import BaseDatos
from backend.cliente_orquestador import ClienteOrquestador
from backend.servicio import Servicio


def servicio_de_prueba(evento_dia: int | None = None, sobre: dict | None = None,
                       sensor: dict | None = None) -> Servicio:
    """Servicio del backend en memoria, con el guion de 7 días cargado.

    sobre:  {dia: {indicador: valor}} datos ingresados A MANO sobre el guion (None = sin dato).
    sensor: {dia: {indicador: valor}} lecturas que llegan DEL SENSOR (no cuentan como manuales).
    """
    ajustes = Ajustes.desde_entorno()
    ajustes.ruta_bd = ":memory:"
    servicio = Servicio(ajustes, BaseDatos(":memory:"), ClienteOrquestador("http://no-usado"))
    for dia_cambio, valores in (sobre or {}).items():
        registro = servicio.bd.registros()[dia_cambio]
        servicio.bd.guardar_registro(
            dia_cambio, {**registro["indicadores"], **valores}, registro["manuales"] + list(valores))
    for dia_cambio, valores in (sensor or {}).items():
        registro = servicio.bd.registros()[dia_cambio]
        servicio.bd.guardar_registro(dia_cambio, {**registro["indicadores"], **valores}, registro["manuales"])
    servicio.bd.guardar_estado("evento_solar_dia", evento_dia)
    return servicio


def entrada(dia: int, evento: bool = False, sobre: dict | None = None, sensor: dict | None = None) -> dict:
    """Entrada del orquestador para 'dia' sobre el guion de 7 días.

    evento: si hay tormenta solar activa ese día.
    sobre:  {dia: {indicador: valor}} cambios a mano sobre el guion (None = sin dato).
    sensor: {dia: {indicador: valor}} lecturas del sensor (pasan por la validación completa).
    """
    return servicio_de_prueba(dia if evento else None, sobre, sensor).construir_entrada(dia)
