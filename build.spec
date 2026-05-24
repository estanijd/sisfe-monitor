# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec para SISFE Monitor.
Genera un .exe standalone con todo incluido.

Uso:
    pyinstaller build.spec
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Archivos de datos a incluir
added_files = [
    ("version.txt",             "."),
    ("assets",                  "assets"),
    ("core/scraper.py",         "core"),
    ("core/notifier.py",        "core"),
    ("core/config_manager.py",  "core"),
    ("core/state_manager.py",   "core"),
    ("core/updater.py",         "core"),
    ("gui/wizard.py",           "gui"),
    ("gui/tray.py",             "gui"),
    ("gui/update_dialog.py",    "gui"),
    ("license/validator.py",    "license"),
    ("run_agent.py",            "."),
]

# Dependencias ocultas de Playwright
hidden = [
    "playwright",
    "playwright.sync_api",
    "pystray",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
]

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SISFEMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # Sin ventana de consola
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SISFEMonitor",
)
