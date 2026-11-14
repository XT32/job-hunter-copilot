import time
from urllib.parse import quote
from src.base_hunter import BaseJobHunter
from src.browser import human_delay
from src.storage import is_job_recorded, record_job
from src.matcher import JobMatcher

class JobstreetHunter(BaseJobHunter):
    def __init__(self, page, config):
        super().__init__(page, config)
        self.matcher = JobMatcher(config.get("profile", {}))

    def check_login_status(self) -> bool:
        """Memeriksa apakah sesi login Jobstreet/SEEK aktif"""
        try:
            login_btn = self.page.locator("a[data-automation='login-button'], a:has-text('Masuk'), a:has-text('Log in')").first
            if login_btn.is_visible(timeout=2500):
                return False
            return True
        except Exception:
            return True

    def search_jobs(self, keywords=None) -> list:
        """Mencari lowongan di JobStreet Indonesia menggunakan selector data-automation resmi SEEK"""
        if not keywords:
            profile = self.config.get("profile", {})
            keywords = profile.get("target_keywords", ["Software Engineer"])

        main_query = keywords[0] if isinstance(keywords, list) and keywords else str(keywords)
        # JobStreet URL format: https://id.jobstreet.com/id/{keyword}-jobs
        slug_query = main_query.strip().replace(" ", "-").lower()
        url = f"https://id.jobstreet.com/id/{slug_query}-jobs"

        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            human_delay(2, 3)
        except Exception as e:
            print(f"[!] Gagal memuat halaman JobStreet: {e}")
            return []

        if not self.check_login_status():
            print("\n[!] PERINGATAN: Sesi login JobStreet belum aktif.")
            print("[!] Silakan login secara manual di jendela browser yang terbuka.")
            input("[!] Jika sudah berhasil login, tekan ENTER di terminal ini...")

        jobs = []

        # Scroll sedikit untuk memastikan render elemen dinamis
        for _ in range(2):
            self.page.mouse.wheel(0, 800)
            time.sleep(1)

        # Cari kartu lowongan via data-automation SEEK
        title_elements = self.page.locator("a[data-automation='jobTitle']").all()
        seen_urls = set()

        for title_el in title_elements:
            try:
                href = title_el.get_attribute("href")
                if not href or "/job/" not in href:
                    continue

                clean_url = href.split("?")[0]
                if not clean_url.startswith("http"):
                    clean_url = "https://id.jobstreet.com" + clean_url

                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)

                if self.config.get("auto_skip_already_seen", True) and is_job_recorded(clean_url):
                    continue

                title = title_el.inner_text().strip()

                # Cari elemen parent/container untuk mengambil company dan salary
                container = title_el.locator("xpath=./ancestor::article").first
                company = "Perusahaan tidak dicantumkan"
                salary = "Tidak dicantumkan"
                location = ""

                if container.is_visible():
                    try:
                        company_el = container.locator("[data-automation='jobCompany']").first
                        if company_el.is_visible():
                            company = company_el.inner_text().strip()
                    except Exception:
                        pass

                    try:
                        salary_el = container.locator("[data-automation='jobSalary']").first
                        if salary_el.is_visible():
                            salary = salary_el.inner_text().strip()
                    except Exception:
                        pass

                    try:
                        loc_el = container.locator("[data-automation='jobLocation']").first
                        if loc_el.is_visible():
                            location = loc_el.inner_text().strip()
                    except Exception:
                        pass

                # Evaluasi kecocokan dengan profil jurusan & pengalaman
                is_match, reason = self.matcher.evaluate(title, company, location=location)
                if not is_match:
                    record_job(clean_url, title, company, status="skipped", notes=f"JobStreet Filter: {reason}")
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
        """Membuka halaman detail loker JobStreet dan mengeksekusi proses lamaran"""
        try:
            self.page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
            human_delay(1.5, 2.5)
        except Exception as e:
            return {"status": "error", "message": f"Timeout membuka URL: {e}"}

        # 1. Cek apakah sudah pernah dilamar
        already_applied = self.page.locator("text='Lamaran terkirim', text='Terkirim', text='Applied'").first
        try:
            if already_applied.is_visible(timeout=1500):
                return {"status": "already_applied", "message": "Lowongan ini sudah pernah dilamar di JobStreet."}
        except Exception:
            pass

        # 2. Cari tombol lamar JobStreet (data-automation='job-detail-apply')
        apply_btn = self.page.locator("a[data-automation='job-detail-apply'], button[data-automation='job-detail-apply'], a:has-text('Lamar cepat'), button:has-text('Lamar cepat')").first
        try:
            if not apply_btn.is_visible(timeout=3000):
                return {"status": "button_not_found", "message": "Tombol lamar tidak ditemukan atau loker sudah kedaluwarsa."}

            btn_text = apply_btn.inner_text().lower()
            if "perusahaan" in btn_text or "situs web" in btn_text:
                return {
                    "status": "external_link",
                    "message": "Lowongan ini mewajibkan lamaran di situs eksternal perusahaan."
                }

            apply_btn.click()
            human_delay(2, 3)

            # Cek modal lamaran JobStreet / pertanyaan screening
            # JobStreet sering meminta review CV atau menjawab form khusus
            submit_btn = self.page.locator("button:has-text('Kirim lamaran'), button:has-text('Kirim'), button[data-automation='submit-application']").first
            if submit_btn.is_visible(timeout=3000):
                submit_btn.click()
                human_delay(2, 3)
                return {"status": "success", "message": "Lamaran berhasil dikirim via JobStreet."}
            else:
                return {
                    "status": "manual_action_needed",
                    "message": "Muncul form/pertanyaan screening JobStreet. Silakan lengkapi di layar browser."
                }
        except Exception as e:
            return {"status": "error", "message": f"Terjadi kesalahan di JobStreet: {str(e)}"}
