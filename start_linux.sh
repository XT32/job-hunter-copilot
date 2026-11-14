#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================="
echo "     LOKER-COPILOT WEB DASHBOARD (UI-FIRST / LINUX)      "
echo "========================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 tidak ditemukan!"
    echo "Silakan pasang python3 dan python3-venv lewat package manager distro kamu."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[*] Membuat Virtual Environment (.venv)..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "[*] Memeriksa modul dan browser Playwright..."
python3 -m pip install -r requirements.txt --quiet
playwright install chromium

echo ""
echo "[*] Membuka Web Dashboard di browser (http://127.0.0.1:5000)..."
python3 web_app.py
