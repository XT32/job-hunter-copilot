import os
import re

STOPWORDS = {
    "dan", "di", "ke", "dari", "yang", "untuk", "pada", "dengan", "adalah", "ini", "itu",
    "atau", "juga", "kami", "saya", "anda", "bisa", "akan", "dalam", "bagi", "secara",
    "the", "and", "in", "to", "of", "a", "is", "for", "on", "with", "as", "at", "by", "an",
    "pt", "tbk", "indonesia", "perusahaan", "company", "posisi", "pekerjaan", "job", "lowongan",
    "kerja", "syarat", "kualifikasi", "kriteria", "requirements", "qualification", "responsibilities"
}


TECH_SPECIAL_TOKENS = {"c++", "c#", ".net"}
KNOWN_SHORT_KEYWORDS = {
    "ui", "ux", "qa", "ai", "ml", "it", "hr", "go", "js", "ts", "db", "pr", "bi", "ci", "cd"
}


def extract_text_from_pdf(pdf_path: str) -> str:
    """Mengekstrak teks mentah dari file PDF CV pelamar"""
    if not pdf_path or not os.path.exists(pdf_path):
        return ""

    try:
        import pypdf
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text.strip()
    except Exception:
        try:
            with open(pdf_path, "rb") as f:
                content = f.read().decode("latin-1", errors="ignore")
                matches = re.findall(r'[a-zA-Z0-9_\-\.\,\s]{4,}', content)
                return " ".join(matches[:500])
        except Exception:
            return ""


def get_keywords(text: str) -> set:
    """Mengekstrak kata kunci esensial (keahlian, teknologi, bidang) dari teks"""
    if not text:
        return set()
    txt = text.lower()
    extracted = set()

    # 1. Token khusus teknis (c++, c#, .net)
    for tok in TECH_SPECIAL_TOKENS:
        if re.search(rf"(?:^|[^\w#+]){re.escape(tok)}(?:[^\w#+]|$)", txt):
            extracted.add(tok)

    # 2. Kata-kata standar minimal 3 huruf
    words = re.findall(r'[a-zA-Z]{3,}', txt)
    for w in words:
        if w not in STOPWORDS:
            extracted.add(w)

    # 3. Kata kunci singkatan teknis & peran 2 huruf yang diakui
    short_words = re.findall(r'\b[a-zA-Z]{2}\b', txt)
    for sw in short_words:
        if sw in KNOWN_SHORT_KEYWORDS and sw not in STOPWORDS:
            extracted.add(sw)

    return extracted


def calculate_ats_match(cv_text: str, job_title: str, job_description: str = "") -> dict:
    """
    Menghitung skor kecocokan ATS (Applicant Tracking System) secara objektif
    berdasarkan overlap keahlian teknis dan peran pekerjaan.
    """
    if not cv_text or not cv_text.strip():
        return {
            "score": 0,
            "matched": [],
            "missing": [],
            "status": "CV belum diunggah",
            "recommendation": "Unggah CV untuk melihat estimasi kecocokan ATS dengan lowongan ini."
        }

    cv_keywords = get_keywords(cv_text)
    title_keywords = get_keywords(job_title)
    desc_keywords = get_keywords(job_description)

    combined_job_keywords = title_keywords.union(desc_keywords)

    if not combined_job_keywords:
        return {
            "score": 60,
            "matched": [],
            "missing": [],
            "status": "Data loker terbatas",
            "recommendation": "Deskripsi pekerjaan singkat. Tinjau kembali detail di portal."
        }

    matched = cv_keywords.intersection(combined_job_keywords)
    missing = combined_job_keywords.difference(cv_keywords)

    # Bobot: kecocokan kata kunci pada judul pekerjaan bernilai tinggi (core role match)
    title_matched = cv_keywords.intersection(title_keywords)
    title_ratio = len(title_matched) / max(len(title_keywords), 1)
    desc_ratio = len(matched) / max(len(combined_job_keywords), 1)

    if title_keywords:
        raw_score = (title_ratio * 0.40) + (desc_ratio * 0.60)
    else:
        raw_score = desc_ratio

    score = int(round(raw_score * 100))
    score = max(5, min(score, 100))

    if score >= 70:
        status = "Tinggi"
        rec = "CV Anda sangat relevan dengan persyaratan lowongan ini."
    elif score >= 45:
        status = "Cukup"
        missing_preview = ", ".join(sorted(list(missing))[:3])
        rec = f"Kecocokan cukup baik. Pertimbangkan menambahkan kata kunci: {missing_preview}" if missing_preview else "Kecocokan cukup baik."
    else:
        status = "Perlu Disesuaikan"
        missing_preview = ", ".join(sorted(list(missing))[:4])
        rec = f"Tingkatkan skor dengan menyertakan keahlian yang relevan: {missing_preview}" if missing_preview else "Perlu penyesuaian isi CV."

    return {
        "score": score,
        "matched": sorted(list(matched))[:8],
        "missing": sorted(list(missing))[:6],
        "status": status,
        "recommendation": rec
    }
