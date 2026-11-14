#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================="
echo "       LOKER-CLI WEB DASHBOARD (LINUX / MACOS)           "
echo "========================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 tidak ditemukan!"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[*] Membuat Virtual Environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "[*] Memeriksa dependensi..."
python3 -m pip install -r requirements.txt --quiet
playwright install chromium

echo ""
echo "========================================================="
echo "  Membuka Web Dashboard di browser kamu...               "
echo "  (http://127.0.0.1:5000)                                "
echo "========================================================="
echo ""
python3 web_app.py
