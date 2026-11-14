import os
import sys
import threading
import time
import webbrowser
from flask import Flask, render_template, request, jsonify, send_file
from playwright.sync_api import sync_playwright

from src.browser import get_browser_context
from src.glints import GlintsHunter
from src.jobstreet import JobstreetHunter
from src.maganghub import MagangHubHunter
from src.storage import load_history, record_job, update_job_status, export_history_to_csv
from src.config import load_config, save_config
from src.cover_letter import generate_cover_letter
from src.email_sender import send_cold_email
from src.notifier import send_telegram_alert

app = Flask(__name__, template_folder="templates")
playwright_lock = threading.Lock()

HUNTER_MAP = {
    "glints": (GlintsHunter, "Glints Indonesia"),
    "jobstreet": (JobstreetHunter, "JobStreet Indonesia"),
    "maganghub": (MagangHubHunter, "MagangHub Kemnaker")
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())

@app.route("/api/config", methods=["POST"])
def update_config():
    data = request.json or {}
    cfg = load_config()
    
    for key in ["profile", "screening_defaults", "smtp", "telegram", "min_delay_sec", "max_delay_sec", "auto_skip_already_seen"]:
        if key in data:
            cfg[key] = data[key]
        
    save_config(cfg)
    return jsonify({"success": True, "config": cfg})

@app.route("/api/scan", methods=["POST"])
def scan_jobs():
    data = request.json or {}
    platform = data.get("platform", "glints").lower()
    cfg = load_config()

    hunter_info = HUNTER_MAP.get(platform, (GlintsHunter, "Glints Indonesia"))
    HunterClass, platform_name = hunter_info

    with playwright_lock:
        with sync_playwright() as p:
            context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 150))
            page = context.new_page()
            
            try:
                hunter = HunterClass(page, cfg)
                jobs = hunter.search_jobs()

                # Notifikasi Telegram jika aktif
                tg_cfg = cfg.get("telegram", {})
                if tg_cfg.get("enabled", False) and jobs:
                    for j in jobs[:3]:
                        send_telegram_alert(
                            title=j["title"],
                            company=j["company"],
                            url=j["url"],
                            platform=platform_name,
                            salary=j.get("salary", "Tidak dicantumkan"),
                            bot_token=tg_cfg.get("bot_token", ""),
                            chat_id=tg_cfg.get("chat_id", "")
                        )

                return jsonify({"success": True, "platform": platform, "jobs": jobs})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
            finally:
                context.close()

@app.route("/api/apply", methods=["POST"])
def apply_job():
    data = request.json or {}
    platform = data.get("platform", "glints").lower()
    job_url = data.get("url")
    title = data.get("title", "Posisi")
    company = data.get("company", "Perusahaan")

    if not job_url:
        return jsonify({"success": False, "error": "URL lowongan wajib disertakan"}), 400

    cfg = load_config()
    hunter_info = HUNTER_MAP.get(platform, (GlintsHunter, "Glints Indonesia"))
    HunterClass, platform_name = hunter_info

    with playwright_lock:
        with sync_playwright() as p:
            context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 150))
            page = context.new_page()

            try:
                hunter = HunterClass(page, cfg)
                result = hunter.inspect_and_apply(job_url)

                if result["status"] == "success":
                    record_job(job_url, title, company, status="applied", notes=f"Lamar via {platform_name}")
                elif result["status"] == "already_applied":
                    record_job(job_url, title, company, status="applied", notes=f"Sudah dilamar sebelumnya ({platform_name})")
                elif result["status"] == "external_link":
                    record_job(job_url, title, company, status="skipped", notes=f"Tautan eksternal ({platform_name})")

                return jsonify({"success": True, "result": result})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
            finally:
                context.close()

@app.route("/api/skip", methods=["POST"])
def skip_job():
    data = request.json or {}
    job_url = data.get("url")
    title = data.get("title", "Posisi")
    company = data.get("company", "Perusahaan")
    notes = data.get("notes", "Dilewati via Web UI")

    if not job_url:
        return jsonify({"success": False, "error": "URL wajib diisi"}), 400

    record_job(job_url, title, company, status="skipped", notes=notes)
    return jsonify({"success": True})

@app.route("/api/status-update", methods=["POST"])
def update_status():
    """Mengubah status dalam papan Kanban pelacak lamaran"""
    data = request.json or {}
    job_url = data.get("url")
    new_status = data.get("status")
    notes = data.get("notes")

    if not job_url or not new_status:
        return jsonify({"success": False, "error": "URL dan status baru diperlukan"}), 400

    success = update_job_status(job_url, new_status, notes)
    return jsonify({"success": success})

@app.route("/api/cover-letter", methods=["POST"])
def get_cover_letter():
    """Menghasilkan surat lamaran / cover letter instan yang dipersonalisasi"""
    data = request.json or {}
    role = data.get("role", "Posisi")
    company = data.get("company", "Perusahaan")
    preset = data.get("preset", "formal")
    
    cfg = load_config()
    profile = cfg.get("profile", {})
    letter = generate_cover_letter(role, company, profile, preset)
    return jsonify({"success": True, "cover_letter": letter})

@app.route("/api/send-email", methods=["POST"])
def direct_send_email():
    """Kirim lamaran langsung ke alamat email HRD via SMTP dengan lampiran CV"""
    data = request.json or {}
    to_email = data.get("to_email")
    subject = data.get("subject")
    body = data.get("body")
    
    cfg = load_config()
    smtp_cfg = cfg.get("smtp", {})
    cv_path = smtp_cfg.get("cv_path", "attachments/CV.pdf")

    result = send_cold_email(to_email, subject, body, attachment_path=cv_path, smtp_config=smtp_cfg)
    if result["success"]:
        record_job(f"mailto:{to_email}", subject, to_email, status="applied", notes="Cold Email Langsung")
    return jsonify(result)

@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify(load_history())

@app.route("/api/export", methods=["GET"])
def export_csv():
    csv_file = export_history_to_csv()
    return send_file(
        csv_file,
        mimetype="text/csv",
        as_attachment=True,
        download_name="riwayat_lamaran_kerja.csv"
    )

def start_server(port=5000, auto_open=True):
    if auto_open:
        def open_browser():
            time.sleep(1.2)
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    print(f"\n[OK] loker-cli Web Dashboard aktif di: http://127.0.0.1:{port}")
    print("[*] Menutup terminal ini akan menghentikan server web.\n")
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    start_server()
