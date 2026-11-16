import os
import tempfile
import unittest
from unittest.mock import MagicMock

from src import browser


class TestBrowserOptimization(unittest.TestCase):
    def setUp(self):
        self.mock_playwright = MagicMock()
        self.mock_chromium = self.mock_playwright.chromium
        self.mock_context = MagicMock()
        self.mock_chromium.launch_persistent_context.return_value = self.mock_context

    def test_browser_args_contains_memory_caps(self):
        # Memastikan batasan V8 heap, cache size, dan limit renderer process aktif
        args = browser.COMMON_BROWSER_ARGS
        self.assertTrue(any("--js-flags=" in a for a in args))
        self.assertTrue(any("--disk-cache-size=" in a for a in args))
        self.assertTrue(any("--renderer-process-limit=" in a for a in args))
        self.assertIn("--mute-audio", args)

    def test_headless_false_omits_disable_gpu(self):
        # Saat mode visual (headless=False), --disable-gpu WAJIB dihilangkan agar GPU laptop
        # merender tampilan secara hardware-accelerated dan tidak membebani CPU 100%
        browser.get_browser_context(self.mock_playwright, headless=False)
        _, kwargs = self.mock_chromium.launch_persistent_context.call_args
        args_passed = kwargs.get("args", [])
        self.assertNotIn("--disable-gpu", args_passed)

    def test_headless_true_includes_disable_gpu(self):
        # Saat mode headless latar belakang, --disable-gpu aktif untuk efisiensi headless
        browser.get_browser_context(self.mock_playwright, headless=True)
        _, kwargs = self.mock_chromium.launch_persistent_context.call_args
        args_passed = kwargs.get("args", [])
        self.assertIn("--disable-gpu", args_passed)

    def test_optimize_page_resources_registers_route(self):
        mock_page = MagicMock()
        browser.optimize_page_resources(mock_page, block_media=True)
        mock_page.route.assert_called_once()
        pattern, route_cb = mock_page.route.call_args[0]
        self.assertEqual(pattern, "**/*")

        # Uji pemblokiran tracker
        mock_route_tracker = MagicMock()
        mock_route_tracker.request.url = "https://www.google-analytics.com/analytics.js"
        mock_route_tracker.request.resource_type = "script"
        route_cb(mock_route_tracker)
        mock_route_tracker.abort.assert_called_once()

        # Uji pemblokiran gambar pada mode scraping (block_media=True)
        mock_route_img = MagicMock()
        mock_route_img.request.url = "https://id.jobstreet.com/static/logo.png"
        mock_route_img.request.resource_type = "image"
        route_cb(mock_route_img)
        mock_route_img.abort.assert_called_once()

        # Uji perizinan dokumen HTML / XHR lowongan
        mock_route_doc = MagicMock()
        mock_route_doc.request.url = "https://id.jobstreet.com/id/job/123456"
        mock_route_doc.request.resource_type = "document"
        route_cb(mock_route_doc)
        mock_route_doc.continue_.assert_called_once()

    def test_cleanup_stale_singleton_locks(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            lock_file = os.path.join(tmp_dir, "SingletonLock")
            with open(lock_file, "w") as f:
                f.write("12345")
            self.assertTrue(os.path.exists(lock_file))

            browser._cleanup_stale_singleton_locks(tmp_dir)
            self.assertFalse(os.path.exists(lock_file))

    def test_user_data_dir_isolation_per_account(self):
        default_dir = browser.get_user_data_dir("default")
        alpha_dir = browser.get_user_data_dir("account_alpha")
        self.assertNotEqual(default_dir, alpha_dir)
        self.assertIn("account_alpha", alpha_dir)


if __name__ == "__main__":
    unittest.main()
