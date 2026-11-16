import unittest
from unittest.mock import patch, MagicMock
import urllib.error
import io

from src.notifier import send_telegram_alert, test_telegram_connection

class TestNotifier(unittest.TestCase):
    def test_send_alert_missing_credentials(self):
        # Tanpa bot_token atau chat_id, harus return False tanpa error
        self.assertFalse(send_telegram_alert("Backend Dev", "PT Tech", "https://example.com"))
        self.assertFalse(send_telegram_alert("Backend Dev", "PT Tech", "https://example.com", bot_token="token_only"))
        self.assertFalse(send_telegram_alert("Backend Dev", "PT Tech", "https://example.com", chat_id="chat_only"))

    @patch("urllib.request.urlopen")
    def test_send_alert_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        success = send_telegram_alert(
            title="Junior Python Dev",
            company="PT Solusi Digital",
            url="https://glints.com/job/123",
            platform="Glints",
            salary="Rp 8.000.000",
            bot_token="dummy_token_123",
            chat_id="dummy_chat_456"
        )
        self.assertTrue(success)
        mock_urlopen.assert_called_once()

    def test_test_connection_empty_params(self):
        res = test_telegram_connection("", "")
        self.assertFalse(res["success"])
        self.assertIn("wajib diisi", res["message"])

    @patch("urllib.request.urlopen")
    def test_test_connection_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        res = test_telegram_connection(bot_token="123456:ABC", chat_id="987654321")
        self.assertTrue(res["success"])
        self.assertIn("berhasil dikirim", res["message"])

    @patch("urllib.request.urlopen")
    def test_test_connection_unauthorized(self, mock_urlopen):
        err = urllib.error.HTTPError(
            url="https://api.telegram.org",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(b'{"ok":false,"error_code":401,"description":"Unauthorized"}')
        )
        mock_urlopen.side_effect = err

        res = test_telegram_connection(bot_token="invalid_token", chat_id="12345")
        self.assertFalse(res["success"])
        self.assertIn("tidak valid", res["message"])

if __name__ == "__main__":
    unittest.main()
