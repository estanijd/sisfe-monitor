"""
Icono en la bandeja del sistema (system tray) para SISFE Monitor.
Permite: correr ahora, abrir configuracion, buscar actualizaciones, salir.
"""
import sys
import threading
import logging
import subprocess
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    logger.warning("pystray/PIL no disponible. Tray deshabilitado.")


def _crear_icono_simple(color_azul="#0f1d59"):
    """Crea un icono simple en memoria si no hay archivo .ico."""
    try:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r, g, b = 15, 29, 89
        draw.ellipse([4, 4, 60, 60], fill=(r, g, b, 255))
        draw.text((18, 18), "SF", fill=(255, 255, 255, 255))
        return img
    except Exception:
        return None


class SISFETray:
    def __init__(self, run_agent_fn, open_wizard_fn):
        self.run_agent_fn  = run_agent_fn
        self.open_wizard_fn = open_wizard_fn
        self.icon = None
        self._running = False

    def start(self):
        if not TRAY_AVAILABLE:
            logger.warning("pystray no disponible, no se inicia el tray.")
            return

        ico_path = Path(__file__).parent.parent / "assets" / "icon.ico"
        if ico_path.exists():
            image = Image.open(ico_path)
        else:
            image = _crear_icono_simple()
            if image is None:
                logger.error("No se pudo crear el icono para el tray.")
                return

        menu = pystray.Menu(
            pystray.MenuItem("▶  Correr ahora",         self._on_correr),
            pystray.MenuItem("⚙  Configuracion",         self._on_config),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📄  Carta Documento",      self._on_carta_doc),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🔄  Buscar actualizacion", self._on_update),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✖  Salir",                 self._on_salir),
        )

        self.icon = pystray.Icon(
            "SISFE Monitor",
            image,
            "SISFE Monitor",
            menu
        )
        self._running = True
        self.icon.run()

    def stop(self):
        if self.icon:
            self.icon.stop()
        self._running = False

    def notify(self, titulo: str, mensaje: str):
        """Muestra una notificacion de Windows desde el tray."""
        if self.icon:
            try:
                self.icon.notify(mensaje, titulo)
            except Exception:
                pass

    # ── Handlers del menu ─────────────────────────────────────────────────────

    def _on_correr(self, icon, item):
        def _run():
            logger.info("Corriendo agente desde el tray...")
            self.notify("SISFE Monitor", "Iniciando verificacion de expedientes...")
            try:
                self.run_agent_fn()
                self.notify("SISFE Monitor", "✅ Verificacion completada. Revisa tu email.")
            except Exception as exc:
                logger.error(f"Error al correr el agente: {exc}")
                self.notify("SISFE Monitor", f"❌ Error: {exc}")
        threading.Thread(target=_run, daemon=True).start()

    def _on_config(self, icon, item):
        threading.Thread(target=self.open_wizard_fn, daemon=True).start()

    def _on_update(self, icon, item):
        def _check():
            from core.updater import hay_actualizacion, descargar_e_instalar
            hay, version, url = hay_actualizacion()
            if hay and url:
                self.notify("SISFE Monitor", f"Nueva version {version} disponible. Descargando...")
                try:
                    descargar_e_instalar(url, version)
                except Exception as exc:
                    self.notify("SISFE Monitor", f"Error al actualizar: {exc}")
            else:
                self.notify("SISFE Monitor", "✅ Ya tenes la ultima version.")
        threading.Thread(target=_check, daemon=True).start()

    def _on_carta_doc(self, icon, item):
        """Abre el generador de Carta Documento en el navegador predeterminado."""
        html_path = Path(__file__).parent / "carta_documento.html"
        try:
            import webbrowser
            webbrowser.open(html_path.as_uri())
        except Exception as exc:
            logger.error(f"No se pudo abrir Carta Documento: {exc}")

    def _on_salir(self, icon, item):
        self.stop()
        sys.exit(0)
