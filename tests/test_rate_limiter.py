import os
import tempfile
import time
import unittest
from src.rate_limiter import SafeRateLimiter


class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.quota_file = os.path.join(self.tmp_dir, "test_quota.json")
        self.limiter = SafeRateLimiter(quota_file=self.quota_file)
        # Custom limits for testing
        self.limiter.limits = {
            "jobstreet": {"max_per_hour": 3, "max_per_day": 5},
            "glints": {"max_per_hour": 2, "max_per_day": 2},
        }

    def tearDown(self):
        if os.path.exists(self.quota_file):
            try:
                os.remove(self.quota_file)
            except Exception:
                pass
        try:
            os.rmdir(self.tmp_dir)
        except Exception:
            pass

    def test_quota_allows_initially(self):
        allowed, msg, stats = self.limiter.check_quota("jobstreet")
        self.assertTrue(allowed)
        self.assertEqual(stats["hour_count"], 0)
        self.assertEqual(stats["day_count"], 0)

    def test_quota_blocks_when_hourly_limit_exceeded(self):
        for _ in range(3):
            self.limiter.record_application("jobstreet")

        allowed, msg, stats = self.limiter.check_quota("jobstreet")
        self.assertFalse(allowed)
        self.assertIn("per jam", msg)
        self.assertEqual(stats["hour_count"], 3)

    def test_quota_blocks_when_daily_limit_exceeded(self):
        # Glints limit is max 2 per day
        self.limiter.record_application("glints")
        self.limiter.record_application("glints")

        allowed, msg, stats = self.limiter.check_quota("glints")
        self.assertFalse(allowed)
        self.assertIn("harian", msg)

    def test_get_all_quotas_summary(self):
        self.limiter.record_application("jobstreet")
        summary = self.limiter.get_all_quotas()
        self.assertIn("jobstreet", summary)
        self.assertEqual(summary["jobstreet"]["hour_count"], 1)
        self.assertEqual(summary["jobstreet"]["day_count"], 1)

    def test_quota_per_account_isolation(self):
        # Akun A melebihi kuota harian Glints (2x)
        self.limiter.record_application("glints", account_id="user_alpha")
        self.limiter.record_application("glints", account_id="user_alpha")

        allowed_a, _, _ = self.limiter.check_quota("glints", account_id="user_alpha")
        self.assertFalse(allowed_a)

        # Akun B harus tetap memiliki kuota penuh
        allowed_b, _, stats_b = self.limiter.check_quota("glints", account_id="user_beta")
        self.assertTrue(allowed_b)
        self.assertEqual(stats_b["day_count"], 0)


if __name__ == "__main__":
    unittest.main()
