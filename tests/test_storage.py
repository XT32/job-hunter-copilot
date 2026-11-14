import os
import unittest
import tempfile
import json
from src import storage

class TestStorage(unittest.TestCase):
    def setUp(self):
        # Gunakan temporary file untuk testing storage
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_file = storage.HISTORY_FILE
        storage.HISTORY_FILE = os.path.join(self.temp_dir.name, "test_history.json")

    def tearDown(self):
        storage.HISTORY_FILE = self.original_file
        self.temp_dir.cleanup()

    def test_record_and_check_job(self):
        url = "https://glints.com/id/opportunities/jobs/test-123"
        self.assertFalse(storage.is_job_recorded(url))

        storage.record_job(url, "Backend Dev", "PT Tech", status="applied")
        self.assertTrue(storage.is_job_recorded(url))

        hist = storage.load_history()
        self.assertEqual(len(hist["applied"]), 1)
        self.assertEqual(hist["applied"][0]["title"], "Backend Dev")

    def test_record_skipped_job(self):
        url = "https://glints.com/id/opportunities/jobs/test-456"
        storage.record_job(url, "Sales", "PT X", status="skipped", notes="Blacklist")
        self.assertTrue(storage.is_job_recorded(url))

        hist = storage.load_history()
        self.assertEqual(len(hist["skipped"]), 1)
        self.assertEqual(hist["skipped"][0]["notes"], "Blacklist")

if __name__ == "__main__":
    unittest.main()
