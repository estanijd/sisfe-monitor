"""
Wizard de configuracion inicial de SISFE Monitor.
Se muestra la primera vez (o desde Configuracion en el tray).
"""
import tkinter as tk
from tkinter import ttk, messagebox
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from license.validator import validate_license, get_license_info
import core.config_manager as cfg_mgr

# ── Colores corporativos ───────────────────────────────────────────────────────
AZUL   = "#0f1d59"
GRIS   = "#f5f5f6"
BORDE  = "#bcbec0"
BLANCO = "#ffffff"
ROJO   = "#c62828"
VERDE  = "#2e7d32"


class WizardApp(tk.Tk):
    def __init__(self, on_finish=None):
        super().__init__()
        self.on_finish = on_finish
        self.config_data = cfg_mgr.load()

        self.title("SISFE Monitor — Configuracion")
        self.resizable(False, False)
        self.configure(bg=BLANCO)

        # Centrar ventana
        self.update_idletasks()
        w, h = 560, 540
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self._build_header()
        self._build_steps()
        self._build_nav()

        self.steps = [
            self._page_licencia,
            self._page_captcha,
            self._page_cuentas,
            self._page_email,
            self._page_horarios,
            self._page_resumen,
        ]
        self.step_index = 0

        # Si ya tiene licencia valida, saltar directamente al paso de cuentas
        if cfg_mgr.is_licensed():
            self.step_index = 1

        self._show_step()

    # ── Layout base ───────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=AZUL, height=64)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="SISFE Monitor", bg=AZUL, fg=BLANCO,
                 font=("Arial", 16, "bold")).pack(side="left", padx=20, pady=16)
        self.lbl_paso = tk.Label(hdr, text="", bg=AZUL, fg=BORDE,
                                  font=("Arial", 10))
        self.lbl_paso.pack(side="right", padx=20)

    def _build_steps(self):
        self.frame_contenido = tk.Frame(self, bg=BLANCO, pady=10)
        self.frame_contenido.pack(fill="both", expand=True, padx=24)

    def _build_nav(self):
        nav = tk.Frame(self, bg=GRIS, pady=12)
        nav.pack(fill="x", side="bottom")
        nav.configure(highlightbackground=BORDE, highlightthickness=1)

        self.btn_atras = tk.Button(nav, text="◀  Atras", command=self._prev,
                                    bg=GRIS, relief="flat", padx=14, pady=6,
                                    font=("Arial", 10), cursor="hand2")
        self.btn_atras.pack(side="left", padx=16)

        self.btn_siguiente = tk.Button(nav, text="Siguiente  ▶", command=self._next,
                                        bg=AZUL, fg=BLANCO, relief="flat",
                                        padx=14, pady=6, font=("Arial", 10, "bold"),
                                        cursor="hand2", activebackground="#1a2f8a",
                                        activeforeground=BLANCO)
        self.btn_siguiente.pack(side="right", padx=16)

    # ── Navegacion ────────────────────────────────────────────────────────────

    def _show_step(self):
        for w in self.frame_contenido.winfo_children():
            w.destroy()
        total = len(self.steps)
        self.lbl_paso.config(text=f"Paso {self.step_index + 1} de {total}")
        self.steps[self.step_index]()
        es_ultimo = self.step_index == len(self.steps) - 1
        self.btn_siguiente.config(text="✔  Finalizar" if es_ultimo else "Siguiente  ▶")
        self.btn_atras.config(state="normal" if self.step_index > 0 else "disabled")

    def _next(self):
        if not self._validate_current():
            return
        self._save_current()
        if self.step_index < len(self.steps) - 1:
            self.step_index += 1
            self._show_step()
        else:
            self._finish()

    def _prev(self):
        if self.step_index > 0:
            self.step_index -= 1
            self._show_step()

    def _finish(self):
        cfg_mgr.save(self.config_data)
        self._programar_tareas()
        messagebox.showinfo(
            "SISFE Monitor",
            "✅ Configuracion guardada correctamente.\n\n"
            "El agente correra automaticamente de lunes a viernes."
        )
        if self.on_finish:
            self.on_finish()
        self.destroy()

    # ── Pagina 1: Licencia ────────────────────────────────────────────────────

    def _page_licencia(self):
        self._titulo("🔑  Activacion de licencia")
        self._subtitulo("Ingresa el codigo que recibiste al adquirir SISFE Monitor.")

        tk.Label(self.frame_contenido, text="Codigo de licencia:",
                 bg=BLANCO, font=("Arial", 10, "bold"), fg=AZUL).pack(anchor="w", pady=(16,4))

        self.ent_licencia = tk.Entry(self.frame_contenido, font=("Courier", 11),
                                      width=44, relief="solid", bd=1)
        self.ent_licencia.pack(anchor="w", ipady=6)
        self.ent_licencia.insert(0, self.config_data.get("licencia", ""))

        self.lbl_lic_status = tk.Label(self.frame_contenido, text="",
                                        bg=BLANCO, font=("Arial", 9))
        self.lbl_lic_status.pack(anchor="w", pady=(4,0))

        tk.Button(self.frame_contenido, text="Validar", command=self._validar_licencia,
                  bg=AZUL, fg=BLANCO, relief="flat", padx=12, pady=4,
                  font=("Arial", 9, "bold"), cursor="hand2").pack(anchor="w", pady=(8,0))

        self._separador()
        self._nota("¿No tenés tu codigo? Contactá a tu proveedor.")

    def _validar_licencia(self):
        code = self.ent_licencia.get().strip()
        valido, msg = validate_license(code)
        if valido:
            self.lbl_lic_status.config(text=f"✅ {msg}", fg=VERDE)
        else:
            self.lbl_lic_status.config(text=f"❌ {msg}", fg=ROJO)

    # ── Pagina 2: 2captcha ────────────────────────────────────────────────────

    def _page_captcha(self):
        self._titulo("🤖  Servicio anti-captcha (2captcha)")
        self._subtitulo(
            "El sistema judicial tiene un captcha de seguridad. SISFE Monitor lo resuelve\n"
            "automáticamente usando 2captcha. Seguí estos pasos para configurarlo:"
        )

        # Instructivo paso a paso
        pasos = [
            ("1", "Entrá a 2captcha.com",
             "Abrí tu navegador y escribí:  2captcha.com"),
            ("2", "Creá una cuenta gratis",
             "Hacé clic en 'Register' → completá email y contraseña → confirmá el email."),
            ("3", "Cargá saldo",
             "Ingresá a tu cuenta → 'Add funds' → cargá u$s 3 (dura varios meses).\n"
             "Aceptan tarjeta de crédito/débito y PayPal."),
            ("4", "Copiá tu API Key",
             "En el menú de tu perfil → 'API key' → copiá el código largo que aparece."),
        ]
        self._instructivo(pasos)

        tk.Button(self.frame_contenido, text="🌐  Abrir 2captcha.com",
                  command=lambda: self._abrir_url("https://2captcha.com"),
                  bg="#e65100", fg=BLANCO, relief="flat", padx=12, pady=5,
                  font=("Arial", 9, "bold"), cursor="hand2").pack(anchor="w", pady=(0, 12))

        tk.Label(self.frame_contenido, text="API Key de 2captcha:",
                 bg=BLANCO, font=("Arial", 10, "bold"), fg=AZUL).pack(anchor="w", pady=(4, 4))

        self.ent_captcha = tk.Entry(self.frame_contenido, font=("Courier", 10),
                                     width=44, relief="solid", bd=1)
        self.ent_captcha.pack(anchor="w", ipady=6)
        self.ent_captcha.insert(0, self.config_data.get("twocaptcha_api_key", ""))

        self._separador()
        self._nota("Costo aproximado: $0.002 por captcha · ~$0.60/mes con 3 verificaciones diarias.")

    # ── Pagina 3: Cuentas SISFE ───────────────────────────────────────────────

    def _page_cuentas(self):
        self._titulo("👤  Cuentas SISFE")
        self._subtitulo("Agregá tus cuentas del sistema SISFE para monitorear.")

        # Lista de cuentas
        frame_lista = tk.Frame(self.frame_contenido, bg=BLANCO)
        frame_lista.pack(fill="x", pady=(12,0))

        self.lista_cuentas = tk.Listbox(frame_lista, height=5, font=("Arial", 10),
                                          selectmode="single", relief="solid", bd=1,
                                          activestyle="none")
        self.lista_cuentas.pack(side="left", fill="x", expand=True)
        for c in self.config_data.get("cuentas", []):
            self.lista_cuentas.insert("end", f"  {c['nombre']}  (mat. {c['matricula']})")

        frame_btns = tk.Frame(frame_lista, bg=BLANCO)
        frame_btns.pack(side="left", padx=(8,0))
        tk.Button(frame_btns, text="➕ Agregar", command=self._agregar_cuenta,
                  bg=AZUL, fg=BLANCO, relief="flat", width=12, pady=4,
                  font=("Arial", 9, "bold"), cursor="hand2").pack(pady=(0,6))
        tk.Button(frame_btns, text="🗑 Eliminar", command=self._eliminar_cuenta,
                  bg=GRIS, fg=ROJO, relief="flat", width=12, pady=4,
                  font=("Arial", 9), cursor="hand2").pack()

    def _agregar_cuenta(self):
        dlg = tk.Toplevel(self)
        dlg.title("Agregar cuenta SISFE")
        dlg.resizable(False, False)
        dlg.configure(bg=BLANCO)
        dlg.grab_set()

        # Centrar
        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 380) // 2
        y = self.winfo_y() + (self.winfo_height() - 320) // 2
        dlg.geometry(f"380x320+{x}+{y}")

        campos = {}
        opciones = {
            "nombre":         ("Nombre / Apodo", "Ej: Juan"),
            "matricula":      ("Matrícula SISFE", "Ej: 9689"),
            "clave":          ("Contraseña SISFE", ""),
            "circunscripcion":("Circunscripción", "Santa Fe"),
            "colegio":        ("Colegio", "Abogados"),
        }

        frame = tk.Frame(dlg, bg=BLANCO, padx=20, pady=16)
        frame.pack(fill="both", expand=True)

        for key, (label, placeholder) in opciones.items():
            tk.Label(frame, text=label + ":", bg=BLANCO, font=("Arial", 9, "bold"),
                     fg=AZUL).pack(anchor="w", pady=(8,2))
            show = "*" if key == "clave" else ""
            ent = tk.Entry(frame, font=("Arial", 10), relief="solid", bd=1, show=show)
            ent.pack(fill="x", ipady=4)
            if placeholder:
                ent.insert(0, placeholder)
                ent.config(fg=BORDE)
                def on_focus_in(e, entry=ent, ph=placeholder):
                    if entry.get() == ph:
                        entry.delete(0, "end")
                        entry.config(fg="black")
                def on_focus_out(e, entry=ent, ph=placeholder):
                    if not entry.get():
                        entry.insert(0, ph)
                        entry.config(fg=BORDE)
                ent.bind("<FocusIn>",  on_focus_in)
                ent.bind("<FocusOut>", on_focus_out)
            campos[key] = ent

        def guardar():
            datos = {k: v.get().strip() for k, v in campos.items()}
            # Limpiar placeholders
            for k, (_, ph) in opciones.items():
                if datos[k] == ph:
                    datos[k] = ""
            if not datos["nombre"] or not datos["matricula"] or not datos["clave"]:
                messagebox.showwarning("Faltan datos", "Nombre, matrícula y contraseña son obligatorios.")
                return
            cuentas = self.config_data.setdefault("cuentas", [])
            cuentas.append(datos)
            self.lista_cuentas.insert("end", f"  {datos['nombre']}  (mat. {datos['matricula']})")
            dlg.destroy()

        tk.Button(dlg, text="Guardar cuenta", command=guardar,
                  bg=AZUL, fg=BLANCO, relief="flat", pady=8,
                  font=("Arial", 10, "bold"), cursor="hand2").pack(
                  fill="x", padx=20, pady=(0,16))

    def _eliminar_cuenta(self):
        sel = self.lista_cuentas.curselection()
        if not sel:
            return
        idx = sel[0]
        self.lista_cuentas.delete(idx)
        self.config_data["cuentas"].pop(idx)

    # ── Pagina 4: Email ───────────────────────────────────────────────────────

    def _page_email(self):
        self._titulo("📧  Configuración de email")

        email_cfg = self.config_data.get("email", {})
        self.ent_email = {}

        # ── Remitente ──
        tk.Label(self.frame_contenido, text="Tu Gmail (desde donde se envía):",
                 bg=BLANCO, font=("Arial", 10, "bold"), fg=AZUL).pack(anchor="w", pady=(10,3))
        ent_rem = tk.Entry(self.frame_contenido, font=("Arial", 10),
                           width=44, relief="solid", bd=1)
        ent_rem.pack(anchor="w", ipady=5)
        ent_rem.insert(0, email_cfg.get("remitente", ""))
        self.ent_email["remitente"] = ent_rem

        # ── Destinatarios ──
        tk.Label(self.frame_contenido, text="Destinatarios (separados por coma):",
                 bg=BLANCO, font=("Arial", 10, "bold"), fg=AZUL).pack(anchor="w", pady=(10,3))
        ent_dest = tk.Entry(self.frame_contenido, font=("Arial", 10),
                            width=44, relief="solid", bd=1)
        ent_dest.pack(anchor="w", ipady=5)
        ent_dest.insert(0, email_cfg.get("destinatario", ""))
        self.ent_email["destinatario"] = ent_dest

        # ── Contraseña de aplicación con instructivo ──
        self._separador()

        frame_pwd_titulo = tk.Frame(self.frame_contenido, bg=BLANCO)
        frame_pwd_titulo.pack(fill="x", pady=(10, 4))
        tk.Label(frame_pwd_titulo, text="Contraseña de aplicación de Gmail:",
                 bg=BLANCO, font=("Arial", 10, "bold"), fg=AZUL).pack(side="left")

        # Toggle instructivo
        self.var_mostrar_ayuda = tk.BooleanVar(value=not bool(email_cfg.get("app_password")))
        tk.Checkbutton(frame_pwd_titulo, text="¿Cómo la obtengo?",
                       variable=self.var_mostrar_ayuda,
                       command=self._toggle_ayuda_gmail,
                       bg=BLANCO, fg="#e65100", font=("Arial", 9, "bold"),
                       activebackground=BLANCO, cursor="hand2",
                       selectcolor=BLANCO).pack(side="right")

        # Panel instructivo (visible por defecto si no hay contraseña)
        self.frame_ayuda_gmail = tk.Frame(self.frame_contenido, bg="#fff8e1",
                                           highlightbackground="#FFE500",
                                           highlightthickness=1)

        pasos_gmail = [
            ("1", "Verificación en 2 pasos activa",
             "Tu cuenta de Gmail necesita tener la verificación en 2 pasos activada.\n"
             "Si no la tenés, el botón de abajo te lleva directo a activarla."),
            ("2", "Generá la contraseña de aplicación",
             "Hacé clic en el botón naranja de abajo → en 'Seleccionar aplicación'\n"
             "elegí 'Otra (nombre personalizado)' → escribí 'SISFE' → clic en 'Generar'."),
            ("3", "Copiá el código",
             "Google te va a mostrar una contraseña de 16 letras (ej: abcd efgh ijkl mnop).\n"
             "Copiá ese código exactamente y pegalo en el campo de abajo."),
        ]
        self._instructivo(pasos_gmail, parent=self.frame_ayuda_gmail, bg="#fff8e1")

        btn_frame = tk.Frame(self.frame_ayuda_gmail, bg="#fff8e1")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(btn_frame, text="🔐  Ir a Contraseñas de aplicación (Google)",
                  command=lambda: self._abrir_url(
                      "https://myaccount.google.com/apppasswords"),
                  bg="#e65100", fg=BLANCO, relief="flat", padx=10, pady=5,
                  font=("Arial", 9, "bold"), cursor="hand2").pack(side="left")

        if self.var_mostrar_ayuda.get():
            self.frame_ayuda_gmail.pack(fill="x", pady=(0, 8))

        # Campo contraseña
        ent_pwd = tk.Entry(self.frame_contenido, font=("Courier", 10),
                           width=44, relief="solid", bd=1, show="●")
        ent_pwd.pack(anchor="w", ipady=5)
        ent_pwd.insert(0, email_cfg.get("app_password", ""))
        self.ent_email["app_password"] = ent_pwd

        self._nota("Esta contraseña es diferente a tu contraseña normal de Gmail.")

    def _toggle_ayuda_gmail(self):
        if self.var_mostrar_ayuda.get():
            self.frame_ayuda_gmail.pack(fill="x", pady=(0, 8),
                                         before=self.ent_email["app_password"])
        else:
            self.frame_ayuda_gmail.pack_forget()

    # ── Pagina 5: Horarios ────────────────────────────────────────────────────

    def _page_horarios(self):
        self._titulo("🕐  Horarios de verificación")
        self._subtitulo(
            "Configurá hasta 5 horarios diarios. El último del día enviará\n"
            "el resumen completo. Los domingos el último envío será el resumen semanal."
        )

        # Cargar horarios existentes
        horarios_cfg = self.config_data.get("horarios", [
            {"hora": "09:00"}, {"hora": "14:00"}, {"hora": "20:00"}
        ])
        # Normalizar formato
        self._horarios_vars = []
        horarios_norm = []
        for h in horarios_cfg:
            if isinstance(h, str):
                horarios_norm.append({"hora": h})
            else:
                horarios_norm.append(h)

        # Frame lista de horarios
        self.frame_horarios = tk.Frame(self.frame_contenido, bg=BLANCO)
        self.frame_horarios.pack(fill="x", pady=(12, 0))

        for h in horarios_norm:
            self._agregar_fila_horario(h["hora"])

        # Botón agregar
        self.btn_add_hora = tk.Button(
            self.frame_contenido, text="＋  Agregar horario",
            command=lambda: self._agregar_fila_horario(""),
            bg=GRIS, fg=AZUL, relief="flat", padx=10, pady=4,
            font=("Arial", 9, "bold"), cursor="hand2"
        )
        self.btn_add_hora.pack(anchor="w", pady=(8, 0))

        self._separador()

        # Resumen semanal dominical
        res_sem = self.config_data.get("resumen_semanal", {"activo": True, "hora": "20:00"})
        tk.Label(self.frame_contenido, text="Resumen semanal (domingos):",
                 bg=BLANCO, font=("Arial", 10, "bold"), fg=AZUL).pack(anchor="w", pady=(14, 4))

        frame_dom = tk.Frame(self.frame_contenido, bg=BLANCO)
        frame_dom.pack(anchor="w")

        self.var_resumen_sem = tk.BooleanVar(value=res_sem.get("activo", True))
        tk.Checkbutton(frame_dom, text="Activar resumen dominical",
                       variable=self.var_resumen_sem,
                       bg=BLANCO, font=("Arial", 9), fg="#333333",
                       activebackground=BLANCO, cursor="hand2").pack(side="left")

        tk.Label(frame_dom, text="  Hora:", bg=BLANCO,
                 font=("Arial", 9), fg="#333333").pack(side="left")
        self.ent_hora_dom = tk.Entry(frame_dom, width=7, font=("Arial", 10),
                                      relief="solid", bd=1)
        self.ent_hora_dom.pack(side="left", ipady=3, padx=(4, 0))
        self.ent_hora_dom.insert(0, res_sem.get("hora", "20:00"))

        self._nota("Formato de hora: HH:MM  (ej: 09:00, 14:30, 20:00)")

    def _agregar_fila_horario(self, hora_inicial=""):
        if len(self._horarios_vars) >= 5:
            messagebox.showinfo("Límite", "Podés configurar hasta 5 horarios.")
            return

        fila = tk.Frame(self.frame_horarios, bg=BLANCO)
        fila.pack(anchor="w", pady=3)

        idx = len(self._horarios_vars)
        tipo_txt = "🌅 Mañana" if idx == 0 else "☀️ Tarde" if idx == 1 else f"⏰ Horario {idx+1}"

        tk.Label(fila, text=f"  {tipo_txt}:", bg=BLANCO,
                 font=("Arial", 9), fg="#444", width=14, anchor="w").pack(side="left")

        var = tk.StringVar(value=hora_inicial)
        ent = tk.Entry(fila, textvariable=var, width=8, font=("Courier", 11),
                       relief="solid", bd=1)
        ent.pack(side="left", ipady=4)

        def eliminar(f=fila, v=var):
            self._horarios_vars.remove(v)
            f.destroy()
            self._actualizar_btn_add()

        tk.Button(fila, text="✕", command=eliminar,
                  bg=GRIS, fg=ROJO, relief="flat", font=("Arial", 9),
                  cursor="hand2", padx=4).pack(side="left", padx=(6, 0))

        self._horarios_vars.append(var)
        self._actualizar_btn_add()

    def _actualizar_btn_add(self):
        if hasattr(self, "btn_add_hora"):
            estado = "disabled" if len(self._horarios_vars) >= 5 else "normal"
            self.btn_add_hora.config(state=estado)

    # ── Pagina 6: Resumen ─────────────────────────────────────────────────────

    def _page_resumen(self):
        self._titulo("✅  Todo listo")
        self._subtitulo("Revisa el resumen antes de finalizar.")

        info = tk.Frame(self.frame_contenido, bg=GRIS, relief="flat",
                        padx=16, pady=14, bd=1, highlightbackground=BORDE,
                        highlightthickness=1)
        info.pack(fill="x", pady=(16,0))

        cuentas = self.config_data.get("cuentas", [])
        email   = self.config_data.get("email", {})

        self._row(info, "Cuentas SISFE",
                  ", ".join(c["nombre"] for c in cuentas) or "—")
        self._row(info, "Remitente",    email.get("remitente", "—"))
        self._row(info, "Destinatarios", email.get("destinatario", "—"))
        horarios_cfg = self.config_data.get("horarios", [])
        horas_txt = ", ".join(
            h["hora"] if isinstance(h, dict) else h
            for h in horarios_cfg
        ) or "—"
        res_sem = self.config_data.get("resumen_semanal", {})
        dom_txt = f"Domingos {res_sem.get('hora','20:00')}" if res_sem.get("activo") else "No"

        self._row(info, "Horarios",      horas_txt)
        self._row(info, "Dias",          "Lunes a Viernes")
        self._row(info, "Resumen sem.",  dom_txt)

        self._separador()
        self._nota("Al finalizar se programarán las tareas automaticas en Windows.")

    # ── Validacion y guardado por paso ────────────────────────────────────────

    def _validate_current(self) -> bool:
        if self.step_index == 0:  # Licencia
            code = self.ent_licencia.get().strip()
            valido, msg = validate_license(code)
            if not valido:
                messagebox.showerror("Licencia invalida", msg)
                return False
        elif self.step_index == 1:  # 2captcha
            if not self.ent_captcha.get().strip():
                messagebox.showwarning("Falta API key", "Ingresa tu API key de 2captcha.")
                return False
        elif self.step_index == 2:  # Cuentas
            if not self.config_data.get("cuentas"):
                messagebox.showwarning("Sin cuentas", "Agrega al menos una cuenta SISFE.")
                return False
        elif self.step_index == 3:  # Email
            rem  = self.ent_email["remitente"].get().strip()
            pwd  = self.ent_email["app_password"].get().strip()
            dest = self.ent_email["destinatario"].get().strip()
            if not rem or not pwd or not dest:
                messagebox.showwarning("Faltan datos", "Completa todos los campos de email.")
                return False
        elif self.step_index == 4:  # Horarios
            horas = [v.get().strip() for v in self._horarios_vars if v.get().strip()]
            if not horas:
                messagebox.showwarning("Sin horarios", "Agrega al menos un horario.")
                return False
            import re
            for h in horas:
                if not re.match(r"^\d{2}:\d{2}$", h):
                    messagebox.showwarning("Formato incorrecto",
                                           f"'{h}' no es un horario válido. Usá el formato HH:MM (ej: 09:00).")
                    return False
        return True

    def _save_current(self):
        if self.step_index == 0:
            self.config_data["licencia"] = self.ent_licencia.get().strip()
        elif self.step_index == 1:
            self.config_data["twocaptcha_api_key"] = self.ent_captcha.get().strip()
        elif self.step_index == 3:
            self.config_data["email"]["remitente"]    = self.ent_email["remitente"].get().strip()
            self.config_data["email"]["app_password"] = self.ent_email["app_password"].get().strip()
            self.config_data["email"]["destinatario"] = self.ent_email["destinatario"].get().strip()
        elif self.step_index == 4:  # Horarios
            horas_validas = sorted(set(
                v.get().strip() for v in self._horarios_vars if v.get().strip()
            ))
            self.config_data["horarios"] = [{"hora": h} for h in horas_validas]
            self.config_data["resumen_semanal"] = {
                "activo": self.var_resumen_sem.get(),
                "hora":   self.ent_hora_dom.get().strip() or "20:00",
            }

    # ── Programar tareas (Windows Task Scheduler) ─────────────────────────────

    def _programar_tareas(self):
        import subprocess, sys
        exe    = sys.executable
        script = str(Path(__file__).parent.parent / "run_agent.py")

        horarios_cfg = self.config_data.get("horarios", [
            {"hora": "09:00"}, {"hora": "14:00"}, {"hora": "20:00"}
        ])
        horas = sorted(set(
            h["hora"] if isinstance(h, dict) else h
            for h in horarios_cfg
        ))
        dias_semana = "MON,TUE,WED,THU,FRI"

        # Eliminar tareas viejas antes de recrear
        for i in range(1, 6):
            subprocess.run(
                f'schtasks /delete /tn "SISFE_Check_{i:02d}" /f',
                shell=True, capture_output=True
            )

        for idx, hora in enumerate(horas, start=1):
            nombre = f"SISFE_Check_{idx:02d}_{hora.replace(':','h')}"
            cmd = (
                f'schtasks /create /tn "{nombre}" '
                f'/tr "\\"{exe}\\" \\"{script}\\"" '
                f'/sc WEEKLY /d {dias_semana} /st {hora} /f /rl HIGHEST'
            )
            try:
                subprocess.run(cmd, shell=True, capture_output=True)
            except Exception:
                pass

        # Resumen dominical
        res_sem = self.config_data.get("resumen_semanal", {})
        if res_sem.get("activo", True):
            hora_dom = res_sem.get("hora", "20:00")
            cmd_dom = (
                f'schtasks /create /tn "SISFE_Resumen_Semanal" '
                f'/tr "\\"{exe}\\" \\"{script}\\"" '
                f'/sc WEEKLY /d SUN /st {hora_dom} /f /rl HIGHEST'
            )
            try:
                subprocess.run(cmd_dom, shell=True, capture_output=True)
            except Exception:
                pass

    # ── Helpers de UI ─────────────────────────────────────────────────────────

    def _instructivo(self, pasos, parent=None, bg=BLANCO):
        """
        Renderiza un instructivo paso a paso.
        pasos = [("N", "Título", "Descripción"), ...]
        """
        contenedor = parent or self.frame_contenido
        for num, titulo, desc in pasos:
            fila = tk.Frame(contenedor, bg=bg)
            fila.pack(fill="x", padx=(8 if parent else 0), pady=3)

            # Círculo con número
            circulo = tk.Label(fila, text=num, bg=AZUL, fg=BLANCO,
                               font=("Arial", 9, "bold"),
                               width=2, height=1, relief="flat")
            circulo.pack(side="left", padx=(0, 8), pady=2, anchor="n")

            # Texto
            bloque = tk.Frame(fila, bg=bg)
            bloque.pack(side="left", fill="x", expand=True)
            tk.Label(bloque, text=titulo, bg=bg, fg=AZUL,
                     font=("Arial", 9, "bold"),
                     anchor="w", justify="left").pack(anchor="w")
            tk.Label(bloque, text=desc, bg=bg, fg="#444444",
                     font=("Arial", 8), anchor="w", justify="left",
                     wraplength=420).pack(anchor="w")

    def _abrir_url(self, url: str):
        """Abre una URL en el navegador del sistema."""
        import webbrowser
        webbrowser.open(url)

    def _titulo(self, texto):
        tk.Label(self.frame_contenido, text=texto, bg=BLANCO, fg=AZUL,
                 font=("Arial", 14, "bold")).pack(anchor="w", pady=(10,4))

    def _subtitulo(self, texto):
        tk.Label(self.frame_contenido, text=texto, bg=BLANCO, fg="#444444",
                 font=("Arial", 9), justify="left", wraplength=500).pack(anchor="w")

    def _separador(self):
        tk.Frame(self.frame_contenido, bg=BORDE, height=1).pack(
            fill="x", pady=(20,0))

    def _nota(self, texto):
        tk.Label(self.frame_contenido, text=texto, bg=BLANCO, fg=BORDE,
                 font=("Arial", 8), justify="left", wraplength=500).pack(
                 anchor="w", pady=(6,0))

    def _row(self, parent, label, value):
        f = tk.Frame(parent, bg=GRIS)
        f.pack(fill="x", pady=3)
        tk.Label(f, text=label + ":", bg=GRIS, fg=AZUL,
                 font=("Arial", 9, "bold"), width=16, anchor="w").pack(side="left")
        tk.Label(f, text=value, bg=GRIS, fg="#333333",
                 font=("Arial", 9), anchor="w", wraplength=340).pack(side="left")


def run_wizard(on_finish=None):
    """Punto de entrada para abrir el wizard."""
    app = WizardApp(on_finish=on_finish)
    app.mainloop()


if __name__ == "__main__":
    run_wizard()
