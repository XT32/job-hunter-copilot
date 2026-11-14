@echo off
setlocal enabledelayedexpansion
title loker-cli Web Dashboard Launcher

echo =========================================================
echo       LOKER-CLI WEB DASHBOARD (WINDOWS)
echo =========================================================
echo.

:: 1. Cek Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak terdeteksi di komputer kamu!
    echo Silakan unduh Python di: https://www.python.org/downloads/
    echo Pastikan centang "Add python.exe to PATH" saat instalasi.
    pause
    exit /b 1
)

:: 2. Cek / Buat Virtual Environment
if not exist ".venv" (
    echo [*] Menyiapkan environment pertama kali...
    python -m venv .venv
)

:: 3. Aktifkan Virtual Environment
call .venv\Scripts\activate.bat

:: 4. Pasang modul yang diperlukan
echo [*] Memeriksa dependensi...
pip install -r requirements.txt --quiet
playwright install chromium

:: 5. Jalankan Web UI
echo.
echo =========================================================
echo  Membuka Web Dashboard di browser kamu...
echo  (http://127.0.0.1:5000)
echo =========================================================
echo.
python web_app.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Aplikasi terhenti karena error.
    pause
)
