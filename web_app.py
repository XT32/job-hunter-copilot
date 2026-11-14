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
from src.storage import load_history, record_job, export_history_to_csv
from src.config import load_config, save_config

app = Flask(__name__, template_folder="templates")

# Lock untuk sinkronisasi pemanggilan Playwright agar aman di web server
playwright_lock = threading.Lock()

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
    
    if "profile" in data:
        cfg["profile"] = data["profile"]
    if "min_delay_sec" in data:
        cfg["min_delay_sec"] = data["min_delay_sec"]
    if "max_delay_sec" in data:
        cfg["max_delay_sec"] = data["max_delay_sec"]
    if "auto_skip_already_seen" in data:
        cfg["auto_skip_already_seen"] = data["auto_skip_already_seen"]
        
    save_config(cfg)
    return jsonify({"success": True, "config": cfg})

@app.route("/api/scan", methods=["POST"])
def scan_jobs():
    data = request.json or {}
    platform = data.get("platform", "glints").lower()
    cfg = load_config()

    with playwright_lock:
        with sync_playwright() as p:
            # Buka browser untuk scan
            context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 150))
            page = context.new_page()
            
            try:
                if platform == "jobstreet":
                    hunter = JobstreetHunter(page, cfg)
                else:
                    hunter = GlintsHunter(page, cfg)

                jobs = hunter.search_jobs()
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

    with playwright_lock:
        with sync_playwright() as p:
            context = get_browser_context(p, headless=False, slow_mo=cfg.get("slow_mo_ms", 150))
            page = context.new_page()

            try:
                if platform == "jobstreet":
                    hunter = JobstreetHunter(page, cfg)
                else:
                    hunter = GlintsHunter(page, cfg)

                result = hunter.inspect_and_apply(job_url)

                if result["status"] == "success":
                    record_job(job_url, title, company, status="applied", notes=f"Web UI: {platform.title()}")
                elif result["status"] == "already_applied":
                    record_job(job_url, title, company, status="applied", notes=f"Sudah dilamar sebelumnya ({platform.title()})")
                elif result["status"] == "external_link":
                    record_job(job_url, title, company, status="skipped", notes=f"Tautan eksternal ({platform.title()})")

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

    print(f"\n[OK] loker-cli Web UI aktif di: http://127.0.0.1:{port}")
    print("[*] Tekan CTRL+C di terminal ini untuk mematikan server.\n")
    app.run(host="127.0.0.1", port=port, debug=False)

if __name__ == "__main__":
    start_server()
