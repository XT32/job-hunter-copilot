import os
import sys
import threading
import time
import webbrowser
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from playwright.sync_api import sync_playwright

from src.browser import get_browser_context
from src.glints import GlintsHunter
from src.jobstreet import JobstreetHunter
from src.maganghub import MagangHubHunter
from src.dealls import DeallsHunter
from src.storage import load_history, record_job, update_job_status, export_history_to_csv, HISTORY_FILE
from src.config import load_config, save_config, DEFAULT_CONFIG_PATH
from src.cover_letter import generate_cover_letter
from src.email_sender import send_cold_email
from src.notifier import send_telegram_alert
from src.cv_analyzer import extract_text_from_pdf, calculate_ats_match
from src.scheduler import AutoHuntScheduler

app = Flask(__name__, template_folder="templates")
playwright_lock = threading.Lock()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "attachments")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
CV_FILE_PATH = os.path.join(UPLOAD_FOLDER, "CV.pdf")

HUNTER_MAP = {
    "glints": (GlintsHunter, "Glints Indonesia"),
    "jobstreet": (JobstreetHunter, "JobStreet Indonesia"),
    "maganghub": (MagangHubHunter, "MagangHub Kemnaker"),
    "dealls": (DeallsHunter, "Dealls Jobs")
}

scheduler = AutoHuntScheduler(HUNTER_MAP, load_config)

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

@app.route("/api/upload-cv", methods=["POST"])
def upload_cv():
    """Menerima unggahan file PDF CV pengguna dan mengekstrak teksnya"""
    if "cv" not in request.files:
        return jsonify({"success": False, "error": "Tidak ada file yang diunggah"}), 400

    file = request.files["cv"]
    if file.filename == "" or not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "File harus berformat PDF"}), 400

    file.save(CV_FILE_PATH)
    text = extract_text_from_pdf(CV_FILE_PATH)

    # Simpan path CV ke config SMTP
    cfg = load_config()
    if "smtp" not in cfg:
        cfg["smtp"] = {}
    cfg["smtp"]["cv_path"] = CV_FILE_PATH
    save_config(cfg)

    return jsonify({
        "success": True,
        "message": "File CV berhasil disimpan!",
        "has_text": len(text) > 20,
        "char_count": len(text)
    })

@app.route("/api/scan", methods=["POST"])
def scan_jobs():
    data = request.json or {}
    platform = data.get("platform", "glints").lower()
    cfg = load_config()

    hunter_info = HUNTER_MAP.get(platform, (GlintsHunter, "Glints Indonesia"))
    HunterClass, platform_name = hunter_info

    # Ekstrak teks CV untuk kalkulasi ATS Match Score
    cv_text = extract_text_from_pdf(CV_FILE_PATH) if os.path.exists(CV_FILE_PATH) else ""

    with playwright_lock:
        with sync_playwright() as p:
            context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 150))
            page = context.new_page()
            
            try:
                hunter = HunterClass(page, cfg)
                jobs = hunter.search_jobs()

                # Tambahkan skor ATS ke setiap pekerjaan
                for j in jobs:
                    j["ats"] = calculate_ats_match(cv_text, j["title"], j.get("company", ""))

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

                return jsonify({"success": True, "platform": platform, "jobs": jobs, "has_cv": bool(cv_text)})
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
    data = request.json or {}
    to_email = data.get("to_email")
    subject = data.get("subject")
    body = data.get("body")
    
    cfg = load_config()
    smtp_cfg = cfg.get("smtp", {})
    cv_path = smtp_cfg.get("cv_path", CV_FILE_PATH)

    result = send_cold_email(to_email, subject, body, attachment_path=cv_path, smtp_config=smtp_cfg)
    if result["success"]:
        record_job(f"mailto:{to_email}", subject, to_email, status="applied", notes="Cold Email Langsung")
    return jsonify(result)

@app.route("/api/scheduler", methods=["GET", "POST"])
def handle_scheduler():
    if request.method == "POST":
        data = request.json or {}
        action = data.get("action")
        if action == "start":
            scheduler.start(interval_minutes=int(data.get("interval", 120)))
        else:
            scheduler.stop()
    return jsonify(scheduler.get_status())

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

@app.route("/api/backup", methods=["GET"])
def download_backup():
    import json
    backup_data = {
        "config": load_config(),
        "history": load_history(),
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    backup_path = os.path.join(os.path.dirname(__file__), "data", "backup_loker_cli.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    return send_file(backup_path, mimetype="application/json", as_attachment=True, download_name="backup_loker_cli.json")

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
