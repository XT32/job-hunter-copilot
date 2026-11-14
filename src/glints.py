import time
from urllib.parse import quote
from src.base_hunter import BaseJobHunter
from src.browser import human_delay
from src.storage import is_job_recorded, record_job
from src.matcher import JobMatcher

class GlintsHunter(BaseJobHunter):
    def __init__(self, page, config):
        super().__init__(page, config)
        self.matcher = JobMatcher(config.get("profile", {}))

    def check_login_status(self) -> bool:
        """Memeriksa apakah user sudah login ke Glints"""
        try:
            login_btn = self.page.locator("a:has-text('Masuk'), button:has-text('Masuk'), a:has-text('Sign In')").first
            if login_btn.is_visible(timeout=2000):
                return False
            return True
        except Exception:
            return True

    def search_jobs(self, keywords=None) -> list:
        """Mencari daftar loker di Glints berdasarkan kata kunci profil"""
        if not keywords:
            profile = self.config.get("profile", {})
            keywords = profile.get("target_keywords", ["Software Engineer"])

        main_query = keywords[0] if isinstance(keywords, list) and keywords else str(keywords)
        encoded_kw = quote(main_query)
        url = f"https://glints.com/id/opportunities/jobs/explore?keyword={encoded_kw}&country=ID"
        
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            human_delay(2, 3)
        except Exception as e:
            print(f"[!] Gagal memuat halaman Glints: {e}")
            return []

        if not self.check_login_status():
            print("\n[!] PERINGATAN: Sesi login Glints belum aktif.")
            print("[!] Silakan login secara manual di jendela browser yang terbuka.")
            input("[!] Jika sudah berhasil login, tekan ENTER di terminal ini...")

        jobs = []
        
        # Scroll bertahap untuk trigger pemuatan kartu loker
        for _ in range(2):
            self.page.mouse.wheel(0, 800)
            time.sleep(1)

        cards = self.page.locator("a[href*='/opportunities/jobs/']").all()
        seen_urls = set()

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
                for line in card_text:
                    if any(c in line for c in ["IDR", "Rp", "Gaji", "Month", "Bulan"]):
                        salary = line.strip()
                        break

                # Evaluasi kecocokan dengan profil pengguna (Jurusan, Pengalaman, Blacklist)
                is_match, reason = self.matcher.evaluate(title, company)
                if not is_match:
                    record_job(clean_url, title, company, status="skipped", notes=f"Filter profil: {reason}")
                    continue

                jobs.append({
                    "title": title,
                    "company": company,
                    "salary": salary,
                    "url": clean_url
                })
            except Exception:
                continue

        return jobs

    def inspect_and_apply(self, job_url: str) -> dict:
        """Membuka halaman detail loker dan mengeksekusi lamaran dengan validasi keamanan"""
        try:
            self.page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            human_delay(1.5, 2.5)
        except Exception as e:
            return {"status": "error", "message": f"Timeout membuka URL: {e}"}

        # 1. Cek apakah sudah pernah dilamar
        already_applied = self.page.locator("text='Sudah Dilamar', text='Terkirim', text='Applied'").first
        try:
            if already_applied.is_visible(timeout=1500):
                return {"status": "already_applied", "message": "Lowongan ini sudah pernah dilamar sebelumnya."}
        except Exception:
            pass

        # 2. Cek apakah ini tautan eksternal (mengarahkan ke web perusahaan luar)
        external_btn = self.page.locator("button:has-text('situs web perusahaan'), a:has-text('situs web perusahaan')").first
        try:
            if external_btn.is_visible(timeout=1500):
                return {
                    "status": "external_link",
                    "message": "Lowongan ini mewajibkan apply di web eksternal perusahaan. Silakan buka link manual."
                }
        except Exception:
            pass

        # 3. Cari tombol lamar internal Glints
        apply_btn = self.page.locator("button:has-text('Lamar'), button:has-text('Lamar Cepat'), button:has-text('Apply')").first
        try:
            if not apply_btn.is_visible(timeout=3000):
                return {"status": "button_not_found", "message": "Tombol lamar tidak ditemukan atau loker sudah ditutup."}
            
            apply_btn.click()
            human_delay(1.5, 2.5)

            # 4. Tangani modal konfirmasi
            confirm_btn = self.page.locator("button:has-text('Kirim Lamaran'), button:has-text('Kirim'), button:has-text('Lanjut')").first
            if confirm_btn.is_visible(timeout=3000):
                confirm_btn.click()
                human_delay(2, 3)
                return {"status": "success", "message": "Lamaran berhasil dikirim via Glints."}
            else:
                return {
                    "status": "manual_action_needed",
                    "message": "Muncul form/pertanyaan tambahan khusus. Silakan lengkapi langsung di layar browser."
                }
        except Exception as e:
            return {"status": "error", "message": f"Terjadi kesalahan teknis: {str(e)}"}
