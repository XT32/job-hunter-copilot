import time
from urllib.parse import quote
from src.base_hunter import BaseJobHunter
from src.browser import human_delay
from src.storage import is_job_recorded, record_job
from src.matcher import JobMatcher

class MagangHubHunter(BaseJobHunter):
    def __init__(self, page, config):
        super().__init__(page, config)
        self.matcher = JobMatcher(config.get("profile", {}))

    def check_login_status(self) -> bool:
        """Memeriksa apakah akun SIAPkerja Kemnaker sudah masuk di MagangHub"""
        try:
            login_btn = self.page.locator("a:has-text('Masuk'), a:has-text('Login'), button:has-text('Masuk')").first
            if login_btn.is_visible(timeout=2500):
                return False
            return True
        except Exception:
            return True

    def search_jobs(self, keywords=None) -> list:
        """Mencari daftar program magang di MagangHub Kemnaker"""
        if not keywords:
            profile = self.config.get("profile", {})
            keywords = profile.get("target_keywords", ["Magang"])

        main_query = keywords[0] if isinstance(keywords, list) and keywords else str(keywords)
        url = f"https://maganghub.kemnaker.go.id/lowongan?cari={quote(main_query)}"

        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            human_delay(2, 3)
        except Exception as e:
            # Fallback jika URL utama tanpa parameter cari
            fallback_url = "https://maganghub.kemnaker.go.id"
            try:
                self.page.goto(fallback_url, wait_until="domcontentloaded", timeout=30000)
                human_delay(2, 3)
            except Exception:
                print(f"[!] Gagal memuat MagangHub: {e}")
                return []

        if not self.check_login_status():
            print("\n[!] PERINGATAN: Sesi login SIAPkerja di MagangHub belum aktif.")
            print("[!] Silakan login akun SIAPkerja Anda di jendela browser yang terbuka.")
            input("[!] Jika sudah berhasil login, tekan ENTER di terminal ini...")

        jobs = []

        for _ in range(2):
            self.page.mouse.wheel(0, 800)
            time.sleep(1)

        # Cari kartu lowongan magang
        cards = self.page.locator("a[href*='/lowongan/'], a[href*='/detail/'], .card, article").all()
        seen_urls = set()

        for card in cards:
            try:
                href = card.get_attribute("href")
                if not href:
                    # Cek anak link
                    child_link = card.locator("a").first
                    if child_link.is_visible():
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
                title = card_text[0].strip() if len(card_text) > 0 else "Posisi Magang"
                company = card_text[1].strip() if len(card_text) > 1 else "Mitra Kemnaker"
                
                location = "Indonesia"
                for line in card_text:
                    if any(k in line.lower() for k in ["kota", "kabupaten", "dki", "provinsi"]):
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
                    "url": clean_url
                })
            except Exception:
                continue

        return jobs

    def inspect_and_apply(self, job_url: str) -> dict:
        """Membuka detail lowongan magang dan mengeksekusi pendaftaran peserta"""
        try:
            self.page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            human_delay(1.5, 2.5)
        except Exception as e:
            return {"status": "error", "message": f"Timeout membuka MagangHub: {e}"}

        # Cek tombol daftar/lamar magang
        apply_btn = self.page.locator("button:has-text('Daftar Magang'), button:has-text('Lamar'), a:has-text('Daftar Magang'), button:has-text('Ajukan Lamaran')").first
        try:
            if not apply_btn.is_visible(timeout=3000):
                return {"status": "button_not_found", "message": "Tombol daftar magang tidak ditemukan atau kuota sudah terpenuhi."}

            apply_btn.click()
            human_delay(2, 3)

            # Cek modal konfirmasi berkas SIAPkerja
            confirm_btn = self.page.locator("button:has-text('Kirim'), button:has-text('Konfirmasi'), button:has-text('Ya, Daftar')").first
            if confirm_btn.is_visible(timeout=3000):
                confirm_btn.click()
                human_delay(2, 3)
                return {"status": "success", "message": "Pendaftaran program magang berhasil dikirim via MagangHub!"}
            else:
                return {
                    "status": "manual_action_needed",
                    "message": "Muncul verifikasi berkas SIAPkerja (Pakta Integritas / Surat Rekomendasi). Silakan konfirmasi di layar."
                }
        except Exception as e:
            return {"status": "error", "message": f"Terjadi kesalahan di MagangHub: {str(e)}"}
