import unittest
from src.cover_letter import generate_cover_letter, TEMPLATES

class TestCoverLetter(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "applicant_name": "Budi Pratama",
            "field_or_major": "Akuntansi",
            "target_keywords": ["Staff Akuntansi", "Pajak", "Finance"],
            "contact_info": "+62 812-3456-7890"
        }

    def test_generate_formal_cover_letter(self):
        letter = generate_cover_letter("Staff Pajak", "PT Mandiri Sukses", self.profile, preset="formal")
        self.assertIn("Budi Pratama", letter)
        self.assertIn("PT Mandiri Sukses", letter)
        self.assertIn("Staff Pajak", letter)
        self.assertIn("Akuntansi", letter)

    def test_generate_magang_cover_letter(self):
        letter = generate_cover_letter("Intern Finance", "Kementerian BUMN", self.profile, preset="magang")
        self.assertIn("Program Pemagangan", letter)
        self.assertIn("Kementerian BUMN", letter)

    def test_generate_english_formal_cover_letter(self):
        letter = generate_cover_letter("Software Engineer", "Google Inc", self.profile, preset="english_formal")
        self.assertIn("Dear Hiring Team at Google Inc", letter)
        self.assertIn("Software Engineer", letter)
        self.assertIn("Budi Pratama", letter)

    def test_generate_english_fresh_grad_cover_letter(self):
        letter = generate_cover_letter("Junior DevOps", "Tokopedia", self.profile, preset="english_fresh_grad")
        self.assertIn("Dear Hiring Manager at Tokopedia", letter)
        self.assertIn("Junior DevOps", letter)
        self.assertIn("Budi Pratama", letter)

    def test_generate_english_internship_cover_letter(self):
        letter = generate_cover_letter("Data Intern", "Traveloka", self.profile, preset="english_internship")
        self.assertIn("Dear Internship Coordinator at Traveloka", letter)
        self.assertIn("Data Intern", letter)
        self.assertIn("Budi Pratama", letter)

if __name__ == "__main__":
    unittest.main()
