# loker-cli

[![Unit Tests](https://github.com/XT32/job-hunter-copilot/actions/workflows/test.yml/badge.svg)](https://github.com/XT32/job-hunter-copilot/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

CLI tool untuk meninjau dan mengirim lamaran kerja di berbagai portal loker (**Glints** & **JobStreet Indonesia**) secara semi-otomatis (*human-in-the-loop*).

Dirancang untuk menghemat waktu browsing puluhan tab tanpa risiko akun kena penalti, tanpa biaya API pihak ketiga, dan ramah untuk laptop dengan spesifikasi standar/rendah.

---

## Karakteristik & Fitur Utama

- **Multi-Platform Support:** Mendukung **Glints Indonesia** dan **JobStreet Indonesia (SEEK)** melalui antarmuka seragam (`BaseJobHunter`).
- **Sistem Profil & Filter Jurusan (`src/matcher.py`):** Tidak asal tembak lowongan. Anda dapat mengatur jurusan/bidang, kata kunci target, serta tingkat pengalaman (Fresh Graduate, Junior, Mid, Senior).
- **Auto-Blacklist & Anti-Zonk:** Otomatis melewati lowongan yang tidak relevan, loker penipuan/sales lapangan, atau posisi yang levelnya terlalu tinggi (misal: posisi "Lead/Manager" jika profil Anda adalah Fresh Graduate).
- **Kendali Manual (Human-in-the-loop):** Setiap lowongan yang lolos filter ditampilkan ringkasannya di terminal, dan pengguna yang memutuskan: melamar (`y`), melewati (`s`), atau membuka tab detail (`o`).
- **Deteksi Tautan Eksternal:** Lowongan yang mengarahkan ke form eksternal (Workable, Greenhouse, dsb) dideteksi dan dilewati secara aman agar tidak memicu error.
- **Ekspor Riwayat ke CSV/Excel:** Seluruh riwayat lamaran (terkirim maupun dilewati) dapat diekspor langsung ke `data/riwayat_lamaran.csv` untuk arsip pribadi atau pelaporan.
- **Konservasi Memori (Low RAM):** Menggunakan flag Chromium khusus (`--disable-gpu`, `--renderer-process-limit=2`, dll) agar tetap lancar di perangkat dengan RAM 4GB.
- **Sesi Lokal Aman:** Sesi login disimpan di direktori lokal (`user_browser_data/`) dan otomatis diabaikan oleh Git, sehingga data kredensial tidak pernah keluar dari komputer pengguna.

---

## Persyaratan Sistem

- **Sistem Operasi:** Windows 10/11, Linux, atau macOS.
- **RAM:** Minimal 4 GB (disarankan 8 GB).
- **Python:** Versi 3.8 ke atas.
- **Koneksi Internet:** Diperlukan untuk mengakses portal lowongan.

---

## Cara Menjalankan

### Windows
1. Pastikan Python sudah terpasang dan opsi **"Add python.exe to PATH"** dicentang saat instalasi.
2. Clone atau unduh repositori ini.
3. Jalankan dengan klik dua kali file:
   ```text
   start_windows.bat
   ```
   *(Script otomatis membuat virtual environment, memasang pustaka yang diperlukan, dan menjalankan program).*

### Linux / macOS
Jalankan melalui terminal:
```bash
chmod +x start_linux.sh
./start_linux.sh
```

---

## Alur Penggunaan

1. **Onboarding Awal:** Saat pertama kali dijalankan, sistem otomatis menanyakan jurusan, kata kunci target, dan tingkat pengalaman Anda.
2. **Pilih Platform:** 
   - Opsi `[1]` untuk Glints Indonesia.
   - Opsi `[2]` untuk JobStreet Indonesia.
3. **Login Browser:** Browser akan terbuka. Jika belum login ke akun portal terkait, lakukan login satu kali di jendela browser, lalu tekan `ENTER` di terminal.
4. **Review Lowongan:**
   - Tekan **`y`** (atau `Enter`) untuk melamar otomatis.
   - Tekan **`s`** untuk melewati.
   - Tekan **`o`** untuk melihat detail di browser sebelum memutuskan.
   - Tekan **`q`** untuk berhenti dan kembali ke menu.
5. **Ekspor Laporan:** Pilih opsi `[3]` untuk melihat riwayat dan mengekspor data ke file CSV.

---

## Menjalankan Unit Tests

Repositori ini dilengkapi rangkaian pengujian otomatis tanpa dependensi eksternal:

```bash
python -m unittest discover tests -v
```

---

## Lisensi
[MIT](LICENSE)
