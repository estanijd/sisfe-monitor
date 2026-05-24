"""
main.py — Punto de entrada principal de SISFE Monitor.

Flags:
  --install-browser  Instala Playwright Chromium (lo llama el instalador)
  --test-email       Envia un email de prueba
  --run              Corre el agente inmediatamente
  --config           Abre el wizard de configuracion
"""
import sys
import logging
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import os as _os
_appdata = _os.environ.get("APPDATA", "")
if _appdata:
    _log_dir = Path(_appdata) / "SISFEMonitor"
    _log_dir.mkdir(parents=True, exist_ok=True)
    LOG_FILE = _log_dir / "sisfe_monitor.log"
else:
    LOG_FILE = BASE_DIR / "sisfe_monitor.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

import core.config_manager as cfg_mgr


def instalar_navegador():
    """
    Descarga e instala Playwright Chromium.
    Se ejecuta una sola vez durante la instalacion del programa.
    """
    import subprocess
    logger.info("Instalando navegador Chromium (puede tardar 1-2 minutos)...")
    try:
        resultado = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=300
        )
        if resultado.returncode == 0:
            logger.info("Navegador instalado correctamente.")
        else:
            logger.error(f"Error al instalar navegador: {resultado.stderr}")
    except Exception as exc:
        logger.error(f"No se pudo instalar el navegador: {exc}")


def abrir_wizard():
    from gui.wizard import run_wizard
    run_wizard()


def correr_agente():
    from run_agent import run
    run()


def main():
    args = sys.argv[1:]

    # ── Instalar navegador (llamado por el instalador) ─────────────────────────
    if "--install-browser" in args:
        instalar_navegador()
        return

    # ── Test email ─────────────────────────────────────────────────────────────
    if "--test-email" in args:
        from core.notifier import EmailNotifier
        config = cfg_mgr.load()
        EmailNotifier(config).send_test_email()
        logger.info("Email de prueba enviado.")
        return

    # ── Correr agente directamente ─────────────────────────────────────────────
    if "--run" in args:
        correr_agente()
        return

    # ── Forzar wizard ──────────────────────────────────────────────────────────
    if "--config" in args:
        abrir_wizard()
        return

    # ── Flujo normal ───────────────────────────────────────────────────────────

    # Primera vez: abrir wizard
    if not cfg_mgr.is_configured():
        logger.info("Primera ejecucion — abriendo wizard de configuracion.")
        abrir_wizard()
        if not cfg_mgr.is_configured():
            logger.info("Configuracion cancelada. Cerrando.")
            return

    # Verificar actualizaciones en background
    try:
        from core.updater import verificar_en_background

        def on_update(version, url):
            logger.info(f"Nueva version disponible: v{version}")
            try:
                from gui.update_dialog import UpdateDialog
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                dlg = UpdateDialog(root, version, url)
                dlg.wait_window()
                root.destroy()
            except Exception:
                pass

        verificar_en_background(on_update_disponible=on_update)
    except Exception:
        pass

    # Iniciar system tray
    try:
        from gui.tray import SISFETray, TRAY_AVAILABLE
        if TRAY_AVAILABLE:
            tray = SISFETray(
                run_agent_fn=correr_agente,
                open_wizard_fn=abrir_wizard,
            )
            logger.info("SISFE Monitor activo en la bandeja del sistema.")
            tray.start()
        else:
            logger.warning("Tray no disponible — corriendo agente directamente.")
            correr_agente()
    except Exception as exc:
        logger.error(f"Error iniciando tray: {exc}")
        correr_agente()


if __name__ == "__main__":
    main()
