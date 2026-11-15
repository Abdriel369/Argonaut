"""Síntesis: convierte reglas + respuestas de especialistas en texto sencillo.

Sin jerga, una o dos frases por alerta, y nunca dosis de medicamentos.
"""

PALABRA_RIESGO = {"verde": "bajo", "amarillo": "moderado", "naranja": "alto", "rojo": "muy alto"}


def unir(frases: list[str]) -> str:
    """'a', 'b', 'c' -> 'a, b y c' (sin duplicar la 'y' si la última ya empieza con 'además')."""
    frases = [f for f in frases if f]
    if not frases:
        return ""
    if len(frases) == 1:
        return frases[0]
    return ", ".join(frases[:-1]) + " y " + frases[-1]


def causa_simple(alerta: dict) -> str:
    """Ejemplo: 'Dormiste 5.0 h (tu normal son 7.0 h) y tu estrés subió a 72 de 100.
    Esta combinación puede causar fatiga... Sigue este protocolo.'"""
    hechos = unir(alerta["hechos"])
    texto = hechos[:1].upper() + hechos[1:] + ". " + alerta["consecuencia"]
    return texto + " Sigue este protocolo."


def opinion_especialistas(nombres: list, respuestas: dict, config: dict) -> str:
    """Una frase corta con lo que dijo la junta sobre esta alerta."""
    partes = []
    for nombre in nombres:
        respuesta = respuestas[nombre]
        titulo = config["especialistas"][nombre]["titulo"].lower()
        partes.append(f"{titulo} ve riesgo {PALABRA_RIESGO[respuesta['nivel']]}")
    if not partes:
        return ""
    return "La junta opina: " + unir(partes) + "."


def _cifra(valor, unidad: str = "") -> str:
    """12.0 -> '12', 36.55 -> '36.55', con su unidad si la hay."""
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        return "un valor desconocido"
    return f"{valor:g} {unidad}".strip()


def aviso_sensor(ficha: dict) -> str:
    """Aviso claro cuando un sensor parece fallar. Ejemplo:
    'El sensor de pulso en reposo parece fallar: marca 250 lpm, un valor que no es posible.
    Revisa el equipo y vuelve a medir. Mientras tanto ese dato no se usa.'

    Es un aviso de equipo, no una alerta de salud: no cambia el nivel.
    """
    nombre = str(ficha.get("nombre") or ficha.get("indicador") or "un indicador").lower()
    unidad = str(ficha.get("unidad") or "")
    leido = _cifra(ficha.get("valor_leido"), unidad)
    motivo = ficha.get("motivo")
    if motivo == "fuera_de_rango":
        detalle = f"marca {leido}, un valor que no es posible"
    elif motivo == "cambio_brusco":
        detalle = f"pasó de {_cifra(ficha.get('valor_anterior'))} a {leido} de una lectura a la siguiente"
    elif motivo == "valor_congelado":
        detalle = f"lleva {ficha.get('dias', 'varios')} días marcando exactamente {leido}"
    else:
        detalle = f"marca {leido} y no es fiable"
    return (f"El sensor de {nombre} parece fallar: {detalle}. "
            "Revisa el equipo y vuelve a medir. Mientras tanto ese dato no se usa.")


def explicacion_global(nivel: str, alertas: list, en_adaptacion: bool, modo: str,
                       datos_sospechosos: int = 0) -> str:
    """Resumen de una o dos frases para la cabecera del tablero."""
    if not alertas:
        texto = "Todo en orden. Tus indicadores están dentro de tu rango normal."
        if en_adaptacion:
            texto += " Estás en los primeros días de adaptación: es normal que algunos valores se muevan."
    else:
        principal = alertas[0]
        texto = f"{principal['titulo']}."
        if len(alertas) > 1:
            otras = len(alertas) - 1
            texto += f" Hay {otras} aviso{'s' if otras > 1 else ''} más."
    if modo == "degradado":
        texto += " Parte de la junta no está disponible; sigo vigilando con las reglas."
    if datos_sospechosos == 1:
        texto += " Hay 1 dato sospechoso: revisa el equipo."
    elif datos_sospechosos > 1:
        texto += f" Hay {datos_sospechosos} datos sospechosos: revisa el equipo."
    return texto
