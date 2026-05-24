"""
Dialogo de actualizacion disponible.
Se muestra cuando el updater detecta una version mas nueva en GitHub.
"""
import tkinter as tk
from tkinter import ttk
import threading

AZUL   = "#0f1d59"
GRIS   = "#f5f5f6"
BORDE  = "#bcbec0"
BLANCO = "#ffffff"
VERDE  = "#2e7d32"


class UpdateDialog(tk.Toplevel):
    def __init__(self, parent, version_nueva: str, url: str):
        super().__init__(parent)
        self.version_nueva = version_nueva
        self.url = url

        self.title("Actualización disponible")
        self.resizable(False, False)
        self.configure(bg=BLANCO)
        self.grab_set()

        # Centrar
        w, h = 420, 260
        self.update_idletasks()
        sx = self.winfo_screenwidth()
        sy = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sx-w)//2}+{(sy-h)//2}")

        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=AZUL, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔄  Nueva versión disponible",
                 bg=AZUL, fg=BLANCO,
                 font=("Arial", 13, "bold")).pack(padx=20, pady=16, anchor="w")

        # Cuerpo
        body = tk.Frame(self, bg=BLANCO, padx=24, pady=20)
        body.pack(fill="both", expand=True)

        tk.Label(body,
                 text=f"Hay una nueva versión de SISFE Monitor disponible:",
                 bg=BLANCO, fg="#333333", font=("Arial", 10)).pack(anchor="w")

        tk.Label(body, text=f"Versión {self.version_nueva}",
                 bg=BLANCO, fg=AZUL,
                 font=("Arial", 18, "bold")).pack(anchor="w", pady=(6, 12))

        tk.Label(body,
                 text="La actualización se descargará e instalará automáticamente.\nNo necesitás hacer nada más.",
                 bg=BLANCO, fg="#555555", font=("Arial", 9),
                 justify="left").pack(anchor="w")

        # Barra de progreso (oculta hasta que empiece la descarga)
        self.progress_frame = tk.Frame(body, bg=BLANCO)
        self.progress_frame.pack(fill="x", pady=(14, 0))
        self.lbl_progress = tk.Label(self.progress_frame, text="",
                                      bg=BLANCO, fg=BORDE, font=("Arial", 8))
        self.lbl_progress.pack(anchor="w")
        self.progress = ttk.Progressbar(self.progress_frame, length=360,
                                         mode="determinate")

        # Botones
        nav = tk.Frame(self, bg=GRIS, pady=12)
        nav.pack(fill="x", side="bottom")

        self.btn_instalar = tk.Button(
            nav, text="⬇  Actualizar ahora",
            command=self._instalar,
            bg=AZUL, fg=BLANCO, relief="flat",
            padx=14, pady=6, font=("Arial", 10, "bold"),
            cursor="hand2")
        self.btn_instalar.pack(side="right", padx=16)

        tk.Button(nav, text="Ahora no",
                  command=self.destroy,
                  bg=GRIS, relief="flat",
                  padx=14, pady=6, font=("Arial", 10),
                  cursor="hand2").pack(side="right")

    def _instalar(self):
        self.btn_instalar.config(state="disabled", text="Descargando...")
        self.lbl_progress.config(text="Descargando actualización...")
        self.progress.pack(fill="x", pady=(4, 0))

        def _download():
            from core.updater import descargar_e_instalar
            def _progreso(pct):
                self.progress["value"] = pct
                self.lbl_progress.config(text=f"Descargando... {pct}%")
                self.update_idletasks()
            try:
                descargar_e_instalar(self.url, self.version_nueva, _progreso)
            except Exception as exc:
                self.lbl_progress.config(
                    text=f"Error: {exc}", fg="#c62828")
                self.btn_instalar.config(state="normal", text="⬇  Reintentar")

        threading.Thread(target=_download, daemon=True).start()


def mostrar_si_hay_update(parent=None):
    """
    Verifica en background y muestra el dialogo si hay update disponible.
    Llamar desde main.py despues de iniciar el tray.
    """
    from core.updater import hay_actualizacion

    def _check():
        hay, version, url = hay_actualizacion()
        if hay and url:
            root = parent or tk.Tk()
            if parent is None:
                root.withdraw()
            dlg = UpdateDialog(root, version, url)
            dlg.wait_window()

    threading.Thread(target=_check, daemon=True).start()
