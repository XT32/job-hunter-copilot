# loker-cli

CLI tool untuk mempermudah peninjauan dan pengiriman lamaran kerja di portal loker secara semi-otomatis (*human-in-the-loop*).

Dirancang untuk menghemat waktu browsing puluhan tab tanpa risiko akun kena penalti, tanpa biaya API pihak ketiga, dan ramah untuk laptop dengan spesifikasi standar/rendah.

---

## Karakteristik & Keamanan

- **Kendali Manual (Human-in-the-loop):** Bukan bot spam yang melamar membabi-buta. Setiap lowongan ditampilkan ringkasannya di terminal, dan pengguna yang memutuskan: melamar (`y`), melewati (`s`), atau membuka tab detail (`o`).
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

1. Buka menu utama dan pilih opsi `[1] Jalankan Review & Lamar`.
2. Browser akan terbuka. Jika belum login ke Glints, lakukan login satu kali secara manual di jendela browser tersebut.
3. Kembali ke terminal dan tekan `ENTER`.
4. Sistem akan mencari lowongan sesuai kata kunci yang diatur di `config.json`.
5. Untuk setiap lowongan yang tampil:
   - Tekan **`y`** (atau `Enter`) untuk melamar.
   - Tekan **`s`** untuk melewati.
   - Tekan **`o`** untuk melihat detail di browser sebelum menentukan pilihan.
   - Tekan **`q`** untuk berhenti dan kembali ke menu.

---

## Konfigurasi (`config.json`)

Pengaturan dapat disesuaikan langsung melalui menu program atau mengedit file `config.json`:

```json
{
  "keyword": "Python Developer",
  "country": "ID",
  "min_delay_sec": 2,
  "max_delay_sec": 4,
  "auto_skip_already_seen": true,
  "slow_mo_ms": 150
}
```

---

## Lisensi
[MIT](LICENSE)
