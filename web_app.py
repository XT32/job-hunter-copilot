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
from src.storage import load_history, record_job, update_job_status, export_history_to_csv, get_analytics_summary, HISTORY_FILE
from src.config import load_config, save_config, DEFAULT_CONFIG_PATH
from src.cover_letter import generate_cover_letter
from src.email_sender import send_cold_email
from src.notifier import send_telegram_alert
from src.cv_analyzer import extract_text_from_pdf, calculate_ats_match
from src.scheduler import AutoHuntScheduler
from src.scam_detector import check_for_red_flags
from src.salary_guide import suggest_salary_range, get_umr_by_location, evaluate_candidate_salary

app = Flask(__name__, template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # Maksimal 10 MB untuk upload CV
playwright_lock = threading.Lock()

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"success": False, "error": "Ukuran file terlalu besar! Maksimal 10 MB."}), 413

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "attachments")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DEFAULT_CV_PATH = os.path.join(UPLOAD_FOLDER, "CV.pdf")

# In-Memory Ring Buffer untuk Live Activity Log (100 log terakhir)
MAX_LOGS = 100
system_logs = []
logs_lock = threading.Lock()

def add_log(message: str, level: str = "info"):
    with logs_lock:
        system_logs.append({
            "time": time.strftime("%H:%M:%S"),
            "message": message,
            "level": level
        })
        if len(system_logs) > MAX_LOGS:
            system_logs.pop(0)

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
    
    for key in ["profile", "screening_defaults", "smtp", "telegram", "active_cv", "min_delay_sec", "max_delay_sec", "auto_skip_already_seen"]:
        if key in data:
            cfg[key] = data[key]
        
    save_config(cfg)
    add_log("Pengaturan profil & kriteria loker diperbarui.", "info")
    return jsonify({"success": True, "config": cfg})

# ================= MULTI-CV ENDPOINTS =================
@app.route("/api/cvs", methods=["GET"])
def list_cvs():
    cfg = load_config()
    active_cv = cfg.get("active_cv", "CV.pdf")
    cv_files = []
    
    if os.path.exists(UPLOAD_FOLDER):
        for f in os.listdir(UPLOAD_FOLDER):
            if f.lower().endswith(".pdf") and not f.startswith("."):
                p = os.path.join(UPLOAD_FOLDER, f)
                cv_files.append({
                    "filename": f,
                    "size": os.path.getsize(p),
                    "active": (f == active_cv)
                })
    
    # Urutkan abjad
    cv_files.sort(key=lambda x: x["filename"])
    return jsonify({"cvs": cv_files, "active_cv": active_cv})

@app.route("/api/upload-cv", methods=["POST"])
def upload_cv():
    """Menerima unggahan file PDF CV pengguna dan menetapkannya sebagai CV aktif"""
    if "cv" not in request.files:
        return jsonify({"success": False, "error": "Tidak ada file yang diunggah"}), 400

    file = request.files["cv"]
    if file.filename == "" or not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "File harus berformat PDF"}), 400

    raw_filename = secure_filename(file.filename)
    if not raw_filename:
        raw_filename = f"CV_{int(time.time())}.pdf"

    target_path = os.path.join(UPLOAD_FOLDER, raw_filename)
    file.save(target_path)
    text = extract_text_from_pdf(target_path)

    # Tetapkan sebagai active_cv
    cfg = load_config()
    cfg["active_cv"] = raw_filename
    if "smtp" not in cfg:
        cfg["smtp"] = {}
    cfg["smtp"]["cv_path"] = target_path
    save_config(cfg)

    add_log(f"CV '{raw_filename}' berhasil diunggah ({len(text)} karakter terbaca).", "success")

    return jsonify({
        "success": True,
        "filename": raw_filename,
        "message": f"File CV '{raw_filename}' berhasil disimpan sebagai CV aktif!",
        "has_text": len(text) > 20,
        "char_count": len(text)
    })

@app.route("/api/set-active-cv", methods=["POST"])
def set_active_cv():
    data = request.json or {}
    filename = data.get("filename", "")
    safe_name = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_FOLDER, safe_name)

    if not safe_name or not os.path.exists(file_path):
        return jsonify({"success": False, "error": "File CV tidak ditemukan"}), 404

    cfg = load_config()
    cfg["active_cv"] = safe_name
    if "smtp" not in cfg:
        cfg["smtp"] = {}
    cfg["smtp"]["cv_path"] = file_path
    save_config(cfg)

    add_log(f"CV aktif dialihkan ke '{safe_name}'.", "info")
    return jsonify({"success": True, "active_cv": safe_name})

@app.route("/api/delete-cv", methods=["POST"])
def delete_cv():
    data = request.json or {}
    filename = data.get("filename", "")
    safe_name = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_FOLDER, safe_name)

    if not safe_name or not os.path.exists(file_path):
        return jsonify({"success": False, "error": "File tidak ditemukan"}), 404

    try:
        os.remove(file_path)
        cfg = load_config()
        if cfg.get("active_cv") == safe_name:
            remaining = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(".pdf")]
            cfg["active_cv"] = remaining[0] if remaining else ""
            save_config(cfg)
        add_log(f"File CV '{safe_name}' dihapus.", "info")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ================= LIVE LOGS & SCANNING =================
@app.route("/api/logs", methods=["GET"])
def get_logs():
    with logs_lock:
        return jsonify(list(system_logs))

@app.route("/api/scan", methods=["POST"])
def scan_jobs():
    data = request.json or {}
    platform = data.get("platform", "glints").lower()
    cfg = load_config()

    hunter_info = HUNTER_MAP.get(platform, (GlintsHunter, "Glints Indonesia"))
    HunterClass, platform_name = hunter_info

    # Tentukan file CV yang sedang aktif untuk ATS scoring
    active_cv = cfg.get("active_cv", "CV.pdf")
    active_cv_path = os.path.join(UPLOAD_FOLDER, active_cv)
    cv_text = extract_text_from_pdf(active_cv_path) if os.path.exists(active_cv_path) else ""

    add_log(f"Menyiapkan browser untuk pemindaian di {platform_name}...", "info")

    with playwright_lock:
        with sync_playwright() as p:
            context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 150))
            page = context.new_page()
            
            try:
                add_log(f"Membuka portal {platform_name} dan mencari lowongan sesuai profil...", "info")
                hunter = HunterClass(page, cfg)
                jobs = hunter.search_jobs()

                add_log(f"Ditemukan {len(jobs)} lowongan cocok di {platform_name}. Menjalankan evaluasi ATS & deteksi penipuan...", "info")

                # Tambahkan skor ATS dan Deteksi Zonk / Red Flag ke setiap pekerjaan
                for j in jobs:
                    j["ats"] = calculate_ats_match(cv_text, j["title"], j.get("company", ""))
                    j["red_flag"] = check_for_red_flags(
                        title=j["title"],
                        company=j["company"],
                        description=j.get("description", ""),
                        location=j.get("location", "")
                    )

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

                add_log(f"Pemindaian {platform_name} selesai. Menampilkan {len(jobs)} hasil.", "success")
                return jsonify({"success": True, "platform": platform, "jobs": jobs, "has_cv": bool(cv_text), "active_cv": active_cv})
            except Exception as e:
                add_log(f"Gagal saat memindai {platform_name}: {str(e)}", "danger")
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

    add_log(f"Membuka proses melamar untuk '{title}' di {company} ({platform_name})...", "info")

    with playwright_lock:
        with sync_playwright() as p:
            context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 150))
            page = context.new_page()

            try:
                hunter = HunterClass(page, cfg)
                result = hunter.inspect_and_apply(job_url)

                if result["status"] == "success":
                    record_job(job_url, title, company, status="applied", notes=f"Lamar via {platform_name}")
                    add_log(f"Lamaran '{title}' di {company} berhasil terkirim!", "success")
                elif result["status"] == "already_applied":
                    record_job(job_url, title, company, status="applied", notes=f"Sudah dilamar sebelumnya ({platform_name})")
                    add_log(f"Lowongan '{title}' di {company} ternyata sudah pernah dilamar.", "warning")
                elif result["status"] == "external_link":
                    record_job(job_url, title, company, status="skipped", notes=f"Tautan eksternal ({platform_name})")
                    add_log(f"Lowongan '{title}' di {company} dialihkan ke web karir eksternal.", "info")

                return jsonify({"success": True, "result": result})
            except Exception as e:
                add_log(f"Kendala melamar '{title}': {str(e)}", "danger")
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
    add_log(f"Lowongan '{title}' di {company} dilewati.", "info")
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
    if success:
        add_log(f"Status lamaran diperbarui ke '{new_status}'.", "info")
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
    active_cv = cfg.get("active_cv", "CV.pdf")
    cv_path = smtp_cfg.get("cv_path") or os.path.join(UPLOAD_FOLDER, active_cv)

    result = send_cold_email(to_email, subject, body, attachment_path=cv_path, smtp_config=smtp_cfg)
    if result["success"]:
        record_job(f"mailto:{to_email}", subject, to_email, status="applied", notes="Cold Email Langsung via SMTP")
        add_log(f"Cold email berhasil terkirim ke {to_email} via SMTP.", "success")
    else:
        add_log(f"Gagal mengirim email via SMTP ke {to_email}: {result.get('message')}", "danger")
    return jsonify(result)

# ================= SALARY GUIDE & ANALYTICS =================
@app.route("/api/salary-guide", methods=["GET"])
def salary_guide():
    location = request.args.get("location", "Jakarta")
    exp = request.args.get("exp", "fresh_graduate")
    guide = suggest_salary_range(location, exp)
    return jsonify(guide)

@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    stats = get_analytics_summary()
    return jsonify(stats)

@app.route("/api/scheduler", methods=["GET", "POST"])
def handle_scheduler():
    if request.method == "POST":
        data = request.json or {}
        action = data.get("action")
        if action == "start":
            scheduler.start(interval_minutes=int(data.get("interval", 120)))
            add_log("Background scheduler diaktifkan.", "info")
        else:
            scheduler.stop()
            add_log("Background scheduler dihentikan.", "info")
    return jsonify(scheduler.get_status())

@app.route("/api/history", methods=["GET"])
def get_history():
    return jsonify(load_history())

@app.route("/api/export", methods=["GET"])
def export_csv():
    csv_file = export_history_to_csv()
    add_log("Rekap riwayat diekspor ke format CSV.", "info")
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
    add_log("Cadangan data JSON diunduh pengguna.", "info")
    return send_file(backup_path, mimetype="application/json", as_attachment=True, download_name="backup_loker_cli.json")

def start_server(port=5000, auto_open=True):
    if auto_open:
        def open_browser():
            time.sleep(1.2)
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    add_log(f"Server dashboard aktif di port {port}.", "success")
    print(f"\n[OK] loker-cli Web Dashboard aktif di: http://127.0.0.1:{port}")
    print("[*] Menutup terminal ini akan menghentikan server web.\n")
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    start_server()
