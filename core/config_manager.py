"""
Gestion de configuracion para SISFE Monitor.
Lee y escribe config.json con una interfaz amigable (sin edicion manual de JSON).
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# config.json se guarda en AppData del usuario en produccion
# En desarrollo, junto al proyecto
import os
_APPDATA = os.environ.get("APPDATA", "")
if _APPDATA:
    CONFIG_DIR  = Path(_APPDATA) / "SISFEMonitor"
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH = CONFIG_DIR / "config.json"
else:
    CONFIG_PATH = Path(__file__).parent.parent / "config.json"

_DEFAULT = {
    "licencia":           "",
    "twocaptcha_api_key": "",
    "email": {
        "destinatario": "",
        "remitente":    "",
        "app_password": "",
        "host":         "smtp.gmail.com",
        "port":         587,
    },
    "horarios": [
        {"hora": "09:00"},
        {"hora": "14:00"},
        {"hora": "20:00"},
    ],
    "resumen_semanal": {
        "activo": True,
        "hora":   "20:00",
    },
    "dias":    ["MON", "TUE", "WED", "THU", "FRI"],
    "cuentas": [],
}


def load() -> dict:
    """Carga la configuracion. Si no existe, retorna la configuracion por defecto."""
    if not CONFIG_PATH.exists():
        return _deep_copy(_DEFAULT)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        merged = _deep_copy(_DEFAULT)
        _deep_merge(merged, data)
        return merged
    except Exception as exc:
        logger.error(f"Error leyendo config: {exc}")
        return _deep_copy(_DEFAULT)


def save(config: dict):
    """Guarda la configuracion en disco."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    logger.info(f"Configuracion guardada en {CONFIG_PATH}")


def is_configured() -> bool:
    """Retorna True si el wizard ya fue completado con todos los datos."""
    cfg = load()
    tiene_licencia = bool(cfg.get("licencia"))
    tiene_cuenta   = len(cfg.get("cuentas", [])) > 0
    tiene_email    = bool(cfg.get("email", {}).get("remitente"))
    tiene_captcha  = bool(cfg.get("twocaptcha_api_key"))
    tiene_horarios = len(cfg.get("horarios", [])) > 0
    return all([tiene_licencia, tiene_cuenta, tiene_email,
                tiene_captcha, tiene_horarios])


def is_licensed() -> bool:
    """Retorna True si hay una licencia valida guardada."""
    from license.validator import validate_license
    cfg  = load()
    code = cfg.get("licencia", "")
    if not code:
        return False
    valido, _ = validate_license(code)
    return valido


def get_config_path() -> Path:
    """Retorna la ruta del archivo de configuracion (util para mostrar al usuario)."""
    return CONFIG_PATH


# ── Helpers internos ──────────────────────────────────────────────────────────

def _deep_copy(d):
    import copy
    return copy.deepcopy(d)


def _deep_merge(base: dict, override: dict):
    """Merge recursivo: override sobreescribe base, preservando claves de base."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
