import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            "No se encontró config.json.\n"
            "Copiá config.json.ejemplo → config.json y completá tus datos."
        )

    with CONFIG_FILE.open(encoding="utf-8") as f:
        cfg = json.load(f)

    errors = []

    if not cfg.get("twocaptcha_api_key") or "COMPLETAR" in cfg["twocaptcha_api_key"]:
        errors.append("  twocaptcha_api_key  →  tu API key de 2captcha.com")

    email = cfg.get("email", {})
    for campo, descripcion in [
        ("destinatario", "email donde recibís las notificaciones"),
        ("remitente",    "cuenta Gmail que envía"),
        ("app_password", "contraseña de aplicación de Gmail"),
    ]:
        if not email.get(campo) or "COMPLETAR" in str(email.get(campo, "")):
            errors.append(f"  email.{campo}  →  {descripcion}")

    cuentas = cfg.get("cuentas", [])
    if not cuentas:
        errors.append("  cuentas  →  al menos una cuenta SISFE")
    for i, c in enumerate(cuentas):
        for campo in ("nombre", "circunscripcion", "colegio", "matricula", "clave"):
            if not c.get(campo) or "COMPLETAR" in str(c.get(campo, "")):
                errors.append(f"  cuentas[{i}].{campo}  →  completar")

    if errors:
        raise ValueError("Faltan datos en config.json:\n" + "\n".join(errors))

    return cfg
