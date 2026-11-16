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

    def test_update_status_kanban(self):
        url = "https://id.jobstreet.com/job/test-kanban"
        storage.record_job(url, "Finance Staff", "PT Indo", status="applied")
        
        # Pindahkan ke interview
        updated = storage.update_job_status(url, "interview", notes="Wawancara HR tgl 20 Nov")
        self.assertTrue(updated)

        hist = storage.load_history()
        self.assertEqual(len(hist["applied"]), 0)
        self.assertEqual(len(hist["interview"]), 1)
        self.assertEqual(hist["interview"][0]["notes"], "Wawancara HR tgl 20 Nov")

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
            self.assertEqual(len(reader), 3)

    def test_analytics_summary(self):
        storage.record_job("https://glints.com/id/1", "Dev 1", "PT A", status="applied")
        storage.record_job("https://id.jobstreet.com/2", "Dev 2", "PT B", status="interview")
        storage.record_job("https://dealls.com/3", "Dev 3", "PT C", status="offering")

        stats = storage.get_analytics_summary()
        self.assertEqual(stats["applied"], 1)
        self.assertEqual(stats["interview"], 1)
        self.assertEqual(stats["offering"], 1)
        self.assertEqual(stats["total_submitted"], 3)
        self.assertAlmostEqual(stats["response_rate"], 66.7, places=1)
        self.assertEqual(stats["platforms"]["glints"], 1)
        self.assertEqual(stats["platforms"]["jobstreet"], 1)
        self.assertEqual(stats["platforms"]["dealls"], 1)

    def test_update_notes_and_delete_job(self):
        url = "https://glints.com/id/opportunities/jobs/notes-test"
        storage.record_job(url, "UI Designer", "PT Kreatif", status="applied", notes="Awal")

        self.assertTrue(storage.update_job_notes(url, "Catatan baru: interview via Zoom"))
        hist = storage.load_history()
        self.assertEqual(hist["applied"][0]["notes"], "Catatan baru: interview via Zoom")

        # Delete job
        self.assertTrue(storage.delete_job(url))
        self.assertFalse(storage.is_job_recorded(url))
        hist_after = storage.load_history()
        self.assertEqual(len(hist_after["applied"]), 0)

    def test_clear_jobs_by_status(self):
        storage.record_job("https://id.jobstreet.com/job/r1", "Job 1", "PT 1", status="rejected")
        storage.record_job("https://id.jobstreet.com/job/r2", "Job 2", "PT 2", status="rejected")
        storage.record_job("https://id.jobstreet.com/job/a1", "Job 3", "PT 3", status="applied")

        cleared = storage.clear_jobs_by_status("rejected")
        self.assertEqual(cleared, 2)
        hist = storage.load_history()
        self.assertEqual(len(hist["rejected"]), 0)
        self.assertEqual(len(hist["applied"]), 1)

if __name__ == "__main__":
    unittest.main()
