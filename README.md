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

### 2. Detektor Lowongan Zonk & Modus Penipuan (`src/scam_detector.py`)
Menganalisis teks lowongan secara heuristik lokal untuk melindungi pencari kerja dari modus penipuan:
- ⚠️ Deteksi **klausul tahan ijazah asli** & denda penalti tidak wajar.
- ⚠️ Deteksi **permintaan pungutan uang** (biaya formulir, uang seragam, tes kesehatan/psikotes berbayar, agen tiket travel).
- ⚠️ Deteksi **penipuan kirim undangan via file APK WhatsApp** (`.apk`, *unduh surat panggilan.apk*).
- ⚠️ Deteksi **modus tugas pesanan e-commerce / deposit saldo berbayar**.
- ⚠️ Deteksi **perusahaan pialang berjangka / futures / forex** terselubung.
- ⚠️ Deteksi modus interview fiktif di titik rawan (ruko Senen, Harmoni, dll).

### 3. Pengelolaan Banyak CV (Multi-CV) & Skor Kecocokan ATS (`src/cv_analyzer.py`)
- Unggah dan kelola beberapa variasi CV (misal: versi IT, Administrasi, Desain).
- Tetapkan salah satu sebagai **CV Aktif** dengan 1 klik.
- Sistem mengekstrak keahlian dan mengalkulasi persentase kecocokan ATS (*Applicant Tracking System*) secara langsung pada setiap kartu lowongan yang ditemukan.

### 4. Panduan Standar Gaji & Rekomendasi UMR 2024/2025 (`src/salary_guide.py`)
- Dilengkapi database Upah Minimum Regional/Kota (UMR/UMK) resmi untuk kota-kota utama (DKI Jakarta, Surabaya, Bandung, Semarang, Karawang, Bekasi, Yogyakarta, Medan, dll).
- Memberikan rekomendasi rentang gaji yang sehat sesuai jenjang pengalaman (*Fresh Graduate*, *Junior*, *Internship*) agar pelamar tidak memasukkan angka di bawah standar upah.

### 5. Auto-Fill Pertanyaan Screening (`src/screener.py`)
Mendeteksi dan mengisi otomatis kuesioner umum saat pop-up lamaran muncul:
- Ekspektasi gaji default.
- Notice period.
- Pengalaman kerja (tahun).
- Kota domisili & kesediaan WFO.

### 6. Generator Cover Letter Instan Bahasa Indonesia & Inggris (`src/cover_letter.py`)
Menghasilkan surat lamaran kerja yang dipersonalisasi sesuai nama pelamar, nama perusahaan tujuan, dan posisi:
- Pilihan gaya Bahasa Indonesia: **Formal Korporat**, **Fresh Graduate**, dan **Program Pemagangan**.
- Pilihan gaya Bahasa Inggris: **Formal Corporate (English)** dan **Fresh Graduate / Entry Level (English)** untuk lowongan startup internasional & multinasional.

### 7. Papan Pelacak Status Lamaran & Mini Analytics (Kanban Pipeline)
Melacak perkembangan lamaran pekerjaan dalam 4 tahapan:
- 📨 **Terkirim (Applied)**
- 💬 **Panggilan Interview**
- 🏆 **Offering / Diterima**
- ❌ **Ditolak / Gugur**
- 🔍 **Pencarian Real-Time:** Filter kartu lowongan berdasarkan posisi, perusahaan, atau catatan secara instan tanpa batasan kuota tampilan.
- ✏️ **Edit Catatan & 🗑️ Hapus:** Perbarui info link interview/nomor HR atau hapus lamaran uji coba langsung dari papan Kanban.
- 🧹 **Bersihkan Massal:** Tombol 1-klik untuk membersihkan seluruh riwayat lamaran yang ditolak agar papan Kanban tetap rapi.
- 📥 **Ekspor CSV/Excel & Kalender (.ics):** Unduh jadwal interview langsung ke Google/Outlook/Apple Calendar atau ekspor CSV dengan 1 klik.

### 8. Kirim Lamaran Email (1-Click Gmail Draft / Mailto / SMTP)
Untuk lowongan yang meminta kirim email langsung ke HRD:
- **🌐 Buka di Gmail Web (1-Klik):** Langsung membuka tab draf Gmail di browser dengan Subjek dan Isi Surat terisi rapi tanpa perlu konfigurasi kata sandi aplikasi.
- **✉️ Buka Mail App (Mailto):** Membuka aplikasi email bawaan sistem operasi.
- **⚙️ Kirim via SMTP:** Opsi otomatis kirim via server SMTP (mendukung Port 465 SSL dan Port 587 TLS/STARTTLS) beserta lampiran file PDF CV.

### 9. Notifikasi Telegram Bot Gratis & Tombol Tes Koneksi (`src/notifier.py`)
Menerima pemberitahuan langsung di aplikasi Telegram pribadi saat bot menemukan lowongan yang cocok dengan jurusan/profil kamu.
- Dilengkapi **Panduan Setup 1 Menit** di Dashboard (`@BotFather` & `@userinfobot`).
- Tombol **`🧪 Tes Sambungan ke Telegram`** langsung di Dashboard Web untuk menguji token dan chat ID secara instan dengan pesan konfirmasi masuk ke ponsel kamu.

### 10. Cadangan Data & Pemulihan Penuh (Backup & Restore JSON)
- **💾 Cadangkan Data:** Unduh seluruh konfigurasi profil, pengaturan screening, dan riwayat lamaran dalam format JSON dengan 1 klik.
- **📥 Pulihkan Data:** Unggah kembali berkas cadangan JSON saat berganti perangkat atau menginstal ulang tanpa kehilangan riwayat atau CV.

---

## 🛡️ Karakteristik Keamanan, Privasi & Resource

- **Privasi CV 100% Lokal:** File CV (`attachments/`), riwayat lamaran (`data/`), dan konfigurasi disimpan sepenuhnya di komputer kamu. Direktori `attachments/` dilindungi `.gitignore` sehingga tidak akan pernah terunggah ke repositori GitHub.
- **Bebas Telemetri & API Pihak Ketiga:** Analisis kecocokan ATS, ekstraksi teks, dan penulisan cover letter dihitung secara lokal tanpa mengirim data pribadi ke server eksternal atau AI cloud berbayar.
- **Konservasi Memori (Low RAM):** Menggunakan flag Chromium khusus (`--disable-gpu`, `--renderer-process-limit=2`, dll) agar tetap lancar di perangkat dengan RAM 4GB.
- **Sesi Lokal Aman:** Sesi login disimpan di direktori lokal (`user_browser_data/`) dan otomatis diabaikan oleh Git, sehingga data kredensial tidak pernah keluar dari komputer pengguna.
- **Dukungan Reverse Proxy & Local Domain:** Mendukung domain lokal (`.local`, `.test`, atau reverse proxy Nginx/Caddy seperti `https://xt32.local`) dengan proteksi Origin CSRF dinamis dan port binding via env `PORT`/`HOST`.
- **Mode Senyap (Headless):** Opsi pemindaian lowongan di latar belakang tanpa membuka jendela peramban saat pengguna sedang sibuk.
- **Human-in-the-loop:** Pengguna memegang kendali penuh atas keputusan melamar atau melewati setiap lowongan.

---

## 🤝 Berkontribusi
Tertarik menambahkan dukungan portal lowongan kerja baru atau memperbaiki bug? Silakan baca panduan lengkap di [CONTRIBUTING.md](CONTRIBUTING.md).

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
