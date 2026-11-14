"""Entradas del orquestador construidas con el MISMO código que usa el backend.

Así las pruebas de reglas y modelos parten de exactamente lo que recibiría el
orquestador durante la demo, sin copiar cifras a mano.
"""

from backend.ajustes import Ajustes
from backend.bd import BaseDatos
from backend.cliente_orquestador import ClienteOrquestador
from backend.servicio import Servicio


def entrada(dia: int, evento: bool = False, sobre: dict | None = None) -> dict:
    """Entrada del orquestador para 'dia' sobre el guion de 7 días.

    evento: si hay tormenta solar activa ese día.
    sobre:  {dia: {indicador: valor}} cambios sobre el guion (None = sin dato).
    """
    ajustes = Ajustes.desde_entorno()
    ajustes.ruta_bd = ":memory:"
    servicio = Servicio(ajustes, BaseDatos(":memory:"), ClienteOrquestador("http://no-usado"))
    for dia_cambio, valores in (sobre or {}).items():
        registro = servicio.bd.registros()[dia_cambio]
        servicio.bd.guardar_registro(
            dia_cambio, {**registro["indicadores"], **valores}, registro["manuales"] + list(valores))
    servicio.bd.guardar_estado("evento_solar_dia", dia if evento else None)
    return servicio.construir_entrada(dia)
