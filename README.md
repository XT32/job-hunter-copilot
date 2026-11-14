# loker-cli

[![Unit Tests](https://github.com/XT32/job-hunter-copilot/actions/workflows/test.yml/badge.svg)](https://github.com/XT32/job-hunter-copilot/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Tool bantu pencari kerja untuk meninjau dan mengirim lamaran di berbagai portal loker (**Glints** & **JobStreet Indonesia**) secara semi-otomatis (*human-in-the-loop*).

Tersedia dalam 2 mode: **Web Dashboard Visual (untuk pengguna awam/umum)** dan **Terminal CLI (untuk pengguna cepat)**.

---

## 📥 Cara Pakai Tanpa Install Git (Untuk Pengguna Umum)

Bagi kamu atau teman kamu yang **tidak paham Git** atau **tidak punya Git di laptop**:

1. Klik tombol hijau **`Code`** di bagian atas halaman GitHub ini, lalu klik **`Download ZIP`** (atau [klik link download ini](https://github.com/XT32/job-hunter-copilot/archive/refs/heads/main.zip)).
2. Ekstrak file zip hasil download ke folder mana saja (misal di folder *Documents* atau *Desktop*).
3. Buka foldernya, lalu:
   - **Di Windows:** Cukup klik dua kali file **`start_windows.bat`**.
   - **Di Linux / macOS:** Buka terminal dan jalankan `./start_linux.sh`.
4. Pilih opsi **`[1] Web Dashboard`** (atau cukup tekan `ENTER`). Halaman dashboard visual akan otomatis terbuka di browser kamu!

> *Catatan: Pastikan komputer kamu sudah terpasang [Python](https://www.python.org/downloads/) (versi 3.8 ke atas). Di Windows, pastikan mencentang "Add python.exe to PATH" saat menginstall Python.*

---

## 🌟 Pilihan Mode Tampilan

### 1. Web Dashboard Visual (`web_app.py`)
Cocok untuk pengguna yang menyukai tampilan visual:
- Tampilan berbasis kartu lowongan (Judul, Perusahaan, Gaji, Lokasi).
- Tombol aksi visual: **`✅ Lamar Otomatis`**, **`⏭️ Lewati`**, dan **`🔗 Buka Link`**.
- Form pengaturan profil jurusan dan filter kata kunci tanpa perlu edit file JSON.
- Tabel riwayat interaktif dengan tombol **`📥 Unduh Rekap (CSV/Excel)`**.

### 2. Terminal CLI (`main.py`)
Cocok untuk pengguna teknis yang menginginkan eksekusi super cepat dan hemat resource.

---

## 🛡️ Karakteristik & Keamanan

- **Multi-Platform Support:** Mendukung **Glints Indonesia** dan **JobStreet Indonesia (SEEK)**.
- **Sistem Profil & Filter Jurusan (`src/matcher.py`):** Tidak asal tembak lowongan. Kamu dapat mengatur jurusan/bidang, kata kunci target, serta tingkat pengalaman (Fresh Graduate, Junior, Mid, Senior).
- **Auto-Blacklist & Anti-Zonk:** Otomatis melewati lowongan yang tidak relevan, loker penipuan/sales lapangan, atau posisi yang levelnya terlalu tinggi (misal: posisi "Lead/Manager" jika profil kamu adalah Fresh Graduate).
- **Kendali Manual (Human-in-the-loop):** Setiap lowongan yang lolos filter ditampilkan untuk kamu putuskan apakah ingin dilamar atau dilewati.
- **Deteksi Tautan Eksternal:** Lowongan yang mengarahkan ke form eksternal (Workable, Greenhouse, dsb) dideteksi dan dilewati secara aman.
- **Ekspor Riwayat ke CSV/Excel:** Seluruh riwayat lamaran dapat diunduh kapan saja untuk arsip pribadi atau pelaporan.
- **Konservasi Memori (Low RAM):** Menggunakan flag Chromium khusus (`--disable-gpu`, `--renderer-process-limit=2`, dll) agar tetap lancar di perangkat dengan RAM 4GB.
- **Sesi Lokal Aman:** Sesi login disimpan di direktori lokal (`user_browser_data/`) dan otomatis diabaikan oleh Git, sehingga data kredensial tidak pernah keluar dari komputer pengguna.

---

## Persyaratan Sistem

- **Sistem Operasi:** Windows 10/11, Linux, atau macOS.
- **RAM:** Minimal 4 GB (disarankan 8 GB).
- **Python:** Versi 3.8 ke atas.
- **Koneksi Internet:** Diperlukan untuk mengakses portal lowongan.

---

## Menjalankan Unit Tests

Repositori ini dilengkapi rangkaian pengujian otomatis:

```bash
python -m unittest discover tests -v
```

---

## Lisensi
[MIT](LICENSE)
