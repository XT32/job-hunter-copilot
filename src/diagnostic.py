"""
Modul Diagnosa Portal & Pembuat Laporan Masalah (Diagnostic Bundle).
Membantu pengguna awam dan pengembang memeriksa kesehatan koneksi, sesi login,
dan mengunduh berkas laporan masalah (debug bundle) secara aman (tanpa data pribadi/password).
"""

import json
import os
import platform
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile

PORTAL_URLS = {
    "jobstreet": "https://id.jobstreet.com",
    "glints": "https://glints.com",
    "dealls": "https://dealls.com",
    "maganghub": "https://maganghub.kemnaker.go.id",
}

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
SCREENSHOTS_DIR = os.path.join(DATA_DIR, "screenshots")
USER_BROWSER_DIR = os.path.join(ROOT_DIR, "user_browser_data")


def check_portal_connectivity(timeout: int = 5) -> dict:
    results = {}
    for name, url in PORTAL_URLS.items():
        start = time.time()
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.status
                latency_ms = int((time.time() - start) * 1000)
                results[name] = {
                    "reachable": status_code in (200, 301, 302, 403),
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "url": url,
                }
        except Exception as e:
            results[name] = {
                "reachable": False,
                "error": str(e),
                "url": url,
            }
    return results


def check_system_health(config_loader=None, db_verifier=None) -> dict:
    portal_status = check_portal_connectivity()

    # Cek direktori browser lokal
    browser_ready = os.path.exists(USER_BROWSER_DIR)
    cookie_file = os.path.join(USER_BROWSER_DIR, "Default", "Cookies")
    has_cookies = os.path.exists(cookie_file) and os.path.getsize(cookie_file) > 1024

    # Cek CV
    active_cv = ""
    has_cv = False
    if config_loader:
        try:
            cfg = config_loader()
            active_cv = cfg.get("active_cv", "")
            cv_path = os.path.join(ROOT_DIR, "attachments", active_cv) if active_cv else ""
            has_cv = bool(cv_path and os.path.exists(cv_path) and os.path.getsize(cv_path) > 100)
        except Exception:
            pass

    # Cek Database
    db_status = {}
    if db_verifier:
        try:
            db_status = db_verifier()
        except Exception as e:
            db_status = {"valid": False, "error": str(e)}

    return {
        "os": f"{platform.system()} {platform.release()}",
        "python_version": sys.version.split()[0],
        "portals": portal_status,
        "browser_session": {
            "profile_dir_exists": browser_ready,
            "session_cookies_present": has_cookies,
        },
        "active_cv": {
            "filename": active_cv,
            "ready": has_cv,
        },
        "database": db_status,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def sanitize_config(cfg: dict) -> dict:
    """Menyensor kata sandi, token, dan data kontak sensitif sebelum disertakan ke laporan debug."""
    clean = json.loads(json.dumps(cfg))
    if "smtp" in clean:
        clean["smtp"]["password"] = "[REDACTED]" if clean["smtp"].get("password") else ""
        clean["smtp"]["email"] = "[REDACTED_EMAIL]" if clean["smtp"].get("email") else ""
    if "telegram" in clean:
        clean["telegram"]["bot_token"] = "[REDACTED]" if clean["telegram"].get("bot_token") else ""
        clean["telegram"]["chat_id"] = "[REDACTED]" if clean["telegram"].get("chat_id") else ""
    if "profile" in clean:
        clean["profile"]["applicant_name"] = "[REDACTED_NAME]"
        clean["profile"]["contact_info"] = "[REDACTED_CONTACT]"
    return clean


def generate_debug_bundle(logs: list = None, cfg: dict = None, db_status: dict = None) -> str:
    """
    Membuat arsip .zip berisi diagnosa sistem, konfigurasi yang disensor,
    log aktivitas, dan tangkapan layar kendala terakhir.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    bundle_path = os.path.join(DATA_DIR, "loker_debug_bundle.zip")

    health = check_system_health(db_verifier=lambda: db_status or {})
    clean_cfg = sanitize_config(cfg or {})

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Info Sistem
        with open(os.path.join(tmpdir, "system_health.json"), "w", encoding="utf-8") as f:
            json.dump(health, f, indent=2)

        # 2. Config tersensor
        with open(os.path.join(tmpdir, "config_redacted.json"), "w", encoding="utf-8") as f:
            json.dump(clean_cfg, f, indent=2)

        # 3. Log aktivitas
        with open(os.path.join(tmpdir, "activity_logs.json"), "w", encoding="utf-8") as f:
            json.dump(logs or [], f, indent=2)

        # 4. Ambil hingga 3 screenshot kegagalan terbaru jika ada
        screenshots_tmp = os.path.join(tmpdir, "screenshots")
        os.makedirs(screenshots_tmp, exist_ok=True)
        if os.path.exists(SCREENSHOTS_DIR):
            shots = sorted(
                [f for f in os.listdir(SCREENSHOTS_DIR) if f.endswith(".png")],
                reverse=True,
            )[:3]
            for s in shots:
                shutil.copy2(os.path.join(SCREENSHOTS_DIR, s), os.path.join(screenshots_tmp, s))

        # Buat zip
        if os.path.exists(bundle_path):
            try:
                os.remove(bundle_path)
            except Exception:
                pass

        with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, tmpdir)
                    zf.write(full_p, rel_p)

    return bundle_path
