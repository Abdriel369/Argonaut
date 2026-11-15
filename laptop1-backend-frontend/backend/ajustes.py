"""Ajustes del backend: variables de entorno (.env) y archivos de configuración."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def _toml(nombre: str) -> dict:
    with open(AQUI / "config" / nombre, "rb") as archivo:
        return tomllib.load(archivo)


@dataclass
class Ajustes:
    """Todo lo configurable del backend. Las direcciones salen del .env, nunca del código."""

    url_orquestador: str
    tiempo_max_orquestador_s: float
    reintentos_orquestador: int
    ruta_bd: str
    dir_frontend: Path
    perfil: dict
    guion: dict
    catalogo: dict
    sensores: dict

    @classmethod
    def desde_entorno(cls) -> "Ajustes":
        return cls(
            url_orquestador=os.environ.get("URL_ORQUESTADOR", "http://127.0.0.1:8300").rstrip("/"),
            tiempo_max_orquestador_s=float(os.environ.get("TIEMPO_MAX_ORQUESTADOR_S", "8")),
            reintentos_orquestador=int(os.environ.get("REINTENTOS_ORQUESTADOR", "2")),
            ruta_bd=os.environ.get("RUTA_BD", str(AQUI / "datos" / "astro_medico.db")),
            dir_frontend=Path(os.environ.get("DIR_FRONTEND", str(AQUI.parent / "frontend"))),
            perfil=_toml("perfil.toml"),
            guion=_toml("guion_7_dias.toml"),
            catalogo=_toml("indicadores.toml"),
            sensores=_toml("sensores.toml"),
        )

    @property
    def dias_guion(self) -> int:
        return len(self.guion["indicadores"]["sueno_h"])
