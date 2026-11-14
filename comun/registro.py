"""Logs con el mismo formato en todos los servicios."""

import logging
import os


def configurar_logs(servicio: str) -> logging.Logger:
    """Devuelve un logger con formato 'hora [servicio] NIVEL mensaje'.

    El nivel se controla con la variable de entorno NIVEL_LOG (INFO por defecto).
    """
    nivel = os.environ.get("NIVEL_LOG", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, nivel, logging.INFO),
        format=f"%(asctime)s [{servicio}] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    # httpx escribe una línea por petición; lo dejamos en avisos para no tapar lo importante.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return logging.getLogger(servicio)
