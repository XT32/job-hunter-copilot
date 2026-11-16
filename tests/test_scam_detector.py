import unittest
from src.scam_detector import check_for_red_flags

class TestScamDetector(unittest.TestCase):
    def test_clean_job_is_safe(self):
        res = check_for_red_flags(
            title="Junior Backend Developer",
            company="PT Teknologi Digital Indonesia",
            description="Kandidat menguasai Python, Flask, dan PostgreSQL. Gaji kompetitif.",
            location="Jakarta Selatan"
        )
        self.assertFalse(res["is_red_flag"])
        self.assertEqual(res["risk_level"], "safe")
        self.assertEqual(len(res["flags"]), 0)

    def test_detect_tahan_ijazah(self):
        res = check_for_red_flags(
            title="Admin Gudang",
            company="PT Logistik Jaya",
            description="Syarat: Usia maks 25 tahun, bersedia penahanan ijazah asli selama masa kontrak.",
            location="Tangerang"
        )
        self.assertTrue(res["is_red_flag"])
        self.assertEqual(res["risk_level"], "danger")
        self.assertTrue(any("Tahan Ijazah" in f for f in res["flags"]))

    def test_detect_biaya_seragam_scam(self):
        res = check_for_red_flags(
            title="Staff Operasional",
            company="PT Mandiri Perkasa Sejahtera",
            description="Pelamar wajib membayar uang seragam sebesar Rp 150.000 saat interview.",
            location="Jakarta Pusat"
        )
        self.assertTrue(res["is_red_flag"])
        self.assertEqual(res["risk_level"], "danger")
        self.assertTrue(any("Permintaan Uang" in f for f in res["flags"]))

    def test_detect_pialang_berjangka(self):
        res = check_for_red_flags(
            title="Management Trainee",
            company="PT Solid Gold Berjangka",
            description="Belajar mengelola portofolio nasabah dan commodity futures.",
            location="Surabaya"
        )
        self.assertTrue(res["is_red_flag"])
        self.assertTrue(any("Pialang Berjangka" in f for f in res["flags"]))

    def test_detect_iming_iming_langsung_kerja(self):
        res = check_for_red_flags(
            title="Data Entry Operator",
            company="Global Express",
            description="Langsung kerja tanpa tes! Penghasilan 2 juta per hari hanya bermodal HP.",
            location="Jakarta"
        )
        self.assertTrue(res["is_red_flag"])
        self.assertEqual(res["risk_level"], "danger")
        self.assertTrue(any("Iming-iming" in f for f in res["flags"]))

    def test_detect_apk_scam(self):
        res = check_for_red_flags(
            title="Customer Service",
            company="PT Citra Abadi",
            description="Silakan unduh surat_undangan.apk untuk jadwal dan lokasi interview.",
            location="Bekasi"
        )
        self.assertTrue(res["is_red_flag"])
        self.assertEqual(res["risk_level"], "danger")
        self.assertTrue(any("APK" in f for f in res["flags"]))

    def test_detect_deposit_task_scam(self):
        res = check_for_red_flags(
            title="Freelance Task Assistant",
            company="Online Mart",
            description="Kandidat wajib melakukan top up saldo awal untuk menyelesaikan tugas pesanan.",
            location="Remote"
        )
        self.assertTrue(res["is_red_flag"])
        self.assertEqual(res["risk_level"], "danger")
        self.assertTrue(any("Deposit" in f for f in res["flags"]))

    def test_detect_fake_travel_reimbursement_scam(self):
        res = check_for_red_flags(
            title="Staff Administrasi BUMN",
            company="Rekrutmen Nasional",
            description="Peserta wajib memesan akomodasi lewat agen perjalanan yang ditunjuk, biaya akomodasi akan diganti saat tes.",
            location="Surabaya"
        )
        self.assertTrue(res["is_red_flag"])
        self.assertEqual(res["risk_level"], "danger")
        self.assertTrue(any("Permintaan Uang" in f for f in res["flags"]))

if __name__ == "__main__":
    unittest.main()
