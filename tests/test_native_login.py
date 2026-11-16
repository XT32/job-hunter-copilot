import os
import unittest
from unittest.mock import MagicMock, patch

import src.browser as browser_mod
import web_app


class TestNativeLoginBypass(unittest.TestCase):
    def setUp(self):
        web_app.app.config["TESTING"] = True
        self.client = web_app.app.test_client()
        self.csrf = web_app.SERVER_CSRF_TOKEN

    @patch("os.path.isfile", return_value=True)
    @patch("shutil.which")
    def test_find_system_browser_executable_linux(self, mock_which, mock_isfile):
        # Simulasi jika google-chrome terinstall di PATH (Linux / POSIX)
        mock_which.side_effect = lambda cmd: "/usr/bin/google-chrome" if cmd == "google-chrome" else None
        exe, name = browser_mod.find_system_browser_executable()
        self.assertEqual(exe, "/usr/bin/google-chrome")
        self.assertEqual(name, "Google Chrome")

    @patch("shutil.which", return_value=None)
    @patch("os.name", "nt")
    @patch("os.path.isfile")
    def test_find_system_browser_executable_windows(self, mock_isfile, mock_which):
        # Simulasi jika msedge.exe terinstall di Program Files Windows
        mock_isfile.side_effect = lambda p: "msedge.exe" in p
        exe, name = browser_mod.find_system_browser_executable()
        self.assertTrue(exe.endswith("msedge.exe"))
        self.assertEqual(name, "Microsoft Edge")

    @patch("shutil.which", return_value=None)
    @patch("os.name", "posix")
    @patch("os.path.isfile", return_value=False)
    def test_find_system_browser_executable_none(self, mock_isfile, mock_which):
        exe, name = browser_mod.find_system_browser_executable()
        self.assertEqual(exe, "")
        self.assertEqual(name, "")

    @patch("subprocess.Popen")
    @patch("src.browser.find_system_browser_executable", return_value=("/usr/bin/google-chrome", "Google Chrome"))
    def test_launch_native_login_browser_with_executable(self, mock_find, mock_popen):
        res = browser_mod.launch_native_login_browser(
            target_url="https://id.jobstreet.com/login",
            account_id="default"
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["browser_name"], "Google Chrome")
        mock_popen.assert_called_once()
        cmd_args = mock_popen.call_args[0][0]
        self.assertEqual(cmd_args[0], "/usr/bin/google-chrome")
        self.assertTrue(any("--user-data-dir=" in arg for arg in cmd_args))
        self.assertEqual(cmd_args[-1], "https://id.jobstreet.com/login")

    @patch("src.browser.find_system_browser_executable", return_value=("", ""))
    def test_launch_native_login_browser_not_found(self, mock_find):
        res = browser_mod.launch_native_login_browser(
            target_url="https://glints.com/id/login",
            account_id="default"
        )
        self.assertFalse(res["success"])
        self.assertIn("Tidak ditemukan", res["error"])

    def test_api_native_login_without_csrf_forbidden(self):
        res = self.client.post("/api/browser/native-login", json={"platform": "jobstreet"})
        self.assertEqual(res.status_code, 403)

    @patch("src.browser.launch_native_login_browser")
    def test_api_native_login_endpoint_success(self, mock_launch):
        mock_launch.return_value = {
            "success": True,
            "browser_name": "Google Chrome",
            "url": "https://glints.com/id",
            "message": "Browser Google Chrome resmi berhasil dibuka."
        }
        res = self.client.post(
            "/api/browser/native-login",
            headers={"X-CSRF-Token": self.csrf},
            json={"platform": "glints"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("Google Chrome", data.get("message", ""))
        mock_launch.assert_called_once()
        call_args = mock_launch.call_args[0]
        self.assertIn("glints.com", call_args[0])

    def test_templates_index_contains_native_google_login_elements(self):
        index_path = os.path.join(os.path.dirname(__file__), "..", "templates", "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("openLoginChoiceModal", content)
        self.assertIn("openNativeGoogleLogin", content)
        self.assertIn("loginChoiceModal", content)
        self.assertIn("loginModalPlatformSelect", content)
        self.assertIn("submitNativeLoginFromModal", content)
        self.assertIn("submitStandardLoginFromModal", content)

    def test_static_js_contains_modal_and_native_login_functions(self):
        js_path = os.path.join(os.path.dirname(__file__), "..", "static", "js", "app.js")
        with open(js_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("function openLoginChoiceModal()", content)
        self.assertIn("function closeLoginChoiceModal()", content)
        self.assertIn("async function openNativeGoogleLogin(", content)
        self.assertIn("function submitNativeLoginFromModal()", content)
        self.assertIn("function submitStandardLoginFromModal()", content)
        self.assertIn("/api/browser/native-login", content)


if __name__ == "__main__":
    unittest.main()
