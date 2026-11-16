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

"""
Database Lokal Terproteksi (SQLite + Enkripsi Payload + HMAC-SHA256 Integrity Seal).

Dirancang agar seluruh perubahan konfigurasi dan riwayat lamaran hanya dilakukan melalui
antarmuka Web UI. Jika file database atau file konfigurasi lama diubah/dibongkar langsung
melalui editor eksternal di luar UI, modul ini mendeteksi manipulasi (Tamper Alert),
memblokir penulisan tidak sah, mencatat log audit keamanan, dan menyediakan pemulihan
dari snapshot terakhir yang sah melalui UI.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_DB_PATH = os.path.join(DATA_DIR, "loker_copilot.db")

_db_lock = threading.RLock()


try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_AESGCM = True
except Exception:
    HAS_AESGCM = False


class TamperDetectedError(RuntimeError):
    """Dilemparkan ketika terdeteksi modifikasi database di luar Web UI."""

    def __init__(self, reason: str, details: dict = None):
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """Menghasilkan keystream deterministik berbasis SHA-256 counter mode (fallback mode)."""
    chunks = []
    counter = 0
    total = 0
    while total < length:
        block = hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        chunks.append(block)
        total += len(block)
        counter += 1
    return b"".join(chunks)[:length]


def _encrypt_text(key: bytes, plaintext: str) -> str:
    raw = plaintext.encode("utf-8")
    if HAS_AESGCM:
        aes = AESGCM(key)
        nonce = secrets.token_bytes(12)
        ct = aes.encrypt(nonce, raw, b"LOKER_COPILOT_DB")
        return "gcm$" + base64.urlsafe_b64encode(nonce + ct).decode("ascii")

    nonce = secrets.token_bytes(16)
    stream = _keystream(key, nonce, len(raw))
    cipher = bytes(a ^ b for a, b in zip(raw, stream))
    tag = hmac.new(key, b"ENC|" + nonce + cipher, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + tag + cipher).decode("ascii")


def _decrypt_text(key: bytes, token: str) -> str:
    if token.startswith("gcm$"):
        if not HAS_AESGCM:
            raise ValueError("Modul cryptography diperlukan untuk membuka payload AES-GCM.")
        raw = base64.urlsafe_b64decode(token[4:].encode("ascii"))
        nonce = raw[:12]
        ct = raw[12:]
        aes = AESGCM(key)
        plain = aes.decrypt(nonce, ct, b"LOKER_COPILOT_DB")
        return plain.decode("utf-8")

    # Format kompatibilitas / fallback
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    if len(raw) < 48:
        raise ValueError("Payload terenkripsi rusak atau terpotong")
    nonce = raw[:16]
    tag = raw[16:48]
    cipher = raw[48:]
    expected_tag = hmac.new(key, b"ENC|" + nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Signature enkripsi tidak valid (kemungkinan dimanipulasi)")
    stream = _keystream(key, nonce, len(cipher))
    plain = bytes(a ^ b for a, b in zip(cipher, stream))
    return plain.decode("utf-8")


def _file_sha256(path: str) -> str:
    if not os.path.exists(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class LocalSecureDB:
    """Manajer database SQLite lokal dengan segel integritas HMAC dan deteksi tamper."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = os.path.abspath(db_path)
        self.base_dir = os.path.dirname(self.db_path)
        self.db_name = os.path.basename(self.db_path)
        self.key_path = os.path.join(self.base_dir, f".{self.db_name}.key")
        self.seal_path = os.path.join(self.base_dir, f".{self.db_name}.seal")
        self.snapshot_path = os.path.join(self.base_dir, f".{self.db_name}.snapshot")
        self._tamper_cache = None

    def _ensure_dirs(self):
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_or_create_key(self) -> bytes:
        self._ensure_dirs()
        # 1. Coba baca dari OS Keyring jika tersedia
        try:
            import keyring
            stored = keyring.get_password("loker_copilot", f"key_{self.db_name}")
            if stored:
                raw_k = base64.urlsafe_b64decode(stored.encode("ascii"))
                if len(raw_k) == 32:
                    return raw_k
        except Exception:
            pass

        # 2. Coba baca dari file .key lokal
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                data = f.read().strip()
            if len(data) >= 32:
                key = base64.urlsafe_b64decode(data)
                try:
                    import keyring
                    keyring.set_password("loker_copilot", f"key_{self.db_name}", base64.urlsafe_b64encode(key).decode("ascii"))
                except Exception:
                    pass
                return key

        # 3. Buat kunci master baru 32-byte (AES-256)
        key = secrets.token_bytes(32)
        with open(self.key_path, "wb") as f:
            f.write(base64.urlsafe_b64encode(key))
        try:
            os.chmod(self.key_path, 0o600)
        except Exception:
            pass

        try:
            import keyring
            keyring.set_password("loker_copilot", f"key_{self.db_name}", base64.urlsafe_b64encode(key).decode("ascii"))
        except Exception:
            pass

        return key

    def _connect(self) -> sqlite3.Connection:
        self._ensure_dirs()
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self, conn: sqlite3.Connection):
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS _warning_notice (
                id INTEGER PRIMARY KEY,
                notice TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                payload_enc TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_via TEXT NOT NULL,
                row_hmac TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS job_history (
                url TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                notes TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                row_hmac TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS security_meta (
                meta_key TEXT PRIMARY KEY,
                meta_value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS security_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time TEXT NOT NULL,
                event_type TEXT NOT NULL,
                detail TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO _warning_notice (id, notice) VALUES (
                1,
                'PERINGATAN KEAMANAN: Database lokal ini dikelola eksklusif lewat Web UI. Mengubah isi file secara langsung akan terdeteksi sebagai manipulasi (Tamper Alert).'
            )
            """
        )

    def _sign_config_row(self, key: bytes, cfg_key: str, payload_enc: str, updated_at: str, updated_via: str) -> str:
        msg = f"CFG|{cfg_key}|{payload_enc}|{updated_at}|{updated_via}".encode("utf-8")
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    def _sign_job_row(self, key: bytes, row: dict) -> str:
        msg = (
            f"JOB|{row['url']}|{row['status']}|{row['title']}|{row['company']}|"
            f"{row['notes']}|{row['timestamp']}|{row['updated_at']}"
        ).encode("utf-8")
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    def _compute_canonical_digest(self, key: bytes, conn: sqlite3.Connection) -> str:
        cfg_rows = conn.execute(
            "SELECT key, payload_enc, updated_at, updated_via, row_hmac FROM app_config ORDER BY key"
        ).fetchall()
        job_rows = conn.execute(
            "SELECT url, status, title, company, notes, timestamp, updated_at, row_hmac FROM job_history ORDER BY url"
        ).fetchall()
        parts = []
        for r in cfg_rows:
            parts.append(f"C:{r['key']}:{r['payload_enc']}:{r['updated_at']}:{r['updated_via']}:{r['row_hmac']}")
        for r in job_rows:
            parts.append(
                f"J:{r['url']}:{r['status']}:{r['title']}:{r['company']}:{r['notes']}:{r['timestamp']}:{r['updated_at']}:{r['row_hmac']}"
            )
        joined = "\n".join(parts).encode("utf-8")
        return hmac.new(key, b"CANONICAL|" + joined, hashlib.sha256).hexdigest()

    def _write_seal_and_snapshot(self, key: bytes, conn: sqlite3.Connection):
        canonical_digest = self._compute_canonical_digest(key, conn)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT OR REPLACE INTO security_meta (meta_key, meta_value) VALUES ('db_digest', ?)",
            (canonical_digest,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO security_meta (meta_key, meta_value) VALUES ('last_ui_write_at', ?)",
            (now,),
        )
        conn.commit()
        conn.close()

        # Hitung SHA-256 byte file .db setelah koneksi ditutup/flush
        db_sha = _file_sha256(self.db_path)
        seal_payload = {
            "db_sha256": db_sha,
            "canonical_digest": canonical_digest,
            "signed_at": now,
        }
        seal_raw = json.dumps(seal_payload, sort_keys=True).encode("utf-8")
        seal_hmac = hmac.new(key, b"SEAL|" + seal_raw, hashlib.sha256).hexdigest()
        with open(self.seal_path, "w", encoding="utf-8") as f:
            json.dump({"payload": seal_payload, "hmac": seal_hmac}, f, indent=2)

        # Simpan snapshot sah terenkripsi untuk fitur pemulihan 1-klik di UI
        self._save_encrypted_snapshot(key)
        self._tamper_cache = None

    def _save_encrypted_snapshot(self, key: bytes):
        conn = self._connect()
        try:
            cfg_data = {}
            for r in conn.execute("SELECT key, payload_enc FROM app_config").fetchall():
                cfg_data[r["key"]] = json.loads(_decrypt_text(key, r["payload_enc"]))
            jobs = []
            for r in conn.execute(
                "SELECT url, status, title, company, notes, timestamp, updated_at FROM job_history"
            ).fetchall():
                jobs.append(dict(r))
            snap = {"config": cfg_data, "jobs": jobs, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}
            enc = _encrypt_text(key, json.dumps(snap, ensure_ascii=False))
            with open(self.snapshot_path, "w", encoding="utf-8") as f:
                f.write(enc)
        except Exception:
            pass
        finally:
            conn.close()

    def _log_audit(self, event_type: str, detail: str):
        try:
            conn = self._connect()
            self._init_schema(conn)
            conn.execute(
                "INSERT INTO security_audit (event_time, event_type, detail) VALUES (?, ?, ?)",
                (time.strftime("%Y-%m-%d %H:%M:%S"), event_type, detail),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def ensure_initialized(self):
        with _db_lock:
            key = self._get_or_create_key()
            is_new = not os.path.exists(self.db_path) or os.path.getsize(self.db_path) == 0
            if is_new:
                conn = self._connect()
                self._init_schema(conn)
                conn.execute(
                    "INSERT INTO security_audit (event_time, event_type, detail) VALUES (?, 'INIT', 'Database lokal terproteksi dibuat oleh sistem.')",
                    (time.strftime("%Y-%m-%d %H:%M:%S"),),
                )
                self._write_seal_and_snapshot(key, conn)

    def verify_integrity(self) -> dict:
        """
        Memeriksa apakah file database pernah dibongkar atau diubah langsung di luar UI.
        Mengembalikan dict: {valid, tampered, reason, details, has_snapshot, audit_logs}
        """
        with _db_lock:
            self.ensure_initialized()
            key = self._get_or_create_key()
            reasons = []

            # 1. Cek keberadaan & validitas file segel (.seal)
            if not os.path.exists(self.seal_path):
                reasons.append("File segel integritas database hilang atau dihapus.")
            else:
                try:
                    with open(self.seal_path, "r", encoding="utf-8") as f:
                        seal_doc = json.load(f)
                    payload = seal_doc.get("payload", {})
                    seal_hmac = seal_doc.get("hmac", "")
                    expected_hmac = hmac.new(
                        key,
                        b"SEAL|" + json.dumps(payload, sort_keys=True).encode("utf-8"),
                        hashlib.sha256,
                    ).hexdigest()
                    if not hmac.compare_digest(seal_hmac, expected_hmac):
                        reasons.append("Segel integritas (.seal) dimanipulasi secara tidak sah.")
                    else:
                        current_sha = _file_sha256(self.db_path)
                        if payload.get("db_sha256") != current_sha:
                            reasons.append(
                                "File database (.db) terdeteksi diubah langsung dari luar UI (checksum file tidak cocok)."
                            )
                except Exception:
                    reasons.append("File segel integritas (.seal) rusak atau tidak terbaca.")

            # 2. Cek isi SQLite (per-row HMAC, dekripsi config, dan canonical digest)
            audit_logs = []
            try:
                conn = self._connect()
                # Pastikan tabel inti ada
                tables = {
                    r["name"]
                    for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                }
                if not {"app_config", "job_history", "security_meta"}.issubset(tables):
                    reasons.append("Struktur tabel database dirusak atau tidak lengkap.")
                else:
                    for r in conn.execute("SELECT * FROM app_config").fetchall():
                        expected_row_hmac = self._sign_config_row(
                            key, r["key"], r["payload_enc"], r["updated_at"], r["updated_via"]
                        )
                        if not hmac.compare_digest(r["row_hmac"], expected_row_hmac):
                            reasons.append(f"Baris konfigurasi '{r['key']}' diubah langsung di luar UI.")
                        try:
                            _decrypt_text(key, r["payload_enc"])
                        except Exception:
                            reasons.append(f"Payload terenkripsi konfigurasi '{r['key']}' dirusak.")

                    for r in conn.execute("SELECT * FROM job_history").fetchall():
                        expected_job_hmac = self._sign_job_row(key, dict(r))
                        if not hmac.compare_digest(r["row_hmac"], expected_job_hmac):
                            reasons.append(f"Data riwayat lamaran '{r['title']}' diubah langsung di luar UI.")

                    meta_row = conn.execute(
                        "SELECT meta_value FROM security_meta WHERE meta_key='db_digest'"
                    ).fetchone()
                    canonical = self._compute_canonical_digest(key, conn)
                    if not meta_row or not hmac.compare_digest(meta_row["meta_value"], canonical):
                        reasons.append("Ringkasan integritas global (db_digest) tidak cocok — ada penambahan/penghapusan baris langsung.")

                    if "security_audit" in tables:
                        for a in conn.execute(
                            "SELECT event_time, event_type, detail FROM security_audit ORDER BY id DESC LIMIT 15"
                        ).fetchall():
                            audit_logs.append(dict(a))
                conn.close()
            except sqlite3.DatabaseError as e:
                reasons.append(f"File database korup atau dibuka/ditulis dengan format tidak sah ({e}).")
            except Exception as e:
                reasons.append(f"Gagal memverifikasi integritas database ({e}).")

            tampered = len(reasons) > 0
            result = {
                "valid": not tampered,
                "tampered": tampered,
                "reason": " | ".join(dict.fromkeys(reasons)) if tampered else "Integritas database terverifikasi (UI-Only).",
                "reasons": list(dict.fromkeys(reasons)),
                "has_snapshot": os.path.exists(self.snapshot_path),
                "db_path": self.db_path,
                "audit_logs": audit_logs,
            }

            if tampered:
                self._tamper_cache = result
            return result

    def _assert_write_allowed(self, source: str):
        if source not in ("ui", "system_init", "system_migration"):
            raise TamperDetectedError(
                "Akses tulis ditolak: Perubahan database hanya diperbolehkan melalui Web UI."
            )
        status = self.verify_integrity()
        if status["tampered"]:
            self._log_audit("TAMPER_BLOCKED", status["reason"])
            raise TamperDetectedError(
                f"PERINGATAN KEAMANAN: Terdeteksi manipulasi file database secara langsung! {status['reason']}",
                details=status,
            )

    def get_config(self, key_name: str = "main_config") -> dict:
        with _db_lock:
            status = self.verify_integrity()
            if status["tampered"]:
                # Jika database dirusak, coba baca dari snapshot sah (read-only) agar UI tetap bisa boot & menampilkan peringatan
                snap = self._read_snapshot()
                if snap and key_name in snap.get("config", {}):
                    return snap["config"][key_name]
                raise TamperDetectedError(status["reason"], details=status)

            key = self._get_or_create_key()
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT payload_enc FROM app_config WHERE key=?", (key_name,)
                ).fetchone()
                if not row:
                    return None
                return json.loads(_decrypt_text(key, row["payload_enc"]))
            finally:
                conn.close()

    def save_config(self, data: dict, key_name: str = "main_config", source: str = "ui"):
        with _db_lock:
            self._assert_write_allowed(source)
            key = self._get_or_create_key()
            conn = self._connect()
            self._init_schema(conn)
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            payload_enc = _encrypt_text(key, json.dumps(data, ensure_ascii=False))
            row_hmac = self._sign_config_row(key, key_name, payload_enc, now, source)
            conn.execute(
                """
                INSERT OR REPLACE INTO app_config (key, payload_enc, updated_at, updated_via, row_hmac)
                VALUES (?, ?, ?, ?, ?)
                """,
                (key_name, payload_enc, now, source, row_hmac),
            )
            conn.execute(
                "INSERT INTO security_audit (event_time, event_type, detail) VALUES (?, 'UI_CONFIG_SAVE', ?)",
                (now, f"Konfigurasi '{key_name}' diperbarui melalui {source}."),
            )
            self._write_seal_and_snapshot(key, conn)

    def load_history(self) -> dict:
        valid_statuses = ["applied", "interview", "offering", "rejected", "skipped"]
        with _db_lock:
            status = self.verify_integrity()
            if status["tampered"]:
                snap = self._read_snapshot()
                hist = {s: [] for s in valid_statuses}
                if snap:
                    for item in snap.get("jobs", []):
                        st = item.get("status", "applied")
                        if st in hist:
                            hist[st].append(item)
                    return hist
                raise TamperDetectedError(status["reason"], details=status)

            conn = self._connect()
            try:
                hist = {s: [] for s in valid_statuses}
                rows = conn.execute(
                    "SELECT url, status, title, company, notes, timestamp, updated_at FROM job_history ORDER BY rowid ASC"
                ).fetchall()
                for r in rows:
                    st = r["status"] if r["status"] in hist else "applied"
                    entry = {
                        "url": r["url"],
                        "title": r["title"],
                        "company": r["company"],
                        "timestamp": r["timestamp"],
                        "notes": r["notes"],
                    }
                    if r["updated_at"]:
                        entry["updated_at"] = r["updated_at"]
                    hist[st].append(entry)
                return hist
            finally:
                conn.close()

    def is_job_recorded(self, job_url: str) -> bool:
        with _db_lock:
            hist = self.load_history()
            for items in hist.values():
                for item in items:
                    if item.get("url") == job_url:
                        return True
            return False

    def record_job(self, job_url: str, title: str, company: str, status: str = "applied", notes: str = "", source: str = "ui"):
        valid_statuses = ["applied", "interview", "offering", "rejected", "skipped"]
        status = status if status in valid_statuses else "applied"
        with _db_lock:
            self._assert_write_allowed(source)
            key = self._get_or_create_key()
            conn = self._connect()
            self._init_schema(conn)
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            row = {
                "url": str(job_url),
                "status": status,
                "title": str(title or ""),
                "company": str(company or ""),
                "notes": str(notes or ""),
                "timestamp": now,
                "updated_at": "",
            }
            row_hmac = self._sign_job_row(key, row)
            conn.execute(
                """
                INSERT OR REPLACE INTO job_history (url, status, title, company, notes, timestamp, updated_at, row_hmac)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (row["url"], row["status"], row["title"], row["company"], row["notes"], row["timestamp"], row["updated_at"], row_hmac),
            )
            conn.execute(
                "INSERT INTO security_audit (event_time, event_type, detail) VALUES (?, 'UI_JOB_RECORD', ?)",
                (now, f"Lamaran '{row['title']}' ({row['status']}) dicatat via {source}."),
            )
            self._write_seal_and_snapshot(key, conn)

    def update_job_status(self, job_url: str, new_status: str, notes: str = None, source: str = "ui") -> bool:
        valid_statuses = ["applied", "interview", "offering", "rejected", "skipped"]
        if new_status not in valid_statuses:
            return False
        with _db_lock:
            self._assert_write_allowed(source)
            key = self._get_or_create_key()
            conn = self._connect()
            existing = conn.execute(
                "SELECT url, status, title, company, notes, timestamp, updated_at FROM job_history WHERE url=?",
                (job_url,),
            ).fetchone()
            if not existing:
                conn.close()
                return False

            now = time.strftime("%Y-%m-%d %H:%M:%S")
            row = {
                "url": existing["url"],
                "status": new_status,
                "title": existing["title"],
                "company": existing["company"],
                "notes": existing["notes"] if notes is None else str(notes),
                "timestamp": existing["timestamp"],
                "updated_at": now,
            }
            row_hmac = self._sign_job_row(key, row)
            conn.execute(
                """
                UPDATE job_history
                SET status=?, notes=?, updated_at=?, row_hmac=?
                WHERE url=?
                """,
                (row["status"], row["notes"], row["updated_at"], row_hmac, row["url"]),
            )
            conn.execute(
                "INSERT INTO security_audit (event_time, event_type, detail) VALUES (?, 'UI_STATUS_UPDATE', ?)",
                (now, f"Status '{row['title']}' diubah ke '{new_status}' via {source}."),
            )
            self._write_seal_and_snapshot(key, conn)
            return True

    def update_job_notes(self, job_url: str, notes: str, source: str = "ui") -> bool:
        """Memperbarui catatan lamaran (misal: link interview, nama HR, hasil) tanpa mengubah status."""
        with _db_lock:
            self._assert_write_allowed(source)
            key = self._get_or_create_key()
            conn = self._connect()
            existing = conn.execute(
                "SELECT url, status, title, company, notes, timestamp, updated_at FROM job_history WHERE url=?",
                (job_url,),
            ).fetchone()
            if not existing:
                conn.close()
                return False

            now = time.strftime("%Y-%m-%d %H:%M:%S")
            row = {
                "url": existing["url"],
                "status": existing["status"],
                "title": existing["title"],
                "company": existing["company"],
                "notes": str(notes or ""),
                "timestamp": existing["timestamp"],
                "updated_at": now,
            }
            row_hmac = self._sign_job_row(key, row)
            conn.execute(
                """
                UPDATE job_history
                SET notes=?, updated_at=?, row_hmac=?
                WHERE url=?
                """,
                (row["notes"], row["updated_at"], row_hmac, row["url"]),
            )
            conn.execute(
                "INSERT INTO security_audit (event_time, event_type, detail) VALUES (?, 'UI_NOTES_UPDATE', ?)",
                (now, f"Catatan '{row['title']}' diperbarui via {source}."),
            )
            self._write_seal_and_snapshot(key, conn)
            return True

    def delete_job(self, job_url: str, source: str = "ui") -> bool:
        """Menghapus entri lamaran tertentu dari riwayat/Kanban."""
        with _db_lock:
            self._assert_write_allowed(source)
            key = self._get_or_create_key()
            conn = self._connect()
            existing = conn.execute(
                "SELECT title FROM job_history WHERE url=?",
                (job_url,),
            ).fetchone()
            if not existing:
                conn.close()
                return False

            title = existing["title"]
            conn.execute("DELETE FROM job_history WHERE url=?", (job_url,))
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO security_audit (event_time, event_type, detail) VALUES (?, 'UI_JOB_DELETE', ?)",
                (now, f"Lamaran '{title}' dihapus via {source}."),
            )
            self._write_seal_and_snapshot(key, conn)
            return True

    def clear_jobs_by_status(self, status: str, source: str = "ui") -> int:
        """Menghapus seluruh entri lamaran dengan status tertentu (misal: membersihkan yang 'rejected')."""
        valid_statuses = ["applied", "interview", "offering", "rejected", "skipped"]
        if status not in valid_statuses:
            return 0
        with _db_lock:
            self._assert_write_allowed(source)
            key = self._get_or_create_key()
            conn = self._connect()
            count = conn.execute("SELECT COUNT(*) FROM job_history WHERE status=?", (status,)).fetchone()[0]
            if count == 0:
                conn.close()
                return 0

            conn.execute("DELETE FROM job_history WHERE status=?", (status,))
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO security_audit (event_time, event_type, detail) VALUES (?, 'UI_JOBS_CLEAR_STATUS', ?)",
                (now, f"Sebanyak {count} lamaran dengan status '{status}' dibersihkan via {source}."),
            )
            self._write_seal_and_snapshot(key, conn)
            return count

    def _read_snapshot(self) -> dict:
        if not os.path.exists(self.snapshot_path):
            return None
        try:
            key = self._get_or_create_key()
            with open(self.snapshot_path, "r", encoding="utf-8") as f:
                enc = f.read().strip()
            return json.loads(_decrypt_text(key, enc))
        except Exception:
            return None

    def restore_from_snapshot(self) -> dict:
        """Memulihkan database dari snapshot terenkripsi terakhir yang dibuat UI."""
        with _db_lock:
            snap = self._read_snapshot()
            if not snap:
                return {"success": False, "message": "Snapshot sah tidak ditemukan atau ikut rusak."}

            key = self._get_or_create_key()
            if os.path.exists(self.db_path):
                try:
                    os.remove(self.db_path)
                except Exception:
                    pass

            conn = self._connect()
            self._init_schema(conn)
            now = time.strftime("%Y-%m-%d %H:%M:%S")

            for cfg_key, cfg_val in snap.get("config", {}).items():
                payload_enc = _encrypt_text(key, json.dumps(cfg_val, ensure_ascii=False))
                row_hmac = self._sign_config_row(key, cfg_key, payload_enc, now, "ui_restore")
                conn.execute(
                    "INSERT OR REPLACE INTO app_config (key, payload_enc, updated_at, updated_via, row_hmac) VALUES (?, ?, ?, 'ui_restore', ?)",
                    (cfg_key, payload_enc, now, row_hmac),
                )

            for item in snap.get("jobs", []):
                row = {
                    "url": item["url"],
                    "status": item.get("status", "applied"),
                    "title": item.get("title", ""),
                    "company": item.get("company", ""),
                    "notes": item.get("notes", ""),
                    "timestamp": item.get("timestamp", now),
                    "updated_at": item.get("updated_at", ""),
                }
                row_hmac = self._sign_job_row(key, row)
                conn.execute(
                    "INSERT OR REPLACE INTO job_history (url, status, title, company, notes, timestamp, updated_at, row_hmac) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (row["url"], row["status"], row["title"], row["company"], row["notes"], row["timestamp"], row["updated_at"], row_hmac),
                )

            conn.execute(
                "INSERT INTO security_audit (event_time, event_type, detail) VALUES (?, 'SNAPSHOT_RESTORED', 'Database dipulihkan dari snapshot terakhir yang sah melalui UI.')",
                (now,),
            )
            self._write_seal_and_snapshot(key, conn)
            return {"success": True, "message": "Database berhasil dipulihkan ke kondisi sah terakhir sebelum dimodifikasi dari luar UI."}

    def reset_database_via_ui(self, default_config: dict = None) -> dict:
        """Mereset & menyegel ulang database secara sah dari Web UI."""
        with _db_lock:
            key = self._get_or_create_key()
            if os.path.exists(self.db_path):
                try:
                    os.remove(self.db_path)
                except Exception:
                    pass
            conn = self._connect()
            self._init_schema(conn)
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            if default_config is not None:
                payload_enc = _encrypt_text(key, json.dumps(default_config, ensure_ascii=False))
                row_hmac = self._sign_config_row(key, "main_config", payload_enc, now, "ui_reset")
                conn.execute(
                    "INSERT OR REPLACE INTO app_config (key, payload_enc, updated_at, updated_via, row_hmac) VALUES ('main_config', ?, ?, 'ui_reset', ?)",
                    (payload_enc, now, row_hmac),
                )
            conn.execute(
                "INSERT INTO security_audit (event_time, event_type, detail) VALUES (?, 'UI_RESET', 'Database di-reset dan disegel ulang melalui UI.')",
                (now,),
            )
            self._write_seal_and_snapshot(key, conn)
            return {"success": True, "message": "Database lokal berhasil dibuat ulang dan disegel via UI."}


def get_default_db() -> LocalSecureDB:
    return LocalSecureDB(DEFAULT_DB_PATH)
