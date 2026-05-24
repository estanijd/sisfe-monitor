"""
run_agent.py — ejecutado por el Task Scheduler de Windows.
Determina automaticamente el tipo de envio segun el horario:
  - novedades:      solo movimientos nuevos desde el ultimo envio
  - resumen_dia:    todos los movimientos del dia (ultimo horario del dia)
  - resumen_semana: acumulado semanal (domingo, ultimo horario)
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# ── Logging — guardar en AppData en Windows ───────────────────────────────────
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
from license.validator import validate_license
from core.scraper  import SISFEScraper
from core.notifier import EmailNotifier
from core import state_manager as sm


def run():
    # ── 1. Verificar licencia ─────────────────────────────────────────────
    config = cfg_mgr.load()
    code = config.get("licencia", "")
    valido, msg = validate_license(code)
    if not valido:
        logger.error(f"Licencia invalida: {msg}. El agente no correra.")
        return

    if not cfg_mgr.is_configured():
        logger.error("Agente no configurado. Abre SISFE Monitor para configurarlo.")
        return

    # ── 2. Verificar límite de cuentas según licencia ─────────────────────
    from license.validator import get_license_info
    lic_info   = get_license_info(code)
    max_cuentas = lic_info.get("max_cuentas", 2) if lic_info else 2
    cuentas_cfg = config.get("cuentas", [])

    if len(cuentas_cfg) > max_cuentas:
        logger.warning(
            f"Licencia permite {max_cuentas} cuenta(s) pero hay {len(cuentas_cfg)} configuradas. "
            f"Solo se procesarán las primeras {max_cuentas}."
        )
        config["cuentas"] = cuentas_cfg[:max_cuentas]

    # ── 3. Determinar tipo de envio ───────────────────────────────────────
    horarios = config.get("horarios", [
        {"hora": "09:00"}, {"hora": "14:00"}, {"hora": "20:00"}
    ])
    tipo_envio = sm.determinar_tipo_envio(horarios)

    logger.info("=" * 55)
    logger.info(f"Verificacion: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    logger.info(f"Tipo de envio: {tipo_envio.upper()}")
    logger.info(f"Cuentas: {', '.join(c['nombre'] for c in config['cuentas'])}")
    logger.info("=" * 55)

    # ── 3. Scraping ───────────────────────────────────────────────────────
    scraper  = SISFEScraper(config)
    notifier = EmailNotifier(config)
    resultados_raw = {}
    hubo_error = False

    for cuenta in config["cuentas"]:
        nombre = cuenta["nombre"]
        logger.info(f"-- Procesando cuenta: {nombre} (mat. {cuenta['matricula']}) --")
        try:
            expedientes = scraper.run(cuenta)
        except Exception as exc:
            logger.exception(f"Error en cuenta {nombre}: {exc}")
            hubo_error = True
            continue

        if expedientes is None:
            logger.error(f"Login fallido para {nombre}")
            hubo_error = True
            continue

        resultados_raw[nombre] = expedientes
        logger.info(f"{nombre}: {len(expedientes)} expediente(s) encontrado(s)")

    if hubo_error:
        notifier.send_error("Uno o mas accesos fallaron. Revisa sisfe_monitor.log.")
        return

    # ── 4. Acumular estado (siempre, antes de filtrar) ────────────────────
    sm.acumular_dia(resultados_raw)

    # ── 5. Construir payload según tipo de envio ──────────────────────────
    if tipo_envio == "resumen_semana":
        payload = sm.get_resumen_semana(resultados_raw)
        total   = sum(len(v) for v in payload.values())
        logger.info(f"Resumen semanal: {total} expediente(s) acumulados")

    elif tipo_envio == "resumen_dia":
        payload = sm.get_resumen_dia(resultados_raw)
        total   = sum(len(v) for v in payload.values())
        logger.info(f"Resumen del dia: {total} expediente(s) acumulados")

    else:  # novedades
        payload = sm.filtrar_novedades(resultados_raw)
        total   = sum(len(v) for v in payload.values())
        logger.info(f"Novedades nuevas: {total} expediente(s)")

    # ── 6. Enviar ─────────────────────────────────────────────────────────
    # Siempre enviar: novedades (aunque sea vacío se omite si no hay nada)
    # Resumen dia/semana: siempre enviar aunque no haya novedades nuevas
    hay_contenido = total > 0
    es_resumen    = tipo_envio in ("resumen_dia", "resumen_semana")

    if hay_contenido or es_resumen:
        try:
            notifier.send_movements(payload, tipo=tipo_envio)
        except Exception as exc:
            logger.error(f"Error enviando email: {exc}")
            return
    else:
        logger.info("Sin novedades nuevas — email omitido.")

    # ── 7. Actualizar estado ──────────────────────────────────────────────
    if hay_contenido:
        sm.marcar_enviados(payload)

    if tipo_envio == "resumen_dia":
        sm.marcar_resumen_dia()
        logger.info("Estado diario reseteado para manana.")

    elif tipo_envio == "resumen_semana":
        sm.marcar_resumen_semana()
        logger.info("Estado semanal reseteado para la proxima semana.")

    logger.info("Ejecucion completada.")


if __name__ == "__main__":
    # Soporte para --test-email desde linea de comandos
    if "--test-email" in sys.argv:
        config   = cfg_mgr.load()
        notifier = EmailNotifier(config)
        notifier.send_test_email()
        logger.info("Email de prueba enviado.")
    else:
        run()
