"""Motor de reglas explicables. Ver motor.py y config/umbrales.toml."""

from reglas.motor import cargar_config, evaluar, excluir_sospechosos

__all__ = ["cargar_config", "evaluar", "excluir_sospechosos"]
