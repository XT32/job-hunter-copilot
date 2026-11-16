import unittest
from unittest.mock import MagicMock, patch
from src.glints import GlintsHunter


class TestGlintsHunter(unittest.TestCase):
    def setUp(self):
        self.config = {
            "profile": {
                "field_or_major": "Teknik Informatika",
                "target_keywords": ["Backend Developer", "Golang"],
                "experience_level": "junior",
                "blacklist_keywords": ["Senior", "Manager"]
            },
            "screening_defaults": {
                "expected_salary": "8000000",
                "years_of_experience": "1",
                "domicile": "Jakarta"
            },
            "auto_skip_already_seen": True
        }
        self.mock_page = MagicMock()
        self.hunter = GlintsHunter(self.mock_page, self.config)

    def test_glints_initialization(self):
        self.assertIsNotNone(self.hunter.matcher)
        self.assertIsNotNone(self.hunter.screener)
        self.assertEqual(self.hunter.config["profile"]["field_or_major"], "Teknik Informatika")

    def test_glints_search_url_encoding(self):
        self.mock_page.locator.return_value.all.return_value = []
        self.mock_page.locator.return_value.first.is_visible.return_value = False

        self.hunter.search_jobs(["Backend Engineer"])
        call_args = self.mock_page.goto.call_args[0][0]
        self.assertIn("glints.com/id/opportunities/jobs/explore?keyword=Backend%20Engineer&country=ID", call_args)

    def test_check_login_status_not_logged_in(self):
        self.mock_page.url = "https://glints.com/id/opportunities/jobs/explore"
        login_btn = MagicMock()
        login_btn.is_visible.return_value = True
        self.mock_page.locator.return_value.first = login_btn

        status = self.hunter.check_login_status()
        self.assertFalse(status)

    def test_check_login_status_logged_in(self):
        self.mock_page.url = "https://glints.com/id/opportunities/jobs/explore"
        login_btn = MagicMock()
        login_btn.is_visible.return_value = False
        self.mock_page.locator.return_value.first = login_btn

        status = self.hunter.check_login_status()
        self.assertTrue(status)

    @patch("src.glints.human_delay", return_value=None)
    @patch("src.glints.is_job_recorded", return_value=False)
    def test_search_jobs_extracts_cards(self, mock_recorded, mock_delay):
        card = MagicMock()
        card.get_attribute.return_value = "/opportunities/jobs/backend-dev-123?source=search"
        card.inner_text.return_value = "Backend Developer (Golang)\nPT Maju Terus\nJakarta\nRp 8.000.000 - Rp 12.000.000"

        self.mock_page.locator.return_value.all.return_value = [card]

        jobs = self.hunter.search_jobs(["Golang"])
        self.assertGreaterEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Backend Developer (Golang)")
        self.assertEqual(jobs[0]["company"], "PT Maju Terus")
        self.assertEqual(jobs[0]["url"], "https://glints.com/opportunities/jobs/backend-dev-123")


if __name__ == "__main__":
    unittest.main()
