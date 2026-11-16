#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================="
echo "   JOB HUNTER COPILOT WEB DASHBOARD (LINUX / MACOS)      "
echo "========================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 tidak ditemukan!"
    echo "Silakan pasang python3 dan python3-venv lewat package manager distro kamu."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[*] Menyiapkan environment pertama kali (.venv)..."
    python3 -m venv .venv
fi

source .venv/bin/activate

if [ ! -f ".venv/.installed" ]; then
    echo "[*] Memeriksa modul dan browser Playwright (setup awal)..."
    python3 -m pip install -r requirements.txt --quiet
    playwright install chromium
    touch .venv/.installed
fi

echo ""
echo "[*] Membuka Web Dashboard di browser (http://127.0.0.1:5000)..."
python3 web_app.py
