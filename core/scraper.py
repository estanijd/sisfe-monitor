import logging
from datetime import date
from pathlib import Path
from twocaptcha import TwoCaptcha
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

logger = logging.getLogger(__name__)

BASE_URL  = "https://sisfe.justiciasantafe.gov.ar"
LOGIN_URL = f"{BASE_URL}/login-matriculado"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"

LOGIN_SELECTORS = {
    "circunscripcion": [
        'select[name="circunscripcion"]', 'select[name="circ"]',
        'select[id="circunscripcion"]',   'select:nth-of-type(1)',
    ],
    "colegio": [
        'select[name="colegio"]', 'select[name="col"]',
        'select[id="colegio"]',   'select:nth-of-type(2)',
    ],
    "matricula": [
        'input[name="matricula"]', 'input[id="matricula"]', '#matricula',
        'input[type="text"]', 'input[type="number"]',
    ],
    "clave": [
        'input[name="clave"]', 'input[id="clave"]', '#clave',
        'input[name="password"]', 'input[type="password"]',
    ],
    "submit": [
        '#ingresar',
        'button:has-text("Ingresar")', 'button:has-text("Entrar")',
        'button[type="submit"]', 'input[type="submit"]',
        '#btnIngresar', '#btnLogin',
    ],
}


class SISFEScraper:
    def __init__(self, config, debug=False):
        self.config    = config
        self.debug     = debug
        self.today_str = date.today().strftime("%d/%m/%Y")
        self.solver    = TwoCaptcha(config["twocaptcha_api_key"])
        if debug:
            SCREENSHOTS_DIR.mkdir(exist_ok=True)

    # ── Punto de entrada ───────────────────────────────────────────────────

    def run(self, cuenta):
        """
        cuenta: dict con nombre, circunscripcion, colegio, matricula, clave
        Devuelve dict { exp_id: {numero, caratula, ultima_actualizacion, movimientos, ...} }
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            page.set_default_timeout(30_000)
            try:
                if not self._login(page, cuenta):
                    return None
                return self._scrape_expedientes(page, cuenta["nombre"])
            except Exception as exc:
                self._shot(page, f"ERROR_{cuenta['nombre']}")
                logger.exception(f"Error en scraper ({cuenta['nombre']}): {exc}")
                return None
            finally:
                browser.close()

    # ── Login ──────────────────────────────────────────────────────────────

    def _login(self, page, cuenta):
        nombre = cuenta["nombre"]
        logger.info(f"[{nombre}] Navegando a: {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="networkidle")
        self._shot(page, f"{nombre}_01_login")

        if self.debug:
            (SCREENSHOTS_DIR / f"{nombre}_login.html").write_text(
                page.content(), encoding="utf-8"
            )

        # Completar formulario
        self._select_dropdown(page, LOGIN_SELECTORS["circunscripcion"],
                               cuenta["circunscripcion"], "circunscripcion")
        page.wait_for_timeout(2000)   # esperar posible recarga AJAX del colegio
        self._select_dropdown(page, LOGIN_SELECTORS["colegio"],
                               cuenta["colegio"], "colegio")
        page.wait_for_timeout(500)
        if not self._fill(page, LOGIN_SELECTORS["matricula"],
                          str(cuenta["matricula"]), "matricula"):
            return False
        if not self._fill(page, LOGIN_SELECTORS["clave"],
                          str(cuenta["clave"]), "clave"):
            return False

        self._shot(page, f"{nombre}_02_form_listo")
        if self.debug:
            for campo, sels in [("circunscripcion", LOGIN_SELECTORS["circunscripcion"]),
                                 ("colegio", LOGIN_SELECTORS["colegio"])]:
                for sel in sels:
                    try:
                        loc = page.locator(sel)
                        if loc.count() > 0:
                            val = loc.evaluate("el => el.options[el.selectedIndex]?.text")
                            logger.debug(f"[{nombre}] Dropdown '{campo}' valor actual: '{val}'")
                            break
                    except Exception:
                        pass

        # Resolver reCAPTCHA
        if not self._solve_recaptcha(page, nombre):
            return False

        self._shot(page, f"{nombre}_03_captcha_resuelto")
        page.wait_for_timeout(1000)   # dejar que el callback procese el token

        # Enviar formulario y esperar la respuesta XHR del servidor
        submitted = False
        try:
            with page.expect_response(
                lambda r: "/iol/login" in r.url, timeout=30_000
            ):
                for sel in LOGIN_SELECTORS["submit"]:
                    try:
                        loc = page.locator(sel)
                        if loc.count() > 0:
                            loc.first.click()
                            submitted = True
                            logger.debug(f"[{nombre}] Form enviado via click: {sel}")
                            break
                    except Exception:
                        continue
                if not submitted:
                    page.evaluate("document.querySelector('form').submit()")
                    logger.debug(f"[{nombre}] Form enviado via JS submit() (fallback)")
        except PWTimeout:
            logger.warning(f"[{nombre}] Timeout esperando respuesta del servidor")

        # Esperar a que Angular complete la navegacion post-login
        try:
            page.wait_for_url(
                lambda url: "login" not in url.lower(),
                timeout=10_000
            )
        except PWTimeout:
            try:
                page.wait_for_load_state("networkidle", timeout=10_000)
            except PWTimeout:
                pass

        self._shot(page, f"{nombre}_04_post_login")
        if self.debug:
            (SCREENSHOTS_DIR / f"{nombre}_post_login.html").write_text(
                page.content(), encoding="utf-8"
            )

        url_actual = page.url
        if "login" in url_actual.lower():
            try:
                body_text = page.locator("body").inner_text()
                lines = [l.strip() for l in body_text.splitlines() if l.strip()][:20]
                logger.error(f"[{nombre}] Respuesta del servidor: {' | '.join(lines)}")
            except Exception:
                pass
            logger.error(f"[{nombre}] Login fallido — URL: {url_actual}")
            return False

        logger.info(f"[{nombre}] Login exitoso. URL: {url_actual}")
        return True

    # ── Resolver reCAPTCHA v2 ──────────────────────────────────────────────

    def _solve_recaptcha(self, page, nombre=""):
        import re

        logger.debug(f"[{nombre}] Esperando que cargue el reCAPTCHA...")
        page.wait_for_timeout(3000)

        site_key = None

        # Metodo 1: atributo data-sitekey directo
        for sel in ['[data-sitekey]', '.g-recaptcha', '#recaptcha']:
            loc = page.locator(sel)
            if loc.count() > 0:
                site_key = loc.first.get_attribute("data-sitekey")
                if site_key:
                    logger.debug(f"[{nombre}] Sitekey encontrado via selector: {sel}")
                    break

        # Metodo 2: sitekey en la URL del iframe de reCAPTCHA
        if not site_key:
            iframes = page.locator('iframe').all()
            logger.debug(f"[{nombre}] Iframes encontrados: {len(iframes)}")
            for iframe in iframes:
                src = iframe.get_attribute("src") or ""
                logger.debug(f"[{nombre}] iframe src: {src[:100]}")
                if "recaptcha" in src or "google.com/recaptcha" in src:
                    match = re.search(r'[?&]k=([^&]+)', src)
                    if match:
                        site_key = match.group(1)
                        logger.debug(f"[{nombre}] Sitekey encontrado en iframe src")
                        break

        # Metodo 3: buscar en el HTML completo
        if not site_key:
            html = page.content()
            for pattern in [
                r'data-sitekey=["\']([^"\']+)["\']',
                r'"sitekey"\s*:\s*"([^"]+)"',
                r'sitekey:\s*["\']([^"\']+)["\']',
                r'grecaptcha\.render\([^,]+,\s*\{[^}]*["\']sitekey["\']\s*:\s*["\']([^"\']+)["\']',
            ]:
                match = re.search(pattern, html)
                if match:
                    site_key = match.group(1)
                    logger.debug(f"[{nombre}] Sitekey encontrado en HTML con patron: {pattern}")
                    break

        if not site_key:
            logger.warning(f"[{nombre}] No se encontro reCAPTCHA en la pagina — continuando sin resolver")
            return True

        logger.info(f"[{nombre}] reCAPTCHA detectado. Enviando a 2captcha (15-30 seg)...")

        try:
            result = self.solver.recaptcha(sitekey=site_key, url=page.url)
            token  = result["code"]
            logger.info(f"[{nombre}] reCAPTCHA resuelto.")
        except Exception as exc:
            logger.error(f"[{nombre}] 2captcha fallo: {exc}")
            return False

        # Inyectar el token en la pagina
        page.evaluate(f"""
            var token = '{token}';

            // 1. Setear el textarea oculto
            var ta = document.getElementById('g-recaptcha-response');
            if (ta) {{ ta.value = token; ta.innerHTML = token; }}

            // 2. Llamar callbacks de reCAPTCHA
            try {{
                if (typeof ___grecaptcha_cfg !== 'undefined') {{
                    var clients = ___grecaptcha_cfg.clients;
                    for (var id in clients) {{
                        var c = clients[id];
                        try {{ if (c.g && c.g.g && typeof c.g.g.callback === 'function') c.g.g.callback(token); }} catch(e) {{}}
                        try {{ if (c.g && typeof c.g.callback === 'function') c.g.callback(token); }} catch(e) {{}}
                        for (var k in c) {{
                            try {{ if (c[k] && typeof c[k].callback === 'function') c[k].callback(token); }} catch(e) {{}}
                            try {{ if (c[k] && c[k].g && typeof c[k].g.callback === 'function') c[k].g.callback(token); }} catch(e) {{}}
                            try {{ if (c[k] && c[k].l && typeof c[k].l.callback === 'function') c[k].l.callback(token); }} catch(e) {{}}
                        }}
                    }}
                }}
            }} catch(e) {{}}

            // 3. Actualizar el Angular FormControl recaptcha directamente (FIX ANGULAR)
            try {{
                var formEl = document.querySelector('form');
                if (formEl && formEl.__ngContext__) {{
                    var ctx = formEl.__ngContext__;
                    for (var i = 0; i < ctx.length; i++) {{
                        var item = ctx[i];
                        if (item && typeof item === 'object' && item.controls && item.controls.recaptcha) {{
                            item.controls.recaptcha.setValue(token);
                            item.controls.recaptcha.markAsDirty();
                            item.controls.recaptcha.markAsTouched();
                            item.controls.recaptcha.updateValueAndValidity();
                        }}
                        if (item && item.captchaSuccess !== undefined) {{
                            item.captchaSuccess = true;
                            item.captchaIsExpired = false;
                        }}
                    }}
                }}
            }} catch(e) {{}}
        """)
        page.wait_for_timeout(2000)
        return True

    # ── Scraping de expedientes ────────────────────────────────────────────

    def _scrape_expedientes(self, page, nombre=""):
        self._shot(page, f"{nombre}_05_inicio")
        if self.debug:
            (SCREENSHOTS_DIR / f"{nombre}_pagina_principal.html").write_text(
                page.content(), encoding="utf-8"
            )

        # ── 1. Completar filtro "novedades en los ultimos N dias" ──────────
        # En SISFE el campo es type="text" con id="diasNovedades"
        # Esperamos explicitamente a que el formulario este renderizado
        try:
            page.wait_for_selector('#diasNovedades', timeout=8_000)
            page.fill('#diasNovedades', '5')
            logger.debug(f"[{nombre}] Campo 'novedades' seteado a 5 (#diasNovedades)")
        except Exception as e:
            logger.warning(f"[{nombre}] No se pudo setear diasNovedades: {e}")
            # Fallback: intentar con otros selectores
            for sel in ['input[formcontrolname="diasNovedades"]',
                        'input[id*="novedad"]', 'input[id*="dias"]']:
                try:
                    if page.locator(sel).count() > 0:
                        page.fill(sel, '5')
                        logger.debug(f"[{nombre}] Campo 'novedades' seteado a 5 ({sel})")
                        break
                except Exception:
                    continue

        # ── 2. Hacer clic en "Efectuar la busqueda" ───────────────────────
        # En SISFE el boton tiene id="efectuarBusqueda"
        busqueda_sels = [
            '#efectuarBusqueda',
            'button:has-text("Efectuar la búsqueda")',
            'button:has-text("Efectuar")',
            'button:has-text("Buscar")',
            'input[value*="squeda"]',
            'input[type="submit"]',
            'button[type="submit"]',
        ]
        busqueda_ok = False
        for sel in busqueda_sels:
            try:
                if page.locator(sel).count() > 0:
                    page.click(sel)
                    busqueda_ok = True
                    logger.info(f"[{nombre}] Busqueda ejecutada ({sel})")
                    break
            except Exception:
                continue
        if not busqueda_ok:
            logger.warning(f"[{nombre}] No se encontro el boton de busqueda")

        # Esperar a que Angular cargue los datos en la tabla (AJAX)
        try:
            page.wait_for_selector("table tbody tr", timeout=15_000)
            logger.debug(f"[{nombre}] Tabla con resultados detectada")
        except PWTimeout:
            logger.info(f"[{nombre}] Sin filas en la tabla tras 15s")

        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except PWTimeout:
            pass

        self._shot(page, f"{nombre}_06_resultados")
        if self.debug:
            (SCREENSHOTS_DIR / f"{nombre}_resultados.html").write_text(
                page.content(), encoding="utf-8"
            )

        # ── 3. Parsear tabla de resultados ────────────────────────────────
        expedientes = {}
        tablas = page.locator("table").all()
        logger.info(f"[{nombre}] Tablas encontradas tras busqueda: {len(tablas)}")

        for tabla in tablas:
            ths = tabla.locator("th").all()
            encabezados_raw = [th.inner_text().strip() for th in ths]
            encabezados     = [h.lower() for h in encabezados_raw]
            if encabezados:
                logger.debug(f"[{nombre}] Encabezados: {encabezados_raw}")

            filas = tabla.locator("tbody tr").all()
            if not filas:
                continue

            # Determinar indice de cada columna por palabras clave del encabezado
            def col_idx(keywords, default):
                for i, h in enumerate(encabezados):
                    if any(kw in h for kw in keywords):
                        return i
                return default

            idx_numero    = col_idx(["expediente", "nro", "número", "numero"], 0)
            idx_caratula  = col_idx(["carátula", "caratula", "car"], 1)
            idx_fecha     = col_idx(["actualiz", "últim", "ultim"], 3)
            idx_radicacion = col_idx(["radic"], 4)

            # Primera pasada: recopilar datos de cada fila SIN navegar fuera de la pagina
            filas_data = []
            for idx_f, fila in enumerate(filas):
                try:
                    celdas = fila.locator("td").all()
                    textos = [c.inner_text().strip() for c in celdas]
                    if not any(textos):
                        continue

                    link      = fila.locator("a").first
                    href      = link.get_attribute("href") if link.count() > 0 else None
                    link_text = link.inner_text().strip() if link.count() > 0 else ""

                    numero       = textos[idx_numero]    if idx_numero    < len(textos) else link_text or f"exp_{idx_f}"
                    caratula     = textos[idx_caratula]  if idx_caratula  < len(textos) else ""
                    ultima_fecha = textos[idx_fecha]     if idx_fecha     < len(textos) else ""
                    radicacion   = textos[idx_radicacion] if idx_radicacion < len(textos) else ""

                    exp_id = href or numero or f"fila_{idx_f}"
                    filas_data.append({
                        "exp_id":             exp_id,
                        "numero":             numero,
                        "caratula":           caratula,
                        "ultima_actualizacion": ultima_fecha,
                        "radicacion":         radicacion,
                        "href":               href,
                    })
                except Exception as e:
                    logger.debug(f"[{nombre}] Error en fila {idx_f}: {e}")

            if not filas_data:
                continue   # intentar con la siguiente tabla

            logger.info(f"[{nombre}] {len(filas_data)} expediente(s) encontrado(s) con novedades")

            # Segunda pasada: entrar a cada expediente para obtener los ultimos 3 movimientos
            for fila in filas_data:
                movimientos = []
                if fila["href"]:
                    try:
                        movimientos = self._get_movimientos(
                            page, fila["href"], nombre, fila["numero"]
                        )
                    except Exception as e:
                        logger.warning(
                            f"[{nombre}] No se pudieron obtener movimientos "
                            f"de {fila['numero']}: {e}"
                        )

                caratula = fila["caratula"]
                ultima   = fila["ultima_actualizacion"]
                resumen  = caratula
                if ultima:
                    resumen += f" — ult. actualizacion: {ultima}"

                expedientes[fila["exp_id"]] = {
                    "numero":              fila["numero"],
                    "caratula":            caratula,
                    "ultima_actualizacion": ultima,
                    "radicacion":          fila["radicacion"],
                    "resumen":             resumen,
                    "movimientos":         movimientos,
                }

            break   # primera tabla valida es la que queremos; salir del loop de tablas

        if not expedientes:
            logger.warning(
                f"[{nombre}] Sin novedades en los ultimos 5 dias. "
                "Corra con --debug para inspeccionar la pagina."
            )

        logger.info(f"[{nombre}] Expedientes con novedades: {len(expedientes)}")
        return expedientes

    # ── Detalle de expediente (ultimos 3 movimientos) ─────────────────────

    def _get_movimientos(self, page, href, nombre="", numero=""):
        """
        Abre el detalle del expediente en una nueva pestana (mismo contexto = misma
        sesion/localStorage) y extrae los primeros 3 movimientos del listado
        (los mas recientes, asumiendo orden descendente).
        Cierra la pestana al terminar sin afectar la pagina de resultados.
        """
        if href.startswith("http"):
            url = href
        elif href.startswith("/"):
            url = f"{BASE_URL}{href}"
        else:
            url = f"{BASE_URL}/{href}"

        logger.debug(f"[{nombre}] Abriendo detalle de '{numero}': {url}")
        context = page.context
        detail  = context.new_page()

        try:
            detail.goto(url, wait_until="networkidle", timeout=30_000)

            # Esperar que aparezca la tabla de movimientos
            try:
                detail.wait_for_selector("table tbody tr", timeout=15_000)
            except PWTimeout:
                logger.warning(
                    f"[{nombre}] No se encontro tabla de movimientos en: {url}"
                )
                return []

            self._shot(detail, f"{nombre}_detalle_{(numero or 'exp').replace('/', '-')}")
            if self.debug:
                slug = (numero or "exp").replace("/", "-").replace(";", "_")
                (SCREENSHOTS_DIR / f"{nombre}_detalle_{slug}.html").write_text(
                    detail.content(), encoding="utf-8"
                )

            # Buscar la tabla de movimientos (la que tenga mas filas con datos)
            mejor_tabla = None
            mejor_cant  = 0
            for tabla in detail.locator("table").all():
                n = tabla.locator("tbody tr").count()
                if n > mejor_cant:
                    mejor_cant  = n
                    mejor_tabla = tabla

            movimientos = []
            if mejor_tabla and mejor_cant > 0:
                # Tomamos las primeras 3 filas (= movimientos mas recientes)
                filas = mejor_tabla.locator("tbody tr").all()
                for fila in filas[:3]:
                    try:
                        celdas = fila.locator("td").all()
                        textos = [c.inner_text().strip() for c in celdas]
                        linea  = " | ".join(t for t in textos if t)
                        if linea:
                            movimientos.append(linea)
                    except Exception:
                        pass

            logger.debug(
                f"[{nombre}] Movimientos extraidos de '{numero}': {len(movimientos)}"
            )
            return movimientos

        except Exception as exc:
            logger.warning(f"[{nombre}] Error al abrir detalle {url}: {exc}")
            return []
        finally:
            try:
                detail.close()
            except Exception:
                pass

    # ── Helpers ───────────────────────────────────────────────────────────

    def _select_dropdown(self, page, selectors, texto, nombre_campo):
        for sel in selectors:
            try:
                loc = page.locator(sel)
                if loc.count() == 0:
                    continue
                try:
                    loc.select_option(label=texto)
                    logger.debug(f"Dropdown '{nombre_campo}' -> '{texto}'")
                    return True
                except Exception:
                    pass
                for opt in loc.locator("option").all():
                    opt_text = opt.inner_text().strip()
                    if texto.lower() in opt_text.lower():
                        loc.select_option(value=opt.get_attribute("value"))
                        logger.debug(f"Dropdown '{nombre_campo}' -> '{opt_text}'")
                        return True
            except Exception:
                continue
        logger.warning(f"No se pudo seleccionar '{texto}' en dropdown '{nombre_campo}'")
        return False

    def _fill(self, page, selectors, valor, nombre_campo):
        for sel in selectors:
            try:
                if page.locator(sel).count() > 0:
                    page.fill(sel, valor)
                    logger.debug(f"Campo '{nombre_campo}' completado con: {sel}")
                    return True
            except Exception:
                continue
        logger.error(f"No se encontro el campo '{nombre_campo}'")
        return False

    def _shot(self, page, nombre):
        if not self.debug:
            return
        try:
            page.screenshot(
                path=str(SCREENSHOTS_DIR / f"{nombre}.png"), full_page=True
            )
        except Exception:
            pass
