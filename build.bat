@echo off
REM build.bat - Funnel-Forge single-binary builder (Windows)
REM
REM 1. Checks that the python venv module is available
REM 2. Creates a fresh virtualenv and installs dependencies inside it
REM 3. Builds a single binary with PyInstaller (the .spec file is
REM    regenerated fresh on every run)
REM 4. Cleans up the venv, build\, __pycache__, and the generated .spec
REM    file afterward - only dist\funnel-forge.exe is kept

setlocal enabledelayedexpansion

set APP_NAME=funnel-forge
set VENV_DIR=.build-venv

echo == Funnel-Forge single-binary build ==

REM --- 1. Check for the venv module ---
python -m venv --help >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python venv module not found. Check your Python installation.
    exit /b 1
)

REM --- 2. Create a fresh venv ---
if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
echo Creating virtual environment (%VENV_DIR%)...
python -m venv "%VENV_DIR%"

call "%VENV_DIR%\Scripts\activate.bat"

REM --- 3. Install dependencies ---
echo Installing dependencies...
pip install --upgrade pip >nul
pip install -r requirements.txt

REM --- 4. Build with PyInstaller (spec regenerated fresh) ---
echo Building with PyInstaller...
pyinstaller --noconfirm --clean --onefile --windowed --name %APP_NAME% main.py

call "%VENV_DIR%\Scripts\deactivate.bat"

REM --- 5. Clean up: venv, build artifacts, generated spec - keep dist\ only ---
echo Cleaning up build artifacts...
if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
if exist build rmdir /s /q build
if exist "%APP_NAME%.spec" del /q "%APP_NAME%.spec"
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

echo Done! Binary available at: dist\%APP_NAME%.exe
