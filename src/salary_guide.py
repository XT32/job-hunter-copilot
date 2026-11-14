"""
Modul Panduan Standar Gaji & Database UMR/UMK Indonesia 2024/2025.
Membantu pelamar (khususnya fresh graduate) agar tidak salah memasukkan ekspektasi gaji.
"""

# Database Upah Minimum Regional / Kota (UMR/UMK) Resmi 2024/2025 (IDR per bulan)
UMR_DATABASE = {
    # DKI Jakarta
    "jakarta": 5067381,
    "dki jakarta": 5067381,
    "jakarta selatan": 5067381,
    "jakarta pusat": 5067381,
    "jakarta barat": 5067381,
    "jakarta timur": 5067381,
    "jakarta utara": 5067381,

    # Jawa Barat (Bodetabek & Karawang)
    "bekasi": 5343430,
    "kota bekasi": 5343430,
    "kabupaten bekasi": 5219263,
    "karawang": 5257834,
    "depok": 4878612,
    "bogor": 4813988,
    "kota bogor": 4813988,
    "kabupaten bogor": 4579541,
    "bandung": 4209309,
    "kota bandung": 4209309,
    "kabupaten bandung": 3527967,
    "cimahi": 3627880,

    # Banten
    "tangerang": 4760289,
    "kota tangerang": 4760289,
    "tangerang selatan": 4670791,
    "kabupaten tangerang": 4601988,
    "cilegon": 4815102,
    "serang": 4148000,

    # Jawa Timur
    "surabaya": 4725479,
    "kota surabaya": 4725479,
    "gresik": 4642031,
    "sidoarjo": 4638582,
    "malang": 3309144,
    "kota malang": 3309144,

    # Jawa Tengah & DI Yogyakarta
    "semarang": 3243969,
    "kota semarang": 3243969,
    "surakarta": 2269070,
    "solo": 2269070,
    "yogyakarta": 2492997,
    "jogja": 2492997,
    "sleman": 2315976,
    "bantul": 2216463,

    # Sumatera & Luar Jawa
    "medan": 3769082,
    "kota medan": 3769082,
    "batam": 4685050,
    "pekanbaru": 3451184,
    "palembang": 3677591,
    "makassar": 3643751,
    "denpasar": 3096523,
    "bali": 3096523,
    "balikpapan": 3475595
}

DEFAULT_NATIONAL_BENCHMARK = 3500000

def get_umr_by_location(location: str) -> int:
    """Mencari nilai UMR/UMK berdasarkan nama kota atau lokasi"""
    if not location:
        return DEFAULT_NATIONAL_BENCHMARK

    loc_clean = location.lower().strip()
    for key, value in UMR_DATABASE.items():
        if key in loc_clean:
            return value

    return DEFAULT_NATIONAL_BENCHMARK

def suggest_salary_range(location: str, exp_level: str = "fresh_graduate") -> dict:
    """
    Memberikan rekomendasi rentang ekspektasi gaji yang sehat untuk pelamar.
    """
    umr = get_umr_by_location(location)
    
    # Pengali berdasarkan level pengalaman
    multipliers = {
        "internship": (0.6, 1.0),       # Uang saku magang (60% - 100% UMR)
        "fresh_graduate": (1.0, 1.3),   # 1x - 1.3x UMR
        "junior": (1.2, 1.8),           # 1.2x - 1.8x UMR
        "mid": (1.8, 3.0),              # 1.8x - 3.0x UMR
        "senior": (3.0, 5.0),           # 3.0x - 5.0x UMR
        "all": (1.0, 1.5)
    }

    min_mult, max_mult = multipliers.get(exp_level, (1.0, 1.3))
    min_sal = int(round(umr * min_mult, -4))
    max_sal = int(round(umr * max_mult, -4))

    return {
        "location": location or "Indonesia",
        "umr": umr,
        "exp_level": exp_level,
        "recommended_min": min_sal,
        "recommended_max": max_sal,
        "formatted_range": f"Rp {min_sal:,.0f} - Rp {max_sal:,.0f}".replace(",", ".")
    }

def evaluate_candidate_salary(expected_salary: int, location: str) -> dict:
    """
    Memeriksa apakah ekspektasi gaji kandidat berada di bawah standar UMR daerah tersebut.
    """
    umr = get_umr_by_location(location)
    if expected_salary <= 0:
        return {"status": "neutral", "message": "Ekspektasi gaji belum ditentukan."}

    if expected_salary < (umr * 0.85):
        return {
            "status": "under_umr",
            "message": f"Ekspektasi kamu (Rp {expected_salary:,.0f}) berada di bawah standar UMR {location} (Rp {umr:,.0f}). Disarankan naikkan minimal ke UMR agar tidak dipandang kurang percaya diri.".replace(",", ".")
        }
    
    return {
        "status": "healthy",
        "message": f"Ekspektasi wajar dan sesuai dengan standar regional {location} (UMR: Rp {umr:,.0f}).".replace(",", ".")
    }
