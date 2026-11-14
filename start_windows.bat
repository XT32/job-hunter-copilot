@echo off
setlocal enabledelayedexpansion
title Job Hunter Copilot - Automated Setup & Launcher

echo =========================================================
echo       JOB HUNTER COPILOT - SETUP & LAUNCHER (WINDOWS)
echo =========================================================
echo.

:: 1. Cek Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python tidak terdeteksi di komputer kamu!
    echo Silakan download dan install Python terlebih dahulu di:
    echo https://www.python.org/downloads/
    echo.
    echo PENTING: Saat install, pastikan centang opsi "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

:: 2. Cek / Buat Virtual Environment
if not exist ".venv" (
    echo [*] Membuat Virtual Environment (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Gagal membuat virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual Environment berhasil dibuat.
)

:: 3. Aktifkan Virtual Environment
call .venv\Scripts\activate.bat

:: 4. Install / Update Dependencies
echo [*] Memeriksa & menginstall modul Python yang dibutuhkan...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Gagal menginstall dependencies dari requirements.txt
    pause
    exit /b 1
)

:: 5. Install Browser Chromium untuk Playwright jika belum ada
echo [*] Memastikan browser Chromium Playwright terpasang...
playwright install chromium
if %errorlevel% neq 0 (
    echo [WARNING] Playwright install browser ada kendala, mencoba melanjutkan...
)

:: 6. Jalankan Aplikasi
echo.
echo =========================================================
echo             MEMULAI JOB HUNTER COPILOT...
echo =========================================================
echo.
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Terjadi kesalahan saat menjalankan aplikasi.
    pause
)
