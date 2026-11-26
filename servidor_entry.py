# ==============================================================================
# NOMBRE: servidor_entry.py
# AUTOR: JOMOCE-SOFT | LICENCIA: GNU GPLv3
# DESCRIPCION: PUNTO DE ENTRADA EMPAQUETADO PARA STREAMLIT EN PRODUCCION.
# ==============================================================================

import os
import sys
from pathlib import Path
from streamlit.web import cli as stcli

def main():
    ruta_base = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    os.chdir(ruta_base)
    script_principal = str(ruta_base / "app_barcode_creator.py")

    sys.argv = [
        "streamlit",
        "run",
        script_principal,
        "--server.port=8501",
        "--server.address=127.0.0.1",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--global.developmentMode=false"
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()