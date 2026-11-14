import json
import os
import time

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history.json")

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
        
    # Prevent duplicate records
    hist[category] = [item for item in hist[category] if item.get("url") != job_url]
    hist[category].append(entry)
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)
