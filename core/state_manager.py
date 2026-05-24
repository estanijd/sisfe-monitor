"""
State Manager — registra qué movimientos ya fueron enviados
para no repetir información entre correos del mismo día.

Estructura de sisfe_state.json:
{
  "ultimo_envio":           "2026-05-24T14:00:00",
  "ultimo_resumen_dia":     "2026-05-24",
  "ultimo_resumen_semana":  "2026-05-20",   ← lunes de esa semana
  "expedientes": {
    "<url>": {
      "movimientos_enviados": ["mov1_hash", "mov2_hash"],
      "acumulado_dia":        ["mov1_hash"],
      "acumulado_semana":     ["mov1_hash", "mov2_hash"]
    }
  }
}
"""
import os
import json
import hashlib
import logging
from datetime import datetime, date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Guardar en AppData en Windows, junto al proyecto en desarrollo
_APPDATA = os.environ.get("APPDATA", "")
if _APPDATA:
    _DATA_DIR = Path(_APPDATA) / "SISFEMonitor"
else:
    _DATA_DIR = Path(__file__).parent.parent
_DATA_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = _DATA_DIR / "sisfe_state.json"

# Palabras clave que identifican sentencias (detección para amarillo)
KEYWORDS_SENTENCIA = [
    "SENTENCIA", "SENTENCIA DEFINITIVA", "SENTENCIA INTERLOCUTORIA",
    "ACUERDO Y SENTENCIA", "FALLO", "RESOLUCION DEFINITIVA",
    "RESOLUCION FINAL", "HACE LUGAR", "RECHAZA LA DEMANDA",
    "AUTO INTERLOCUTORIO",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash_mov(mov: str) -> str:
    """Identificador único de un movimiento basado en su texto."""
    return hashlib.md5(mov.strip().encode("utf-8")).hexdigest()[:12]


def _lunes_de_semana(d: date) -> str:
    """Retorna el lunes de la semana de la fecha dada (ISO string)."""
    lunes = d - timedelta(days=d.weekday())
    return lunes.isoformat()


def _load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "ultimo_envio":          None,
        "ultimo_resumen_dia":    None,
        "ultimo_resumen_semana": None,
        "expedientes":           {},
    }


def _save(state: dict):
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ── API pública ───────────────────────────────────────────────────────────────

def es_sentencia(texto: str) -> bool:
    """Detecta si un movimiento es una sentencia/fallo."""
    upper = texto.upper()
    return any(kw in upper for kw in KEYWORDS_SENTENCIA)


def filtrar_novedades(resultados: dict) -> dict:
    """
    Dado resultados_por_cuenta, retorna solo los movimientos
    que NO fueron incluidos en el último envío.
    Útil para los envíos parciales del día.
    """
    state = _load()
    exp_state = state.get("expedientes", {})
    filtrados = {}

    for cuenta, expedientes in resultados.items():
        filtrados[cuenta] = {}
        for url, info in expedientes.items():
            movs = info.get("movimientos", [])
            ya_enviados = set(exp_state.get(url, {}).get("movimientos_enviados", []))
            nuevos = [m for m in movs if _hash_mov(m) not in ya_enviados]

            if nuevos:
                filtrados[cuenta][url] = {**info, "movimientos": nuevos}

    return filtrados


def acumular_dia(resultados: dict):
    """
    Agrega los movimientos actuales al acumulado del día.
    Llamar después de cada scrape, antes de filtrar.
    """
    state = _load()
    hoy = date.today().isoformat()

    # Si cambió el día, resetear el acumulado diario
    for url_data in state.get("expedientes", {}).values():
        if state.get("ultimo_resumen_dia") != hoy:
            url_data["acumulado_dia"] = []

    exp_state = state.setdefault("expedientes", {})

    for cuenta, expedientes in resultados.items():
        for url, info in expedientes.items():
            movs = info.get("movimientos", [])
            entry = exp_state.setdefault(url, {
                "movimientos_enviados": [],
                "acumulado_dia":        [],
                "acumulado_semana":     [],
            })
            # Agregar nuevos hashes al acumulado del día y de la semana
            for m in movs:
                h = _hash_mov(m)
                if h not in entry["acumulado_dia"]:
                    entry["acumulado_dia"].append(h)
                if h not in entry["acumulado_semana"]:
                    entry["acumulado_semana"].append(h)
            # También guardar el texto completo para poder reconstruir
            entry.setdefault("textos", {})
            for m in movs:
                entry["textos"][_hash_mov(m)] = m

    _save(state)


def get_resumen_dia(resultados: dict) -> dict:
    """
    Retorna todos los movimientos acumulados durante el día,
    independientemente de si ya fueron enviados en correos anteriores.
    Para el último envío del día.
    """
    state = _load()
    exp_state = state.get("expedientes", {})
    resumen = {}

    for cuenta, expedientes in resultados.items():
        resumen[cuenta] = {}
        for url, info in expedientes.items():
            entry = exp_state.get(url, {})
            textos = entry.get("textos", {})
            hashes_dia = entry.get("acumulado_dia", [])
            movs_dia = [textos[h] for h in hashes_dia if h in textos]
            if movs_dia:
                resumen[cuenta][url] = {**info, "movimientos": movs_dia}

    return resumen


def get_resumen_semana(resultados: dict) -> dict:
    """
    Retorna todos los movimientos acumulados durante la semana.
    Para el resumen dominical.
    """
    state = _load()
    exp_state = state.get("expedientes", {})
    resumen = {}

    for cuenta, expedientes in resultados.items():
        resumen[cuenta] = {}
        for url, info in expedientes.items():
            entry = exp_state.get(url, {})
            textos = entry.get("textos", {})
            hashes_semana = entry.get("acumulado_semana", [])
            movs_semana = [textos[h] for h in hashes_semana if h in textos]
            if movs_semana:
                resumen[cuenta][url] = {**info, "movimientos": movs_semana}

    return resumen


def marcar_enviados(resultados: dict):
    """
    Registra los movimientos incluidos en el último envío
    para no repetirlos en el próximo correo del día.
    """
    state = _load()
    exp_state = state.setdefault("expedientes", {})

    for cuenta, expedientes in resultados.items():
        for url, info in expedientes.items():
            movs = info.get("movimientos", [])
            entry = exp_state.setdefault(url, {
                "movimientos_enviados": [],
                "acumulado_dia":        [],
                "acumulado_semana":     [],
                "textos":               {},
            })
            for m in movs:
                h = _hash_mov(m)
                if h not in entry["movimientos_enviados"]:
                    entry["movimientos_enviados"].append(h)
                entry.setdefault("textos", {})[h] = m

    state["ultimo_envio"] = datetime.now().isoformat(timespec="seconds")
    _save(state)


def marcar_resumen_dia():
    """Registra que se hizo el resumen del día de hoy."""
    state = _load()
    state["ultimo_resumen_dia"] = date.today().isoformat()
    # Resetear movimientos_enviados (nueva jornada = todo es nuevo)
    for entry in state.get("expedientes", {}).values():
        entry["movimientos_enviados"] = []
        entry["acumulado_dia"]        = []
    _save(state)


def marcar_resumen_semana():
    """Registra que se hizo el resumen semanal y resetea el acumulado."""
    state = _load()
    state["ultimo_resumen_semana"] = _lunes_de_semana(date.today())
    for entry in state.get("expedientes", {}).values():
        entry["acumulado_semana"]     = []
        entry["movimientos_enviados"] = []
        entry["acumulado_dia"]        = []
    _save(state)


def determinar_tipo_envio(horarios: list) -> str:
    """
    Dado la lista de horarios configurados, determina qué tipo de envío
    corresponde a la hora actual:
    - 'novedades'     → envío parcial (solo movimientos nuevos)
    - 'resumen_dia'   → último horario del día (resumen completo del día)
    - 'resumen_semana'→ domingo a la noche (resumen semanal)
    """
    ahora = datetime.now()
    hora_actual = ahora.strftime("%H:%M")
    es_domingo = ahora.weekday() == 6  # 6 = domingo

    # Ordenar horarios para identificar el último del día
    horas_ordenadas = sorted(
        [h["hora"] if isinstance(h, dict) else h for h in horarios]
    )
    ultimo_horario = horas_ordenadas[-1] if horas_ordenadas else "20:00"

    if es_domingo and hora_actual >= ultimo_horario:
        return "resumen_semana"
    elif hora_actual >= ultimo_horario:
        return "resumen_dia"
    else:
        return "novedades"
