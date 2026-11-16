import csv
import datetime
import hashlib
import json
import os
import re
import time
from src.local_db import LocalSecureDB, DEFAULT_DB_PATH, TamperDetectedError

DEFAULT_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "history.json")
HISTORY_FILE = DEFAULT_HISTORY_FILE
DEFAULT_CSV_EXPORT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "riwayat_lamaran.csv")

VALID_STATUSES = ["applied", "interview", "offering", "rejected", "skipped"]


def _get_db() -> LocalSecureDB:
    if HISTORY_FILE == DEFAULT_HISTORY_FILE:
        db = LocalSecureDB(DEFAULT_DB_PATH)
        db.ensure_initialized()
        _migrate_legacy_history_if_needed(db)
        return db
    db_path = os.path.splitext(HISTORY_FILE)[0] + ".db"
    db = LocalSecureDB(db_path)
    db.ensure_initialized()
    return db


def _migrate_legacy_history_if_needed(db: LocalSecureDB):
    """Migrasi satu kali dari data/history.json lama ke SQLite lokal terproteksi."""
    if not os.path.exists(DEFAULT_HISTORY_FILE):
        return
    try:
        current = db.load_history()
        total_items = sum(len(v) for v in current.values())
        if total_items > 0:
            return
        with open(DEFAULT_HISTORY_FILE, "r", encoding="utf-8") as f:
            legacy = json.load(f)
        for st in VALID_STATUSES:
            for item in legacy.get(st, []):
                if item.get("url"):
                    db.record_job(
                        item["url"],
                        item.get("title", ""),
                        item.get("company", ""),
                        status=st,
                        notes=item.get("notes", ""),
                        source="system_migration",
                    )
    except Exception:
        pass


def load_history():
    try:
        return _get_db().load_history()
    except TamperDetectedError:
        raise
    except Exception:
        return {s: [] for s in VALID_STATUSES}


def is_job_recorded(job_url):
    return _get_db().is_job_recorded(job_url)


def record_job(job_url, title, company, status="applied", notes="", source="ui"):
    _get_db().record_job(job_url, title, company, status=status, notes=notes, source=source)


def update_job_status(job_url, new_status, notes=None, source="ui") -> bool:
    """Mengubah status lamaran dalam alur pipeline/kanban (misal: applied -> interview)"""
    return _get_db().update_job_status(job_url, new_status, notes=notes, source=source)


def update_job_notes(job_url, notes="", source="ui") -> bool:
    """Memperbarui catatan lamaran (misal: link Zoom, nomor kontak HR) tanpa mengubah status."""
    return _get_db().update_job_notes(job_url, notes=notes, source=source)


def delete_job(job_url, source="ui") -> bool:
    """Menghapus lowongan kerja dari Kanban dan riwayat lokal."""
    return _get_db().delete_job(job_url, source=source)


def verify_database_integrity() -> dict:
    """Mengembalikan status keamanan & deteksi tamper database lokal."""
    db = _get_db()
    status = db.verify_integrity()

    # Cek jika ada percobaan ubah file legacy history.json / config.json secara langsung
    if HISTORY_FILE == DEFAULT_HISTORY_FILE:
        legacy_warnings = []
        root_dir = os.path.dirname(os.path.dirname(__file__))
        legacy_cfg = os.path.join(root_dir, "config.json")
        marker_path = os.path.join(os.path.dirname(DEFAULT_DB_PATH), ".legacy_hashes.json")
        current_hashes = {}
        for name, p in [("data/history.json", DEFAULT_HISTORY_FILE), ("config.json", legacy_cfg)]:
            if os.path.exists(p):
                h = hashlib.sha256(open(p, "rb").read()).hexdigest()
                current_hashes[name] = h

        if os.path.exists(marker_path):
            try:
                saved_hashes = json.load(open(marker_path, "r", encoding="utf-8"))
                for name, h in current_hashes.items():
                    if name in saved_hashes and saved_hashes[name] != h:
                        legacy_warnings.append(
                            f"File '{name}' terdeteksi diubah langsung di luar UI. Perubahan file langsung diabaikan demi keamanan."
                        )
            except Exception:
                pass
        else:
            try:
                os.makedirs(os.path.dirname(marker_path), exist_ok=True)
                with open(marker_path, "w", encoding="utf-8") as f:
                    json.dump(current_hashes, f, indent=2)
            except Exception:
                pass

        if legacy_warnings:
            status["legacy_file_warning"] = " ".join(legacy_warnings)
    return status


def acknowledge_legacy_hashes():
    """Memperbarui baseline hash file legacy via UI setelah peringatan ditinjau."""
    root_dir = os.path.dirname(os.path.dirname(__file__))
    legacy_cfg = os.path.join(root_dir, "config.json")
    marker_path = os.path.join(os.path.dirname(DEFAULT_DB_PATH), ".legacy_hashes.json")
    current_hashes = {}
    for name, p in [("data/history.json", DEFAULT_HISTORY_FILE), ("config.json", legacy_cfg)]:
        if os.path.exists(p):
            current_hashes[name] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    os.makedirs(os.path.dirname(marker_path), exist_ok=True)
    with open(marker_path, "w", encoding="utf-8") as f:
        json.dump(current_hashes, f, indent=2)


def export_history_to_csv(export_path=DEFAULT_CSV_EXPORT) -> str:
    """Mengekspor seluruh riwayat (semua status pipeline) ke format CSV"""
    hist = load_history()
    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    status_labels = {
        "applied": "Terkirim",
        "interview": "Interview",
        "offering": "Offering/Diterima",
        "rejected": "Ditolak",
        "skipped": "Dilewati",
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
                    item.get("notes", ""),
                ])

    return export_path


def get_analytics_summary(hist=None) -> dict:
    """Menghitung metrik performa pelamaran kerja dari riwayat pipeline"""
    if hist is None:
        hist = load_history()

    applied_count = len(hist.get("applied", []))
    interview_count = len(hist.get("interview", []))
    offering_count = len(hist.get("offering", []))
    rejected_count = len(hist.get("rejected", []))
    skipped_count = len(hist.get("skipped", []))

    total_submitted = applied_count + interview_count + offering_count + rejected_count
    response_rate = (
        round(((interview_count + offering_count) / total_submitted * 100), 1)
        if total_submitted > 0
        else 0.0
    )

    platforms = {"glints": 0, "jobstreet": 0, "maganghub": 0, "dealls": 0, "email": 0, "lainnya": 0}
    for s in ["applied", "interview", "offering", "rejected"]:
        for item in hist.get(s, []):
            url = item.get("url", "").lower()
            if "glints.com" in url:
                platforms["glints"] += 1
            elif "jobstreet" in url:
                platforms["jobstreet"] += 1
            elif "maganghub" in url or "kemnaker" in url:
                platforms["maganghub"] += 1
            elif "dealls.com" in url:
                platforms["dealls"] += 1
            elif "mailto:" in url or "@" in url:
                platforms["email"] += 1
            else:
                platforms["lainnya"] += 1

    return {
        "applied": applied_count,
        "interview": interview_count,
        "offering": offering_count,
        "rejected": rejected_count,
        "skipped": skipped_count,
        "total_submitted": total_submitted,
        "response_rate": response_rate,
        "platforms": platforms,
    }


def set_interview_schedule(job_url: str, interview_datetime: str, location: str = "", notes: str = "", source: str = "ui") -> bool:
    """
    Menetapkan jadwal interview pada item lamaran dan memperbarui status menjadi 'interview'.
    Format catatan terstruktur: [Jadwal: YYYY-MM-DDTHH:MM] [Lokasi: ...] Catatan
    """
    prefix_parts = []
    if interview_datetime:
        prefix_parts.append(f"[Jadwal: {interview_datetime.strip()}]")
    if location:
        prefix_parts.append(f"[Lokasi: {location.strip()}]")

    full_notes = " ".join(prefix_parts)
    if notes:
        full_notes = f"{full_notes} {notes.strip()}".strip()

    return update_job_status(job_url, "interview", notes=full_notes, source=source)


def generate_interview_ics(job_url: str = None, output_path: str = None) -> str:
    """
    Menghasilkan file kalender RFC 5545 (.ics) untuk jadwal interview kerja.
    Bisa diekspor untuk satu lamaran tertentu atau seluruh jadwal interview di pipeline.
    """
    hist = load_history()
    interviews = hist.get("interview", [])

    if job_url:
        interviews = [item for item in interviews if item.get("url") == job_url]

    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Job Hunter Copilot//ID",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Jadwal Interview Loker",
    ]

    for idx, item in enumerate(interviews):
        notes_str = item.get("notes", "") or ""
        # Cari [Jadwal: ...]
        match_dt = re.search(r"\[Jadwal:\s*([^\]]+)\]", notes_str)
        # Cari [Lokasi: ...]
        match_loc = re.search(r"\[Lokasi:\s*([^\]]+)\]", notes_str)

        raw_dt = match_dt.group(1).strip() if match_dt else ""
        location = match_loc.group(1).strip() if match_loc else ""

        # Parse datetime
        dt_start = None
        if raw_dt:
            for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt_start = datetime.datetime.strptime(raw_dt, fmt)
                    break
                except ValueError:
                    pass

        if not dt_start:
            # Fallback ke timestamp pencatatan + 1 hari jam 09:00
            try:
                base_dt = datetime.datetime.strptime(item.get("timestamp", ""), "%Y-%m-%d %H:%M:%S")
                dt_start = base_dt.replace(hour=9, minute=0, second=0) + datetime.timedelta(days=1)
            except Exception:
                dt_start = datetime.datetime.now() + datetime.timedelta(days=1)

        dt_end = dt_start + datetime.timedelta(hours=1)

        title = item.get("title") or "Wawancara Kerja"
        company = item.get("company") or "Perusahaan"
        url = item.get("url") or ""

        clean_notes = re.sub(r"\[(Jadwal|Lokasi):[^\]]+\]", "", notes_str).strip()
        desc = f"Wawancara posisi {title} di {company}.\\nTautan: {url}"
        if clean_notes:
            desc += f"\\nCatatan: {clean_notes}"

        uid_raw = f"{url}_{idx}_{dt_start.strftime('%Y%m%d%H%M')}"
        uid = hashlib.md5(uid_raw.encode("utf-8")).hexdigest()

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}@jobhuntercopilot",
            f"DTSTAMP:{now_utc}",
            f"DTSTART:{dt_start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:Interview {title} - {company}",
            f"DESCRIPTION:{desc}",
        ])
        if location:
            lines.append(f"LOCATION:{location}")
        lines.extend([
            "STATUS:CONFIRMED",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(lines) + "\r\n"

    if not output_path:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(data_dir, exist_ok=True)
        output_path = os.path.join(data_dir, "jadwal_interview.ics")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ics_content)

    return output_path

