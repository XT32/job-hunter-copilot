# Copyright (C) 2024-2026 XT32 <https://github.com/XT32/job-hunter-copilot>
#
# This file is part of Job Hunter Copilot.
#
# Job Hunter Copilot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Job Hunter Copilot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import re


def _contains_pattern(pattern: str, text: str) -> bool:
    if not pattern or not text:
        return False
    pat = pattern.strip().lower()
    txt = text.lower()
    # Jika pola pendek (<= 4 karakter) atau satu kata, gunakan batas kata (word boundary)
    if len(pat) <= 4 or " " not in pat:
        return bool(re.search(rf"\b{re.escape(pat)}\b", txt))
    return pat in txt


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
            if bad_word and (_contains_pattern(bad_word, title_lower) or _contains_pattern(bad_word, combined_text)):
                return False, f"Mengandung kata blacklist: '{bad_word}'"

        # 2. Cek Kesesuaian Level Pengalaman (Jika Fresh Graduate / Junior)
        if self.experience_level in ["fresh_graduate", "junior"]:
            senior_triggers = ["senior", "lead", "head of", "manager", "principal", "direktur", "vp"]
            for trigger in senior_triggers:
                # Pengecualian khusus: 'lead generation', 'lead generator', 'lead gen', 'community lead' dll yang bukan tech lead
                if trigger == "lead" and any(exc in title_lower for exc in ["lead generation", "lead generator", "lead gen", "community lead"]):
                    continue
                # Cek di judul pekerjaan dengan batas kata
                if _contains_pattern(trigger, title_lower):
                    return False, f"Level terlalu tinggi untuk {self.experience_level} ('{trigger}' di judul)"

        # 3. Cek Kesesuaian Kata Kunci Utama (Jika ada target keywords)
        if self.target_keywords:
            matched = any(_contains_pattern(kw, title_lower) or _contains_pattern(kw, combined_text) for kw in self.target_keywords)
            if not matched:
                return False, "Tidak cocok dengan target kata kunci jurusan/posisi"

        # 4. Cek Lokasi / Tipe Kerja jika dikonfigurasi
        if self.preferred_locations:
            loc_combined = f"{location.lower()} {title_lower} {desc_lower}"
            loc_matched = any(_contains_pattern(pref, loc_combined) for pref in self.preferred_locations)
            if not loc_matched:
                return False, f"Lokasi tidak sesuai preferensi ({', '.join(self.preferred_locations)})"

        return True, "Sesuai profil"
