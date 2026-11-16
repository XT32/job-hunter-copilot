import unittest
from unittest.mock import MagicMock, patch
from src.maganghub import MagangHubHunter


class TestMagangHubHunter(unittest.TestCase):
    def setUp(self):
        self.config = {
            "profile": {
                "field_or_major": "Sistem Informasi",
                "target_keywords": ["Magang Web", "Frontend"],
                "experience_level": "fresh_graduate",
                "blacklist_keywords": ["Senior"]
            },
            "screening_defaults": {
                "expected_salary": "3000000",
                "years_of_experience": "0",
                "domicile": "Jakarta"
            },
            "auto_skip_already_seen": True
        }
        self.mock_page = MagicMock()
        self.hunter = MagangHubHunter(self.mock_page, self.config)

    def test_maganghub_initialization(self):
        self.assertIsNotNone(self.hunter.matcher)
        self.assertIsNotNone(self.hunter.screener)
        self.assertEqual(self.hunter.config["profile"]["field_or_major"], "Sistem Informasi")

    def test_maganghub_search_url_encoding(self):
        self.mock_page.locator.return_value.all.return_value = []
        self.mock_page.locator.return_value.first.is_visible.return_value = False

        self.hunter.search_jobs(["Magang Web"])
        call_args = self.mock_page.goto.call_args[0][0]
        self.assertIn("maganghub.kemnaker.go.id/lowongan?cari=Magang%20Web", call_args)

    def test_check_login_status_not_logged_in(self):
        self.mock_page.url = "https://maganghub.kemnaker.go.id/lowongan"
        login_btn = MagicMock()
        login_btn.is_visible.return_value = True
        self.mock_page.locator.return_value.first = login_btn

        status = self.hunter.check_login_status()
        self.assertFalse(status)

    def test_check_login_status_logged_in(self):
        self.mock_page.url = "https://maganghub.kemnaker.go.id/lowongan"
        login_btn = MagicMock()
        login_btn.is_visible.return_value = False
        self.mock_page.locator.return_value.first = login_btn

        status = self.hunter.check_login_status()
        self.assertTrue(status)

    @patch("src.maganghub.human_delay", return_value=None)
    @patch("src.maganghub.is_job_recorded", return_value=False)
    def test_search_jobs_extracts_cards(self, mock_recorded, mock_delay):
        card = MagicMock()
        card.get_attribute.return_value = "/lowongan/detail/12345?batch=4"
        card.inner_text.return_value = "Magang Web Frontend\nPT Telkom Indonesia\nDKI Jakarta\nBatch 4"

        self.mock_page.locator.return_value.all.return_value = [card]

        jobs = self.hunter.search_jobs(["Magang Web"])
        self.assertGreaterEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Magang Web Frontend")
        self.assertEqual(jobs[0]["company"], "PT Telkom Indonesia")
        self.assertEqual(jobs[0]["url"], "https://maganghub.kemnaker.go.id/lowongan/detail/12345")


if __name__ == "__main__":
    unittest.main()
