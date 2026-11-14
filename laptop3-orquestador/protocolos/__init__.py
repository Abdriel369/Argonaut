"""Protocolos de acción paso a paso por tipo de alerta (texto en protocolos.toml)."""

import tomllib
from functools import lru_cache
from pathlib import Path

RUTA = Path(__file__).resolve().parent / "protocolos.toml"


@lru_cache(maxsize=1)
def cargar_protocolos() -> dict:
    """Devuelve {protocolo_id: {id, titulo, objetivo, pasos:[{id, texto, temporizador_min?}]}}."""
    with open(RUTA, "rb") as archivo:
        crudo = tomllib.load(archivo)
    return {clave: {"id": clave, **valor} for clave, valor in crudo.items()}


def obtener(protocolo_id: str) -> dict:
    """Protocolo pedido, o el de vigilancia general si no existe."""
    protocolos = cargar_protocolos()
    return protocolos.get(protocolo_id, protocolos["general"])
