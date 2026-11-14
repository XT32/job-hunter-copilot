import csv
import json
import os
import time

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history.json")
DEFAULT_CSV_EXPORT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "riwayat_lamaran.csv")

VALID_STATUSES = ["applied", "interview", "offering", "rejected", "skipped"]

def _ensure_history_file():
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump({s: [] for s in VALID_STATUSES}, f, indent=2)

def load_history():
    _ensure_history_file()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for s in VALID_STATUSES:
                if s not in data:
                    data[s] = []
            return data
    except Exception:
        return {s: [] for s in VALID_STATUSES}

def is_job_recorded(job_url):
    hist = load_history()
    for s in VALID_STATUSES:
        for item in hist.get(s, []):
            if item.get("url") == job_url:
                return True
    return False

def record_job(job_url, title, company, status="applied", notes=""):
    _ensure_history_file()
    hist = load_history()
    status = status if status in VALID_STATUSES else "applied"

    entry = {
        "url": job_url,
        "title": title,
        "company": company,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "notes": notes
    }

    # Hapus dari kategori mana pun jika sebelumnya ada (update)
    for s in VALID_STATUSES:
        hist[s] = [item for item in hist.get(s, []) if item.get("url") != job_url]

    hist[status].append(entry)

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)

def update_job_status(job_url, new_status, notes=None) -> bool:
    """Mengubah status lamaran dalam alur pipeline/kanban (misal: applied -> interview)"""
    if new_status not in VALID_STATUSES:
        return False

    _ensure_history_file()
    hist = load_history()

    found_item = None
    for s in VALID_STATUSES:
        for item in hist.get(s, []):
            if item.get("url") == job_url:
                found_item = item.copy()
                break
        if found_item:
            hist[s] = [it for it in hist[s] if it.get("url") != job_url]
            break

    if not found_item:
        return False

    if notes is not None:
        found_item["notes"] = notes
    found_item["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    hist[new_status].append(found_item)

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)
    return True

def export_history_to_csv(export_path=DEFAULT_CSV_EXPORT) -> str:
    """Mengekspor seluruh riwayat (semua status pipeline) ke format CSV"""
    hist = load_history()
    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    status_labels = {
        "applied": "Terkirim",
        "interview": "Interview",
        "offering": "Offering/Diterima",
        "rejected": "Ditolak",
        "skipped": "Dilewati"
    }

    with open(export_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Status", "Posisi", "Perusahaan", "Waktu", "Tautan Loker", "Catatan"])

        for status_key, label in status_labels.items():
            for item in hist.get(status_key, []):
                writer.writerow([
                    label,
                    item.get("title", ""),
                    item.get("company", ""),
                    item.get("timestamp", ""),
                    item.get("url", ""),
                    item.get("notes", "")
                ])

    return export_path
