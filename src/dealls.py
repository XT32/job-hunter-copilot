import time
from urllib.parse import quote
from src.base_hunter import BaseJobHunter
from src.browser import human_delay
from src.storage import is_job_recorded, record_job
from src.matcher import JobMatcher
from src.screener import ScreeningAutoFiller
from src.cover_letter import generate_cover_letter


class DeallsHunter(BaseJobHunter):
    def __init__(self, page, config):
        super().__init__(page, config)
        self.matcher = JobMatcher(config.get("profile", {}))
        self.screener = ScreeningAutoFiller(page, config.get("screening_defaults", {}))

    def check_login_status(self) -> bool:
        """Memeriksa apakah akun Dealls sudah login."""
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
        """Mencari daftar lowongan kerja di Dealls Jobs."""
        keyword_list = self._normalize_keywords(keywords, default=["Software Engineer"])
        jobs = []
        seen_urls = set()

        for main_query in keyword_list[:3]:
            encoded_kw = quote(main_query)
            url = f"https://dealls.com/jobs?q={encoded_kw}"

            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                human_delay(1.5, 2.5)
            except Exception as e:
                print(f"[!] Gagal memuat Dealls ({main_query}): {e}")
                continue

            for _ in range(2):
                self.page.mouse.wheel(0, 800)
                time.sleep(0.8)

            cards = self.page.locator("a[href*='/job/'], a[href*='/jobs/'], .job-card, [data-testid='job-card']").all()

            for card in cards:
                try:
                    href = card.get_attribute("href")
                    if not href:
                        child_a = card.locator("a").first
                        if child_a.count() > 0:
                            href = child_a.get_attribute("href")

                    if not href or ("/job/" not in href and "/jobs/" not in href):
                        continue

                    clean_url = href.split("?")[0]
                    if not clean_url.startswith("http"):
                        clean_url = "https://dealls.com" + clean_url

                    if clean_url in seen_urls:
                        continue
                    seen_urls.add(clean_url)

                    if self.config.get("auto_skip_already_seen", True) and is_job_recorded(clean_url):
                        continue

                    card_text = card.inner_text().split("\n")
                    title = card_text[0].strip() if len(card_text) > 0 else "Posisi Dealls"
                    company = card_text[1].strip() if len(card_text) > 1 else "Perusahaan Dealls"

                    salary = "Transparan / Sesuai profil"
                    location = "Indonesia"
                    for line in card_text:
                        if any(c in line for c in ["IDR", "Rp", "Juta"]):
                            salary = line.strip()
                        elif any(k in line.lower() for k in ["jakarta", "bandung", "surabaya", "bekasi", "tangerang", "remote", "hybrid"]):
                            location = line.strip()

                    is_match, reason = self.matcher.evaluate(title, company, location=location)
                    if not is_match:
                        record_job(clean_url, title, company, status="skipped", notes=f"Dealls Filter: {reason}")
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
        """Membuka halaman detail loker Dealls dan mengeksekusi lamaran."""
        try:
            self.page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            human_delay(1.5, 2.5)
        except Exception as e:
            return {"status": "error", "message": f"Timeout membuka Dealls: {e}"}

        already_applied = self.page.locator("text='Sudah Dilamar', text='Applied', text='Lamaran Terkirim'").first
        try:
            if already_applied.is_visible(timeout=1500):
                return {"status": "already_applied", "message": "Lowongan ini sudah pernah dilamar di Dealls."}
        except Exception:
            pass

        apply_btn = self.page.locator("button:has-text('Lamar'), button:has-text('Apply'), a:has-text('Lamar Cepat')").first
        try:
            if not apply_btn.is_visible(timeout=3000):
                return {"status": "button_not_found", "message": "Tombol lamar Dealls tidak ditemukan."}

            btn_text = apply_btn.inner_text().lower()
            if "eksternal" in btn_text or "perusahaan" in btn_text:
                return {"status": "external_link", "message": "Lowongan ini mewajibkan melamar di situs eksternal perusahaan."}

            pages_before = len(self.page.context.pages)
            apply_btn.click()
            human_delay(1.5, 2.5)
            self._switch_to_latest_tab_if_opened(pages_before)

            if self._is_login_redirect() or self.page.locator("input[type='password'], text='Masuk ke Dealls', text='Sign in to Dealls'").first.is_visible(timeout=1000):
                shot = self._capture_failure_screenshot("dealls", "login_required")
                return {
                    "status": "login_required",
                    "message": "Akun Dealls belum login. Silakan login di jendela browser yang terbuka, lalu selesaikan lamaran.",
                    "screenshot": shot,
                }

            confirm_before_submit = bool(self.config.get("screening_defaults", {}).get("confirm_before_submit", False))
            profile = self.config.get("profile", {})

            for _step in range(5):
                if self._page_has_text(["lamaran berhasil", "lamaran terkirim", "application submitted"]):
                    return {"status": "success", "message": "Lamaran berhasil dikirim via Dealls."}

                self._upload_active_cv_if_present()
                self.screener.auto_fill_form()

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
                        shot = self._capture_failure_screenshot("dealls", "review_pause")
                        return {
                            "status": "manual_action_needed",
                            "message": "Form Dealls sudah diisi! Silakan cek di jendela browser dan klik 'Kirim', lalu konfirmasi di dashboard.",
                            "screenshot": shot,
                            "unanswered_questions": self.screener.last_unanswered,
                        }
                    confirm_btn.click()
                    human_delay(2, 3)
                    return {"status": "success", "message": "Lamaran berhasil dikirim via Dealls."}

                next_btn = self.page.locator("button:has-text('Lanjut'), button:has-text('Berikutnya'), button:has-text('Next')").first
                if next_btn.is_visible(timeout=1200) and next_btn.is_enabled():
                    next_btn.click()
                    human_delay(1.2, 2.0)
                    continue
                break

            shot = self._capture_failure_screenshot("dealls", "manual_action")
            return {
                "status": "manual_action_needed",
                "message": "Silakan konfirmasi resume dan pertanyaan di jendela browser Dealls yang terbuka.",
                "screenshot": shot,
                "unanswered_questions": self.screener.last_unanswered,
            }
        except Exception as e:
            shot = self._capture_failure_screenshot("dealls", "error")
            return {"status": "error", "message": f"Terjadi kesalahan di Dealls: {str(e)}", "screenshot": shot}
