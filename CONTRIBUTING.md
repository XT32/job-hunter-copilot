# Panduan Kontribusi (Contributing Guide)

Terima kasih atas ketertarikanmu untuk berkontribusi pada pengembangan **loker-cli**! Proyek ini bersifat *open-source*, gratis selamanya, dan bertujuan membantu para pencari kerja serta pemagang di Indonesia.

---

## 🧭 Prinsip Utama Proyek
1. **100% Gratis & Mandiri:** Dilarang menambahkan dependensi API AI berbayar (seperti OpenAI API key, Claude API key). Semua ekstraksi teks, pencocokan kata kunci, dan scoring harus berjalan lokal di komputer pengguna.
2. **Privasi Pengguna Terjaga:** Kredensial, cookies, dan CV pengguna tidak boleh dikirim ke server pihak ketiga mana pun.
3. **Ramah Pengguna Awam:** Tetap sediakan skrip launcher 1-klik (`.bat` dan `.sh`) serta visual web dashboard untuk pengguna non-teknis.

---

## 🛠️ Menambahkan Portal Lowongan Kerja Baru

Jika kamu ingin menambahkan scraper/integrasi portal loker baru (misalnya *Kalibrr*, *Karir.com*, atau lainnya):

1. Buat file baru di direktori `src/` (misal: `src/kalibrr.py`).
2. Warisi class abstrak `BaseHunter` dari `src/base_hunter.py`:
   ```python
   from src.base_hunter import BaseHunter

   class KalibrrHunter(BaseHunter):
       def search_jobs(self):
           # Logika pemindaian lowongan kerja
           ...

       def apply_job(self, job_url):
           # Logika melamar / membuka lowongan
           ...
   ```
3. Daftarkan class hunter baru ke `HUNTER_MAP` di:
   - `web_app.py`
   - `main.py`
4. Buat unit test di `tests/test_kalibrr.py` untuk menguji parsing dan inisialisasi tanpa membuka browser asli.

---

## 🧪 Menjalankan Pengujian (Unit Tests)

Sebelum mengirimkan Pull Request, pastikan seluruh pengujian lokal berhasil lolos (0 failure, 0 error):

```bash
python -m unittest discover tests -v
```

---

## 🚀 Alur Pengajuan Pull Request (PR)

1. *Fork* repositori ini ke akun GitHub kamu.
2. Buat *feature branch* baru:
   ```bash
   git checkout -b feat/tambah-portal-kalibrr
   ```
3. Lakukan *commit* dengan pesan yang jelas (format Conventional Commits disarankan):
   ```bash
   git commit -m "feat: add Kalibrr job board scraper and screening handler"
   ```
4. *Push* branch kamu dan buka **Pull Request** ke branch `main`.
5. Pastikan semua *checks* di GitHub Actions (Ubuntu & Windows matrix) berstatus hijau (pass).
