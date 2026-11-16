"""
Modul Detektor Indikasi Risiko & Pola Red Flag Lowongan Kerja (Scam Heuristic).
Berjalan 100% lokal tanpa API berbayar menggunakan heuristik pola kata kunci.

PENTING (DISCLAIMER HUKUM & REKAYASA):
Deteksi ini bekerja berbasis heuristik pencocokan pola teks (keyword pattern matching)
dan TIDAK mewakili verifikasi legalitas resmi suatu badan usaha/perusahaan.
Hasil deteksi harus dipahami sebagai "Indikasi Risiko" guna meningkatkan kehati-hatian
pencari kerja, BUKAN vonis hukum bahwa perusahaan tersebut pasti melakukan penipuan.
"""

import re

# 1. Pola Tahan Dokumen / Ijazah Asli
TAHAN_IJAZAH_PATTERNS = [
    r"tahan\s+ijazah",
    r"penahanan\s+ijazah",
    r"ijazah\s+asli\s+ditahan",
    r"menahan\s+ijazah",
    r"jaminan\s+ijazah\s+asli",
    r"menitipkan\s+ijazah\s+asli",
    r"ijazah\s+sebagai\s+jaminan",
    r"ijazah\s+disimpan\s+perusahaan"
]

# 2. Pola Pungutan Biaya / Uang di Muka (Scam Klasik)
PUNGUTAN_BIAYA_PATTERNS = [
    r"uang\s+seragam",
    r"biaya\s+seragam",
    r"biaya\s+formulir",
    r"biaya\s+pendaftaran",
    r"uang\s+jaminan\s+awal",
    r"biaya\s+administrasi",
    r"biaya\s+registrasi",
    r"biaya\s+tes\s+kesehatan",
    r"biaya\s+psikotes",
    r"travel\s+agent\s+resmi\s+yang\s+ditunjuk",
    r"agen\s+perjalanan\s+yang\s+ditunjuk",
    r"uang\s+pengganti\s+tiket",
    r"reimbursement\s+tiket\s+pesawat",
    r"biaya\s+akomodasi\s+akan\s+diganti",
    r"biaya\s+tiket\s+ditalangi\s+dahulu",
    r"biaya\s+transportasi\s+dan\s+penginapan\s+ditanggung\s+peserta"
]

# 3. Pialang Berjangka / Futures / Trading / Forex Bodong
BERJANGKA_FUTURES_PATTERNS = [
    r"pialang\s+berjangka",
    r"perdagangan\s+berjangka",
    r"commodity\s+futures",
    r"forex\s+trading",
    r"rifan\s+financindo",
    r"solid\s+gold\s+berjangka",
    r"bestprofit\s+futures",
    r"valbury",
    r"equityworld\s+futures",
    r"kontak\s+perkasa\s+futures",
    r"trader\s+binary",
    r"mencari\s+investor\s+trading"
]

# 4. Modus Langsung Kerja Tanpa Seleksi / Iming-iming Palsu
IMING_PALSU_PATTERNS = [
    r"langsung\s+kerja\s+tanpa\s+tes",
    r"tanpa\s+seleksi\s+langsung\s+penempatan",
    r"pasti\s+diterima\s+100%",
    r"penghasilan\s+\d+\s*juta\s+per\s+hari",
    r"hanya\s+bermodal\s+hp\s+dapat\s+\d+",
    r"like\s+and\s+subscribe\s+dibayar"
]

# 5. Lokasi Ruko Rawan Penipuan Massal
LOKASI_RAWAN_PATTERNS = [
    r"ruko\s+senen",
    r"kawasan\s+senen\s+raya",
    r"kawasan\s+harmoni\s+raya",
    r"ruko\s+rawa\s+bokor",
    r"roxy\s+square\s+lt\s*\d+",
    r"ruko\s+grand\s+mall\s+bekasi"
]

# 6. Modus Malware APK / Dokumen Undangan Palsu
MALWARE_APK_PATTERNS = [
    r"\.apk\b",
    r"unduh\s+surat\s+undangan\.apk",
    r"install\s+file\s+apk",
    r"surat_panggilan_interview\.apk",
    r"klik\s+link\s+apk"
]

# 7. Modus Tugas Berbayar / Deposit Saldo E-Commerce
DEPOSIT_TASK_PATTERNS = [
    r"deposit\s+saldo",
    r"top\s*up\s+saldo\s+awal",
    r"tugas\s+pesanan\s+e-commerce",
    r"transfer\s+deposit",
    r"menyelesaikan\s+misi\s+pesanan"
]

# 8. Modus Registrasi Pinjol / Paylater / Buka Rekening Fiktif
PINJOL_PAYLATER_PATTERNS = [
    r"aktivasi\s+akun\s+paylater",
    r"pendaftaran\s+pinjaman\s+online",
    r"buka\s+rekening\s+bank\s+baru\s+untuk",
    r"verifikasi\s+limit\s+kredit",
    r"kuota\s+limit\s+pinjaman",
    r"foto\s+selfie\s+memegang\s+ktp\s+dan\s+buku\s+tabungan",
    r"wajib\s+memiliki\s+limit\s+akulaku",
    r"wajib\s+memiliki\s+limit\s+kredivo"
]

def check_for_red_flags(title: str, company: str, description: str = "", location: str = "") -> dict:
    """
    Menganalisis teks lowongan kerja untuk mendeteksi potensi bahaya, klausul tahan ijazah, atau penipuan.
    
    Returns:
        dict: {
            "is_red_flag": bool,
            "risk_level": "safe" | "warning" | "danger",
            "flags": list of str,
            "advice": str
        }
    """
    full_text = f"{title} {company} {description} {location}".lower()
    flags = []

    # Cek tahan ijazah (Tingkat DANGER)
    for p in TAHAN_IJAZAH_PATTERNS:
        if re.search(p, full_text):
            flags.append("Klausul Tahan Ijazah Asli (Sangat Berisiko)")
            break

    # Cek pungutan biaya (Tingkat DANGER)
    for p in PUNGUTAN_BIAYA_PATTERNS:
        if re.search(p, full_text):
            flags.append("Permintaan Uang / Biaya Seragam / Tiket (Indikasi Penipuan)")
            break

    # Cek pialang berjangka / futures (Tingkat WARNING/DANGER)
    for p in BERJANGKA_FUTURES_PATTERNS:
        if re.search(p, full_text):
            flags.append("Pialang Berjangka / Forex / Trading Komoditas")
            break

    # Cek iming-iming palsu / MLM / like-subscribe (Tingkat DANGER)
    for p in IMING_PALSU_PATTERNS:
        if re.search(p, full_text):
            flags.append("Iming-iming Langsung Kerja Tanpa Seleksi / Task Scam")
            break

    # Cek lokasi rawan ruko penipuan (Tingkat WARNING)
    for p in LOKASI_RAWAN_PATTERNS:
        if re.search(p, full_text):
            flags.append("Alamat Ruko / Titik Lokasi Rawan Modus Interview Fiktif")
            break

    # Cek penyusupan file APK berbahaya (Tingkat DANGER)
    for p in MALWARE_APK_PATTERNS:
        if re.search(p, full_text):
            flags.append("Indikasi File APK Mencurigakan / Malware Undangan")
            break

    # Cek permintaan deposit saldo atau misi pesanan (Tingkat DANGER)
    for p in DEPOSIT_TASK_PATTERNS:
        if re.search(p, full_text):
            flags.append("Modus Deposit Saldo / Misi Pesanan E-Commerce Berbayar")
            break

    # Cek modus pinjol / paylater / buka rekening (Tingkat DANGER)
    for p in PINJOL_PAYLATER_PATTERNS:
        if re.search(p, full_text):
            flags.append("Modus Registrasi Paylater / Pinjol / Buka Rekening Fiktif (Indikasi Penipuan Identitas)")
            break

    is_red_flag = len(flags) > 0
    if not is_red_flag:
        return {
            "is_red_flag": False,
            "risk_level": "safe",
            "flags": [],
            "advice": "Lowongan tampak wajar dan aman."
        }

    # Tentukan risk level
    has_danger = any(
        "Tahan Ijazah" in f or "Permintaan Uang" in f or "Iming-iming" in f or "APK" in f or "Deposit" in f or "Paylater" in f or "Pinjol" in f
        for f in flags
    )
    risk_level = "danger" if has_danger else "warning"

    advice = (
        "INDIKASI RISIKO TINGGI: Teks lowongan memuat pola red flag (klausul pungutan biaya / tahan ijazah / file APK / deposit / paylater). "
        "Perusahaan kredibel tidak memungut biaya tes/seragam. Perhatian: ini adalah deteksi heuristik pola teks, bukan vonis hukum resmi. Hindari menyerahkan uang atau dokumen berharga!"
        if risk_level == "danger" else
        "INDIKASI RISIKO SEDANG: Terdeteksi pola kata kunci berisiko (alamat ruko rawan / komoditas berjangka). "
        "Lakukan riset mandiri terkait kredibilitas perusahaan sebelum menghadiri interview."
    )

    return {
        "is_red_flag": True,
        "risk_level": risk_level,
        "flags": flags,
        "advice": advice
    }
