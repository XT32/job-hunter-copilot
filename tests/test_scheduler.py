import unittest
from unittest.mock import MagicMock, patch
import threading

from src.scheduler import AutoHuntScheduler


class DummyHunter:
    def __init__(self, page, cfg):
        self.page = page
        self.cfg = cfg

    def search_jobs(self, keywords=None):
        return [
            {
                "title": "Junior Python Dev",
                "company": "PT Tech Solusi",
                "url": "https://glints.com/jobs/sched-test-1",
                "salary": "Rp 8.000.000",
                "description": "Dibutuhkan staf Python backend.",
                "location": "Jakarta",
            },
            {
                "title": "Admin E-commerce",
                "company": "Toko Cepat",
                "url": "https://glints.com/jobs/sched-test-2",
                "salary": "Rp 5.000.000",
                "description": "Tugas like and subscribe dibayar dan deposit saldo.",
                "location": "Remote",
            },
        ]


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.dummy_hunter_map = {
            "glints": (DummyHunter, "Glints Indonesia")
        }
        self.config = {
            "profile": {
                "target_keywords": ["Python", "Backend"]
            },
            "telegram": {
                "enabled": True,
                "bot_token": "dummy_token",
                "chat_id": "dummy_chat_id"
            }
        }
        self.scheduler = AutoHuntScheduler(
            hunter_map=self.dummy_hunter_map,
            config_loader=lambda: self.config,
            log_callback=MagicMock(),
            playwright_lock=threading.Lock()
        )

    def test_initial_status(self):
        status = self.scheduler.get_status()
        self.assertFalse(status["active"])
        self.assertEqual(status["interval_minutes"], 120)
        self.assertEqual(status["total_discovered"], 0)

    def test_start_and_stop(self):
        started = self.scheduler.start(interval_minutes=60)
        self.assertTrue(started)
        status = self.scheduler.get_status()
        self.assertTrue(status["active"])
        self.assertEqual(status["interval_minutes"], 60)

        # Calling start again while running returns False
        self.assertFalse(self.scheduler.start(interval_minutes=30))

        stopped = self.scheduler.stop()
        self.assertTrue(stopped)
        self.assertFalse(self.scheduler.get_status()["active"])

    @patch("src.scheduler.sync_playwright")
    @patch("src.scheduler.get_browser_context")
    @patch("src.scheduler.send_telegram_alert")
    def test_run_scan_cycle(self, mock_tg_alert, mock_browser_ctx, mock_playwright):
        # Setup mocks for Playwright
        mock_ctx = MagicMock()
        mock_page = MagicMock()
        mock_ctx.new_page.return_value = mock_page
        mock_browser_ctx.return_value = mock_ctx

        p_instance = MagicMock()
        p_instance.__enter__.return_value = p_instance
        mock_playwright.return_value = p_instance

        self.scheduler.running = True
        self.scheduler._run_scan_cycle()

        self.assertEqual(self.scheduler.total_discovered, 2)
        self.assertEqual(mock_tg_alert.call_count, 2)

        # Verify the second job had a scam red flag tag
        calls = mock_tg_alert.call_args_list
        job1_title = calls[0].kwargs.get("title")
        job2_title = calls[1].kwargs.get("title")
        self.assertNotIn("🚨", job1_title)
        self.assertIn("🚨", job2_title)


if __name__ == "__main__":
    unittest.main()
