# loker-cli

[![Unit Tests](https://github.com/XT32/job-hunter-copilot/actions/workflows/test.yml/badge.svg)](https://github.com/XT32/job-hunter-copilot/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Platform asisten pencari kerja & pemagangan multi-portal (**Glints**, **JobStreet Indonesia**, **MagangHub Kemnaker**, dan **Dealls Jobs**) secara semi-otomatis (*human-in-the-loop*).

Tersedia dalam 2 mode: **Web Dashboard Visual (untuk pengguna umum/awam)** dan **Terminal CLI (untuk pengguna cepat)**.

---

## 📥 Cara Pakai Tanpa Install Git (Untuk Pengguna Umum)

Bagi kamu yang **tidak paham Git** atau **tidak punya Git di komputer**:

1. Klik tombol hijau **`Code`** di bagian atas halaman GitHub ini, lalu klik **`Download ZIP`** (atau [klik tautan download zip ini](https://github.com/XT32/job-hunter-copilot/archive/refs/heads/main.zip)).
2. Ekstrak file zip hasil download ke folder mana saja (misal di folder *Documents* atau *Desktop*).
3. Buka foldernya, lalu:
   - **Di Windows:** Cukup klik dua kali file **`start_windows.bat`** (atau `start_web_windows.bat`).
   - **Di Linux / macOS:** Buka terminal dan jalankan `./start_linux.sh` (atau `./start_web_linux.sh`).
4. Pilih opsi **`[1] Web Dashboard`** (atau cukup tekan `ENTER`). Halaman dashboard visual akan otomatis terbuka di browser kamu!

> *Catatan: Pastikan komputer kamu sudah terpasang [Python](https://www.python.org/downloads/) (versi 3.8 ke atas). Di Windows, pastikan mencentang "Add python.exe to PATH" saat menginstall Python.*

---

## 🌟 Fitur & Kemampuan Lengkap

### 1. Multi-Platform Support (4 Portal Terbesar di Indonesia)
- **Glints Indonesia** (Lamar Cepat lowongan teknologi, startup & korporat).
- **JobStreet Indonesia (SEEK)** (Menggunakan selector resmi data-automation SEEK).
- **MagangHub Kemnaker** (Program Pemagangan Nasional resmi Kementerian Ketenagakerjaan RI).
- **Dealls Jobs Indonesia** (Pilihan posisi full-time, part-time & internship terkemuka).

### 2. Pengecekan Skor Kecocokan ATS (`src/cv_analyzer.py`)
- Unggah file PDF CV kamu langsung di Web Dashboard.
- Sistem mengekstrak keahlian dan mengalkulasi persentase kecocokan ATS (Applicant Tracking System) secara langsung pada setiap kartu lowongan yang ditemukan.

### 3. Auto-Fill Pertanyaan Screening (`src/screener.py`)
Mendeteksi dan mengisi otomatis kuesioner umum saat pop-up lamaran muncul:
- Ekspektasi gaji default.
- Notice period.
- Pengalaman kerja (tahun).
- Kota domisili & kesediaan WFO.

### 4. Generator Cover Letter Instan (`src/cover_letter.py`)
Menghasilkan surat lamaran kerja yang dipersonalisasi sesuai nama pelamar, nama perusahaan tujuan, dan posisi:
- Pilihan gaya: **Formal Korporat**, **Fresh Graduate**, dan **Program Pemagangan**.

### 5. Papan Pelacak Status Lamaran (Kanban Pipeline)
Melacak perkembangan lamaran pekerjaan dalam 4 tahapan:
- 📨 **Terkirim (Applied)**
- 💬 **Panggilan Interview**
- 🏆 **Offering / Diterima**
- ❌ **Ditolak / Gugur**
Lengkap dengan fitur **Ekspor CSV/Excel** dengan 1 klik.

### 6. Modul Direct Cold-Email (`src/email_sender.py`)
Untuk lowongan yang tidak memiliki tombol apply di web (misal di Twitter atau LinkedIn yang meminta kirim email langsung ke HRD):
- Kirim email profesional via SMTP (Gmail App Password).
- Lampirkan file PDF CV secara otomatis.

### 7. Notifikasi Telegram Bot Gratis (`src/notifier.py`)
Menerima pemberitahuan langsung di aplikasi Telegram pribadi saat bot menemukan lowongan yang cocok dengan jurusan/profil kamu.

### 8. Cadangan Data (Backup & Restore)
Unduh seluruh konfigurasi dan riwayat lamaran dalam format JSON dengan tombol **Backup** di pojok kanan atas dashboard.

---

## 🛡️ Karakteristik Keamanan & Resource

- **Konservasi Memori (Low RAM):** Menggunakan flag Chromium khusus (`--disable-gpu`, `--renderer-process-limit=2`, dll) agar tetap lancar di perangkat dengan RAM 4GB.
- **Sesi Lokal Aman:** Sesi login disimpan di direktori lokal (`user_browser_data/`) dan otomatis diabaikan oleh Git, sehingga data kredensial tidak pernah keluar dari komputer pengguna.
- **Human-in-the-loop:** Pengguna memegang kendali penuh atas keputusan melamar atau melewati setiap lowongan.

---

## Persyaratan Sistem

- **Sistem Operasi:** Windows 10/11, Linux, atau macOS.
- **RAM:** Minimal 4 GB (disarankan 8 GB).
- **Python:** Versi 3.8 ke atas.
- **Koneksi Internet:** Diperlukan untuk mengakses portal lowongan.

---

## Menjalankan Unit Tests

Repositori ini dilengkapi rangkaian 21 pengujian otomatis tanpa dependensi eksternal:

```bash
python -m unittest discover tests -v
```

---

## Lisensi
[MIT](LICENSE)
