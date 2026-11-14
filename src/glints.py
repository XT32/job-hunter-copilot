import time
from urllib.parse import quote
from src.base_hunter import BaseJobHunter
from src.browser import human_delay
from src.storage import is_job_recorded, record_job
from src.matcher import JobMatcher
from src.screener import ScreeningAutoFiller
from src.cover_letter import generate_cover_letter


class GlintsHunter(BaseJobHunter):
    def __init__(self, page, config):
        super().__init__(page, config)
        self.matcher = JobMatcher(config.get("profile", {}))
        self.screener = ScreeningAutoFiller(page, config.get("screening_defaults", {}))

    def check_login_status(self) -> bool:
        """Memeriksa apakah user sudah login ke Glints."""
        try:
            if self._is_login_redirect():
                return False
            login_btn = self.page.locator("a:has-text('Masuk'), button:has-text('Masuk'), a:has-text('Sign In')").first
            if login_btn.is_visible(timeout=2000):
                return False
            return True
        except Exception:
            return True

    def search_jobs(self, keywords=None) -> list:
        """Mencari daftar loker di Glints berdasarkan kata kunci profil."""
        keyword_list = self._normalize_keywords(keywords, default=["Software Engineer"])
        jobs = []
        seen_urls = set()

        for main_query in keyword_list[:3]:
            encoded_kw = quote(main_query)
            url = f"https://glints.com/id/opportunities/jobs/explore?keyword={encoded_kw}&country=ID"

            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                human_delay(1.5, 2.5)
            except Exception as e:
                print(f"[!] Gagal memuat halaman Glints ({main_query}): {e}")
                continue

            for _ in range(2):
                self.page.mouse.wheel(0, 800)
                time.sleep(0.8)

            cards = self.page.locator("a[href*='/opportunities/jobs/']").all()

            for card in cards:
                try:
                    href = card.get_attribute("href")
                    if not href or "/opportunities/jobs/" not in href:
                        continue

                    clean_url = href.split("?")[0]
                    if not clean_url.startswith("http"):
                        clean_url = "https://glints.com" + clean_url

                    if clean_url in seen_urls:
                        continue
                    seen_urls.add(clean_url)

                    if self.config.get("auto_skip_already_seen", True) and is_job_recorded(clean_url):
                        continue

                    card_text = card.inner_text().split("\n")
                    title = card_text[0].strip() if len(card_text) > 0 else "Posisi tidak diketahui"
                    company = card_text[1].strip() if len(card_text) > 1 else "Perusahaan tidak diketahui"

                    salary = "Tidak dicantumkan"
                    location = ""
                    for line in card_text:
                        if any(c in line for c in ["IDR", "Rp", "Gaji", "Month", "Bulan"]):
                            salary = line.strip()
                        elif any(k in line.lower() for k in ["jakarta", "bandung", "surabaya", "bekasi", "tangerang", "remote", "hybrid", "indonesia"]):
                            location = line.strip()

                    is_match, reason = self.matcher.evaluate(title, company, location=location)
                    if not is_match:
                        record_job(clean_url, title, company, status="skipped", notes=f"Filter profil: {reason}")
                        continue

                    jobs.append({
                        "title": title,
                        "company": company,
                        "salary": salary,
                        "location": location,
                        "url": clean_url,
                    })
                except Exception:
                    continue

        return jobs

    def inspect_and_apply(self, job_url: str, job_title: str = "", company: str = "") -> dict:
        """Membuka halaman detail loker Glints dan mengeksekusi lamaran dengan handoff browser."""
        try:
            self.page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            human_delay(1.5, 2.5)
        except Exception as e:
            return {"status": "error", "message": f"Timeout membuka URL Glints: {e}"}

        # 1. Cek apakah sudah pernah dilamar
        already_applied = self.page.locator("text='Sudah Dilamar', text='Terkirim', text='Applied'").first
        try:
            if already_applied.is_visible(timeout=1500):
                return {"status": "already_applied", "message": "Lowongan ini sudah pernah dilamar sebelumnya di Glints."}
        except Exception:
            pass

        # 2. Cek apakah ini tautan eksternal
        external_btn = self.page.locator("button:has-text('situs web perusahaan'), a:has-text('situs web perusahaan')").first
        try:
            if external_btn.is_visible(timeout=1500):
                return {
                    "status": "external_link",
                    "message": "Lowongan ini mewajibkan apply di web eksternal perusahaan. Silakan buka link manual.",
                }
        except Exception:
            pass

        # 3. Cari tombol lamar internal Glints
        apply_btn = self.page.locator("button:has-text('Lamar Cepat'), button:has-text('Lamar'), button:has-text('Apply')").first
        try:
            if not apply_btn.is_visible(timeout=3000):
                return {"status": "button_not_found", "message": "Tombol lamar tidak ditemukan atau loker sudah ditutup."}

            pages_before = len(self.page.context.pages)
            apply_btn.click()
            human_delay(1.5, 2.5)
            self._switch_to_latest_tab_if_opened(pages_before)

            # 4. Cek apakah muncul modal/halaman login Glints
            login_modal = self.page.locator("input[type='password'], button:has-text('Masuk dengan Google'), text='Masuk ke Glints'").first
            if self._is_login_redirect() or (login_modal.is_visible(timeout=1200) and not self.page.locator("button:has-text('Kirim Lamaran')").first.is_visible(timeout=500)):
                shot = self._capture_failure_screenshot("glints", "login_required")
                return {
                    "status": "login_required",
                    "message": "Akun Glints belum login. Silakan login di jendela browser yang tetap terbuka, lalu selesaikan lamaran.",
                    "screenshot": shot,
                }

            confirm_before_submit = bool(self.config.get("screening_defaults", {}).get("confirm_before_submit", False))
            profile = self.config.get("profile", {})

            # 5. Loop langkah modal Glints (Upload CV -> Screening -> Cover Letter -> Lanjut -> Kirim)
            for _step in range(5):
                if self._page_has_text(["lamaran kamu telah terkirim", "lamaran berhasil dikirim", "application sent"]):
                    return {"status": "success", "message": "Lamaran berhasil dikirim via Glints."}

                self._upload_active_cv_if_present()
                self.screener.auto_fill_form()

                # Isi textarea cover letter/catatan pelamar bila kosong
                try:
                    ta = self.page.locator("textarea").first
                    if ta.is_visible(timeout=600) and not ta.input_value().strip():
                        name = profile.get("applicant_name", "")
                        if name and name != "Nama Lengkap Kamu":
                            ta.fill(generate_cover_letter(job_title or "Posisi", company or "Perusahaan", profile, preset="formal"))
                except Exception:
                    pass

                human_delay(0.8, 1.5)

                confirm_btn = self.page.locator("button:has-text('Kirim Lamaran'), button:has-text('Kirim'), button:has-text('Submit')").first
                if confirm_btn.is_visible(timeout=1800) and confirm_btn.is_enabled():
                    if confirm_before_submit:
                        shot = self._capture_failure_screenshot("glints", "review_pause")
                        return {
                            "status": "manual_action_needed",
                            "message": "Form Glints sudah diisi! Silakan cek di jendela browser dan klik 'Kirim Lamaran', lalu konfirmasi di dashboard.",
                            "screenshot": shot,
                            "unanswered_questions": self.screener.last_unanswered,
                        }
                    confirm_btn.click()
                    human_delay(2, 3)
                    return {"status": "success", "message": "Lamaran berhasil dikirim via Glints."}

                next_btn = self.page.locator("button:has-text('Lanjut'), button:has-text('Berikutnya'), button:has-text('Next')").first
                if next_btn.is_visible(timeout=1200) and next_btn.is_enabled():
                    next_btn.click()
                    human_delay(1.2, 2.0)
                    continue
                break

            shot = self._capture_failure_screenshot("glints", "manual_action")
            return {
                "status": "manual_action_needed",
                "message": "Muncul form/pertanyaan tambahan khusus di Glints. Silakan lengkapi langsung di jendela browser yang terbuka.",
                "screenshot": shot,
                "unanswered_questions": self.screener.last_unanswered,
            }
        except Exception as e:
            shot = self._capture_failure_screenshot("glints", "error")
            return {
                "status": "error",
                "message": f"Terjadi kesalahan teknis di Glints: {str(e)}",
                "screenshot": shot,
            }
