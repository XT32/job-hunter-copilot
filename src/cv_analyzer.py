import os
import re

STOPWORDS = {
    "dan", "di", "ke", "dari", "yang", "untuk", "pada", "dengan", "adalah", "ini", "itu",
    "atau", "juga", "kami", "saya", "anda", "bisa", "akan", "dalam", "bagi", "secara",
    "the", "and", "in", "to", "of", "a", "is", "for", "on", "with", "as", "at", "by", "an",
    "pt", "tbk", "indonesia", "perusahaan", "company", "posisi", "pekerjaan", "job"
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
        # Fallback sederhana jika pypdf belum terpasang: baca bytes dengan filter string
        try:
            with open(pdf_path, "rb") as f:
                content = f.read().decode("latin-1", errors="ignore")
                matches = re.findall(r'[a-zA-Z0-9_\-\.\,\s]{4,}', content)
                return " ".join(matches[:500])
        except Exception:
            return ""

def get_keywords(text: str) -> set:
    """Mengekstrak kata kunci esensial (keahlian, teknologi, bidang) dari teks"""
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    return {w for w in words if w not in STOPWORDS}

def calculate_ats_match(cv_text: str, job_title: str, job_description: str = "") -> dict:
    """
    Menghitung skor kecocokan ATS (Applicant Tracking System) antara CV dan lowongan pekerjaan.
    Mengembalikan persentase skor (0-100%), kata kunci yang cocok, dan kata kunci yang kurang.
    """
    if not cv_text:
        return {"score": 50, "matched": [], "missing": [], "status": "CV belum diunggah"}

    cv_keywords = get_keywords(cv_text)
    job_text = f"{job_title} {job_description}"
    job_keywords = get_keywords(job_text)

    if not job_keywords:
        return {"score": 75, "matched": [], "missing": [], "status": "Data loker terbatas"}

    matched = cv_keywords.intersection(job_keywords)
    missing = job_keywords.difference(cv_keywords)

    score = int((len(matched) / len(job_keywords)) * 100)
    # Normalisasi agar skor tetap proporsional (rentang wajar 40 - 95%)
    score = min(max(score + 35, 45), 98)

    return {
        "score": score,
        "matched": sorted(list(matched))[:6],
        "missing": sorted(list(missing))[:4],
        "status": "Tinggi" if score >= 80 else ("Cukup" if score >= 65 else "Perlu Disesuaikan")
    }
