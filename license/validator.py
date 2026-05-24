"""
Validacion de licencias SISFE Monitor.
Las licencias se generan con generator.py y se validan aqui.
"""
import base64
import json
import gzip
import hashlib
import os
from datetime import datetime, date

# ── Clave secreta (NO compartir) ──────────────────────────────────────────────
# Esta misma clave debe estar en generator.py
_SECRET = b"SisfeM0n1t0r#2026$LicenseKey!AbogadosSantaFe"


def _derive_key(secret: bytes) -> bytes:
    """Deriva una clave de 32 bytes a partir del secreto."""
    return hashlib.sha256(secret).digest()


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    """Cifrado XOR simple con la clave derivada (sin dependencias externas)."""
    result = bytearray(len(data))
    for i, byte in enumerate(data):
        result[i] = byte ^ key[i % len(key)]
    return bytes(result)


def encode_license(datos: dict) -> str:
    """
    Convierte un dict de datos en un codigo de licencia.
    Solo se usa en generator.py.
    """
    key = _derive_key(_SECRET)
    payload = json.dumps(datos, ensure_ascii=False).encode("utf-8")
    compressed = gzip.compress(payload)
    encrypted = _xor_encrypt(compressed, key)
    encoded = base64.b64encode(encrypted).decode("ascii")
    # Formatear como SISFE-XXXX-XXXX-XXXX
    chunks = [encoded[i:i+6] for i in range(0, len(encoded), 6)]
    return "SISFE-" + "-".join(chunks)


def decode_license(code: str):
    """
    Decodifica y valida un codigo de licencia.
    Retorna el dict de datos si es valido, None si no.
    """
    try:
        # Limpiar y decodificar (NO uppercase — base64 es case-sensitive)
        code = code.strip()
        if not code.upper().startswith("SISFE-"):
            return None
        raw = code[6:].replace("-", "")
        # Puede haber padding incorrecto en base64
        padding = 4 - len(raw) % 4
        if padding != 4:
            raw += "=" * padding
        encrypted = base64.b64decode(raw)
        key = _derive_key(_SECRET)
        compressed = _xor_encrypt(encrypted, key)
        payload = gzip.decompress(compressed)
        datos = json.loads(payload.decode("utf-8"))
        return datos
    except Exception:
        return None


def validate_license(code: str) -> tuple[bool, str]:
    """
    Valida un codigo de licencia.
    Retorna (valido: bool, mensaje: str).
    """
    datos = decode_license(code)
    if datos is None:
        return False, "Codigo de licencia invalido."

    # Verificar campo producto
    if datos.get("producto") != "SISFE_MONITOR":
        return False, "Licencia no corresponde a este producto."

    # Verificar vencimiento (si existe)
    expires = datos.get("vencimiento")
    if expires:
        try:
            exp_date = date.fromisoformat(expires)
            if date.today() > exp_date:
                return False, f"Licencia vencida el {exp_date.strftime('%d/%m/%Y')}."
        except ValueError:
            return False, "Fecha de vencimiento invalida en la licencia."

    nombre = datos.get("nombre", "Usuario")
    return True, f"Licencia valida — {nombre}"


def get_license_info(code: str):
    """Retorna los datos de la licencia si es valida, None si no."""
    datos = decode_license(code)
    if datos is None:
        return None
    valido, _ = validate_license(code)
    return datos if valido else None
