import os
import time
import unittest
from unittest.mock import MagicMock, patch

import web_app


class TestShutdownAndWatchdog(unittest.TestCase):
    def setUp(self):
        web_app.app.config["TESTING"] = True
        self.client = web_app.app.test_client()
        self.csrf = web_app.SERVER_CSRF_TOKEN
        # Reset internal watchdog state for tests
        web_app._connected_tabs.clear()
        web_app._is_shutting_down = False
        web_app._last_client_heartbeat = time.time()

    def test_record_heartbeat_and_disconnect(self):
        # 1. Tab 1 mengirim heartbeat
        res1 = web_app.record_heartbeat("tab_1")
        self.assertTrue(res1["success"])
        self.assertEqual(res1["active_tabs"], 1)

        # 2. Tab 2 mengirim heartbeat
        res2 = web_app.record_heartbeat("tab_2")
        self.assertEqual(res2["active_tabs"], 2)

        # 3. Tab 1 ditutup
        res3 = web_app.record_tab_disconnect("tab_1")
        self.assertEqual(res3["active_tabs"], 1)

        # 4. Tab 2 ditutup
        res4 = web_app.record_tab_disconnect("tab_2")
        self.assertEqual(res4["active_tabs"], 0)

    def test_api_system_heartbeat_endpoint(self):
        res = self.client.post(
            "/api/system/heartbeat",
            headers={"X-CSRF-Token": self.csrf},
            json={"tab_id": "test_tab_api"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(data.get("active_tabs"), 1)

    def test_api_system_disconnect_endpoint(self):
        self.client.post(
            "/api/system/heartbeat",
            headers={"X-CSRF-Token": self.csrf},
            json={"tab_id": "test_tab_to_close"},
        )
        res = self.client.post(
            "/api/system/client-disconnect",
            headers={"X-CSRF-Token": self.csrf},
            json={"tab_id": "test_tab_to_close"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

    def test_api_system_status_endpoint(self):
        res = self.client.get("/api/system/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("lifecycle", data)
        self.assertIn("uptime_seconds", data["lifecycle"])
        self.assertIn("active_tabs_count", data["lifecycle"])

    @patch("web_app.load_config")
    def test_should_trigger_auto_shutdown_evaluations(self, mock_load_cfg):
        mock_load_cfg.return_value = {"auto_shutdown_idle_minutes": 5}
        web_app._app_start_time = 1000.0
        web_app._last_client_heartbeat = 1000.0

        # Kasus A: Dalam masa toleransi startup (90 detik pertama) -> TIDAK boleh shutdown
        self.assertFalse(web_app.should_trigger_auto_shutdown(now=1050.0))

        # Kasus B: Melewati masa toleransi tapi baru 1 menit sejak heartbeat -> TIDAK boleh shutdown
        web_app._last_client_heartbeat = 2000.0
        web_app._connected_tabs["tab_active"] = 2000.0
        self.assertFalse(web_app.should_trigger_auto_shutdown(now=2060.0))

        # Kasus C: Tidak ada tab dan sudah idle lebih dari threshold (5 menit = 300s) -> SHUTDOWN
        web_app._connected_tabs.clear()
        web_app._last_client_heartbeat = 2000.0
        self.assertTrue(web_app.should_trigger_auto_shutdown(now=2305.0))

        # Kasus D: Fitur dinonaktifkan (auto_shutdown_idle_minutes = 0) -> TIDAK boleh shutdown
        mock_load_cfg.return_value = {"auto_shutdown_idle_minutes": 0}
        self.assertFalse(web_app.should_trigger_auto_shutdown(now=2500.0))

    @patch("web_app.load_config")
    @patch.object(web_app.browser_session, "is_active", return_value=True)
    def test_should_not_shutdown_while_browser_is_active(self, _mock_active, mock_load_cfg):
        # Saat pengguna sedang membuka browser interaktif, sistem tidak boleh mati otomatis
        mock_load_cfg.return_value = {"auto_shutdown_idle_minutes": 5}
        web_app._app_start_time = 1000.0
        web_app._last_client_heartbeat = 1000.0
        self.assertFalse(web_app.should_trigger_auto_shutdown(now=3000.0))

    @patch("os._exit")
    def test_api_system_shutdown_endpoint(self, mock_exit):
        res = self.client.post(
            "/api/system/shutdown",
            headers={"X-CSRF-Token": self.csrf},
            json={"csrf_token": self.csrf},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("dimatikan secara aman", data.get("message", ""))
        self.assertTrue(web_app._is_shutting_down)

    def test_index_page_contains_shutdown_controls(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("confirmShutdownApp()", html)
        self.assertIn("shutdownModal", html)
        self.assertIn("shutdownOverlay", html)
        self.assertIn("cfgAutoShutdownMinutes", html)


if __name__ == "__main__":
    unittest.main()
