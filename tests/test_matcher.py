import unittest
from src.matcher import JobMatcher

class TestJobMatcher(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "field_or_major": "Akuntansi",
            "target_keywords": ["Akuntansi", "Finance", "Staff Pajak"],
            "experience_level": "fresh_graduate",
            "blacklist_keywords": ["SPG", "Sales Lapangan", "Canvasser", "Asuransi"],
            "preferred_locations": ["Jakarta", "Remote"]
        }
        self.matcher = JobMatcher(self.profile)

    def test_match_valid_junior_job(self):
        title = "Staff Akuntansi & Perpajakan"
        company = "PT Maju Terus"
        is_match, reason = self.matcher.evaluate(title, company, location="Jakarta")
        self.assertTrue(is_match)
        self.assertEqual(reason, "Sesuai profil")

    def test_block_blacklist_keyword(self):
        title = "Staff Akuntansi dan SPG Promosi"
        company = "PT Retail Sukses"
        is_match, reason = self.matcher.evaluate(title, company, location="Jakarta")
        self.assertFalse(is_match)
        self.assertIn("blacklist", reason.lower())

    def test_block_senior_for_fresh_graduate(self):
        title = "Head of Finance and Accounting"
        company = "PT Finance Corp"
        is_match, reason = self.matcher.evaluate(title, company, location="Jakarta")
        self.assertFalse(is_match)
        self.assertIn("level terlalu tinggi", reason.lower())

    def test_block_unrelated_job(self):
        title = "Guru Olahraga SMP"
        company = "Yayasan Sekolah"
        is_match, reason = self.matcher.evaluate(title, company, location="Jakarta")
        self.assertFalse(is_match)
        self.assertIn("tidak cocok", reason.lower())

    def test_location_filter(self):
        title = "Staff Finance"
        company = "PT Sukses"
        is_match, reason = self.matcher.evaluate(title, company, location="Papua")
        self.assertFalse(is_match)
        self.assertIn("lokasi tidak sesuai", reason.lower())

    def test_short_keyword_word_boundary(self):
        it_matcher = JobMatcher({"target_keywords": ["IT"], "experience_level": "all"})
        # "Quality" mengandung substring "it", tapi bukan kata "IT"
        is_match_qa, _ = it_matcher.evaluate("Quality Assurance", "PT Indo")
        self.assertFalse(is_match_qa)

        # "IT Support" mengandung kata utuh "IT"
        is_match_it, _ = it_matcher.evaluate("IT Support Specialist", "PT Indo")
        self.assertTrue(is_match_it)

    def test_lead_generation_exception_for_junior(self):
        marketing_matcher = JobMatcher({
            "target_keywords": ["Lead Generation", "Marketing"],
            "experience_level": "fresh_graduate"
        })
        # Lead Generation Officer tidak boleh diblokir oleh trigger 'lead'
        is_match, reason = marketing_matcher.evaluate("Lead Generation Officer", "PT Startup")
        self.assertTrue(is_match)
        self.assertEqual(reason, "Sesuai profil")

        # Tech Lead tetap harus diblokir untuk fresh graduate
        is_match_tech, reason_tech = marketing_matcher.evaluate("Tech Lead Marketing", "PT Startup")
        self.assertFalse(is_match_tech)
        self.assertIn("level terlalu tinggi", reason_tech.lower())

if __name__ == "__main__":
    unittest.main()
