import time
from src.base_hunter import BaseJobHunter
from src.browser import human_delay
from src.storage import is_job_recorded, record_job
from src.matcher import JobMatcher
from src.screener import ScreeningAutoFiller
from src.cover_letter import generate_cover_letter


class JobstreetHunter(BaseJobHunter):
    def __init__(self, page, config):
        super().__init__(page, config)
        self.matcher = JobMatcher(config.get("profile", {}))
        self.screener = ScreeningAutoFiller(page, config.get("screening_defaults", {}))

    def check_login_status(self) -> bool:
        """Memeriksa apakah sesi login Jobstreet/SEEK aktif."""
        try:
            if self._is_login_redirect():
                return False
            login_btn = self.page.locator(
                "a[data-automation='login-button'], a:has-text('Masuk'), button:has-text('Masuk'), a:has-text('Log in')"
            ).first
            if login_btn.is_visible(timeout=2000):
                return False
            return True
        except Exception:
            return True

    def search_jobs(self, keywords=None) -> list:
        """Mencari lowongan di JobStreet Indonesia menggunakan selector data-automation resmi SEEK."""
        keyword_list = self._normalize_keywords(keywords, default=["Software Engineer"])
        jobs = []
        seen_urls = set()

        for query in keyword_list[:3]:
            slug_query = query.strip().replace(" ", "-").lower()
            url = f"https://id.jobstreet.com/id/{slug_query}-jobs"

            try:
                self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                human_delay(1.5, 2.5)
            except Exception as e:
                print(f"[!] Gagal memuat halaman JobStreet ({query}): {e}")
                continue

            for _ in range(2):
                self.page.mouse.wheel(0, 800)
                time.sleep(0.8)

            title_elements = self.page.locator("a[data-automation='jobTitle']").all()

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

                    is_match, reason = self.matcher.evaluate(title, company, location=location)
                    if not is_match:
                        record_job(clean_url, title, company, status="skipped", notes=f"JobStreet Filter: {reason}")
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

    def _click_continue_button(self) -> bool:
        continue_btn = self.page.locator(
            "button[data-automation='continue-button'], "
            "button:has-text('Lanjut'), "
            "button:has-text('Berikutnya'), "
            "button:has-text('Continue'), "
            "button:has-text('Next')"
        ).first
        try:
            if continue_btn.is_visible(timeout=2500) and continue_btn.is_enabled():
                continue_btn.click()
                human_delay(1.5, 2.5)
                return True
        except Exception:
            pass
        return False

    def _handle_choose_documents_step(self, job_title: str, company: str):
        """Menangani Tahap 1 JobStreet: Pilih/Unggah Resume dan Surat Lamaran."""
        # 1. Jika ada radio resume tersimpan yang belum dipilih, pilih yang pertama
        try:
            resume_radios = self.page.locator("input[type='radio'][name*='resume' i], input[type='radio'][id*='resume' i]").all()
            if resume_radios and not any(r.is_checked() for r in resume_radios):
                resume_radios[0].check(force=True)
        except Exception:
            pass

        # 2. Unggah CV PDF aktif jika ada input file
        self._upload_active_cv_if_present()

        # 3. Tangani opsi Cover Letter (Tulis surat lamaran vs Jangan sertakan)
        try:
            write_cl_radio = self.page.locator(
                "label:has-text('Tulis surat lamaran'), label:has-text('Write a cover letter')"
            ).first
            skip_cl_radio = self.page.locator(
                "label:has-text('Jangan sertakan'), label:has-text('Do not include'), label:has-text('Tidak perlu')"
            ).first

            profile = self.config.get("profile", {})
            applicant_name = profile.get("applicant_name", "")
            has_real_name = bool(applicant_name and applicant_name != "Nama Lengkap Kamu")

            if write_cl_radio.is_visible(timeout=800) and has_real_name:
                write_cl_radio.click()
                human_delay(0.5, 1.0)
                cl_textarea = self.page.locator("textarea").first
                if cl_textarea.is_visible(timeout=1000) and not cl_textarea.input_value().strip():
                    letter = generate_cover_letter(
                        job_title or "Posisi yang Dilamar",
                        company or "Perusahaan",
                        profile,
                        preset="formal",
                    )
                    cl_textarea.fill(letter)
            elif skip_cl_radio.is_visible(timeout=800):
                skip_cl_radio.click()
        except Exception:
            pass

    def inspect_and_apply(self, job_url: str, job_title: str = "", company: str = "") -> dict:
        """Membuka halaman detail loker JobStreet dan mengeksekusi wizard 4 tahap secara semi-otomatis."""
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
        apply_btn = self.page.locator(
            "a[data-automation='job-detail-apply'], "
            "button[data-automation='job-detail-apply'], "
            "a:has-text('Lamar cepat'), "
            "button:has-text('Lamar cepat'), "
            "a:has-text('Lamar'), "
            "button:has-text('Lamar')"
        ).first
        try:
            if not apply_btn.is_visible(timeout=3500):
                return {"status": "button_not_found", "message": "Tombol lamar tidak ditemukan atau loker sudah kedaluwarsa."}

            btn_text = apply_btn.inner_text().lower()
            if "perusahaan" in btn_text or "situs web" in btn_text or "company site" in btn_text:
                return {
                    "status": "external_link",
                    "message": "Lowongan ini mewajibkan lamaran di situs eksternal perusahaan.",
                }

            pages_before = len(self.page.context.pages)
            apply_btn.click()
            human_delay(2, 3)
            self._switch_to_latest_tab_if_opened(pages_before)

            # 3. Cek apakah diarahkan ke halaman login SEEK/JobStreet
            current_url = (self.page.url or "").lower()
            if "login.seek.com" in current_url or "/login" in current_url or "signin" in current_url:
                return {
                    "status": "login_required",
                    "message": "Sesi JobStreet belum login. Silakan login di jendela browser yang tetap terbuka, lalu selesaikan lamaran.",
                }

            confirm_before_submit = bool(self.config.get("screening_defaults", {}).get("confirm_before_submit", False))

            # 4. Jalankan loop Wizard 4 Tahap JobStreet (Pilih dokumen -> Pertanyaan -> Profil -> Review & Kirim)
            for _step in range(7):
                # Cek jika sudah terkirim
                if self._page_has_text(["lamaran Anda telah terkirim", "lamaran terkirim", "application has been sent", "application submitted"]):
                    return {"status": "success", "message": "Lamaran berhasil dikirim via JobStreet."}

                # Cek Tahap 4: Tombol Kirim Lamaran (Review dan Kirim)
                submit_btn = self.page.locator(
                    "button[data-automation='submit-button'], "
                    "button[data-automation='submit-application'], "
                    "button:has-text('Kirim lamaran'), "
                    "button:has-text('Submit application')"
                ).first
                if submit_btn.is_visible(timeout=1500):
                    if confirm_before_submit:
                        return {
                            "status": "manual_action_needed",
                            "message": "Tahap 1–3 selesai! Browser berhenti di halaman 'Review dan kirim'. Silakan cek & klik 'Kirim lamaran' di browser, lalu klik 'Sudah Saya Kirim' di dashboard.",
                        }
                    submit_btn.click()
                    human_delay(2.5, 3.5)
                    return {"status": "success", "message": "Lamaran 4 tahap berhasil dikirim via JobStreet."}

                # Cek Tahap 1: Pilih Dokumen (Resume & Surat Lamaran)
                if self._page_has_text(["pilih dokumen", "choose documents", "unggah resume", "upload a resume", "surat lamaran"]):
                    self._handle_choose_documents_step(job_title, company)
                    if self._click_continue_button():
                        continue
                    return {
                        "status": "manual_action_needed",
                        "message": "Di tahap 'Pilih dokumen' JobStreet: silakan pilih/unggah CV di jendela browser yang terbuka, lalu klik Lanjut dan selesaikan.",
                    }

                # Cek Tahap 2: Jawab Pertanyaan Perusahaan
                if self._page_has_text(["pertanyaan perusahaan", "employer questions", "jawab pertanyaan"]):
                    self.screener.auto_fill_form()
                    human_delay(0.8, 1.5)
                    url_before = self.page.url
                    if self._click_continue_button():
                        # Jika gagal lanjut karena ada pertanyaan wajib yang belum terjawab
                        if self.page.url == url_before and self._page_has_text(["wajib diisi", "required", "harus diisi", "mohon jawab"]):
                            unanswered = "; ".join(self.screener.last_unanswered[:3])
                            hint = f" ({unanswered})" if unanswered else ""
                            return {
                                "status": "manual_action_needed",
                                "message": f"Ada pertanyaan perusahaan wajib yang butuh jawaban manual{hint}. Silakan lengkapi di browser yang terbuka.",
                            }
                        continue
                    return {
                        "status": "manual_action_needed",
                        "message": "Muncul pertanyaan perusahaan JobStreet. Silakan lengkapi jawabannya di browser yang terbuka.",
                    }

                # Cek Tahap 3: Perbarui Profil JobStreet
                if self._page_has_text(["perbarui profil", "update your profile", "profil seek", "seek profile"]):
                    if self._click_continue_button():
                        continue

                # Fallback umum: jalankan screener lalu coba klik Lanjut jika ada
                self.screener.auto_fill_form()
                if self._click_continue_button():
                    continue
                break

            return {
                "status": "manual_action_needed",
                "message": "Wizard lamaran JobStreet terbuka di browser. Silakan lengkapi tahap yang tersisa di browser, lalu konfirmasi di dashboard.",
            }
        except Exception as e:
            return {"status": "error", "message": f"Terjadi kesalahan di JobStreet: {str(e)}"}
