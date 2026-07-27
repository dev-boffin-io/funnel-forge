#!/bin/bash
#
# build.sh — Funnel-Forge single-binary builder (Linux / Termux / proot-Debian)
#
# 1. python3-venv মডিউল আছে কিনা যাচাই করে
# 2. একটা ফ্রেশ virtualenv বানিয়ে তার ভেতরে dependencies ইনস্টল করে
# 3. PyInstaller দিয়ে সিঙ্গেল বাইনারি বিল্ড করে (.spec প্রতিবার নতুন করে জেনারেট হয়,
#    কমিট করা কোনো .spec ফাইলের উপর নির্ভর করে না — যে কেউ এই স্ক্রিপ্ট চালালে
#    নিজে থেকেই একটা .spec তৈরি হবে)
# 4. venv, build/, __pycache__, এবং জেনারেটেড .spec ফাইল মুছে পরিষ্কার করে —
#    শুধু dist/funnel-forge (চূড়ান্ত বাইনারি) রেখে দেয়

set -e

APP_NAME="funnel-forge"
VENV_DIR=".build-venv"

echo "== Funnel-Forge single-binary build =="

# --- ১. python3-venv চেক ---
if ! python3 -m venv --help > /dev/null 2>&1; then
    echo "❌ python3 venv মডিউল পাওয়া যায়নি।"
    echo "   Debian/Termux-proot এ ইনস্টল করতে রান করুন: sudo apt install python3-venv"
    exit 1
fi

# --- ২. ফ্রেশ venv তৈরি ---
rm -rf "$VENV_DIR"
echo "🔧 Virtual environment তৈরি করা হচ্ছে ($VENV_DIR)..."
python3 -m venv "$VENV_DIR"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# --- ৩. venv-এর ভেতরে dependency ইনস্টল ---
echo "📦 Dependencies ইনস্টল করা হচ্ছে..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

# --- ৪. PyInstaller দিয়ে সিঙ্গেল বাইনারি বিল্ড (spec প্রতিবার ফ্রেশ জেনারেট হয়) ---
echo "🚀 PyInstaller দিয়ে বিল্ড করা হচ্ছে..."
pyinstaller --noconfirm --clean --onefile --windowed --name "$APP_NAME" main.py

deactivate

# --- ৫. ক্লিনআপ: venv, build artifacts, generated spec — dist/ ছাড়া সব মুছে ফেলা ---
echo "🧹 বিল্ড আর্টিফ্যাক্ট পরিষ্কার করা হচ্ছে..."
rm -rf "$VENV_DIR" build "${APP_NAME}.spec" __pycache__ core/__pycache__ ui/__pycache__

echo "✅ বিল্ড সম্পন্ন! বাইনারি পাবেন: dist/${APP_NAME}"
