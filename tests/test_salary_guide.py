import unittest
from src.salary_guide import get_umr_by_location, suggest_salary_range, evaluate_candidate_salary

class TestSalaryGuide(unittest.TestCase):
    def test_get_umr_jakarta(self):
        umr = get_umr_by_location("Jakarta Selatan")
        self.assertEqual(umr, 5067381)

    def test_get_umr_karawang(self):
        umr = get_umr_by_location("Karawang Barat")
        self.assertEqual(umr, 5257834)

    def test_get_umr_lampung_and_jayapura(self):
        umr_lpg = get_umr_by_location("Bandar Lampung")
        self.assertEqual(umr_lpg, 3103631)
        umr_jyp = get_umr_by_location("Jayapura")
        self.assertEqual(umr_jyp, 4024270)

    def test_get_umr_unknown_fallback(self):
        umr = get_umr_by_location("Kota Antah Berantah")
        self.assertEqual(umr, 3500000)

    def test_suggest_salary_fresh_graduate(self):
        sugg = suggest_salary_range("Jakarta", "fresh_graduate")
        self.assertGreaterEqual(sugg["recommended_min"], 5000000)
        self.assertGreaterEqual(sugg["recommended_max"], sugg["recommended_min"])
        self.assertIn("Rp", sugg["formatted_range"])

    def test_evaluate_under_umr(self):
        eval_res = evaluate_candidate_salary(2500000, "Jakarta")
        self.assertEqual(eval_res["status"], "under_umr")

    def test_evaluate_healthy(self):
        eval_res = evaluate_candidate_salary(5500000, "Jakarta")
        self.assertEqual(eval_res["status"], "healthy")

if __name__ == "__main__":
    unittest.main()
