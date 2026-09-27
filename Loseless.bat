@echo off
chcp 65001 >nul
title Loseless
cd /d "%~dp0"

echo.
echo   ==============================
echo      LOSELESS - audio para DJ
echo   ==============================
echo.

rem --- 1. Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [X] No se encontro Python.
    echo     Instalalo desde https://www.python.org/downloads/
    echo     y marca la casilla "Add python.exe to PATH".
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

rem --- 2. ffmpeg ---
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo [!] No se encontro ffmpeg. Instalandolo con winget...
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    echo.
    echo     Listo. Cierra esta ventana y vuelve a abrir Loseless.bat
    pause
    exit /b 0
)

rem --- 3. Entorno propio de la app (solo la primera vez) ---
if not exist ".venv\Scripts\python.exe" (
    echo Preparando la app por primera vez, espera un momento...
    python -m venv .venv
    if errorlevel 1 (
        echo [X] No se pudo crear el entorno de Python.
        pause
        exit /b 1
    )
)

rem --- 4. Instalar / actualizar dependencias (yt-dlp se actualiza seguido) ---
echo Revisando actualizaciones...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check --upgrade -r requirements.txt
if errorlevel 1 (
    echo [X] Error instalando dependencias. Revisa tu conexion a internet.
    pause
    exit /b 1
)

rem --- 5. Abrir la app ---
echo.
echo Abriendo Loseless en tu navegador...
echo NO cierres esta ventana mientras descargas. Para salir, cierrala.
echo.
".venv\Scripts\python.exe" -m loseless --web
pause
