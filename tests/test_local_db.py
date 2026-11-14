import os
import sqlite3
import tempfile
import unittest
from src.local_db import LocalSecureDB, TamperDetectedError


class TestLocalSecureDB(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_copilot.db")
        self.db = LocalSecureDB(self.db_path)
        self.db.ensure_initialized()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_encrypts_config_and_verifies_integrity(self):
        secret_cfg = {
            "profile": {"applicant_name": "Budi Santoso"},
            "smtp": {"password": "super_secret_app_password_999"},
        }
        self.db.save_config(secret_cfg, source="ui")

        # Pastikan plaintext secret tidak terlihat langsung di byte file .db
        with open(self.db_path, "rb") as f:
            raw_bytes = f.read()
        self.assertNotIn(b"super_secret_app_password_999", raw_bytes)

        status = self.db.verify_integrity()
        self.assertTrue(status["valid"])
        self.assertFalse(status["tampered"])
        loaded = self.db.get_config()
        self.assertEqual(loaded["smtp"]["password"], "super_secret_app_password_999")

    def test_blocks_non_ui_write(self):
        with self.assertRaises(TamperDetectedError):
            self.db.record_job("https://id.jobstreet.com/job/1", "PPIC Staff", "PT A", source="cli_hack")

    def test_detects_direct_sqlite_tampering_and_restores_snapshot(self):
        self.db.save_config({"profile": {"applicant_name": "Nama Sah"}}, source="ui")
        self.db.record_job("https://id.jobstreet.com/job/ppic-1", "PPIC Staff", "PT Manufaktur", status="applied", source="ui")

        # Simulasi orang membongkar & mengubah langsung file .db lewat SQLite di luar UI
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE job_history SET status='offering', title='Direktur Palsu' WHERE url='https://id.jobstreet.com/job/ppic-1'")
        conn.commit()
        conn.close()

        status = self.db.verify_integrity()
        self.assertTrue(status["tampered"])
        self.assertFalse(status["valid"])

        # Penulisan baru harus diblokir sebelum dipulihkan/direset lewat UI
        with self.assertRaises(TamperDetectedError):
            self.db.record_job("https://id.jobstreet.com/job/2", "Staff", "PT B", source="ui")

        # Pulihkan dari snapshot sah terakhir melalui UI
        res = self.db.restore_from_snapshot()
        self.assertTrue(res["success"])

        status_after = self.db.verify_integrity()
        self.assertFalse(status_after["tampered"])
        hist = self.db.load_history()
        self.assertEqual(hist["applied"][0]["title"], "PPIC Staff")

    def test_detects_missing_seal_file(self):
        self.db.save_config({"profile": {"applicant_name": "Test"}}, source="ui")
        os.remove(self.db.seal_path)

        status = self.db.verify_integrity()
        self.assertTrue(status["tampered"])


if __name__ == "__main__":
    unittest.main()
