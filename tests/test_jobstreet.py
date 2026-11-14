import unittest
from unittest.mock import MagicMock
from src.jobstreet import JobstreetHunter

class TestJobstreetHunter(unittest.TestCase):
    def setUp(self):
        self.config = {
            "profile": {
                "field_or_major": "Teknik Informatika",
                "target_keywords": ["Python Developer", "Backend"],
                "experience_level": "junior",
                "blacklist_keywords": ["Senior", "Manager"]
            },
            "auto_skip_already_seen": True
        }
        self.mock_page = MagicMock()
        self.hunter = JobstreetHunter(self.mock_page, self.config)

    def test_hunter_initialization(self):
        self.assertIsNotNone(self.hunter.matcher)
        self.assertEqual(self.hunter.config["profile"]["field_or_major"], "Teknik Informatika")

    def test_search_jobs_url_slug_generation(self):
        # Pastikan format URL jobstreet diubah menjadi slug
        self.mock_page.locator.return_value.all.return_value = []
        self.mock_page.locator.return_value.first.is_visible.return_value = False

        self.hunter.search_jobs(["Software Engineer"])
        # Verifikasi page.goto dipanggil dengan slug URL yang benar
        call_args = self.mock_page.goto.call_args[0][0]
        self.assertIn("id.jobstreet.com/id/software-engineer-jobs", call_args)

if __name__ == "__main__":
    unittest.main()
