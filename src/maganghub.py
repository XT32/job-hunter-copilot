import time
from urllib.parse import quote
from src.base_hunter import BaseJobHunter
from src.browser import human_delay
from src.storage import is_job_recorded, record_job
from src.matcher import JobMatcher
from src.screener import ScreeningAutoFiller


BADGE_TAGS = {
    "baru", "new", "magang bersertifikat", "batch", "aktif", "terverifikasi",
    "kemnaker", "bumn", "nasional", "populer"
}


class MagangHubHunter(BaseJobHunter):
    def __init__(self, page, config):
        super().__init__(page, config)
        self.matcher = JobMatcher(config.get("profile", {}))
        self.screener = ScreeningAutoFiller(page, config.get("screening_defaults", {}))

    def check_login_status(self) -> bool:
        """Memeriksa apakah akun SIAPkerja Kemnaker sudah masuk di MagangHub."""
        try:
            if self._is_login_redirect():
                return False
            login_btn = self.page.locator("a:has-text('Masuk'), a:has-text('Login'), button:has-text('Masuk')").first
            if login_btn.is_visible(timeout=2500):
                return False
            return True
        except Exception:
            return True

    def search_jobs(self, keywords=None) -> list:
        """Mencari daftar program magang di MagangHub Kemnaker."""
        keyword_list = self._normalize_keywords(keywords, default=["Magang"])
        jobs = []
        seen_urls = set()

        for main_query in keyword_list[:3]:
            url = f"https://maganghub.kemnaker.go.id/lowongan?cari={quote(main_query)}"

            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                human_delay(1.5, 2.5)
            except Exception as e:
                fallback_url = "https://maganghub.kemnaker.go.id"
                try:
                    self.page.goto(fallback_url, wait_until="domcontentloaded", timeout=30000)
                    human_delay(1.5, 2.5)
                except Exception:
                    print(f"[!] Gagal memuat MagangHub ({main_query}): {e}")
                    continue

            for _ in range(2):
                self.page.mouse.wheel(0, 800)
                time.sleep(0.8)

            cards = self.page.locator("a[href*='/lowongan/'], a[href*='/detail/'], .card, article").all()

            for card in cards:
                try:
                    href = card.get_attribute("href")
                    if not href:
                        child_link = card.locator("a").first
                        if child_link.count() > 0:
                            href = child_link.get_attribute("href")

                    if not href or ("lowongan" not in href and "detail" not in href):
                        continue

                    clean_url = href.split("?")[0]
                    if not clean_url.startswith("http"):
                        clean_url = "https://maganghub.kemnaker.go.id" + clean_url

                    if clean_url in seen_urls:
                        continue
                    seen_urls.add(clean_url)

                    if self.config.get("auto_skip_already_seen", True) and is_job_recorded(clean_url):
                        continue

                    card_text = card.inner_text().split("\n")
                    clean_lines = [line.strip() for line in card_text if line.strip() and line.strip().lower() not in BADGE_TAGS]
                    title = clean_lines[0] if len(clean_lines) > 0 else "Posisi Magang"
                    company = clean_lines[1] if len(clean_lines) > 1 else "Mitra Kemnaker"

                    location = "Indonesia"
                    for line in card_text:
                        if any(k in line.lower() for k in ["kota", "kabupaten", "dki", "provinsi", "jakarta", "bandung", "surabaya", "bekasi"]):
                            location = line.strip()
                            break

                    is_match, reason = self.matcher.evaluate(title, company, location=location)
                    if not is_match:
                        record_job(clean_url, title, company, status="skipped", notes=f"MagangHub Filter: {reason}")
                        continue

                    jobs.append({
                        "title": title,
                        "company": company,
                        "salary": "Uang Saku Kemnaker (Sesuai Ketentuan)",
                        "location": location,
                        "url": clean_url,
                    })
                except Exception:
                    continue

        return jobs

    def inspect_and_apply(self, job_url: str, job_title: str = "", company: str = "") -> dict:
        """Membuka detail lowongan magang dan mengeksekusi pendaftaran peserta."""
        try:
            self.page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            human_delay(1.5, 2.5)
        except Exception as e:
            return {"status": "error", "message": f"Timeout membuka MagangHub: {e}"}

        already_registered = self.page.locator("text='Sudah Mendaftar', text='Sudah Terdaftar', text='Sudah Dilamar'").first
        try:
            if already_registered.is_visible(timeout=1500):
                return {"status": "already_applied", "message": "Program magang ini sudah pernah kamu daftar di MagangHub."}
        except Exception:
            pass

        apply_btn = self.page.locator(
            "button:has-text('Daftar Magang'), button:has-text('Lamar'), a:has-text('Daftar Magang'), button:has-text('Ajukan Lamaran')"
        ).first
        try:
            if not apply_btn.is_visible(timeout=3000):
                return {"status": "button_not_found", "message": "Tombol daftar magang tidak ditemukan atau kuota sudah terpenuhi."}

            pages_before = len(self.page.context.pages)
            apply_btn.click()
            human_delay(1.8, 2.8)
            self._switch_to_latest_tab_if_opened(pages_before)

            if self._is_login_redirect() or self._page_has_text(["masuk siapkerja", "login siapkerja", "nik / email"]):
                shot = self._capture_failure_screenshot("maganghub", "login_required")
                return {
                    "status": "login_required",
                    "message": "Akun SIAPkerja Kemnaker belum login. Silakan login di jendela browser yang terbuka, lalu selesaikan pendaftaran.",
                    "screenshot": shot,
                }

            self._upload_active_cv_if_present()
            self.screener.auto_fill_form()
            human_delay(0.8, 1.4)

            confirm_before_submit = bool(self.config.get("screening_defaults", {}).get("confirm_before_submit", False))
            confirm_btn = self.page.locator("button:has-text('Kirim'), button:has-text('Konfirmasi'), button:has-text('Ya, Daftar')").first
            if confirm_btn.is_visible(timeout=2500) and confirm_btn.is_enabled():
                if confirm_before_submit:
                    shot = self._capture_failure_screenshot("maganghub", "review_pause")
                    return {
                        "status": "manual_action_needed",
                        "message": "Silakan cek berkas MagangHub di browser yang terbuka dan klik Konfirmasi/Daftar.",
                        "screenshot": shot,
                        "unanswered_questions": self.screener.last_unanswered,
                    }
                confirm_btn.click()
                human_delay(2, 3)
                return {"status": "success", "message": "Pendaftaran program magang berhasil dikirim via MagangHub!"}

            shot = self._capture_failure_screenshot("maganghub", "manual_action")
            return {
                "status": "manual_action_needed",
                "message": "Muncul verifikasi berkas SIAPkerja (Pakta Integritas / Surat Rekomendasi). Silakan lengkapi di jendela browser yang terbuka.",
                "screenshot": shot,
                "unanswered_questions": self.screener.last_unanswered,
            }
        except Exception as e:
            shot = self._capture_failure_screenshot("maganghub", "error")
            return {"status": "error", "message": f"Terjadi kesalahan di MagangHub: {str(e)}", "screenshot": shot}
