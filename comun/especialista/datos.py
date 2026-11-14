"""Ayudas para leer el bloque 'datos' de una consulta sin romperse si falta algo.

Todas devuelven None cuando no hay dato; el modelo lo imputa y baja su confianza.
"""

import math


def valor(datos: dict, indicador: str):
    """Valor de hoy de un indicador, o None."""
    v = (datos.get("indicadores") or {}).get(indicador)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def serie(datos: dict, indicador: str) -> list[float]:
    """Valores de los últimos días (del más antiguo a hoy), sin los 'sin dato'."""
    crudos = (datos.get("tendencias_7d") or {}).get(indicador) or []
    limpios = [float(v) for v in crudos if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if not limpios and valor(datos, indicador) is not None:
        limpios = [valor(datos, indicador)]
    return limpios


def media_ultimos(datos: dict, indicador: str, n: int):
    """Media de los últimos n días disponibles."""
    ultimos = serie(datos, indicador)[-n:]
    return sum(ultimos) / len(ultimos) if ultimos else None


def irregularidad(datos: dict, indicador: str):
    """Desviación típica de la semana (qué tanto cambia de un día a otro). Necesita 3 días."""
    valores = serie(datos, indicador)
    if len(valores) < 3:
        return None
    media = sum(valores) / len(valores)
    return math.sqrt(sum((v - media) ** 2 for v in valores) / len(valores))


def desviacion_pct(datos: dict, indicador: str):
    """Desviación porcentual de hoy contra la línea base personal."""
    desviacion = (datos.get("desviaciones_vs_base") or {}).get(indicador)
    if isinstance(desviacion, dict) and isinstance(desviacion.get("porcentual"), (int, float)):
        return float(desviacion["porcentual"])
    hoy = valor(datos, indicador)
    base = (datos.get("linea_base") or {}).get(indicador)
    if hoy is None or not isinstance(base, (int, float)) or base == 0:
        return None
    return 100.0 * (hoy - base) / base


def pct_del_plan(datos: dict, indicador: str):
    """Valor de hoy como porcentaje de lo planificado (100 = se cumplió el plan)."""
    hoy = valor(datos, indicador)
    plan = (datos.get("plan") or {}).get(indicador)
    if hoy is None or not isinstance(plan, (int, float)) or plan <= 0:
        return None
    return 100.0 * hoy / plan
