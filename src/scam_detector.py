"""
Modul Detektor Lowongan Zonk, Scam, Pialang Berjangka & Klausul Tahan Ijazah.
Berjalan 100% lokal tanpa API berbayar menggunakan heuristik pola kata kunci.
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
    r"uang\s+pengganti\s+tiket",
    r"reimbursement\s+tiket\s+pesawat"
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
        "Tahan Ijazah" in f or "Permintaan Uang" in f or "Iming-iming" in f or "APK" in f or "Deposit" in f
        for f in flags
    )
    risk_level = "danger" if has_danger else "warning"

    advice = (
        "PERINGATAN: Perusahaan kredibel TIDAK PERNAH memungut biaya tes/seragam dalam bentuk apa pun "
        "dan dilarang menahan ijazah asli. Hindari menyerahkan uang atau dokumen berharga!"
        if risk_level == "danger" else
        "WASPADA: Lakukan riset mandiri terkait kredibilitas perusahaan dan model bisnisnya sebelum menghadiri interview."
    )

    return {
        "is_red_flag": True,
        "risk_level": risk_level,
        "flags": flags,
        "advice": advice
    }
