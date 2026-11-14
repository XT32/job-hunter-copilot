import unittest
from unittest.mock import MagicMock
from src.screener import ScreeningAutoFiller

class TestScreeningAutoFiller(unittest.TestCase):
    def setUp(self):
        self.mock_page = MagicMock()
        self.defaults = {
            "expected_salary": "7500000",
            "notice_period": "1 Bulan",
            "years_of_experience": "2",
            "domicile": "Surabaya",
            "willing_to_wfo": True
        }
        self.screener = ScreeningAutoFiller(self.mock_page, self.defaults)

    def test_screener_defaults(self):
        self.assertEqual(self.screener.defaults["expected_salary"], "7500000")
        self.assertEqual(self.screener.defaults["domicile"], "Surabaya")

    def test_auto_fill_form_execution(self):
        mock_input = MagicMock()
        mock_input.is_visible.return_value = True
        mock_input.input_value.return_value = ""

        self.mock_page.locator.return_value.all.return_value = [mock_input]
        count = self.screener.auto_fill_form()
        self.assertGreater(count, 0)
        mock_input.fill.assert_called()

if __name__ == "__main__":
    unittest.main()
