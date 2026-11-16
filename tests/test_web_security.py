import json
import unittest

try:
    from web_app import app, SERVER_CSRF_TOKEN
    HAS_WEB_DEPS = True
except ImportError:
    HAS_WEB_DEPS = False
    app = None
    SERVER_CSRF_TOKEN = ""


@unittest.skipUnless(HAS_WEB_DEPS, "Flask is not installed in the testing environment")
class TestWebSecurityAndEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = app.test_client()

    def test_index_page_includes_csrf_meta(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(f'<meta name="csrf-token" content="{SERVER_CSRF_TOKEN}">', resp.get_data(as_text=True))

    def test_post_without_csrf_is_forbidden(self):
        resp = self.client.post("/api/scan", json={"platform": "glints"})
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("CSRF", data.get("error", ""))

    def test_post_with_invalid_csrf_is_forbidden(self):
        resp = self.client.post(
            "/api/scan",
            json={"platform": "glints"},
            headers={"X-CSRF-Token": "invalid_token_12345"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_post_with_malicious_origin_is_forbidden(self):
        resp = self.client.post(
            "/api/qa/save",
            json={"keyword": "test", "answer": "test"},
            headers={
                "X-CSRF-Token": SERVER_CSRF_TOKEN,
                "Origin": "http://malicious-site.com",
            },
        )
        self.assertEqual(resp.status_code, 403)

    def test_rate_limits_endpoint(self):
        resp = self.client.get("/api/rate-limits")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("quotas", data)
        self.assertIn("jobstreet", data["quotas"])

    def test_qa_bank_save_and_delete(self):
        # 1. Save QA
        resp = self.client.post(
            "/api/qa/save",
            json={"keyword": "sim a", "question": "Apakah memiliki SIM A?", "answer": "Ya, aktif"},
            headers={"X-CSRF-Token": SERVER_CSRF_TOKEN},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))

        # 2. List QA
        resp_list = self.client.get("/api/qa")
        self.assertEqual(resp_list.status_code, 200)
        qas = resp_list.get_json().get("custom_qa", [])
        saved = [q for q in qas if q.get("keyword") == "sim a"]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["answer"], "Ya, aktif")

        # 3. Delete QA
        resp_del = self.client.post(
            "/api/qa/delete",
            json={"keyword": "sim a"},
            headers={"X-CSRF-Token": SERVER_CSRF_TOKEN},
        )
        self.assertEqual(resp_del.status_code, 200)

    def test_telegram_test_endpoint(self):
        # Menguji endpoint test-telegram dengan token kosong
        resp = self.client.post(
            "/api/test-telegram",
            json={"bot_token": "", "chat_id": ""},
            headers={"X-CSRF-Token": SERVER_CSRF_TOKEN},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("wajib diisi", data.get("message"))

    def test_post_with_local_domain_origin_is_allowed(self):
        resp = self.client.post(
            "/api/qa/save",
            json={"keyword": "localtest", "answer": "ok"},
            headers={
                "X-CSRF-Token": SERVER_CSRF_TOKEN,
                "Origin": "https://xt32.local",
                "Host": "xt32.local",
            },
        )
        self.assertEqual(resp.status_code, 200)

        # Cleanup
        self.client.post(
            "/api/qa/delete",
            json={"keyword": "localtest"},
            headers={"X-CSRF-Token": SERVER_CSRF_TOKEN},
        )

    def test_job_update_notes_and_delete_endpoints(self):
        # 1. Record a manual job first
        test_url = "https://id.jobstreet.com/job/test-endpoint-notes"
        resp_rec = self.client.post(
            "/api/record-manual",
            json={"url": test_url, "title": "QA Engineer", "company": "PT Tech", "status": "applied", "notes": "Initial"},
            headers={"X-CSRF-Token": SERVER_CSRF_TOKEN},
        )
        self.assertEqual(resp_rec.status_code, 200)

        # 2. Update notes
        resp_notes = self.client.post(
            "/api/job/update-notes",
            json={"url": test_url, "notes": "Interview via Google Meet jam 14:00"},
            headers={"X-CSRF-Token": SERVER_CSRF_TOKEN},
        )
        self.assertEqual(resp_notes.status_code, 200)
        self.assertTrue(resp_notes.get_json().get("success"))

        # 3. Delete job
        resp_del = self.client.post(
            "/api/job/delete",
            json={"url": test_url},
            headers={"X-CSRF-Token": SERVER_CSRF_TOKEN},
        )
        self.assertEqual(resp_del.status_code, 200)
        self.assertTrue(resp_del.get_json().get("success"))


if __name__ == "__main__":
    unittest.main()
