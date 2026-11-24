# ==============================================================================
# PROYECTO: BARCODE-CREATOR | FIRMA: JOMOCE-SOFT
# LICENCIA: GNU GENERAL PUBLIC LICENSE V3 (GNU GPLv3)
# COPYRIGHT (C) 2026 JOMOCE-SOFT - TODOS LOS DERECHOS CONCEDIDOS BAJO GNU GPLv3
# ==============================================================================
import os
import sys
import time
import socket
import subprocess
import webbrowser
import traceback
from pathlib import Path
from PIL import Image, ImageDraw
import pystray
from rutas import obtener_dir_recursos, obtener_dir_datos

PUERTO = 8501
URL_APP = f"http://127.0.0.1:{PUERTO}"
NOMBRE_ACCESO = "BARCODE-CREATOR.lnk"
proceso_servidor = None


def ruta_startup_windows() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / NOMBRE_ACCESO


def esta_en_inicio_windows() -> bool:
    return ruta_startup_windows().exists()


def alternar_inicio_windows(icon=None, item=None):
    acceso = ruta_startup_windows()
    if acceso.exists():
        acceso.unlink(missing_ok=True)
        return

    objetivo = sys.executable if getattr(sys, "frozen", False) else str(Path(__file__).resolve())
    dir_trabajo = str(obtener_dir_datos())

    ps_script = (
        f'$ws = New-Object -ComObject WScript.Shell; '
        f'$s = $ws.CreateShortcut("{acceso}"); '
        f'$s.TargetPath = "{objetivo}"; '
        f'$s.WorkingDirectory = "{dir_trabajo}"; '
        f'$s.Description = "BARCODE-CREATOR - IMPRESION DE ETIQUETAS"; '
        f'$s.Save()'
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )


def _crear_icono_tray() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([2, 2, 61, 61], radius=12, fill=(15, 23, 42, 255), outline=(56, 189, 248, 255), width=3)
    barras = [(12, 4), (19, 2), (24, 5), (32, 2), (37, 4), (44, 2), (49, 3)]
    for x, ancho in barras:
        draw.rectangle([x, 14, x + ancho - 1, 50], fill=(255, 255, 255, 255))
    return img


def _puerto_activo(puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def _correr_modo_servidor():
    ruta_log = obtener_dir_datos() / "tray_error.log"
    try:
        os.chdir(str(obtener_dir_datos()))
        ruta_app = str(obtener_dir_recursos() / "app_barcode_creator.py")
        from streamlit.web import cli as stcli
        sys.argv = [
            "streamlit",
            "run",
            ruta_app,
            f"--server.port={PUERTO}",
            "--server.address=127.0.0.1",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
            "--global.developmentMode=false",
        ]
        sys.exit(stcli.main())
    except Exception:
        ruta_log.write_text(traceback.format_exc(), encoding="utf-8")
        sys.exit(1)


def _iniciar_subproceso_servidor():
    global proceso_servidor
    ruta_log = obtener_dir_datos() / "tray_error.log"
    if ruta_log.exists():
        ruta_log.unlink(missing_ok=True)

    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--servidor"]
    else:
        cmd = [sys.executable, str(Path(__file__).resolve()), "--servidor"]

    proceso_servidor = subprocess.Popen(
        cmd,
        cwd=str(obtener_dir_datos()),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def accion_abrir_navegador(icon=None, item=None):
    if not _puerto_activo(PUERTO):
        _iniciar_subproceso_servidor()
        for _ in range(25):
            if _puerto_activo(PUERTO):
                break
            time.sleep(0.4)
    webbrowser.open(URL_APP)


def accion_salir(icon, item):
    global proceso_servidor
    icon.stop()
    if proceso_servidor and proceso_servidor.poll() is None:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proceso_servidor.pid)],
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
    os._exit(0)


def main():
    if "--servidor" in sys.argv:
        _correr_modo_servidor()
        return

    if _puerto_activo(PUERTO):
        webbrowser.open(URL_APP)
        sys.exit(0)

    bandera_init = obtener_dir_datos() / ".startup_configurado"
    if not bandera_init.exists():
        if not esta_en_inicio_windows():
            alternar_inicio_windows()
        bandera_init.write_text("OK", encoding="utf-8")

    _iniciar_subproceso_servidor()

    for _ in range(30):
        if _puerto_activo(PUERTO):
            break
        time.sleep(0.4)

    menu = pystray.Menu(
        pystray.MenuItem("ABRIR BARCODE-CREATOR", accion_abrir_navegador, default=True),
        pystray.MenuItem(
            "INICIAR CON WINDOWS",
            alternar_inicio_windows,
            checked=lambda item: esta_en_inicio_windows(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("SALIR DE BARCODE-CREATOR", accion_salir),
    )

    icono = pystray.Icon(
        name="BARCODE-CREATOR",
        icon=_crear_icono_tray(),
        title="BARCODE-CREATOR | JOMOCE-SOFT (GNU GPLv3)",
        menu=menu,
    )
    icono.run()


if __name__ == "__main__":
    main()


