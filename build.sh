#!/bin/bash
#
# build.sh — Funnel-Forge single-binary builder (Linux / Termux / proot-Debian)
#
# 1. Checks that the python3-venv module is available
# 2. Creates a fresh virtualenv and installs dependencies inside it
# 3. Builds a single binary with PyInstaller (the .spec file is regenerated
#    fresh on every run - it is not committed, so anyone running this
#    script gets one created automatically)
# 4. Cleans up the venv, build/, __pycache__, and the generated .spec file
#    afterward - only dist/funnel-forge (the final binary) is kept

set -e

APP_NAME="funnel-forge"
VENV_DIR=".build-venv"

echo "== Funnel-Forge single-binary build =="

# --- 1. Check for python3-venv ---
if ! python3 -m venv --help > /dev/null 2>&1; then
    echo "Error: python3 venv module not found."
    echo "On Debian/Termux-proot install it with: sudo apt install python3-venv"
    exit 1
fi

# --- 2. Create a fresh venv ---
rm -rf "$VENV_DIR"
echo "Creating virtual environment ($VENV_DIR)..."
python3 -m venv "$VENV_DIR"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# --- 3. Install dependencies inside the venv ---
echo "Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

# --- 4. Build a single binary with PyInstaller (spec is generated fresh) ---
echo "Building with PyInstaller..."
pyinstaller --noconfirm --clean --onefile --windowed --name "$APP_NAME" main.py

deactivate

# --- 5. Clean up: venv, build artifacts, generated spec - keep dist/ only ---
echo "Cleaning up build artifacts..."
rm -rf "$VENV_DIR" build "${APP_NAME}.spec" __pycache__ core/__pycache__ ui/__pycache__

echo "Done! Binary available at: dist/${APP_NAME}"
