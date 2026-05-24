@echo off
REM ============================================================
REM  SISFE Monitor — Script de build para Windows
REM  Ejecutar como Administrador en la PC de desarrollo
REM ============================================================

echo.
echo ============================================================
echo   SISFE Monitor — Build v1.0.0
echo ============================================================
echo.

REM Detectar Python
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON=py -3.12
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set PYTHON=python
    ) else (
        echo ERROR: No se encontro Python. Instalalo desde python.org
        pause
        exit /b 1
    )
)

echo [1/5] Instalando dependencias...
%PYTHON% -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Fallo pip install
    pause
    exit /b 1
)
echo       OK

echo [2/5] Instalando PyInstaller...
%PYTHON% -m pip install pyinstaller --quiet
echo       OK

echo [3/5] Instalando Playwright Chromium...
%PYTHON% -m playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Fallo playwright install
    pause
    exit /b 1
)
echo       OK

echo [4/5] Compilando con PyInstaller...
%PYTHON% -m PyInstaller build.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Fallo PyInstaller
    pause
    exit /b 1
)
echo       OK — dist\SISFEMonitor\ creado

echo [5/5] Copiando Chromium al build...
REM Copiar el navegador de Playwright al directorio del build
for /d %%D in ("%LOCALAPPDATA%\ms-playwright\chromium-*") do (
    xcopy "%%D" "dist\SISFEMonitor\chromium\" /E /I /Q /Y
)
echo       OK

echo.
echo ============================================================
echo   Build completado exitosamente.
echo.
echo   Siguiente paso:
echo   1. Abri installer.iss con Inno Setup
echo   2. Presiona F9 para compilar el instalador
echo   3. El .exe queda en Output\SISFE_Monitor_Setup_v1.0.0.exe
echo ============================================================
echo.
pause
