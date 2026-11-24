# ==============================================================================
# PROYECTO: BARCODE-CREATOR | FIRMA: JOMOCE-SOFT
# LICENCIA: GNU GENERAL PUBLIC LICENSE V3 (GNU GPLv3)
# COPYRIGHT (C) 2026 JOMOCE-SOFT - TODOS LOS DERECHOS CONCEDIDOS BAJO GNU GPLv3
# ==============================================================================
import sys
from pathlib import Path


def obtener_dir_recursos() -> Path:
    """Ruta de archivos internos (styles.css, app_barcode_creator.py) en desarrollo o PyInstaller."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def obtener_dir_datos() -> Path:
    """Ruta persistente junto al ejecutable (para barcode_creator.db)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

