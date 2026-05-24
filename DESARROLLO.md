# SISFE Monitor — Guía de Desarrollo

## Estructura del proyecto

```
sisfe_monitor/
├── main.py                  # Punto de entrada (tray + wizard)
├── run_agent.py             # Runner del scraper (llamado por Task Scheduler)
├── version.txt              # Versión actual (ej: 1.0.0)
├── requirements.txt
├── build.spec               # PyInstaller config
├── installer.iss            # Inno Setup config
│
├── core/
│   ├── scraper.py           # COPIAR desde sisfe_agent/
│   ├── notifier.py          # COPIAR desde sisfe_agent/
│   ├── config_manager.py    # Manejo de config.json
│   └── updater.py           # Auto-actualización desde GitHub
│
├── gui/
│   ├── wizard.py            # Wizard de configuración (Tkinter)
│   └── tray.py              # Ícono en bandeja del sistema
│
├── license/
│   ├── validator.py         # Validación de licencias
│   ├── generator.py         # Generador de licencias (solo vos)
│   └── licencias_emitidas.json  # Registro de clientes
│
└── assets/
    └── icon.ico             # Ícono de la app
```

---

## Setup inicial (una sola vez)

```bash
cd sisfe_monitor

# Copiar scraper y notifier desde el agente original
cp ../sisfe_agent/scraper.py  core/scraper.py
cp ../sisfe_agent/notifier.py core/notifier.py

# Instalar dependencias
pip install -r requirements.txt
playwright install chromium
```

---

## Generar licencias para clientes

```bash
# Generar una licencia perpetua
python license/generator.py "Juan Perez" "juan@gmail.com"

# Con vencimiento (1 año)
python license/generator.py "Juan Perez" "juan@gmail.com" --vence 2027-12-31

# Ver todas las licencias emitidas
python license/generator.py --lista

# Validar un código existente
python license/generator.py --validar "SISFE-XXXX-XXXX-..."
```

---

## Probar el wizard localmente

```bash
python gui/wizard.py
```

---

## Publicar una actualización

1. Modificá el código
2. Actualizá `version.txt` (ej: `1.0.1`)
3. Buildeá con PyInstaller (desde Windows):
   ```
   pyinstaller build.spec
   ```
4. Compilá el instalador con Inno Setup → genera `Output/SISFE_Monitor_Setup_v1.0.1.exe`
5. En GitHub → Releases → "Create a new release"
   - Tag: `v1.0.1`
   - Adjuntá el `.exe` del instalador
6. Los usuarios con la app instalada verán la notificación de actualización automáticamente ✅

---

## Configurar GitHub para las actualizaciones

Antes de buildear por primera vez, editá `core/updater.py`:
```python
GITHUB_USER = "tu-usuario-github"   # ← tu usuario real
GITHUB_REPO = "sisfe-monitor-releases"
```

Creá el repo en GitHub (puede ser privado, pero las Releases deben ser públicas
para que la descarga funcione sin autenticación).

---

## Build completo (en Windows)

```bat
REM 1. Instalar todo
pip install -r requirements.txt
playwright install chromium

REM 2. Build PyInstaller
pyinstaller build.spec --clean

REM 3. El resultado queda en dist/SISFEMonitor/
REM 4. Abrir installer.iss en Inno Setup y presionar F9
REM 5. El instalador queda en Output/SISFE_Monitor_Setup_v1.0.0.exe
```

---

## Precio sugerido

| Plan | Precio | Incluye |
|------|--------|---------|
| Licencia perpetua | $30.000 ARS | Licencia única, soporte 3 meses |
| Anual con soporte | $15.000 ARS/año | Actualizaciones + soporte por email |
