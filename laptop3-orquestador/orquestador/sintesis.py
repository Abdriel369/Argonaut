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


def explicacion_global(nivel: str, alertas: list, en_adaptacion: bool, modo: str) -> str:
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
    return texto
