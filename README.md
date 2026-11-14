# loker-cli

[![Unit Tests](https://github.com/XT32/job-hunter-copilot/actions/workflows/test.yml/badge.svg)](https://github.com/XT32/job-hunter-copilot/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

CLI tool untuk mempermudah peninjauan dan pengiriman lamaran kerja di portal loker secara semi-otomatis (*human-in-the-loop*).

Dirancang untuk menghemat waktu browsing puluhan tab tanpa risiko akun kena penalti, tanpa biaya API pihak ketiga, dan ramah untuk laptop dengan spesifikasi standar/rendah.

---

## Karakteristik & Keamanan

- **Sistem Profil & Filter Jurusan (`src/matcher.py`):** Tidak asal tembak lowongan. Anda dapat mengatur jurusan/bidang, kata kunci target, serta tingkat pengalaman (Fresh Graduate, Junior, Mid, Senior).
- **Auto-Blacklist & Anti-Zonk:** Otomatis melewati lowongan yang tidak relevan, loker penipuan/sales lapangan, atau posisi yang levelnya terlalu tinggi (misal: posisi "Lead/Manager" jika profil Anda adalah Fresh Graduate).
- **Kendali Manual (Human-in-the-loop):** Setiap lowongan yang lolos filter ditampilkan ringkasannya di terminal, dan pengguna yang memutuskan: melamar (`y`), melewati (`s`), atau membuka tab detail (`o`).
- **Deteksi Tautan Eksternal:** Lowongan yang mengarahkan ke form eksternal (Workable, Greenhouse, dsb) dideteksi dan dilewati secara aman agar tidak memicu error.
- **Konservasi Memori (Low RAM):** Menggunakan flag Chromium khusus (`--disable-gpu`, `--renderer-process-limit=2`, dll) agar tetap lancar di perangkat dengan RAM 4GB.
- **Sesi Lokal Aman:** Sesi login disimpan di direktori lokal (`user_browser_data/`) dan otomatis diabaikan oleh Git, sehingga data kredensial tidak pernah keluar dari komputer pengguna.
- **Pencatat Riwayat:** Setiap lowongan yang sudah diproses disimpan di `data/history.json` agar tidak ditinjau berulang kali.

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

1. Buka menu utama dan pilih opsi `[3] Atur Profil & Kata Kunci Jurusan` untuk menyesuaikan bidang Anda (misal: Akuntansi, Desain Grafis, IT, Marketing) serta tingkat pengalaman.
2. Pilih opsi `[1] Jalankan Review & Lamar`.
3. Browser akan terbuka. Jika belum login ke Glints, lakukan login satu kali secara manual di jendela browser tersebut.
4. Kembali ke terminal dan tekan `ENTER`.
5. Sistem akan memindai lowongan dan otomatis menyaringnya menggunakan filter profil.
6. Untuk setiap lowongan yang tampil:
   - Tekan **`y`** (atau `Enter`) untuk melamar.
   - Tekan **`s`** untuk melewati.
   - Tekan **`o`** untuk melihat detail di browser sebelum menentukan pilihan.
   - Tekan **`q`** untuk berhenti dan kembali ke menu.

---

## Konfigurasi (`config.json`)

Pengaturan dapat disesuaikan langsung melalui menu program atau mengedit file `config.json`:

```json
{
  "profile": {
    "field_or_major": "Akuntansi",
    "target_keywords": [
      "Staff Akuntansi",
      "Finance Staff",
      "Tax Officer"
    ],
    "experience_level": "fresh_graduate",
    "work_type": "all",
    "preferred_locations": ["Jakarta", "Remote"],
    "blacklist_keywords": [
      "Senior",
      "Manager",
      "Head of",
      "SPG",
      "Sales Lapangan",
      "Canvasser"
    ]
  },
  "country": "ID",
  "min_delay_sec": 2,
  "max_delay_sec": 4,
  "auto_skip_already_seen": true,
  "slow_mo_ms": 150
}
```

---

## Menjalankan Unit Tests

Repositori ini dilengkapi rangkaian pengujian otomatis tanpa dependensi eksternal:

```bash
python -m unittest discover tests -v
```

---

## Lisensi
[MIT](LICENSE)
