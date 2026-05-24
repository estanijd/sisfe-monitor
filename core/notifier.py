import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.state_manager import es_sentencia

logger = logging.getLogger(__name__)

# ── Paleta BE LEGAL ───────────────────────────────────────────────────────
_NARANJA     = "#F03010"   # color principal BE LEGAL
_NARANJA_OSC = "#C02000"
_GRIS        = "#F5F5F5"
_BORDE       = "#DDDDDD"
_TEXTO       = "#111111"
_MUTED       = "#777777"
_FONT        = "Arial, Helvetica, sans-serif"
_AMARILLO    = "#FFE500"   # fluorescente para sentencias
_AMARILLO_T  = "#7A6B00"  # texto sobre amarillo

# Alias internos
_AZUL        = _NARANJA
_AZUL_CLARO  = "#FFE8E4"


class EmailNotifier:
    def __init__(self, config):
        self.cfg = config["email"]
        dest = self.cfg["destinatario"]
        self.recipients = [d.strip() for d in dest.split(",") if d.strip()]

    # ── API pública ────────────────────────────────────────────────────────

    def send_movements(self, resultados_por_cuenta, tipo="novedades"):
        """
        tipo: 'novedades' | 'resumen_dia' | 'resumen_semana'
        """
        ahora     = datetime.now().strftime("%d/%m/%Y %H:%M")
        total_exp = sum(len(v) for v in resultados_por_cuenta.values())

        prefijos = {
            "novedades":      "[SISFE]",
            "resumen_dia":    "[SISFE · RESUMEN DÍA]",
            "resumen_semana": "[SISFE · RESUMEN SEMANA]",
        }
        prefijo = prefijos.get(tipo, "[SISFE]")

        if total_exp > 0:
            asunto = f"{prefijo} {total_exp} expediente(s) con novedades — {ahora}"
        else:
            asunto = f"{prefijo} Sin novedades — {ahora}"

        self._send(
            asunto,
            self._txt(resultados_por_cuenta, ahora, total_exp, tipo),
            self._html(resultados_por_cuenta, ahora, total_exp, tipo),
        )

    def send_test_email(self):
        ahora  = datetime.now().strftime("%d/%m/%Y %H:%M")
        asunto = "[SISFE] Email de prueba"
        txt    = f"El agente SISFE esta configurado correctamente.\nFecha: {ahora}"
        html   = self._wrap(f"""
          <div style="background:{_AZUL_CLARO};border-left:4px solid {_AZUL};
                      padding:16px 20px;border-radius:0 6px 6px 0;">
            <p style="margin:0;font-size:15px;color:{_TEXTO};font-weight:bold;">
              El agente SISFE esta configurado correctamente.
            </p>
            <p style="margin:8px 0 0;font-size:13px;color:{_MUTED};">Fecha: {ahora}</p>
          </div>""", ahora, "novedades")
        self._send(asunto, txt, html)
        logger.info("Email de prueba enviado.")

    def send_error(self, detalle):
        ahora  = datetime.now().strftime("%d/%m/%Y %H:%M")
        asunto = "[SISFE] Error en el agente"
        txt    = f"Error en el agente SISFE:\n\n{detalle}\n\nRevisa sisfe_monitor.log."
        html   = self._wrap(f"""
          <div style="background:#fdecea;border-left:4px solid #c62828;
                      padding:16px 20px;border-radius:0 6px 6px 0;">
            <p style="margin:0;font-size:15px;color:#c62828;font-weight:bold;">
              Error en el agente
            </p>
            <p style="margin:10px 0 0;font-size:14px;color:{_TEXTO};">{self._e(detalle)}</p>
            <p style="margin:10px 0 0;font-size:12px;color:{_MUTED};">
              Revisa sisfe_monitor.log para mas detalles.
            </p>
          </div>""", ahora, "novedades")
        self._send(asunto, txt, html)

    # ── Construccion HTML ──────────────────────────────────────────────────

    def _html(self, resultados_por_cuenta, ahora, total_exp, tipo="novedades"):
        # Badge de tipo de envío
        if tipo == "resumen_semana":
            badge_txt  = "📋 Resumen semanal"
            badge_bg   = "#4a148c"
        elif tipo == "resumen_dia":
            badge_txt  = "📊 Resumen del día"
            badge_bg   = "#1b5e20"
        else:
            badge_txt  = f"{total_exp} expediente(s) con novedades" if total_exp > 0 else "Sin novedades"
            badge_bg   = _AZUL if total_exp > 0 else _BORDE

        badge = (f'<span style="background:{badge_bg};color:#fff;padding:3px 12px;'
                 f'border-radius:12px;font-size:13px;font-weight:600;">'
                 f'{badge_txt}</span>')

        subtitulo = {
            "resumen_semana": "Resumen completo de la semana",
            "resumen_dia":    "Todos los movimientos del día",
            "novedades":      "Ultimos 5 dias",
        }.get(tipo, "Ultimos 5 dias")

        cuerpo = f'<p style="margin:0 0 22px;">{badge} &nbsp;· {subtitulo}</p>\n'

        for nombre_cuenta, expedientes in resultados_por_cuenta.items():
            cuerpo += (
                f'<h2 style="margin:0 0 12px;padding:9px 16px;background:{_AZUL};'
                f'color:#fff;font-size:13px;font-weight:700;border-radius:4px;'
                f'letter-spacing:1.2px;font-family:{_FONT};">'
                f'👤 {self._e(nombre_cuenta.upper())}</h2>\n'
            )

            if not expedientes:
                cuerpo += (
                    f'<p style="margin:0 0 20px;padding:12px 16px;background:{_GRIS};'
                    f'border-left:4px solid {_BORDE};color:{_MUTED};font-size:14px;'
                    f'border-radius:0 4px 4px 0;">'
                    f'Sin novedades.</p>\n'
                )
                continue

            for info in expedientes.values():
                numero     = info.get("numero", "")
                caratula   = info.get("caratula", "")
                ultima     = info.get("ultima_actualizacion", "")
                radicacion = info.get("radicacion", "")
                movs       = info.get("movimientos", [])

                # Verificar si algún movimiento es sentencia
                tiene_sentencia = any(es_sentencia(m) for m in movs)

                borde_card = "#c8a000" if tiene_sentencia else _BORDE
                cuerpo += (
                    f'<div style="margin-bottom:14px;border:1px solid {borde_card};'
                    f'border-radius:6px;overflow:hidden;">\n'
                )

                # Header tarjeta — amarillo si tiene sentencia
                header_bg = _AMARILLO if tiene_sentencia else _GRIS
                header_txt_color = _AMARILLO_T if tiene_sentencia else _MUTED
                cuerpo += (
                    f'<div style="background:{header_bg};padding:12px 16px;'
                    f'border-bottom:1px solid {borde_card};">\n'
                )

                if tiene_sentencia:
                    cuerpo += (
                        f'<p style="margin:0 0 5px;font-size:11px;color:{_AMARILLO_T};'
                        f'font-weight:800;letter-spacing:1px;">⚖️ SENTENCIA / FALLO DETECTADO</p>\n'
                    )

                if numero:
                    cuerpo += (
                        f'<p style="margin:0 0 5px;font-size:12px;color:{header_txt_color};">'
                        f'<b style="color:{_AZUL};font-weight:700;">Exp.</b>'
                        f'&nbsp;{self._e(numero)}</p>\n'
                    )
                cuerpo += (
                    f'<p style="margin:0 0 6px;font-size:14px;color:{_TEXTO};'
                    f'font-weight:700;line-height:1.3;">'
                    f'{self._e(caratula)}</p>\n'
                )
                if ultima:
                    cuerpo += (
                        f'<p style="margin:0 0 3px;font-size:12px;color:{header_txt_color};">'
                        f'📅 Ultima actualizacion: '
                        f'<b style="color:{_TEXTO};">{self._e(ultima)}</b></p>\n'
                    )
                if radicacion:
                    cuerpo += (
                        f'<p style="margin:0;font-size:12px;color:{header_txt_color};">'
                        f'🏛️ {self._e(radicacion)}</p>\n'
                    )
                cuerpo += '</div>\n'

                # Movimientos
                if movs:
                    cuerpo += (
                        f'<div style="padding:10px 16px;background:#fff;">\n'
                        f'<p style="margin:0 0 8px;font-size:11px;color:{_BORDE};'
                        f'text-transform:uppercase;letter-spacing:0.8px;font-weight:700;">'
                        f'Movimientos</p>\n'
                        f'<table style="width:100%;border-collapse:collapse;'
                        f'font-size:13px;font-family:{_FONT};">\n'
                    )
                    for i, mov in enumerate(movs):
                        partes  = mov.split(" | ", 2)
                        fecha   = self._e(partes[0].strip()) if len(partes) > 0 else ""
                        tipo_m  = self._e(partes[1].strip()) if len(partes) > 1 else ""
                        detalle = self._e(partes[2].strip()) if len(partes) > 2 else ""

                        # Resaltar si es sentencia
                        es_sent = es_sentencia(partes[1].strip() if len(partes) > 1 else mov)
                        if es_sent:
                            row_bg     = _AMARILLO
                            tipo_color = _AMARILLO_T
                            sentencia_badge = (
                                f'<span style="background:#c8a000;color:#fff;'
                                f'font-size:10px;padding:1px 6px;border-radius:4px;'
                                f'margin-left:6px;font-weight:700;">⚖️ SENTENCIA</span>'
                            )
                        else:
                            row_bg         = "#ffffff" if i % 2 == 0 else _GRIS
                            tipo_color     = _TEXTO
                            sentencia_badge = ""

                        det_html = (
                            f'<br><span style="color:{_MUTED};font-size:12px;">'
                            f'{detalle}</span>'
                        ) if detalle else ""

                        cuerpo += (
                            f'<tr style="background:{row_bg};">'
                            f'<td style="padding:7px 10px;color:{_BORDE};'
                            f'white-space:nowrap;vertical-align:top;width:76px;'
                            f'font-size:12px;">{fecha}</td>'
                            f'<td style="padding:7px 10px;color:{tipo_color};'
                            f'vertical-align:top;font-weight:600;">'
                            f'{tipo_m}{sentencia_badge}{det_html}</td>'
                            f'</tr>\n'
                        )
                    cuerpo += '</table>\n</div>\n'
                else:
                    cuerpo += (
                        f'<div style="padding:10px 16px;background:#fff;">'
                        f'<p style="margin:0;font-size:12px;color:{_MUTED};">'
                        f'Sin detalle de movimientos.</p></div>\n'
                    )

                cuerpo += '</div>\n'

            cuerpo += '<div style="height:8px;"></div>\n'

        return self._wrap(cuerpo, ahora, tipo)

    def _wrap(self, cuerpo, ahora, tipo="novedades"):
        color_header = {
            "resumen_semana": "#7B1FA2",
            "resumen_dia":    "#1b5e20",
            "novedades":      _NARANJA,
        }.get(tipo, _NARANJA)

        subtitulo_header = {
            "resumen_semana": "Resumen Semanal",
            "resumen_dia":    "Resumen del Día",
            "novedades":      "Monitor de Expedientes",
        }.get(tipo, "Monitor de Expedientes")

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#EBEBEB;font-family:{_FONT};color:{_TEXTO};">
<div style="max-width:680px;margin:28px auto;background:#ffffff;
            border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,0.15);overflow:hidden;">

  <!-- Header BE LEGAL -->
  <div style="background:{color_header};padding:18px 28px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td>
          <span style="color:#ffffff;font-size:22px;font-weight:900;
                       letter-spacing:-0.5px;font-family:Arial,sans-serif;">BE LEGAL</span>
          <span style="color:#FFD0C0;font-size:13px;margin-left:8px;">· {subtitulo_header}</span>
        </td>
        <td align="right">
          <span style="color:#FFD0C0;font-size:11px;">{ahora}</span>
        </td>
      </tr>
    </table>
  </div>

  <!-- Cuerpo -->
  <div style="padding:24px 28px;">
{cuerpo}
  </div>

  <!-- Footer -->
  <div style="background:{_GRIS};border-top:1px solid {_BORDE};padding:12px 28px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="font-size:11px;color:#999;">
          Mensaje automático · <strong style="color:{_NARANJA};">BE LEGAL</strong> · SISFE Monitor
        </td>
        <td align="right" style="font-size:11px;color:#999;">
          <a href="mailto:ediaz@belegal.ar" style="color:{_NARANJA};text-decoration:none;">
            ediaz@belegal.ar
          </a>
        </td>
      </tr>
    </table>
  </div>

</div>
</body></html>"""

    # ── Texto plano ────────────────────────────────────────────────────────

    def _txt(self, resultados_por_cuenta, ahora, total_exp, tipo="novedades"):
        headers = {
            "resumen_semana": f"RESUMEN SEMANAL — {ahora}",
            "resumen_dia":    f"RESUMEN DEL DÍA — {ahora}",
            "novedades":      f"SISFE — Verificacion del {ahora}",
        }
        lineas = [headers.get(tipo, f"SISFE — {ahora}")]

        if total_exp > 0:
            lineas.append(f"{total_exp} expediente(s) con novedades.")
        else:
            lineas.append("Sin novedades.")

        for nombre_cuenta, expedientes in resultados_por_cuenta.items():
            lineas += ["", "=" * 55, f"  {nombre_cuenta.upper()}", "=" * 55]
            if not expedientes:
                lineas.append("  Sin novedades.")
                continue
            for info in expedientes.values():
                numero     = info.get("numero", "")
                caratula   = info.get("caratula", "")
                ultima     = info.get("ultima_actualizacion", "")
                radicacion = info.get("radicacion", "")
                movs       = info.get("movimientos", [])
                lineas.append("")
                if numero:
                    lineas.append(f"  Expediente : {numero}")
                lineas.append(    f"  Caratula   : {caratula}")
                if ultima:
                    lineas.append(f"  Ult. act.  : {ultima}")
                if radicacion:
                    lineas.append(f"  Radicacion : {radicacion}")
                if movs:
                    lineas.append("  Movimientos:")
                    for m in movs:
                        prefijo = "  ⚖️ [SENTENCIA] " if es_sentencia(m) else "    * "
                        lineas.append(f"{prefijo}{m}")
                lineas.append("  " + "-" * 50)

        lineas += ["", "-" * 55, "Mensaje automatico — Agente SISFE"]
        return "\n".join(lineas)

    # ── SMTP ──────────────────────────────────────────────────────────────

    def _send(self, asunto, txt, html):
        msg = MIMEMultipart("alternative")
        msg["From"]    = self.cfg["remitente"]
        msg["To"]      = ", ".join(self.recipients)
        msg["Subject"] = asunto
        msg.attach(MIMEText(txt,  "plain", "utf-8"))
        msg.attach(MIMEText(html, "html",  "utf-8"))

        try:
            with smtplib.SMTP(self.cfg.get("host", "smtp.gmail.com"),
                               self.cfg.get("port", 587)) as server:
                server.ehlo()
                server.starttls()
                server.login(self.cfg["remitente"], self.cfg["app_password"])
                server.sendmail(self.cfg["remitente"], self.recipients, msg.as_string())
            logger.info(f"Email enviado ({asunto})")
        except Exception as exc:
            logger.error(f"Error enviando email: {exc}")
            raise

    @staticmethod
    def _e(t):
        return (str(t)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))
