import unittest
import os
import tempfile
from src import config

class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.temp_dir.name, "test_config.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_config_creation(self):
        cfg = config.load_config(self.test_file)
        self.assertIn("profile", cfg)
        self.assertIn("target_keywords", cfg["profile"])
        self.assertTrue(os.path.exists(self.test_file))

    def test_save_and_reload_config(self):
        cfg = config.load_config(self.test_file)
        cfg["profile"]["field_or_major"] = "Desain Komunikasi Visual"
        config.save_config(cfg, self.test_file)

        reloaded = config.load_config(self.test_file)
        self.assertEqual(reloaded["profile"]["field_or_major"], "Desain Komunikasi Visual")

if __name__ == "__main__":
    unittest.main()
