import unittest
from src.email_sender import send_cold_email


class TestEmailSender(unittest.TestCase):
    def test_missing_credentials_returns_error(self):
        res = send_cold_email(
            to_email="hrd@example.com",
            subject="Lamaran Kerja",
            body="Halo HRD",
            smtp_config={"email": "", "password": ""},
        )
        self.assertFalse(res["success"])
        self.assertIn("belum disetel", res["message"])

    def test_missing_attachment_file_handled(self):
        res = send_cold_email(
            to_email="hrd@example.com",
            subject="Lamaran Kerja",
            body="Halo HRD",
            attachment_path="attachments/non_existent_cv_12345.pdf",
            smtp_config={"email": "test@gmail.com", "password": "pass"},
        )
        # Should attempt connection (which fails without real SMTP credentials) without crashing on file read
        self.assertFalse(res["success"])


if __name__ == "__main__":
    unittest.main()
