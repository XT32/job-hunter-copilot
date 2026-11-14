import time

class ScreeningAutoFiller:
    def __init__(self, page, defaults=None):
        self.page = page
        self.defaults = defaults or {
            "expected_salary": "6000000",
            "notice_period": "Immediately",
            "years_of_experience": "1",
            "willing_to_wfo": True,
            "willing_to_relocate": True,
            "domicile": "Jakarta"
        }

    def auto_fill_form(self) -> int:
        """Mendeteksi dan mengisi otomatis pertanyaan screening umum di modal popup"""
        filled_count = 0
        try:
            # 1. Gaji / Ekspektasi Gaji
            salary_inputs = self.page.locator("input[placeholder*='gaji' i], input[placeholder*='salary' i], input[name*='salary' i], input[name*='gaji' i], input[aria-label*='gaji' i]").all()
            for inp in salary_inputs:
                if inp.is_visible() and not inp.input_value():
                    inp.fill(str(self.defaults.get("expected_salary", "6000000")))
                    filled_count += 1

            # 2. Pengalaman (Tahun)
            exp_inputs = self.page.locator("input[placeholder*='pengalaman' i], input[placeholder*='experience' i], input[name*='year' i]").all()
            for inp in exp_inputs:
                if inp.is_visible() and not inp.input_value():
                    inp.fill(str(self.defaults.get("years_of_experience", "1")))
                    filled_count += 1

            # 3. Domisili / Lokasi
            dom_inputs = self.page.locator("input[placeholder*='domisili' i], input[placeholder*='kota' i], input[placeholder*='lokasi' i]").all()
            for inp in dom_inputs:
                if inp.is_visible() and not inp.input_value():
                    inp.fill(str(self.defaults.get("domicile", "Jakarta")))
                    filled_count += 1

            # 4. Radio/Pilihan Persetujuan (WFO / Kesediaan Bekerja)
            if self.defaults.get("willing_to_wfo", True):
                yes_options = self.page.locator("label:has-text('Ya'), label:has-text('Yes'), input[value*='yes' i], input[value*='ya' i]").all()
                for opt in yes_options:
                    try:
                        if opt.is_visible() and not opt.is_checked():
                            opt.click()
                            filled_count += 1
                    except Exception:
                        pass

        except Exception as e:
            print(f"[!] Info auto-fill screening: {e}")

        return filled_count
