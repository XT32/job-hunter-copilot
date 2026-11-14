import json
import os
import tempfile
import unittest
import zipfile

from src.diagnostic import sanitize_config, check_system_health, generate_debug_bundle


class TestDiagnostic(unittest.TestCase):
    def test_sanitize_config_redacts_secrets(self):
        dirty_cfg = {
            "smtp": {
                "host": "smtp.gmail.com",
                "email": "user@gmail.com",
                "password": "secret_app_password_123",
            },
            "telegram": {
                "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
                "chat_id": "987654321",
            },
            "profile": {
                "applicant_name": "Budi Raharja",
                "contact_info": "+628123456789",
            },
        }

        clean = sanitize_config(dirty_cfg)
        self.assertEqual(clean["smtp"]["password"], "[REDACTED]")
        self.assertEqual(clean["smtp"]["email"], "[REDACTED_EMAIL]")
        self.assertEqual(clean["telegram"]["bot_token"], "[REDACTED]")
        self.assertEqual(clean["telegram"]["chat_id"], "[REDACTED]")
        self.assertEqual(clean["profile"]["applicant_name"], "[REDACTED_NAME]")
        self.assertEqual(clean["profile"]["contact_info"], "[REDACTED_CONTACT]")

    def test_check_system_health_structure(self):
        health = check_system_health()
        self.assertIn("os", health)
        self.assertIn("python_version", health)
        self.assertIn("portals", health)
        self.assertIn("browser_session", health)
        self.assertIn("database", health)

    def test_generate_debug_bundle_creates_valid_zip(self):
        test_logs = [{"time": "12:00:00", "message": "Test log message", "level": "info"}]
        test_cfg = {"smtp": {"password": "supersecretpassword"}}
        test_db_status = {"valid": True, "tampered": False}

        bundle_path = generate_debug_bundle(logs=test_logs, cfg=test_cfg, db_status=test_db_status)
        self.assertTrue(os.path.exists(bundle_path))
        self.assertTrue(zipfile.is_zipfile(bundle_path))

        with zipfile.ZipFile(bundle_path, "r") as zf:
            namelist = zf.namelist()
            self.assertIn("system_health.json", namelist)
            self.assertIn("config_redacted.json", namelist)
            self.assertIn("activity_logs.json", namelist)

            # Pastikan password tidak bocor ke dalam zip
            redacted_bytes = zf.read("config_redacted.json")
            self.assertNotIn(b"supersecretpassword", redacted_bytes)
            self.assertIn(b"[REDACTED]", redacted_bytes)


if __name__ == "__main__":
    unittest.main()
