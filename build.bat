@echo off
REM build.bat — Funnel-Forge single-binary builder (Windows)
REM
REM 1. python venv module আছে কিনা যাচাই করে
REM 2. ফ্রেশ virtualenv বানিয়ে dependencies ইনস্টল করে
REM 3. PyInstaller দিয়ে সিঙ্গেল বাইনারি বিল্ড করে (.spec প্রতিবার নতুন জেনারেট হয়)
REM 4. venv, build\, __pycache__, এবং জেনারেটেড .spec মুছে পরিষ্কার করে —
REM    শুধু dist\funnel-forge.exe রেখে দেয়

setlocal enabledelayedexpansion

set APP_NAME=funnel-forge
set VENV_DIR=.build-venv

echo == Funnel-Forge single-binary build ==

REM --- 1. venv module চেক ---
python -m venv --help >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python venv module পাওয়া যায়নি। Python ইনস্টলেশন যাচাই করুন।
    exit /b 1
)

REM --- 2. ফ্রেশ venv তৈরি ---
if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
echo Virtual environment তৈরি করা হচ্ছে (%VENV_DIR%)...
python -m venv "%VENV_DIR%"

call "%VENV_DIR%\Scripts\activate.bat"

REM --- 3. dependency ইনস্টল ---
echo Dependencies ইনস্টল করা হচ্ছে...
pip install --upgrade pip >nul
pip install -r requirements.txt

REM --- 4. PyInstaller দিয়ে বিল্ড (spec ফ্রেশ জেনারেট হয়) ---
echo PyInstaller দিয়ে বিল্ড করা হচ্ছে...
pyinstaller --noconfirm --clean --onefile --windowed --name %APP_NAME% main.py

call "%VENV_DIR%\Scripts\deactivate.bat"

REM --- 5. ক্লিনআপ: venv, build artifacts, generated spec — dist\ ছাড়া সব মুছে ফেলা ---
echo বিল্ড আর্টিফ্যাক্ট পরিষ্কার করা হচ্ছে...
if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"
if exist build rmdir /s /q build
if exist "%APP_NAME%.spec" del /q "%APP_NAME%.spec"
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

echo বিল্ড সম্পন্ন! বাইনারি পাবেন: dist\%APP_NAME%.exe
