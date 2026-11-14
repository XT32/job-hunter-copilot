import csv
import json
import os
import time

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history.json")
DEFAULT_CSV_EXPORT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "riwayat_lamaran.csv")

def _ensure_history_file():
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"applied": [], "skipped": []}, f, indent=2)

def load_history():
    _ensure_history_file()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"applied": [], "skipped": []}

def is_job_recorded(job_url):
    hist = load_history()
    applied_urls = {item["url"] for item in hist.get("applied", []) if "url" in item}
    skipped_urls = {item["url"] for item in hist.get("skipped", []) if "url" in item}
    return job_url in applied_urls or job_url in skipped_urls

def record_job(job_url, title, company, status="applied", notes=""):
    _ensure_history_file()
    hist = load_history()
    entry = {
        "url": job_url,
        "title": title,
        "company": company,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "notes": notes
    }
    
    category = "applied" if status == "applied" else "skipped"
    if category not in hist:
        hist[category] = []
        
    hist[category] = [item for item in hist[category] if item.get("url") != job_url]
    hist[category].append(entry)
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)

def export_history_to_csv(export_path=DEFAULT_CSV_EXPORT) -> str:
    """Mengekspor seluruh riwayat (dilamar dan dilewati) ke format CSV"""
    hist = load_history()
    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    with open(export_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Status", "Posisi", "Perusahaan", "Waktu", "Tautan Loker", "Catatan"])
        
        for item in hist.get("applied", []):
            writer.writerow([
                "Dilamar",
                item.get("title", ""),
                item.get("company", ""),
                item.get("timestamp", ""),
                item.get("url", ""),
                item.get("notes", "")
            ])

        for item in hist.get("skipped", []):
            writer.writerow([
                "Dilewati",
                item.get("title", ""),
                item.get("company", ""),
                item.get("timestamp", ""),
                item.get("url", ""),
                item.get("notes", "")
            ])

    return export_path
