import os
import unittest
import tempfile
import csv
from src import storage

class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_file = storage.HISTORY_FILE
        self.test_history_path = os.path.join(self.temp_dir.name, "test_history.json")
        storage.HISTORY_FILE = self.test_history_path

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

    def test_export_to_csv(self):
        url1 = "https://id.jobstreet.com/job/111"
        url2 = "https://glints.com/id/opportunities/jobs/222"
        storage.record_job(url1, "Finance Staff", "PT Indo", status="applied", notes="Sukses")
        storage.record_job(url2, "Sales Lapangan", "PT Toko", status="skipped", notes="Blacklist")

        csv_path = os.path.join(self.temp_dir.name, "export.csv")
        storage.export_history_to_csv(csv_path)

        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = list(csv.reader(f))
            # Header + 2 data rows
            self.assertEqual(len(reader), 3)
            self.assertEqual(reader[0][0], "Status")
            self.assertEqual(reader[1][0], "Dilamar")
            self.assertEqual(reader[2][0], "Dilewati")

if __name__ == "__main__":
    unittest.main()
