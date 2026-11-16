# Copyright (C) 2024-2026 XT32 <https://github.com/XT32/job-hunter-copilot>
#
# This file is part of Job Hunter Copilot.
#
# Job Hunter Copilot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Job Hunter Copilot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import io
import json
import os
import secrets
import sys
import threading
import time
import webbrowser
import zipfile
from urllib.parse import urlparse
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
from playwright.sync_api import sync_playwright

from src.browser import get_browser_context
from src.glints import GlintsHunter
from src.jobstreet import JobstreetHunter
from src.maganghub import MagangHubHunter
from src.dealls import DeallsHunter
from src.storage import (
    load_history,
    record_job,
    update_job_status,
    update_job_notes,
    delete_job,
    clear_jobs_by_status,
    export_history_to_csv,
    get_analytics_summary,
    verify_database_integrity,
    acknowledge_legacy_hashes,
    set_interview_schedule,
    generate_interview_ics,
)
from src.local_db import get_default_db, TamperDetectedError
from src.config import load_config, save_config, DEFAULT_CONFIG
from src.accounts import (
    list_accounts,
    create_account,
    switch_account,
    update_account,
    delete_account,
    get_active_account,
)
from src.cover_letter import generate_cover_letter
from src.email_sender import send_cold_email
from src.notifier import (
    send_telegram_alert,
    test_telegram_connection,
    send_telegram_interview_alert,
    send_telegram_job_alert,
)
from src.cv_analyzer import extract_text_from_pdf, calculate_ats_match
from src.scheduler import AutoHuntScheduler
from src.scam_detector import check_for_red_flags
from src.salary_guide import suggest_salary_range
from src.updater import check_for_updates, apply_update, get_local_version_info
from src.rate_limiter import get_limiter
from src.diagnostic import check_system_health, generate_debug_bundle

app = Flask(__name__, template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # Maksimal 10 MB untuk upload CV
playwright_lock = threading.Lock()

SERVER_CSRF_TOKEN = secrets.token_hex(24)


@app.before_request
def csrf_and_origin_protect():
    """
    Melindungi dashboard UI-first dari serangan Cross-Site Request Forgery (CSRF)
    dan eksekusi permintaan lintas domain berbahaya, sambil tetap mendukung
    reverse proxy lokal (.local, .test, .lan, atau domain lokal kustom).
    """
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        # 1. Periksa header Origin / Referer jika ada
        origin = request.headers.get("Origin") or request.headers.get("Referer")
        if origin:
            try:
                parsed = urlparse(origin)
                current_host = (request.host or "").split(":")[0].lower()
                origin_host = (parsed.hostname or "").lower()
                allowed_hosts = {"127.0.0.1", "localhost", "0.0.0.0"}
                if current_host:
                    allowed_hosts.add(current_host)

                is_allowed = (
                    origin_host in allowed_hosts
                    or origin_host.endswith(".local")
                    or origin_host.endswith(".test")
                    or origin_host.endswith(".lan")
                    or origin_host.startswith("192.168.")
                    or origin_host.startswith("10.")
                    or (origin_host.startswith("172.") and any(origin_host.startswith(f"172.{i}.") for i in range(16, 32)))
                )
                if not is_allowed:
                    return jsonify({"success": False, "error": "Akses ditolak: Permintaan lintas domain dilarang."}), 403
            except Exception:
                return jsonify({"success": False, "error": "Origin header tidak valid."}), 403

        # 2. Periksa header X-CSRF-Token
        token = request.headers.get("X-CSRF-Token")
        if not token or not secrets.compare_digest(token, SERVER_CSRF_TOKEN):
            return jsonify({"success": False, "error": "Token keamanan CSRF tidak valid atau sesi kadaluarsa."}), 403


@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"success": False, "error": "Ukuran file terlalu besar! Maksimal 10 MB."}), 413


@app.errorhandler(TamperDetectedError)
def handle_tamper_error(error):
    add_log(f"PERINGATAN KEAMANAN: {error.reason}", "danger")
    return jsonify({
        "success": False,
        "tamper_alert": True,
        "error": error.reason,
        "security_status": error.details or verify_database_integrity(),
    }), 423


UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "attachments")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-Memory Ring Buffer untuk Live Activity Log (100 log terakhir)
MAX_LOGS = 100
system_logs = []
logs_lock = threading.Lock()


def add_log(message: str, level: str = "info"):
    with logs_lock:
        system_logs.append({
            "time": time.strftime("%H:%M:%S"),
            "message": message,
            "level": level,
        })
        if len(system_logs) > MAX_LOGS:
            system_logs.pop(0)


HUNTER_MAP = {
    "glints": (GlintsHunter, "Glints Indonesia"),
    "jobstreet": (JobstreetHunter, "JobStreet Indonesia"),
    "maganghub": (MagangHubHunter, "MagangHub Kemnaker"),
    "dealls": (DeallsHunter, "Dealls Jobs"),
}

LOGIN_PORTAL_URLS = {
    "jobstreet": "https://id.jobstreet.com/id",
    "glints": "https://glints.com/id",
    "maganghub": "https://maganghub.kemnaker.go.id",
    "dealls": "https://dealls.com",
}

scheduler = AutoHuntScheduler(
    HUNTER_MAP,
    load_config,
    log_callback=add_log,
    playwright_lock=playwright_lock,
)


class InteractiveBrowserSession:
    """
    Menjaga browser Playwright tetap terbuka di thread miliknya sendiri ketika user
    perlu login manual atau menyelesaikan tahap wizard lamaran di layar browser.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._active = False
        self._close_event = None
        self._done_event = None
        self._meta = {}
        self._thread = None

    def is_active(self) -> bool:
        with self._lock:
            return self._active

    def get_status(self) -> dict:
        with self._lock:
            return {
                "active": self._active,
                "meta": dict(self._meta) if self._active else {},
            }

    def close(self) -> bool:
        with self._lock:
            if not self._active:
                return False
            close_ev = self._close_event
            done_ev = self._done_event
        if close_ev:
            close_ev.set()
        if done_ev:
            done_ev.wait(timeout=8)
        return True

    def run_apply_with_handoff(self, platform: str, job_url: str, title: str, company: str, cfg: dict) -> dict:
        if self.is_active():
            self.close()

        result_holder = {}
        ready_event = threading.Event()
        close_event = threading.Event()
        done_event = threading.Event()

        HunterClass, platform_name = HUNTER_MAP.get(platform, (GlintsHunter, "Glints Indonesia"))

        def worker():
            try:
                with playwright_lock:
                    with sync_playwright() as p:
                        context = get_browser_context(
                            p,
                            headless=False,
                            slow_mo=cfg.get("slow_mo_ms", 150),
                            account_id=cfg.get("active_account_id", "default"),
                        )
                        page = context.new_page()
                        try:
                            hunter = HunterClass(page, cfg)
                            res = hunter.inspect_and_apply(job_url, job_title=title, company=company)

                            result_holder["result"] = res
                            keep_open = res.get("status") in ("manual_action_needed", "login_required")

                            if keep_open:
                                with self._lock:
                                    self._active = True
                                    self._close_event = close_event
                                    self._done_event = done_event
                                    self._meta = {
                                        "mode": "apply_handoff",
                                        "platform": platform,
                                        "platform_name": platform_name,
                                        "url": job_url,
                                        "title": title,
                                        "company": company,
                                        "status": res.get("status"),
                                    }
                                ready_event.set()
                                # Tahan browser tetap terbuka sampai user selesai atau menutupnya dari UI
                                while not close_event.is_set():
                                    try:
                                        if len(context.pages) == 0:
                                            break
                                    except Exception:
                                        break
                                    close_event.wait(timeout=0.5)
                            else:
                                ready_event.set()
                        except Exception as e:
                            result_holder["error"] = str(e)
                            ready_event.set()
                        finally:
                            try:
                                context.close()
                            except Exception:
                                pass
            except Exception as e:
                result_holder["error"] = str(e)
                ready_event.set()
            finally:
                with self._lock:
                    self._active = False
                    self._close_event = None
                    self._done_event = None
                    self._meta = {}
                done_event.set()

        t = threading.Thread(target=worker, daemon=True)
        self._thread = t
        t.start()
        ready_event.wait(timeout=90)

        if "error" in result_holder:
            raise RuntimeError(result_holder["error"])
        return result_holder.get("result", {"status": "error", "message": "Timeout saat membuka proses lamaran."})

    def open_interactive_url(self, url: str, label: str, cfg: dict, mode: str = "login") -> dict:
        if self.is_active():
            self.close()

        ready_event = threading.Event()
        close_event = threading.Event()
        done_event = threading.Event()
        error_holder = {}

        def worker():
            try:
                with playwright_lock:
                    with sync_playwright() as p:
                        context = get_browser_context(
                            p,
                            headless=False,
                            slow_mo=cfg.get("slow_mo_ms", 150),
                            account_id=cfg.get("active_account_id", "default"),
                        )
                        page = context.new_page()
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        except Exception as e:
                            error_holder["error"] = str(e)
                        with self._lock:
                            self._active = True
                            self._close_event = close_event
                            self._done_event = done_event
                            self._meta = {
                                "mode": mode,
                                "label": label,
                                "url": url,
                            }
                        ready_event.set()
                        while not close_event.is_set():
                            try:
                                if len(context.pages) == 0:
                                    break
                            except Exception:
                                break
                            close_event.wait(timeout=0.5)
                        try:
                            context.close()
                        except Exception:
                            pass
            except Exception as e:
                error_holder["error"] = str(e)
                ready_event.set()
            finally:
                with self._lock:
                    self._active = False
                    self._close_event = None
                    self._done_event = None
                    self._meta = {}
                done_event.set()

        t = threading.Thread(target=worker, daemon=True)
        self._thread = t
        t.start()
        ready_event.wait(timeout=35)
        if "error" in error_holder:
            return {"success": False, "error": error_holder["error"]}
        return {"success": True, "browser": self.get_status()}


browser_session = InteractiveBrowserSession()


TAB_ROUTES = {
    "": "huntTab",
    "loker": "huntTab",
    "hunt": "huntTab",
    "cv": "cvTab",
    "kanban": "kanbanTab",
    "lamaran": "kanbanTab",
    "email": "emailTab",
    "profil": "profileTab",
    "pengaturan": "profileTab",
    "settings": "profileTab",
}


@app.route("/")
@app.route("/loker")
@app.route("/hunt")
@app.route("/cv")
@app.route("/kanban")
@app.route("/lamaran")
@app.route("/email")
@app.route("/profil")
@app.route("/pengaturan")
@app.route("/settings")
def index():
    segment = request.path.strip("/").lower()
    initial_tab = TAB_ROUTES.get(segment, "huntTab")
    return render_template(
        "index.html",
        csrf_token=SERVER_CSRF_TOKEN,
        initial_tab=initial_tab,
    )


@app.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    return jsonify({"csrf_token": SERVER_CSRF_TOKEN})


# ================= DATABASE SECURITY & TAMPER ENDPOINTS =================
@app.route("/api/security/status", methods=["GET"])
def security_status():
    status = verify_database_integrity()
    if status.get("tampered"):
        add_log("Pemberitahuan: Terdeteksi perubahan data yang tidak sesuai. Silakan pulihkan salinan terakhir.", "danger")
    elif status.get("legacy_file_warning"):
        add_log("Pemberitahuan: Pengaturan disesuaikan ke format terbaru.", "warning")
    return jsonify({"success": True, "security": status})


@app.route("/api/security/restore", methods=["POST"])
def security_restore():
    res = get_default_db().restore_from_snapshot()
    if res.get("success"):
        acknowledge_legacy_hashes()
        add_log("Data berhasil dipulihkan dari salinan aman terakhir.", "success")
    else:
        add_log("Gagal memulihkan data: " + str(res.get("message", "Terjadi kendala")), "danger")
    return jsonify({**res, "security": verify_database_integrity()})


@app.route("/api/security/reset", methods=["POST"])
def security_reset():
    res = get_default_db().reset_database_via_ui(DEFAULT_CONFIG)
    acknowledge_legacy_hashes()
    add_log("Pengaturan berhasil dikembalikan ke nilai awal.", "info")
    return jsonify({**res, "security": verify_database_integrity()})


@app.route("/api/security/ack-legacy", methods=["POST"])
def security_ack_legacy():
    acknowledge_legacy_hashes()
    add_log("Pemberitahuan pembaruan telah dikonfirmasi.", "info")
    return jsonify({"success": True, "security": verify_database_integrity()})


# ================= CONFIG ENDPOINTS (UI-ONLY DB) =================
@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def update_config():
    data = request.json or {}
    cfg = load_config()

    for key in ["profile", "screening_defaults", "smtp", "telegram", "active_cv", "min_delay_sec", "max_delay_sec", "auto_skip_already_seen", "browser_headless"]:
        if key in data:
            if isinstance(data[key], dict) and isinstance(cfg.get(key), dict):
                cfg[key].update(data[key])
            else:
                cfg[key] = data[key]

    save_config(cfg, source="ui")
    add_log("Pengaturan profil & kriteria loker diperbarui di database lokal via UI.", "info")
    return jsonify({"success": True, "config": cfg})


# ================= MULTI-ACCOUNT ENDPOINTS =================
@app.route("/api/accounts", methods=["GET"])
def api_list_accounts():
    cfg = load_config()
    return jsonify({
        "success": True,
        "active_account_id": cfg.get("active_account_id", "default"),
        "accounts": list_accounts(cfg),
    })


@app.route("/api/accounts/switch", methods=["POST"])
def api_switch_account():
    data = request.json or {}
    target_id = data.get("account_id")
    if not target_id:
        return jsonify({"success": False, "error": "ID akun wajib disertakan"}), 400

    cfg = load_config()
    if browser_session.is_active():
        browser_session.close()
        add_log("Sesi jendela browser ditutup otomatis karena Anda beralih akun.", "info")

    try:
        target_acc, cfg = switch_account(cfg, target_id)
        save_config(cfg, source="ui")
        add_log(f"Beralih ke profil akun '{target_acc.get('name')}'.", "success")
        return jsonify({
            "success": True,
            "active_account_id": target_id,
            "account": target_acc,
            "accounts": list_accounts(cfg),
            "config": cfg,
            "message": f"Berhasil beralih ke {target_acc.get('name')}",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/accounts/create", methods=["POST"])
def api_create_account():
    data = request.json or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "error": "Nama akun tidak boleh kosong"}), 400

    clone_current = bool(data.get("clone_current", False))
    switch_now = bool(data.get("switch_now", True))
    field_or_major = data.get("field_or_major")
    target_keywords = data.get("target_keywords")
    experience_level = data.get("experience_level")
    active_cv = data.get("active_cv")

    cfg = load_config()
    try:
        new_acc, cfg = create_account(
            cfg,
            name=name,
            clone_current=clone_current,
            field_or_major=field_or_major,
            target_keywords=target_keywords,
            experience_level=experience_level,
            active_cv=active_cv,
        )
        if switch_now:
            if browser_session.is_active():
                browser_session.close()
            new_acc, cfg = switch_account(cfg, new_acc["id"])

        save_config(cfg, source="ui")
        add_log(f"Akun baru '{name}' berhasil dibuat{' dan diaktifkan' if switch_now else ''}.", "success")
        return jsonify({
            "success": True,
            "account": new_acc,
            "active_account_id": cfg.get("active_account_id"),
            "accounts": list_accounts(cfg),
            "config": cfg,
            "message": f"Akun '{name}' berhasil dibuat!",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/accounts/update", methods=["POST"])
def api_update_account():
    data = request.json or {}
    account_id = data.get("account_id")
    updates = data.get("updates", {})
    if not account_id:
        return jsonify({"success": False, "error": "ID akun wajib disertakan"}), 400

    cfg = load_config()
    try:
        updated_acc, cfg = update_account(cfg, account_id, updates)
        save_config(cfg, source="ui")
        add_log(f"Data akun '{updated_acc.get('name')}' berhasil diperbarui.", "info")
        return jsonify({
            "success": True,
            "account": updated_acc,
            "accounts": list_accounts(cfg),
            "config": cfg,
            "message": f"Akun '{updated_acc.get('name')}' berhasil diperbarui.",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/accounts/delete", methods=["POST"])
def api_delete_account():
    data = request.json or {}
    account_id = data.get("account_id")
    if not account_id:
        return jsonify({"success": False, "error": "ID akun wajib disertakan"}), 400

    cfg = load_config()
    if browser_session.is_active():
        browser_session.close()

    try:
        deleted, cfg = delete_account(cfg, account_id)
        save_config(cfg, source="ui")
        add_log(f"Akun '{deleted.get('name')}' berhasil dihapus.", "info")
        return jsonify({
            "success": True,
            "deleted": deleted,
            "active_account_id": cfg.get("active_account_id"),
            "accounts": list_accounts(cfg),
            "config": cfg,
            "message": f"Akun '{deleted.get('name')}' berhasil dihapus.",
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/test-telegram", methods=["POST"])
def test_telegram_route():
    data = request.json or {}
    token = (data.get("bot_token") or "").strip()
    chat_id = str(data.get("chat_id") or "").strip()

    if not token or not chat_id:
        cfg = load_config()
        tg = cfg.get("telegram", {})
        token = token or tg.get("bot_token", "")
        chat_id = chat_id or tg.get("chat_id", "")

    result = test_telegram_connection(bot_token=token, chat_id=chat_id)
    if result.get("success"):
        add_log("Tes notifikasi bot Telegram berhasil terkirim.", "success")
    else:
        add_log(f"Tes notifikasi bot Telegram gagal: {result.get('message')}", "warning")
    return jsonify(result)


@app.route("/api/telegram/share-job", methods=["POST"])
def share_job_telegram():
    data = request.json or {}
    title = data.get("title", "Posisi")
    company = data.get("company", "Perusahaan")
    url = data.get("url", "")
    platform = data.get("platform", "Web")
    salary = data.get("salary", "Tidak dicantumkan")
    ats_score = data.get("ats_score")

    cfg = load_config()
    tg_cfg = cfg.get("telegram", {})
    bot_token = tg_cfg.get("bot_token", "")
    chat_id = tg_cfg.get("chat_id", "")

    if not tg_cfg.get("enabled", False) or not bot_token or not chat_id:
        return jsonify({
            "success": False,
            "message": "Fitur bot Telegram belum aktif. Silakan isi Bot Token & Chat ID di menu Profil & Pengaturan."
        })

    success = send_telegram_job_alert(
        title=title,
        company=company,
        url=url,
        platform=platform,
        salary=salary,
        ats_score=ats_score,
        bot_token=bot_token,
        chat_id=chat_id,
    )
    if success:
        add_log(f"Lowongan '{title}' di '{company}' berhasil dibagikan ke Telegram.", "success")
        return jsonify({"success": True, "message": "Lowongan berhasil dikirim ke bot Telegram kamu!"})
    else:
        add_log(f"Gagal mengirim lowongan '{title}' ke Telegram. Periksa token/koneksi.", "warning")
        return jsonify({"success": False, "message": "Gagal mengirim ke Telegram. Periksa token bot atau koneksi internet."})



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
                    "active": (f == active_cv),
                })

    cv_files.sort(key=lambda x: x["filename"])
    return jsonify({"cvs": cv_files, "active_cv": active_cv})


@app.route("/api/upload-cv", methods=["POST"])
def upload_cv():
    """Menerima unggahan file PDF CV pengguna dan menetapkannya sebagai CV aktif."""
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

    cfg = load_config()
    cfg["active_cv"] = raw_filename
    if "smtp" not in cfg:
        cfg["smtp"] = {}
    cfg["smtp"]["cv_path"] = target_path
    save_config(cfg, source="ui")

    add_log(f"CV '{raw_filename}' berhasil diunggah ({len(text)} karakter terbaca).", "success")

    return jsonify({
        "success": True,
        "filename": raw_filename,
        "message": f"File CV '{raw_filename}' berhasil disimpan sebagai CV aktif!",
        "has_text": len(text) > 20,
        "char_count": len(text),
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
    save_config(cfg, source="ui")

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
            save_config(cfg, source="ui")
        add_log(f"File CV '{safe_name}' dihapus.", "info")
        return jsonify({"success": True})
    except TamperDetectedError:
        raise
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ================= INTERACTIVE BROWSER CONTROL =================
@app.route("/api/browser/status", methods=["GET"])
def browser_status():
    return jsonify({"success": True, "browser": browser_session.get_status()})


@app.route("/api/browser/login", methods=["POST"])
def open_portal_login():
    data = request.json or {}
    platform = data.get("platform", "jobstreet").lower()
    url = data.get("url") or LOGIN_PORTAL_URLS.get(platform, "https://id.jobstreet.com/id")
    label = data.get("label") or f"Login {platform.upper()}"
    cfg = load_config()

    add_log(f"Membuka jendela browser Copilot untuk {label} ({url})...", "info")
    res = browser_session.open_interactive_url(url, label=label, cfg=cfg, mode="login")
    return jsonify(res)


@app.route("/api/browser/close", methods=["POST"])
def close_interactive_browser():
    closed = browser_session.close()
    if closed:
        add_log("Jendela browser interaktif ditutup melalui dashboard.", "info")
    return jsonify({"success": True, "closed": closed})


@app.route("/api/browser/complete-apply", methods=["POST"])
def complete_manual_apply():
    data = request.json or {}
    job_url = data.get("url")
    title = data.get("title", "Posisi")
    company = data.get("company", "Perusahaan")
    platform = data.get("platform", "jobstreet").lower()
    _, platform_name = HUNTER_MAP.get(platform, (JobstreetHunter, "JobStreet Indonesia"))

    if job_url:
        record_job(job_url, title, company, status="applied", notes=f"Selesai via Browser Copilot ({platform_name})", source="ui")
        try:
            get_limiter().record_application(platform)
        except Exception:
            pass
        add_log(f"Lamaran '{title}' di {company} dikonfirmasi terkirim & dicatat ke Kanban.", "success")

    browser_session.close()
    return jsonify({"success": True})


# ================= LIVE LOGS & SCANNING =================
@app.route("/api/logs", methods=["GET"])
def get_logs():
    with logs_lock:
        return jsonify(list(system_logs))


@app.route("/api/scan", methods=["POST"])
def scan_jobs():
    data = request.json or {}
    platform = data.get("platform", "glints").lower()
    override_keywords = data.get("keywords")
    cfg = load_config()

    if browser_session.is_active():
        add_log("Menutup sesi browser interaktif sebelumnya sebelum memindai...", "info")
        browser_session.close()

    hunter_info = HUNTER_MAP.get(platform, (GlintsHunter, "Glints Indonesia"))
    HunterClass, platform_name = hunter_info

    active_cv = cfg.get("active_cv", "CV.pdf")
    active_cv_path = os.path.join(UPLOAD_FOLDER, active_cv) if active_cv else ""
    cv_text = extract_text_from_pdf(active_cv_path) if active_cv_path and os.path.exists(active_cv_path) else ""

    # Jika user mengetik kata kunci langsung di bar Scan, gunakan itu sementara untuk filter juga
    scan_cfg = json.loads(json.dumps(cfg))
    if override_keywords:
        kw_list = [k.strip() for k in str(override_keywords).split(",") if k.strip()]
        if kw_list:
            scan_cfg["profile"]["target_keywords"] = kw_list

    is_headless = bool(scan_cfg.get("browser_headless", False))
    browser_mode_txt = "latar belakang (headless)" if is_headless else "jendela visual"
    add_log(f"Menyiapkan browser [{browser_mode_txt}] untuk pemindaian di {platform_name}...", "info")

    with playwright_lock:
        with sync_playwright() as p:
            context = get_browser_context(
                p,
                headless=is_headless,
                slow_mo=scan_cfg.get("slow_mo_ms", 150),
                account_id=scan_cfg.get("active_account_id", "default"),
            )
            page = context.new_page()

            try:
                add_log(f"Membuka portal {platform_name} dan mencari lowongan sesuai profil...", "info")
                hunter = HunterClass(page, scan_cfg)
                jobs = hunter.search_jobs(keywords=scan_cfg["profile"].get("target_keywords"))

                add_log(f"Ditemukan {len(jobs)} lowongan cocok di {platform_name}. Menjalankan evaluasi ATS & deteksi penipuan...", "info")

                for j in jobs:
                    j["ats"] = calculate_ats_match(cv_text, j["title"], j.get("company", ""))
                    j["red_flag"] = check_for_red_flags(
                        title=j["title"],
                        company=j["company"],
                        description=j.get("description", ""),
                        location=j.get("location", ""),
                    )

                tg_cfg = scan_cfg.get("telegram", {})
                if tg_cfg.get("enabled", False) and jobs:
                    for j in jobs[:3]:
                        send_telegram_alert(
                            title=j["title"],
                            company=j["company"],
                            url=j["url"],
                            platform=platform_name,
                            salary=j.get("salary", "Tidak dicantumkan"),
                            bot_token=tg_cfg.get("bot_token", ""),
                            chat_id=tg_cfg.get("chat_id", ""),
                        )

                add_log(f"Pemindaian {platform_name} selesai. Menampilkan {len(jobs)} hasil.", "success")
                return jsonify({"success": True, "platform": platform, "jobs": jobs, "has_cv": bool(cv_text), "active_cv": active_cv})
            except TamperDetectedError:
                raise
            except Exception as e:
                add_log(f"Gagal saat memindai {platform_name}: {str(e)}", "danger")
                return jsonify({"success": False, "error": str(e)}), 500
            finally:
                try:
                    context.close()
                except Exception:
                    pass


@app.route("/api/apply", methods=["POST"])
def apply_job():
    data = request.json or {}
    platform = data.get("platform", "glints").lower()
    job_url = data.get("url")
    title = data.get("title", "Posisi")
    company = data.get("company", "Perusahaan")

    if not job_url:
        return jsonify({"success": False, "error": "URL lowongan wajib disertakan"}), 400

    # Lindungi akun dari shadowban/blokir via safe rate limiter
    limiter = get_limiter()
    allowed, quota_reason, quota_stats = limiter.check_quota(platform)
    if not allowed:
        add_log(f"BATAS AMAN KUOTA TERCAPAI: {quota_reason}", "warning")
        return jsonify({
            "success": False,
            "rate_limited": True,
            "error": quota_reason,
            "quota_stats": quota_stats,
        }), 429

    cfg = load_config()
    _, platform_name = HUNTER_MAP.get(platform, (GlintsHunter, "Glints Indonesia"))

    add_log(f"Membuka proses melamar untuk '{title}' di {company} ({platform_name})...", "info")

    try:
        active_acc = get_active_account(cfg)
        acc_tag = f" [Akun: {active_acc.get('name', 'Akun Utama')}]"
        result = browser_session.run_apply_with_handoff(platform, job_url, title, company, cfg)

        if result.get("status") == "success":
            record_job(job_url, title, company, status="applied", notes=f"Lamar via {platform_name}{acc_tag}", source="ui")
            limiter.record_application(platform)
            add_log(f"Lamaran '{title}' di {company} berhasil terkirim!", "success")
        elif result.get("status") == "already_applied":
            record_job(job_url, title, company, status="applied", notes=f"Sudah dilamar sebelumnya ({platform_name}){acc_tag}", source="ui")
            add_log(f"Lowongan '{title}' di {company} ternyata sudah pernah dilamar.", "warning")
        elif result.get("status") == "external_link":
            record_job(job_url, title, company, status="skipped", notes=f"Tautan eksternal ({platform_name}){acc_tag}", source="ui")
            add_log(f"Lowongan '{title}' di {company} dialihkan ke web karir eksternal.", "info")
        elif result.get("status") in ("manual_action_needed", "login_required"):
            add_log(f"Browser dibiarkan terbuka untuk '{title}': {result.get('message')}", "warning")

        return jsonify({
            "success": True,
            "result": result,
            "browser": browser_session.get_status(),
            "unanswered_questions": result.get("unanswered_questions", []),
            "screenshot": result.get("screenshot"),
            "quota_stats": limiter.check_quota(platform)[2],
        })
    except TamperDetectedError:
        raise
    except Exception as e:
        add_log(f"Kendala melamar '{title}': {str(e)}", "danger")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/skip", methods=["POST"])
def skip_job():
    data = request.json or {}
    job_url = data.get("url")
    title = data.get("title", "Posisi")
    company = data.get("company", "Perusahaan")
    notes = data.get("notes", "Dilewati via Web UI")

    if not job_url:
        return jsonify({"success": False, "error": "URL wajib diisi"}), 400

    record_job(job_url, title, company, status="skipped", notes=notes, source="ui")
    add_log(f"Lowongan '{title}' di {company} dilewati.", "info")
    return jsonify({"success": True})


@app.route("/api/record-manual", methods=["POST"])
def record_manual():
    data = request.json or {}
    job_url = data.get("url")
    title = data.get("title", "Lamaran Manual")
    company = data.get("company", "Perusahaan")
    status = data.get("status", "applied")
    notes = data.get("notes", "Dicatat lewat Web UI")

    if not job_url:
        return jsonify({"success": False, "error": "URL wajib diisi"}), 400

    record_job(job_url, title, company, status=status, notes=notes, source="ui")
    add_log(f"Lamaran '{title}' di {company} dicatat ke Kanban ({status}).", "success")
    return jsonify({"success": True})


@app.route("/api/status-update", methods=["POST"])
def update_status():
    data = request.json or {}
    job_url = data.get("url")
    new_status = data.get("status")
    notes = data.get("notes")

    if not job_url or not new_status:
        return jsonify({"success": False, "error": "URL dan status baru diperlukan"}), 400

    success = update_job_status(job_url, new_status, notes, source="ui")
    if success:
        add_log(f"Status lamaran diperbarui ke '{new_status}'.", "info")
    return jsonify({"success": success})


@app.route("/api/job/update-notes", methods=["POST"])
def api_update_job_notes():
    data = request.json or {}
    job_url = data.get("url")
    notes = data.get("notes", "")

    if not job_url:
        return jsonify({"success": False, "error": "URL lowongan wajib disertakan"}), 400

    success = update_job_notes(job_url, notes=notes, source="ui")
    if success:
        add_log("Catatan perkembangan lamaran diperbarui.", "info")
    return jsonify({"success": success})


@app.route("/api/job/delete", methods=["POST"])
def api_delete_job():
    data = request.json or {}
    job_url = data.get("url")

    if not job_url:
        return jsonify({"success": False, "error": "URL lowongan wajib disertakan"}), 400

    success = delete_job(job_url, source="ui")
    if success:
        add_log("Lamaran berhasil dihapus dari papan riwayat.", "info")
    return jsonify({"success": success})


@app.route("/api/job/clear-rejected", methods=["POST"])
def api_clear_rejected():
    count = clear_jobs_by_status("rejected", source="ui")
    if count > 0:
        add_log(f"Berhasil membersihkan {count} lamaran dengan status 'Ditolak'.", "info")
    return jsonify({"success": True, "count": count})


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
        record_job(f"mailto:{to_email}", subject, to_email, status="applied", notes="Cold Email Langsung via SMTP", source="ui")
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
        download_name="riwayat_lamaran_kerja.csv",
    )


@app.route("/api/backup", methods=["GET"])
def download_backup():
    backup_data = {
        "config": load_config(),
        "history": load_history(),
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    backup_path = os.path.join(os.path.dirname(__file__), "data", "backup_loker_cli.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    add_log("Cadangan data JSON diunduh pengguna.", "info")
    return send_file(backup_path, mimetype="application/json", as_attachment=True, download_name="backup_loker_cli.json")


@app.route("/api/backup/restore", methods=["POST"])
def restore_backup():
    """Memulihkan konfigurasi dan riwayat lamaran dari berkas cadangan JSON."""
    data = None
    if "backup_file" in request.files:
        f = request.files["backup_file"]
        if not f.filename or not f.filename.lower().endswith(".json"):
            return jsonify({"success": False, "error": "Berkas cadangan harus berformat JSON (.json)"}), 400
        try:
            data = json.load(f.stream)
        except Exception as e:
            return jsonify({"success": False, "error": f"Berkas JSON tidak dapat dibaca: {str(e)}"}), 400
    elif request.is_json:
        data = request.json
    else:
        return jsonify({"success": False, "error": "Tidak ada berkas atau data cadangan yang dikirim."}), 400

    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Format berkas cadangan tidak valid."}), 400

    imported_cfg = False
    imported_jobs = 0

    # 1. Pulihkan Config jika tersedia
    if "config" in data and isinstance(data["config"], dict):
        cfg = load_config()
        for k in ["profile", "screening_defaults", "smtp", "telegram", "active_cv", "min_delay_sec", "max_delay_sec", "auto_skip_already_seen", "browser_headless"]:
            if k in data["config"]:
                if isinstance(data["config"][k], dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(data["config"][k])
                else:
                    cfg[k] = data["config"][k]
        save_config(cfg, source="ui")
        imported_cfg = True

    # 2. Pulihkan History jika tersedia
    if "history" in data and isinstance(data["history"], dict):
        for status, items in data["history"].items():
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and item.get("url"):
                    record_job(
                        job_url=item["url"],
                        title=item.get("title", "Posisi"),
                        company=item.get("company", "Perusahaan"),
                        status=status,
                        notes=item.get("notes", ""),
                        source="ui",
                    )
                    imported_jobs += 1

    add_log(f"Cadangan berhasil dipulihkan ({imported_jobs} riwayat lamaran diimpor).", "success")
    return jsonify({
        "success": True,
        "message": f"Cadangan berhasil dipulihkan! ({imported_jobs} riwayat lamaran diimpor)",
        "config_restored": imported_cfg,
        "jobs_restored": imported_jobs,
    })


# ================= RATE LIMITS & QUOTA =================
@app.route("/api/rate-limits", methods=["GET"])
def api_rate_limits():
    return jsonify({"success": True, "quotas": get_limiter().get_all_quotas()})


# ================= DIAGNOSTIC & DEBUG BUNDLE =================
@app.route("/api/diagnostic/health", methods=["GET"])
def api_diagnostic_health():
    res = check_system_health(config_loader=load_config, db_verifier=verify_database_integrity)
    return jsonify({"success": True, "health": res})


@app.route("/api/diagnostic/bundle", methods=["GET"])
def api_diagnostic_bundle():
    with logs_lock:
        recent_logs = list(system_logs)
    cfg = load_config()
    db_stat = verify_database_integrity()
    bundle_path = generate_debug_bundle(logs=recent_logs, cfg=cfg, db_status=db_stat)
    add_log("Berkas diagnosa (loker_debug_bundle.zip) dibuat dan siap diunduh.", "info")
    return send_file(
        bundle_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name="loker_debug_bundle.zip",
    )


# ================= SCREENSHOTS VIEWER =================
@app.route("/api/screenshots/<path:filename>", methods=["GET"])
def api_get_screenshot(filename):
    safe_name = os.path.basename(filename)
    screenshots_dir = os.path.join(os.path.dirname(__file__), "data", "screenshots")
    return send_from_directory(screenshots_dir, safe_name)


# ================= SCREENING Q&A BANK =================
@app.route("/api/qa", methods=["GET"])
def api_get_qa():
    cfg = load_config()
    qas = cfg.get("screening_defaults", {}).get("custom_qa", [])
    return jsonify({"success": True, "custom_qa": qas})


@app.route("/api/qa/save", methods=["POST"])
def api_save_qa():
    data = request.json or {}
    keyword = str(data.get("keyword", "")).strip()
    answer = str(data.get("answer", "")).strip()
    question = str(data.get("question", "")).strip()

    if not keyword or not answer:
        return jsonify({"success": False, "error": "Kata kunci (keyword) dan jawaban wajib diisi."}), 400

    cfg = load_config()
    if "screening_defaults" not in cfg:
        cfg["screening_defaults"] = {}
    if "custom_qa" not in cfg["screening_defaults"] or not isinstance(cfg["screening_defaults"]["custom_qa"], list):
        cfg["screening_defaults"]["custom_qa"] = []

    qas = cfg["screening_defaults"]["custom_qa"]
    updated = False
    for item in qas:
        if isinstance(item, dict) and item.get("keyword", "").lower() == keyword.lower():
            item["answer"] = answer
            if question:
                item["question"] = question
            updated = True
            break
    if not updated:
        entry = {"keyword": keyword, "answer": answer}
        if question:
            entry["question"] = question
        qas.append(entry)

    cfg["screening_defaults"]["custom_qa"] = qas
    save_config(cfg, source="ui")
    add_log(f"Jawaban untuk kata kunci '{keyword}' disimpan ke Bank Jawaban Otomatis.", "success")
    return jsonify({"success": True, "custom_qa": qas})


@app.route("/api/qa/delete", methods=["POST"])
def api_delete_qa():
    data = request.json or {}
    keyword = str(data.get("keyword", "")).strip().lower()
    cfg = load_config()
    qas = cfg.get("screening_defaults", {}).get("custom_qa", [])
    new_qas = [item for item in qas if isinstance(item, dict) and item.get("keyword", "").lower() != keyword]
    cfg["screening_defaults"]["custom_qa"] = new_qas
    save_config(cfg, source="ui")
    add_log(f"Kata kunci '{keyword}' dihapus dari Bank Jawaban.", "info")
    return jsonify({"success": True, "custom_qa": new_qas})


# ================= INTERVIEW SCHEDULING & ICALENDAR (.ICS) =================
@app.route("/api/job/set-interview", methods=["POST"])
def api_set_interview():
    data = request.json or {}
    job_url = data.get("url")
    interview_datetime = data.get("datetime", "")
    location = data.get("location", "")
    notes = data.get("notes", "")

    if not job_url:
        return jsonify({"success": False, "error": "URL lowongan wajib diisi."}), 400

    success = set_interview_schedule(job_url, interview_datetime, location=location, notes=notes, source="ui")
    if not success:
        title = data.get("title") or "Pekerjaan"
        company = data.get("company") or "Perusahaan"
        full_notes_list = []
        if interview_datetime:
            full_notes_list.append(f"[Jadwal: {interview_datetime.strip()}]")
        if location:
            full_notes_list.append(f"[Lokasi: {location.strip()}]")
        if notes:
            full_notes_list.append(notes.strip())
        record_job(job_url, title, company, status="interview", notes=" ".join(full_notes_list), source="ui")
        success = True

    if success:
        add_log("Jadwal interview dicatat & status dipindahkan ke tahap Interview.", "success")
        try:
            cfg = load_config()
            tg_cfg = cfg.get("telegram", {})
            if tg_cfg.get("enabled", False) and tg_cfg.get("bot_token") and tg_cfg.get("chat_id"):
                title = data.get("title") or "Pekerjaan"
                company = data.get("company") or "Perusahaan"
                send_telegram_interview_alert(
                    title=title,
                    company=company,
                    datetime_str=interview_datetime,
                    location=location,
                    notes=notes,
                    bot_token=tg_cfg.get("bot_token"),
                    chat_id=tg_cfg.get("chat_id"),
                )
        except Exception:
            pass
    return jsonify({"success": success})


@app.route("/api/job/export-ics", methods=["GET"])
def api_export_ics():
    job_url = request.args.get("url")
    ics_path = generate_interview_ics(job_url=job_url)
    add_log("Jadwal wawancara diekspor ke format kalender iCalendar (.ics).", "info")
    return send_file(
        ics_path,
        mimetype="text/calendar",
        as_attachment=True,
        download_name="jadwal_interview.ics",
    )


# ================= 1-CLICK APP UPDATE (GITHUB) =================
@app.route("/api/update/check", methods=["GET"])
def api_update_check():
    res = check_for_updates()
    return jsonify(res)


@app.route("/api/update/apply", methods=["POST"])
def api_update_apply():
    if browser_session.is_active():
        browser_session.close()
    add_log("Memeriksa dan mengunduh pembaruan aplikasi dari GitHub...", "info")
    res = apply_update()
    if res.get("success"):
        add_log(res.get("message", "Aplikasi berhasil diperbarui."), "success")
    else:
        add_log(f"Gagal update aplikasi: {res.get('error')}", "danger")
    return jsonify(res)


@app.route("/api/update/restart", methods=["POST"])
def api_update_restart():
    if browser_session.is_active():
        browser_session.close()
    add_log("Memuat ulang server aplikasi agar pembaruan aktif...", "info")

    def _restart_later():
        time.sleep(0.6)
        os.execv(sys.executable, [sys.executable] + sys.argv)

    threading.Thread(target=_restart_later, daemon=True).start()
    return jsonify({"success": True, "message": "Aplikasi sedang dimuat ulang..."})


# ================= LEGAL NOTICE & AGPL-3.0 SOURCE ACCESS =================
@app.route("/api/legal", methods=["GET"])
def api_get_legal_info():
    """Mengembalikan informasi hak cipta, lisensi AGPLv3, dan daftar dependensi pihak ketiga."""
    return jsonify({
        "success": True,
        "app_name": "Job Hunter Copilot",
        "version": "1.0.0",
        "copyright": "Copyright (C) 2024-2026 XT32. All rights reserved.",
        "author": "XT32",
        "license": "GNU Affero General Public License v3 (AGPL-3.0)",
        "license_url": "/api/legal/license",
        "source_repository": "https://github.com/XT32/job-hunter-copilot",
        "source_archive_url": "https://github.com/XT32/job-hunter-copilot/archive/refs/heads/main.zip",
        "source_download_url": "/api/legal/source",
        "network_copyleft_notice": (
            "Sesuai dengan ketentuan GNU AGPLv3 Seksi 13, seluruh pengguna yang berinteraksi dengan "
            "perangkat lunak ini melalui jaringan komputer berhak mendapatkan salinan lengkap dari kode sumber "
            "versi ini tanpa dipungut biaya melalui tautan unduh atau repositori resmi."
        ),
        "warranty_disclaimer": (
            "This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; "
            "without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. "
            "See the GNU Affero General Public License for more details."
        ),
        "third_party_dependencies": [
            {
                "name": "Flask",
                "license": "BSD-3-Clause",
                "url": "https://palletsprojects.com/p/flask/",
                "compatibility": "Kompatibel AGPLv3 (Lisensi permisif BSD)"
            },
            {
                "name": "Playwright",
                "license": "Apache-2.0",
                "url": "https://playwright.dev/",
                "compatibility": "Kompatibel AGPLv3 (Lisensi permisif Apache 2.0)"
            },
            {
                "name": "pypdf",
                "license": "BSD-3-Clause",
                "url": "https://pypdf.readthedocs.io/",
                "compatibility": "Kompatibel AGPLv3 (Lisensi permisif BSD)"
            },
            {
                "name": "Rich",
                "license": "MIT",
                "url": "https://github.com/Textualize/rich",
                "compatibility": "Kompatibel AGPLv3 (Lisensi permisif MIT)"
            },
            {
                "name": "python-dotenv",
                "license": "BSD-3-Clause",
                "url": "https://github.com/theskumar/python-dotenv",
                "compatibility": "Kompatibel AGPLv3 (Lisensi permisif BSD)"
            },
            {
                "name": "cryptography (opsional)",
                "license": "Apache-2.0 / BSD-3-Clause",
                "url": "https://cryptography.io/",
                "compatibility": "Kompatibel AGPLv3 (Dual license permisif)"
            }
        ]
    })


@app.route("/api/legal/license", methods=["GET"])
def api_get_license():
    """Mengembalikan teks lisensi lengkap GNU AGPLv3."""
    license_path = os.path.join(os.path.dirname(__file__), "LICENSE")
    if os.path.exists(license_path):
        with open(license_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content, 200, {"Content-Type": "text/plain; charset=utf-8"}
    return "GNU Affero General Public License v3 (AGPL-3.0)\nhttps://www.gnu.org/licenses/agpl-3.0.txt", 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/api/legal/source", methods=["GET"])
def api_download_source():
    """
    Menyediakan arsip kode sumber lengkap aplikasi sesuai ketentuan GNU AGPLv3 Seksi 13.
    Mengecualikan data pribadi pengguna (.venv, data/, attachments/, log, dsb).
    """
    root_dir = os.path.dirname(__file__)
    buf = io.BytesIO()

    allowed_exts = {".py", ".html", ".js", ".css", ".md", ".txt", ".bat", ".sh", ".json", ".example"}
    allowed_dirs = {"src", "templates", "static", "tests"}
    include_files = {
        "web_app.py", "requirements.txt", "README.md", "LICENSE", "CONTRIBUTING.md",
        "start_windows.bat", "start_linux.sh", "start_web_windows.bat", "config.example.json"
    }

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in include_files:
            p = os.path.join(root_dir, f)
            if os.path.isfile(p):
                zf.write(p, arcname=f)

        for d in allowed_dirs:
            dp = os.path.join(root_dir, d)
            if os.path.isdir(dp):
                for dirpath, _, filenames in os.walk(dp):
                    if "__pycache__" in dirpath:
                        continue
                    for fn in filenames:
                        _, ext = os.path.splitext(fn)
                        if ext.lower() in allowed_exts:
                            fp = os.path.join(dirpath, fn)
                            arcname = os.path.relpath(fp, root_dir)
                            zf.write(fp, arcname=arcname)

    buf.seek(0)
    add_log("Arsip kode sumber lengkap AGPLv3 diunduh pengguna.", "info")
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name="job-hunter-copilot-source.zip",
    )


def start_server(port=5000, auto_open=True):
    port = int(os.environ.get("PORT", port))
    host = os.environ.get("HOST", "127.0.0.1")
    if os.environ.get("AUTO_OPEN", "").lower() in ("0", "false", "no"):
        auto_open = False

    # Inisialisasi database lokal saat mulai
    try:
        sec = verify_database_integrity()
        if sec.get("tampered"):
            add_log("Pemberitahuan: Terdeteksi perubahan data. Salinan cadangan siap dipulihkan.", "warning")
        elif sec.get("legacy_file_warning"):
            add_log("Pengaturan telah dimigrasikan dengan aman.", "info")
        else:
            add_log("Aplikasi siap digunakan.", "success")
    except Exception:
        add_log("Aplikasi siap digunakan.", "success")

    if auto_open:
        def open_browser():
            time.sleep(1.2)
            webbrowser.open(f"http://{host if host != '0.0.0.0' else '127.0.0.1'}:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    print(f"\n[OK] Job Hunter Copilot aktif di: http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    start_server()
