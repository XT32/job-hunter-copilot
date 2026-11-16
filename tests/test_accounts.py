import copy
import os
import tempfile
import unittest
from unittest.mock import patch

from src import accounts, browser, config
from web_app import app, SERVER_CSRF_TOKEN


class TestMultiAccounts(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_cfg_path = os.path.join(self.temp_dir.name, "test_config.json")
        self.app = app
        self.client = app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ensure_accounts_initialized_creates_default(self):
        cfg = {"profile": {"field_or_major": "Teknik Informatika", "target_keywords": ["Backend"]}}
        initialized = accounts.ensure_accounts_initialized(cfg)
        self.assertIn("accounts", initialized)
        self.assertEqual(len(initialized["accounts"]), 1)
        self.assertEqual(initialized["active_account_id"], "default")
        self.assertEqual(initialized["accounts"][0]["name"], "Akun Utama")
        self.assertEqual(initialized["accounts"][0]["profile"]["field_or_major"], "Teknik Informatika")

    def test_create_and_switch_account(self):
        cfg = copy.deepcopy(config.DEFAULT_CONFIG)
        accounts.ensure_accounts_initialized(cfg)

        # Buat akun kedua
        new_acc, cfg = accounts.create_account(
            cfg,
            name="Akun Marketing",
            clone_current=False,
            field_or_major="Digital Marketing",
            target_keywords=["SEO", "Content Writer"],
            active_cv="CV_Marketing.pdf",
        )
        self.assertEqual(len(cfg["accounts"]), 2)
        self.assertEqual(new_acc["name"], "Akun Marketing")
        self.assertEqual(new_acc["profile"]["field_or_major"], "Digital Marketing")

        # Beralih ke akun kedua
        switched, cfg = accounts.switch_account(cfg, new_acc["id"])
        self.assertEqual(cfg["active_account_id"], new_acc["id"])
        self.assertEqual(cfg["profile"]["field_or_major"], "Digital Marketing")
        self.assertEqual(cfg["active_cv"], "CV_Marketing.pdf")

        # Beralih kembali ke Akun Utama
        switched_back, cfg = accounts.switch_account(cfg, "default")
        self.assertEqual(cfg["active_account_id"], "default")
        self.assertEqual(cfg["profile"]["field_or_major"], "Akuntansi")

    def test_delete_account(self):
        cfg = copy.deepcopy(config.DEFAULT_CONFIG)
        accounts.ensure_accounts_initialized(cfg)

        # Tidak bisa hapus jika hanya 1 akun
        with self.assertRaises(ValueError):
            accounts.delete_account(cfg, "default")

        # Buat akun kedua
        new_acc, cfg = accounts.create_account(cfg, name="Akun Magang")
        self.assertEqual(len(cfg["accounts"]), 2)

        # Hapus akun kedua
        deleted, cfg = accounts.delete_account(cfg, new_acc["id"])
        self.assertEqual(deleted["name"], "Akun Magang")
        self.assertEqual(len(cfg["accounts"]), 1)

    def test_browser_profile_directory_isolation(self):
        default_dir = browser.get_user_data_dir("default")
        custom_dir = browser.get_user_data_dir("acc_test_123")
        self.assertNotEqual(default_dir, custom_dir)
        self.assertTrue(custom_dir.endswith(os.path.join("profiles", "acc_test_123")))

    def test_api_accounts_endpoints(self):
        # 1. GET /api/accounts
        res = self.client.get("/api/accounts")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("active_account_id", data)
        self.assertTrue(len(data["accounts"]) >= 1)

        # 2. POST /api/accounts/create
        headers = {"X-CSRF-Token": SERVER_CSRF_TOKEN}
        res_create = self.client.post(
            "/api/accounts/create",
            json={
                "name": "Akun Desain Grafis",
                "field_or_major": "Desain Komunikasi Visual",
                "target_keywords": ["Graphic Designer", "UI UX"],
                "switch_now": True,
            },
            headers=headers,
        )
        self.assertEqual(res_create.status_code, 200)
        create_data = res_create.get_json()
        self.assertTrue(create_data["success"])
        created_id = create_data["account"]["id"]
        self.assertEqual(create_data["active_account_id"], created_id)

        # 3. POST /api/accounts/switch back to default
        res_switch = self.client.post(
            "/api/accounts/switch",
            json={"account_id": "default"},
            headers=headers,
        )
        self.assertEqual(res_switch.status_code, 200)
        self.assertEqual(res_switch.get_json()["active_account_id"], "default")

        # 4. POST /api/accounts/delete
        res_del = self.client.post(
            "/api/accounts/delete",
            json={"account_id": created_id},
            headers=headers,
        )
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
