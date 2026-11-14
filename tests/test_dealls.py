import unittest
from unittest.mock import MagicMock
from src.dealls import DeallsHunter

class TestDeallsHunter(unittest.TestCase):
    def setUp(self):
        self.config = {
            "profile": {
                "field_or_major": "Teknik Informatika",
                "target_keywords": ["Backend Developer"],
                "experience_level": "junior",
                "blacklist_keywords": ["Senior", "Manager"]
            },
            "auto_skip_already_seen": True
        }
        self.mock_page = MagicMock()
        self.hunter = DeallsHunter(self.mock_page, self.config)

    def test_dealls_initialization(self):
        self.assertIsNotNone(self.hunter.matcher)

    def test_dealls_search_url_encoding(self):
        self.mock_page.locator.return_value.all.return_value = []
        self.mock_page.locator.return_value.first.is_visible.return_value = False

        self.hunter.search_jobs(["Frontend Developer"])
        call_args = self.mock_page.goto.call_args[0][0]
        self.assertIn("dealls.com/jobs?q=Frontend%20Developer", call_args)

if __name__ == "__main__":
    unittest.main()
