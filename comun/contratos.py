"""Validación de mensajes contra los esquemas JSON de la carpeta contratos/.

Todos los servicios validan lo que reciben y lo que devuelven. Si un mensaje
no cumple el contrato se lanza ErrorContrato con un texto corto y claro.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

NOMBRES = (
    "entrada_orquestador",
    "consulta_especialista",
    "respuesta_especialista",
    "consulta_gateway",
    "respuesta_gateway",
    "resultado_final",
)


class ErrorContrato(ValueError):
    """El mensaje no cumple el esquema acordado entre laptops."""


def carpeta_contratos() -> Path:
    """Carpeta de esquemas: variable CONTRATOS_DIR o ../contratos junto a comun/."""
    ruta = os.environ.get("CONTRATOS_DIR")
    return Path(ruta) if ruta else Path(__file__).resolve().parent.parent / "contratos"


@lru_cache(maxsize=None)
def _validador(nombre: str) -> Draft202012Validator:
    if nombre not in NOMBRES:
        raise KeyError(f"Contrato desconocido: {nombre}")
    ruta = carpeta_contratos() / f"{nombre}.schema.json"
    esquema = json.loads(ruta.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(esquema)
    return Draft202012Validator(esquema)


def errores(nombre: str, mensaje) -> list[str]:
    """Lista de errores legibles (vacía si el mensaje es válido)."""
    salida = []
    for error in sorted(_validador(nombre).iter_errors(mensaje), key=lambda e: list(e.path)):
        donde = "/".join(str(p) for p in error.path) or "(raíz)"
        salida.append(f"{donde}: {error.message}")
    return salida


def validar(nombre: str, mensaje):
    """Devuelve el mismo mensaje si es válido; si no, lanza ErrorContrato."""
    problemas = errores(nombre, mensaje)
    if problemas:
        raise ErrorContrato(f"No cumple el contrato '{nombre}': " + "; ".join(problemas[:5]))
    return mensaje
