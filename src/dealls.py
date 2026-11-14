import time
from urllib.parse import quote
from src.base_hunter import BaseJobHunter
from src.browser import human_delay
from src.storage import is_job_recorded, record_job
from src.matcher import JobMatcher

class DeallsHunter(BaseJobHunter):
    def __init__(self, page, config):
        super().__init__(page, config)
        self.matcher = JobMatcher(config.get("profile", {}))

    def check_login_status(self) -> bool:
        """Memeriksa apakah akun Dealls sudah login"""
        try:
            login_btn = self.page.locator("a:has-text('Masuk'), button:has-text('Masuk'), a:has-text('Sign In')").first
            if login_btn.is_visible(timeout=2000):
                return False
            return True
        except Exception:
            return True

    def search_jobs(self, keywords=None) -> list:
        """Mencari daftar lowongan kerja di Dealls Jobs"""
        if not keywords:
            profile = self.config.get("profile", {})
            keywords = profile.get("target_keywords", ["Software Engineer"])

        main_query = keywords[0] if isinstance(keywords, list) and keywords else str(keywords)
        encoded_kw = quote(main_query)
        url = f"https://dealls.com/jobs?q={encoded_kw}"

        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            human_delay(2, 3)
        except Exception as e:
            print(f"[!] Gagal memuat Dealls: {e}")
            return []

        if not self.check_login_status():
            print("\n[!] PERINGATAN: Sesi login Dealls belum aktif.")
            print("[!] Silakan login secara manual di jendela browser yang terbuka.")
            input("[!] Jika sudah berhasil login, tekan ENTER di terminal ini...")

        jobs = []

        for _ in range(2):
            self.page.mouse.wheel(0, 800)
            time.sleep(1)

        # Cari kartu lowongan di Dealls
        cards = self.page.locator("a[href*='/job/'], a[href*='/jobs/'], .job-card, [data-testid='job-card']").all()
        seen_urls = set()

        for card in cards:
            try:
                href = card.get_attribute("href")
                if not href:
                    child_a = card.locator("a").first
                    if child_a.is_visible():
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
                    elif any(k in line.lower() for k in ["jakarta", "bandung", "surabaya", "remote", "hybrid"]):
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
                    "url": clean_url
                })
            except Exception:
                continue

        return jobs

    def inspect_and_apply(self, job_url: str) -> dict:
        """Membuka halaman detail loker Dealls dan mengeksekusi lamaran"""
        try:
            self.page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            human_delay(1.5, 2.5)
        except Exception as e:
            return {"status": "error", "message": f"Timeout membuka Dealls: {e}"}

        apply_btn = self.page.locator("button:has-text('Lamar'), button:has-text('Apply'), a:has-text('Lamar Cepat')").first
        try:
            if not apply_btn.is_visible(timeout=3000):
                return {"status": "button_not_found", "message": "Tombol lamar Dealls tidak ditemukan."}

            apply_btn.click()
            human_delay(2, 3)

            confirm_btn = self.page.locator("button:has-text('Kirim'), button:has-text('Submit'), button:has-text('Lanjut')").first
            if confirm_btn.is_visible(timeout=3000):
                confirm_btn.click()
                human_delay(2, 3)
                return {"status": "success", "message": "Lamaran berhasil dikirim via Dealls."}
            else:
                return {
                    "status": "manual_action_needed",
                    "message": "Silakan konfirmasi resume dan jawaban di jendela browser Dealls."
                }
        except Exception as e:
            return {"status": "error", "message": f"Terjadi kesalahan di Dealls: {str(e)}"}
