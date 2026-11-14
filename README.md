# 🤖 Job Hunter Copilot

> **Auto Job Search & Interactive Copilot Application Tool**  
> Asisten pencari lowongan kerja & automasi lamaran semi-otomatis (Human-in-the-loop).  
> **100% Gratis**, tanpa API berbayar, aman dari banned, dan siap pakai di **Windows** & **Linux**!

---

## 🌟 Kenapa Job Hunter Copilot?

Banyak bot pelamar kerja otomatis yang gagal atau membuat akun di-*banned* karena mengirim lamaran secara membabi-buta (*blind spamming*). 

**Job Hunter Copilot hadir dengan pendekatan cerdas:**
- 🛡️ **Anti-Banned & 100% Gratis:** Menggunakan browser nyata (*persistent profile session*). Anda cukup login sekali secara manual di awal. Seterusnya sesi login tersimpan dan aman dari deteksi bot.
- 🎯 **Fitur Toggle Manual (Copilot Mode):** Anda tetap memiliki kendali penuh! Sistem akan mencari loker yang sesuai, menampilkannya di terminal, lalu Anda cukup menekan tombol:
  - `[Y]` untuk lamar otomatis (bot akan mengeklik tombol lamar dan memilih resume).
  - `[S]` untuk lewati (skip).
  - `[O]` untuk membuka halaman loker di browser sebelum memutuskan.
- 📊 **Riwayat & Pencegah Duplikat:** Loker yang sudah pernah Anda lamar atau lewati otomatis dicatat agar tidak muncul dua kali.
- 🚀 **1-Click Setup:** Tidak perlu mengetik perintah terminal rumit. Tinggal klik 1 file untuk install dan jalankan langsung.

---

## 🚀 Cara Menjalankan (Sangat Mudah!)

### 🪟 Pengguna Windows
1. Pastikan komputer Anda sudah terpasang [Python](https://www.python.org/downloads/) (centang opsi *"Add python.exe to PATH"* saat instalasi).
2. Download atau Clone repositori ini.
3. Cukup **Double-Click** file:
   ```text
   start_windows.bat
   ```
   *(Script akan otomatis membuat virtual environment, menginstal modul yang dibutuhkan, mengunduh browser Chromium, dan langsung menjalankan aplikasi).*

---

### 🐧 Pengguna Linux / macOS
1. Buka terminal di folder project ini.
2. Jalankan perintah:
   ```bash
   ./start_linux.sh
   ```
   *(Atau klik kanan `start_linux.sh` -> Run as Program).*

---

## 🎮 Cara Pemakaian

1. **Jalankan Aplikasi:** Pilih menu `[1] Jalankan Copilot`.
2. **Login Pertama Kali:**
   - Jendela browser Chromium akan terbuka.
   - Jika Anda belum login ke akun Glints, login secara manual di browser tersebut satu kali saja.
   - Tekan `ENTER` di terminal untuk melanjutkan.
3. **Mulai Review Loker:**
   - Bot akan memindai daftar lowongan sesuai kata kunci (default: `Python Developer`).
   - Setiap lowongan akan ditampilkan rapi di terminal beserta judul, nama perusahaan, gaji (jika ada), dan link.
   - Pilih aksi:
     - Tekan **`y`** (atau langsung Enter) ➡️ Bot otomatis melamar dan submit resume Anda.
     - Tekan **`s`** ➡️ Lewati loker ini.
     - Tekan **`o`** ➡️ Buka link di browser untuk melihat detail lengkap sebelum memutuskan.
     - Tekan **`q`** ➡️ Selesai dan kembali ke menu utama.

---

## ⚙️ Konfigurasi (`config.json`)

Anda bisa mengubah pengaturan kata kunci langsung dari menu aplikasi atau mengedit file `config.json`:

```json
{
  "keyword": "Backend Developer",
  "country": "ID",
  "min_delay_sec": 2,
  "max_delay_sec": 4,
  "auto_skip_already_seen": true,
  "slow_mo_ms": 200
}
```

---

## 📂 Struktur Folder Proyek

```text
job-hunter-copilot/
├── main.py              # Entry point utama aplikasi & menu interaktif (Rich)
├── config.json          # File konfigurasi kata kunci & delay
├── requirements.txt     # Daftar pustaka Python (Playwright & Rich)
├── start_windows.bat    # 1-Click launcher untuk Windows
├── start_linux.sh       # 1-Click launcher untuk Linux/macOS
├── src/
│   ├── browser.py       # Pengelola browser Playwright & persistent context
│   ├── glints.py        # Logika scraping & auto-apply Glints
│   └── storage.py       # Pengelola riwayat (applied & skipped jobs)
├── user_browser_data/   # Tempat menyimpan cookie & sesi login (tidak di-upload ke GitHub)
└── data/
    └── history.json     # Catatan riwayat lamaran Anda
```

---

## 🛡️ Disclaimer & Etika Penggunaan
Aplikasi ini ditujukan sebagai asisten pribadi (*productivity copilot*) untuk mempermudah pencari kerja mengulas dan melamar pekerjaan secara efisien. Pengguna bertanggung jawab penuh atas data yang dikirimkan ke masing-masing platform lowongan kerja.

---

## 📄 Lisensi
[MIT License](LICENSE) - Bebas digunakan, dimodifikasi, dan didistribusikan.
