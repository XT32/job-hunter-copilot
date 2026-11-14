import re

class JobMatcher:
    def __init__(self, profile):
        """
        profile: dict yang memuat kriteria pencari kerja:
        - target_keywords: list[str] (misal: ["Akuntansi", "Finance", "Staff Keuangan"])
        - experience_level: str ("fresh_graduate", "junior", "mid", "senior", "all")
        - work_type: str ("all", "remote", "onsite")
        - blacklist_keywords: list[str] (misal: ["Senior", "Manager", "SPG", "Sales Lapangan"])
        - preferred_locations: list[str] (misal: ["Jakarta", "Remote", "Tangerang"])
        """
        self.profile = profile or {}
        self.target_keywords = [k.lower().strip() for k in self.profile.get("target_keywords", []) if k.strip()]
        self.blacklist = [b.lower().strip() for b in self.profile.get("blacklist_keywords", []) if b.strip()]
        self.experience_level = self.profile.get("experience_level", "all").lower()
        self.preferred_locations = [loc.lower().strip() for loc in self.profile.get("preferred_locations", []) if loc.strip()]

    def evaluate(self, title, company="", location="", description=""):
        """
        Mengevaluasi apakah lowongan cocok dengan profil pengguna.
        Mengembalikan tuple: (is_match: bool, reason: str)
        """
        title_lower = title.lower()
        desc_lower = description.lower()
        combined_text = f"{title_lower} {desc_lower}"

        # 1. Cek Blacklist (Kata Kunci Terlarang)
        for bad_word in self.blacklist:
            if bad_word and (bad_word in title_lower or bad_word in combined_text):
                return False, f"Mengandung kata blacklist: '{bad_word}'"

        # 2. Cek Kesesuaian Level Pengalaman (Jika Fresh Graduate / Junior)
        if self.experience_level in ["fresh_graduate", "junior"]:
            senior_triggers = ["senior", "lead", "head of", "manager", "principal", "direktur", "vp "]
            for trigger in senior_triggers:
                # Cek di judul pekerjaan
                if trigger in title_lower:
                    return False, f"Level terlalu tinggi untuk {self.experience_level} ('{trigger}' di judul)"

        # 3. Cek Kesesuaian Kata Kunci Utama (Jika ada target keywords)
        if self.target_keywords:
            matched = any(kw in title_lower or kw in combined_text for kw in self.target_keywords)
            if not matched:
                return False, "Tidak cocok dengan target kata kunci jurusan/posisi"

        # 4. Cek Lokasi / Tipe Kerja jika dikonfigurasi
        if self.preferred_locations:
            loc_combined = f"{location.lower()} {title_lower} {desc_lower}"
            loc_matched = any(pref in loc_combined for pref in self.preferred_locations)
            if not loc_matched:
                return False, f"Lokasi tidak sesuai preferensi ({', '.join(self.preferred_locations)})"

        return True, "Sesuai profil"
