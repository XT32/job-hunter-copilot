#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================="
echo "       JOB HUNTER COPILOT - SETUP & LAUNCHER (LINUX)     "
echo "========================================================="
echo ""

# 1. Cek Python3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 tidak ditemukan di sistem kamu!"
    echo "Silakan install python3 (misal: sudo apt update && sudo apt install python3 python3-venv python3-pip)"
    exit 1
fi

# 2. Cek / Buat venv
if [ ! -d ".venv" ]; then
    echo "[*] Membuat Virtual Environment Python (.venv)..."
    python3 -m venv .venv
    echo "[OK] Virtual Environment berhasil dibuat."
fi

# 3. Aktifkan venv
source .venv/bin/activate

# 4. Install dependencies
echo "[*] Memeriksa & menginstall dependencies..."
python3 -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# 5. Pastikan Chromium Playwright terpasang
echo "[*] Memastikan browser Chromium Playwright terpasang..."
playwright install chromium

# 6. Jalankan aplikasi
echo ""
echo "========================================================="
echo "             MEMULAI JOB HUNTER COPILOT...               "
echo "========================================================="
echo ""
python3 main.py
