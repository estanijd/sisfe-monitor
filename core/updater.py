"""
Auto-updater para SISFE Monitor.
Compara la version local con la ultima release de GitHub.
Si hay una nueva version, la descarga y lanza el instalador.
"""
import os
import sys
import logging
import tempfile
import subprocess
import threading
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# ── Configuracion ─────────────────────────────────────────────────────────────
GITHUB_USER = "estanijd"
GITHUB_REPO = "sisfe-monitor-releases"
GITHUB_API  = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"

VERSION_FILE = Path(__file__).parent.parent / "version.txt"


def get_local_version() -> str:
    """Lee la version local desde version.txt."""
    try:
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "0.0.0"


def get_remote_version():
    """
    Consulta GitHub API y retorna (version, url_del_instalador).
    Retorna (None, None) si no puede conectarse.
    """
    try:
        r = requests.get(GITHUB_API, timeout=8)
        r.raise_for_status()
        data = r.json()
        version = data["tag_name"].lstrip("v")
        # Buscar el .exe en los assets
        for asset in data.get("assets", []):
            if asset["name"].endswith(".exe"):
                return version, asset["browser_download_url"]
        return version, None
    except Exception as exc:
        logger.debug(f"No se pudo verificar actualizaciones: {exc}")
        return None, None


def _version_tuple(v: str) -> tuple:
    """Convierte '1.2.3' en (1, 2, 3) para comparacion."""
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def hay_actualizacion():
    """
    Verifica si hay una version mas nueva disponible.
    Retorna (hay_update: bool, version_remota: str, url: str).
    """
    local = get_local_version()
    remota, url = get_remote_version()
    if remota is None:
        return False, "", ""
    if _version_tuple(remota) > _version_tuple(local):
        return True, remota, url or ""
    return False, remota, ""


def descargar_e_instalar(url: str, version: str, callback_progreso=None):
    """
    Descarga el nuevo instalador y lo ejecuta.
    callback_progreso(porcentaje: int) se llama durante la descarga.
    """
    logger.info(f"Descargando v{version} desde {url}")
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()

        total = int(r.headers.get("content-length", 0))
        descargado = 0

        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".exe", prefix="SISFE_update_"
        )
        with tmp as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                descargado += len(chunk)
                if callback_progreso and total:
                    callback_progreso(int(descargado / total * 100))

        logger.info(f"Descarga completada: {tmp.name}")
        # Ejecutar el instalador y cerrar la app actual
        subprocess.Popen([tmp.name, "/SILENT"])
        sys.exit(0)

    except Exception as exc:
        logger.error(f"Error durante la actualizacion: {exc}")
        raise


def verificar_en_background(on_update_disponible=None):
    """
    Verifica actualizaciones en un hilo secundario.
    Si hay update y se provee callback, lo llama con (version, url).
    """
    def _check():
        hay, version, url = hay_actualizacion()
        if hay and on_update_disponible:
            on_update_disponible(version, url)

    t = threading.Thread(target=_check, daemon=True)
    t.start()
