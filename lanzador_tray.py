# ==============================================================================
# NOMBRE: lanzador_tray.py
# AUTOR: JOMOCE-SOFT | LICENCIA: GNU GPLv3
# DESCRIPCION: GESTOR DE BANDEJA DEL SISTEMA (SYSTEM TRAY) PARA BARCODE-CREATOR.
# ==============================================================================

import os
import sys
import time
import socket
import webbrowser
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

APP_NOMBRE = "BARCODE-CREATOR | JOMOCE-SOFT"
PUERTO_STREAMLIT = 8501
URL_APP = f"http://localhost:{PUERTO_STREAMLIT}"

def obtener_ruta_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def puerto_en_uso(puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", puerto)) == 0

def generar_icono_tray() -> Image.Image:
    ruta_ico = obtener_ruta_base() / "assets" / "icono_barcode.ico"
    if ruta_ico.exists():
        return Image.open(ruta_ico)
    img = Image.new("RGB", (64, 64), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    barras = [8, 14, 18, 26, 30, 38, 44, 50, 54]
    for x in barras:
        ancho = 3 if x % 2 == 0 else 2
        draw.rectangle([x, 12, x + ancho, 52], fill=(56, 189, 248))
    return img

class ControladorTray:
    def __init__(self):
        self.ruta_base = obtener_ruta_base()
        self.proceso_streamlit = None
        self.icono = None

    def iniciar_servidor(self):
        if puerto_en_uso(PUERTO_STREAMLIT):
            return
        script_app = self.ruta_base / "app_barcode_creator.py"
        env = os.environ.copy()
        env["BARCODE_CREATOR_DATA_DIR"] = str(Path(os.environ.get("LOCALAPPDATA", self.ruta_base)) / "JOMOCE-SOFT" / "BARCODE-CREATOR")
        Path(env["BARCODE_CREATOR_DATA_DIR"]).mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable if not getattr(sys, "frozen", False) else str(self.ruta_base / "BARCODE-CREATOR-SERVER.exe"),
            "-m", "streamlit", "run", str(script_app),
            "--server.port", str(PUERTO_STREAMLIT),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--global.developmentMode", "false"
        ]
        if getattr(sys, "frozen", False):
            cmd = [str(self.ruta_base / "BARCODE-CREATOR-SERVER.exe")]

        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.proceso_streamlit = subprocess.Popen(
            cmd,
            cwd=str(self.ruta_base),
            env=env,
            creationflags=creation_flags
        )

        for _ in range(30):
            if puerto_en_uso(PUERTO_STREAMLIT):
                break
            time.sleep(0.3)

    def abrir_interfaz(self, icon=None, item_menu=None):
        if not puerto_en_uso(PUERTO_STREAMLIT):
            self.iniciar_servidor()
        webbrowser.open(URL_APP)

    def reiniciar_servicio(self, icon=None, item_menu=None):
        self.detener_servidor()
        time.sleep(0.5)
        self.iniciar_servidor()
        webbrowser.open(URL_APP)

    def detener_servidor(self):
        if self.proceso_streamlit and self.proceso_streamlit.poll() is None:
            self.proceso_streamlit.terminate()
            try:
                self.proceso_streamlit.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proceso_streamlit.kill()

    def salir_aplicacion(self, icon, item_menu):
        self.detener_servidor()
        icon.stop()

    def ejecutar(self):
        self.iniciar_servidor()
        menu = pystray.Menu(
            item("ABRIR BARCODE-CREATOR", self.abrir_interfaz, default=True),
            item("REINICIAR SERVICIO LOCAL", self.reiniciar_servicio),
            pystray.Menu.SEPARATOR,
            item("SALIR Y DETENER MOTOR", self.salir_aplicacion)
        )
        self.icono = pystray.Icon("BARCODE_CREATOR_TRAY", generar_icono_tray(), APP_NOMBRE, menu)
        self.icono.run()

if __name__ == "__main__":
    if puerto_en_uso(PUERTO_STREAMLIT):
        webbrowser.open(URL_APP)
        sys.exit(0)
    app = ControladorTray()
    app.ejecutar()