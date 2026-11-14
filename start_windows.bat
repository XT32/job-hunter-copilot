@echo off
setlocal enabledelayedexpansion
title loker-copilot Web Dashboard (UI-First)

echo =========================================================
echo     LOKER-COPILOT WEB DASHBOARD (UI-FIRST / WINDOWS)     
echo =========================================================
echo.

:: 1. Cek Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak terdeteksi di komputer kamu!
    echo Silakan unduh Python di: https://www.python.org/downloads/
    echo PENTING: Saat instalasi, centang opsi "Add python.exe to PATH".
    pause
    exit /b 1
)

:: 2. Cek / Buat Virtual Environment
if not exist ".venv" (
    echo [*] Menyiapkan environment pertama kali (mohon tunggu)...
    python -m venv .venv
)

:: 3. Aktifkan Virtual Environment
call .venv\Scripts\activate.bat

:: 4. Pasang modul yang diperlukan
echo [*] Memeriksa modul dan browser Playwright...
pip install -r requirements.txt --quiet
playwright install chromium

:: 5. Langsung jalankan Web UI (UI-First)
echo.
echo [*] Membuka Web Dashboard di browser (http://127.0.0.1:5000)...
python web_app.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Aplikasi terhenti karena error.
    pause
)
