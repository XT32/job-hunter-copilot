import time
from urllib.parse import quote
from src.browser import human_delay
from src.storage import is_job_recorded

class GlintsHunter:
    def __init__(self, page, config):
        self.page = page
        self.config = config

    def check_login_status(self):
        """Memeriksa apakah user sudah login ke Glints"""
        try:
            # Jika ada tombol "Masuk" / "Sign in", berarti belum login
            login_btn = self.page.locator("a:has-text('Masuk'), button:has-text('Masuk'), a:has-text('Sign In')").first
            if login_btn.is_visible(timeout=3000):
                return False
            return True
        except Exception:
            return True

    def search_jobs(self, keyword, max_pages=1):
        """Mencari daftar loker di Glints berdasarkan kata kunci"""
        encoded_kw = quote(keyword)
        url = f"https://glints.com/id/opportunities/jobs/explore?keyword={encoded_kw}&country=ID"
        
        self.page.goto(url, wait_until="domcontentloaded")
        human_delay(2, 4)

        # Cek apakah user perlu login dulu
        if not self.check_login_status():
            print("\n[!] PERINGATAN: Kamu belum login ke Glints.")
            print("[!] Silakan login secara manual di jendela browser yang terbuka.")
            input("[!] Jika sudah berhasil login, tekan ENTER di terminal ini untuk melanjutkan...")

        jobs = []
        
        # Scroll perlahan untuk memicu pemuatan kartu loker
        for _ in range(3):
            self.page.mouse.wheel(0, 1000)
            time.sleep(1)

        # Cari kartu-kartu loker
        cards = self.page.locator("a[href*='/opportunities/jobs/']").all()
        seen_urls = set()

        for card in cards:
            try:
                href = card.get_attribute("href")
                if not href or "/opportunities/jobs/" not in href:
                    continue
                
                # Normalisasi URL
                clean_url = href.split("?")[0]
                if not clean_url.startswith("http"):
                    clean_url = "https://glints.com" + clean_url
                
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)

                # Skip jika sudah ada di riwayat
                if self.config.get("auto_skip_already_seen", True) and is_job_recorded(clean_url):
                    continue

                # Ambil teks info dari card
                card_text = card.inner_text().split("\n")
                title = card_text[0] if len(card_text) > 0 else "Lowongan Kerja"
                company = card_text[1] if len(card_text) > 1 else "Perusahaan"
                
                # Cari kemungkinan info gaji
                salary = "Dirahasiakan / Tidak dicantumkan"
                for line in card_text:
                    if "IDR" in line or "Rp" in line or "Gaji" in line:
                        salary = line.strip()
                        break

                jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "salary": salary,
                    "url": clean_url
                })
            except Exception:
                continue

        return jobs

    def inspect_and_apply(self, job_url):
        """Membuka halaman detail loker dan mengeksekusi lamaran"""
        self.page.goto(job_url, wait_until="domcontentloaded")
        human_delay(1.5, 3)

        # Cek apakah sudah pernah dilamar sebelumnya
        already_applied = self.page.locator("text='Sudah Dilamar', text='Terkirim', text='Applied'").first
        try:
            if already_applied.is_visible(timeout=1500):
                return {"status": "already_applied", "message": "Lowongan ini sudah pernah dilamar sebelumnya."}
        except Exception:
            pass

        # Cari tombol lamar utama
        apply_btn = self.page.locator("button:has-text('Lamar'), button:has-text('Lamar Cepat'), button:has-text('Apply')").first
        try:
            if not apply_btn.is_visible(timeout=3000):
                return {"status": "button_not_found", "message": "Tombol lamar tidak ditemukan atau loker sudah ditutup."}
            
            # Klik tombol Lamar
            apply_btn.click()
            human_delay(1.5, 2.5)

            # Cek modal popup konfirmasi lamaran
            confirm_btn = self.page.locator("button:has-text('Kirim Lamaran'), button:has-text('Lanjut'), button:has-text('Submit')").first
            if confirm_btn.is_visible(timeout=3000):
                confirm_btn.click()
                human_delay(2, 3)
                return {"status": "success", "message": "Lamaran berhasil dikirim!"}
            else:
                # Jika ada formulir khusus (pertanyaan screening tambahan)
                return {
                    "status": "manual_action_needed",
                    "message": "Muncul form / pertanyaan tambahan di browser. Silakan lengkapi langsung di layar."
                }
        except Exception as e:
            return {"status": "error", "message": f"Terjadi kesalahan: {str(e)}"}
