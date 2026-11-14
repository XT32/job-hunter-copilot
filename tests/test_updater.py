import io
import os
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from src import updater


class TestUpdater(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = self.temp_dir.name
        os.makedirs(os.path.join(self.root, "data"), exist_ok=True)
        os.makedirs(os.path.join(self.root, "attachments"), exist_ok=True)
        os.makedirs(os.path.join(self.root, "src"), exist_ok=True)

        with open(os.path.join(self.root, "data", "loker_copilot.db"), "wb") as f:
            f.write(b"USER_PRIVATE_DB")
        with open(os.path.join(self.root, "attachments", "CV_Saya.pdf"), "wb") as f:
            f.write(b"USER_PRIVATE_CV")
        with open(os.path.join(self.root, "web_app.py"), "w", encoding="utf-8") as f:
            f.write("# old version")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_zip_update_preserves_user_data_and_updates_code(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("job-hunter-copilot-main/web_app.py", "# new version")
            zf.writestr("job-hunter-copilot-main/src/new_mod.py", "X = 1")
            zf.writestr("job-hunter-copilot-main/data/loker_copilot.db", "OVERWRITE_ATTEMPT")
            zf.writestr("job-hunter-copilot-main/attachments/dummy.pdf", "OVERWRITE_CV")

        updater._apply_zip_bytes_safely(buf.getvalue(), self.root)

        # Kode terupdate
        with open(os.path.join(self.root, "web_app.py"), "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "# new version")
        self.assertTrue(os.path.exists(os.path.join(self.root, "src", "new_mod.py")))

        # Data pribadi tidak tertimpa
        with open(os.path.join(self.root, "data", "loker_copilot.db"), "rb") as f:
            self.assertEqual(f.read(), b"USER_PRIVATE_DB")
        self.assertTrue(os.path.exists(os.path.join(self.root, "attachments", "CV_Saya.pdf")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "attachments", "dummy.pdf")))

    @patch("src.updater.fetch_remote_latest")
    def test_check_for_updates_detects_available_and_uptodate(self, mock_remote):
        mock_remote.return_value = {
            "sha": "abcdef1234567890",
            "short_sha": "abcdef1",
            "message": "feat: update baru",
            "date": "2026-11-14T12:00:00Z",
        }
        res1 = updater.check_for_updates(self.root)
        self.assertTrue(res1["success"])
        self.assertTrue(res1["update_available"])

        updater._save_local_version_info("abcdef1234567890", "feat: update baru", root_dir=self.root)
        res2 = updater.check_for_updates(self.root)
        self.assertTrue(res2["success"])
        self.assertTrue(res2["up_to_date"])


if __name__ == "__main__":
    unittest.main()
