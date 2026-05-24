# SISFE Monitor — Guía de Build y Release

> **USO EXCLUSIVO DEL DESARROLLADOR** — no distribuir este archivo.

---

## Índice

1. [Requisitos del entorno de build](#1-requisitos)
2. [Estructura del proyecto](#2-estructura)
3. [Generar una licencia para un cliente](#3-generar-licencias)
4. [Compilar el .exe con PyInstaller](#4-compilar-exe)
5. [Crear el instalador con Inno Setup](#5-crear-instalador)
6. [Publicar una nueva release en GitHub](#6-publicar-release)
7. [Actualizar versión](#7-actualizar-version)
8. [Checklist completo de release](#8-checklist)

---

## 1. Requisitos

Necesitás una PC con **Windows 10/11 (64-bit)** para compilar el .exe.

### Software a instalar:

| Herramienta | Link | Notas |
|---|---|---|
| Python 3.12 (64-bit) | [python.org](https://python.org) | Marcar "Add to PATH" |
| Inno Setup 6 | [jrsoftware.org](https://jrsoftware.org/isinfo.php) | Para el instalador |
| Git | [git-scm.com](https://git-scm.com) | Para clonar el repo |

---

## 2. Estructura del proyecto

```
sisfe_monitor/
├── main.py              ← Punto de entrada
├── run_agent.py         ← Ejecutado por el Task Scheduler
├── build.spec           ← Configuración de PyInstaller
├── build_windows.bat    ← Script de build (ejecutar como Admin)
├── installer.iss        ← Script de Inno Setup
├── version.txt          ← Versión actual (ej: 1.0.0)
├── requirements.txt     ← Dependencias Python
├── assets/
│   ├── icon.ico         ← Ícono de la aplicación
│   ├── icon.png         ← Ícono PNG (para tray)
│   └── RobotoFlex.ttf   ← Fuente BE LEGAL
├── core/                ← Lógica del agente
├── gui/                 ← Wizard y tray
├── license/             ← Validador y generador de licencias
│   ├── validator.py     ← Se distribuye con el .exe
│   ├── generator.py     ← SOLO PARA DESARROLLADOR — no distribuir
│   └── licencias_emitidas.json  ← Registro de clientes (gitignoreado)
└── GUIA_INSTALACION.html  ← Guía para el cliente
```

---

## 3. Generar licencias

### Nuevo cliente — Plan Básico (1 cuenta, u$s 100)
```bash
python3 license/generator.py "Juan Perez" "juan@gmail.com" --cuentas 1
```

### Nuevo cliente — Plan Pro (2 cuentas, u$s 120)
```bash
python3 license/generator.py "Maria Lopez" "maria@gmail.com"
```

### Con fecha de vencimiento (si querés vender con soporte por tiempo)
```bash
python3 license/generator.py "Estudio Gomez" "info@estudio.com" --cuentas 2 --vence 2027-05-24
```

### Ver todos los clientes
```bash
python3 license/generator.py --lista
```

### Validar un código
```bash
python3 license/generator.py --validar "SISFE-XXXXXX-XXXXXX-..."
```

> **Guardá siempre `license/licencias_emitidas.json` — está en .gitignore para no exponerlo.**

---

## 4. Compilar el .exe

### Paso a paso en Windows:

1. Abrí una terminal **como Administrador** (`cmd` → clic derecho → "Ejecutar como administrador")

2. Cloná o actualizá el repo:
   ```bat
   git clone https://github.com/estanijd/sisfe-monitor .
   REM o si ya existe:
   git pull origin main
   ```

3. Ejecutá el script de build:
   ```bat
   build_windows.bat
   ```

El script hace automáticamente:
- ✅ Instala dependencias (`requirements.txt`)
- ✅ Instala PyInstaller
- ✅ Instala Playwright Chromium
- ✅ Compila con `pyinstaller build.spec --clean`
- ✅ Copia el navegador Chromium al build

Al terminar, el resultado está en `dist\SISFEMonitor\`.

### Si falla algún paso:

**"No se encontró Python"**
→ Instalá Python 3.12 desde python.org y marcá "Add to PATH"

**"Failed to install playwright"**
→ Ejecutá manualmente: `python -m playwright install chromium`

**"UPX is not available"**
→ Es un warning, no un error. El .exe se genera igual (solo un poco más grande).

---

## 5. Crear el instalador

1. Abrí **Inno Setup Compiler**
2. Archivo → Abrir → seleccioná `installer.iss`
3. Presioná **F9** (o Build → Compile)
4. El instalador queda en `Output\SISFE_Monitor_Setup_v1.0.0.exe`

### Imágenes del asistente (opcionales):
El `.iss` referencia dos archivos BMP para personalizar el instalador de Windows:
- `assets\wizard_banner.bmp` — Banner lateral (164×314 px)
- `assets\icon_small.bmp` — Ícono pequeño (55×58 px)

Si no existen, Inno Setup usa los predeterminados. Para crear los BMP con la marca BE LEGAL, usá cualquier editor de imagen (Paint, GIMP) y exportá como BMP.

---

## 6. Publicar release en GitHub

1. Andá a: https://github.com/estanijd/sisfe-monitor-releases

2. Hacé clic en **Releases → Draft a new release**

3. Completá:
   - **Tag**: `v1.0.1` (o la versión correspondiente)
   - **Title**: `SISFE Monitor v1.0.1`
   - **Description**: listado de cambios (ver sección siguiente)

4. Adjuntá el archivo: `SISFE_Monitor_Setup_v1.0.1.exe`

5. Hacé clic en **Publish release**

Los usuarios ya instalados recibirán automáticamente la notificación de actualización la próxima vez que abran SISFE Monitor.

### Formato de release notes:
```markdown
## SISFE Monitor v1.0.1

### Novedades
- [Descripción del cambio 1]
- [Descripción del cambio 2]

### Correcciones
- [Bug fix 1]

### Cómo actualizar
Descargá el instalador y ejecutalo — tu configuración se mantiene.
```

---

## 7. Actualizar versión

Cuando hagas una nueva release, actualizá estos dos archivos:

### `version.txt`
```
1.0.1
```

### `installer.iss` (línea 2)
```ini
#define MyAppVersion   "1.0.1"
```

También actualizá el nombre del archivo en `build_windows.bat` (línea del echo final):
```bat
echo   3. El .exe queda en Output\SISFE_Monitor_Setup_v1.0.1.exe
```

---

## 8. Checklist completo de release

```
PREPARACIÓN
  [ ] Actualizar version.txt con la nueva versión
  [ ] Actualizar #define MyAppVersion en installer.iss
  [ ] Hacer commit y push de todos los cambios al repo de desarrollo

BUILD
  [ ] Ejecutar build_windows.bat como Administrador
  [ ] Verificar que dist\SISFEMonitor\ se generó correctamente
  [ ] Abrir installer.iss en Inno Setup y presionar F9
  [ ] Verificar que Output\SISFE_Monitor_Setup_vX.X.X.exe existe

TESTING
  [ ] Instalar en una PC limpia (o VM) con el .exe generado
  [ ] Completar el wizard de configuración completo
  [ ] Verificar que llega el email de prueba
  [ ] Verificar que correr el agente manualmente funciona (--run)
  [ ] Verificar que los horarios programados en Task Scheduler están creados

RELEASE
  [ ] Subir el .exe a GitHub Releases con tag vX.X.X
  [ ] Verificar que la API devuelve la nueva versión:
      curl https://api.github.com/repos/estanijd/sisfe-monitor-releases/releases/latest
  [ ] Instalar la versión anterior en otra PC y verificar que aparece el aviso de actualización

DISTRIBUCIÓN
  [ ] Enviar el link de descarga al cliente (GitHub Release)
  [ ] Enviar la GUIA_INSTALACION.html como PDF
  [ ] Enviar el código de licencia generado
```

---

## Contacto / Soporte

**BE LEGAL** · ediaz@belegal.ar
