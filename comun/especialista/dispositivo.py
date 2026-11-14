"""Detección automática de GPU NVIDIA. Nunca es obligatoria: sin GPU se usa CPU."""

import logging
import os
import shutil
import subprocess

log = logging.getLogger(__name__)


def _nvidia_visible() -> bool:
    """True si 'nvidia-smi' existe y responde (hay controlador y tarjeta visibles)."""
    if shutil.which("nvidia-smi") is None:
        return False
    try:
        return subprocess.run(["nvidia-smi"], capture_output=True, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def detectar_dispositivo() -> str:
    """Devuelve 'cuda' si XGBoost puede entrenar en la GPU; si no, 'cpu'.

    Variable USAR_GPU: 'auto' (por defecto), 'no' para forzar CPU.
    """
    preferencia = os.environ.get("USAR_GPU", "auto").strip().lower()
    if preferencia in ("no", "0", "false", "cpu"):
        return "cpu"
    if not _nvidia_visible():
        return "cpu"
    try:
        import numpy as np
        import xgboost as xgb

        prueba = xgb.DMatrix(np.array([[0.0], [1.0], [0.0], [1.0]]), label=[0, 1, 0, 1])
        xgb.train({"device": "cuda", "tree_method": "hist", "verbosity": 0}, prueba, 1)
        return "cuda"
    except Exception as error:  # cualquier fallo de CUDA: seguimos en CPU
        log.warning("GPU visible pero no utilizable por XGBoost (%s); se usa CPU.", error)
        return "cpu"
