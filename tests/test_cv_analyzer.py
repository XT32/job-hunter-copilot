import unittest
from src.cv_analyzer import get_keywords, calculate_ats_match

class TestCVAnalyzer(unittest.TestCase):
    def test_get_keywords(self):
        text = "Saya memiliki keahlian dalam Python, Flask, SQL, dan akuntansi keuangan"
        keywords = get_keywords(text)
        self.assertIn("python", keywords)
        self.assertIn("flask", keywords)
        self.assertIn("akuntansi", keywords)
        # Pastikan stopword terbuang
        self.assertNotIn("dan", keywords)
        self.assertNotIn("dalam", keywords)

    def test_calculate_ats_match_high(self):
        cv_text = "Proficient in Python, SQL, REST API, Git, Docker, Linux, and backend development"
        job_title = "Backend Python Developer"
        job_desc = "Requirements: Python, SQL, REST API, Git"

        match = calculate_ats_match(cv_text, job_title, job_desc)
        self.assertGreaterEqual(match["score"], 70)
        self.assertIn("python", match["matched"])

    def test_get_keywords_short_and_special_tokens(self):
        text = "Mencari UI/UX Designer dan QA Engineer dengan keahlian Go, AI, C++, dan JS"
        keywords = get_keywords(text)
        self.assertIn("ui", keywords)
        self.assertIn("ux", keywords)
        self.assertIn("qa", keywords)
        self.assertIn("go", keywords)
        self.assertIn("ai", keywords)
        self.assertIn("c++", keywords)
        self.assertIn("js", keywords)
        self.assertIn("designer", keywords)
        self.assertIn("engineer", keywords)
        # Stopword 2 huruf bahasa Indonesia/Inggris tidak boleh masuk
        self.assertNotIn("di", keywords)
        self.assertNotIn("dan", keywords)

    def test_calculate_ats_match_empty_cv(self):
        match = calculate_ats_match("", "Python Developer", "Requirements: Python")
        self.assertEqual(match["status"], "CV belum diunggah")

if __name__ == "__main__":
    unittest.main()
