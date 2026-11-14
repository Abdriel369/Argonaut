"""Niveles de alerta y operaciones sencillas sobre ellos."""

NIVELES = ["verde", "amarillo", "naranja", "rojo"]

# Texto que acompaña SIEMPRE al color (accesibilidad: nunca solo color).
TEXTO_NIVEL = {
    "verde": "Normal",
    "amarillo": "Atención",
    "naranja": "Alerta",
    "rojo": "Crítico",
}


def indice(nivel: str) -> int:
    """Posición del nivel en la escala (verde=0 ... rojo=3)."""
    return NIVELES.index(nivel)


def maximo(*niveles: str) -> str:
    """El nivel más grave de la lista. Sin argumentos devuelve 'verde'."""
    return max(niveles, key=indice, default="verde")


def subir(nivel: str, pasos: int = 1) -> str:
    """Sube 'pasos' escalones sin pasar de rojo."""
    return NIVELES[min(indice(nivel) + pasos, len(NIVELES) - 1)]


def nivel_por_riesgo(riesgo: float, cortes=(0.20, 0.50, 0.75)) -> str:
    """Convierte un riesgo 0-1 en nivel usando tres cortes (valores de ejemplo)."""
    nivel = "verde"
    for corte, nombre in zip(cortes, NIVELES[1:]):
        if riesgo >= corte:
            nivel = nombre
    return nivel
