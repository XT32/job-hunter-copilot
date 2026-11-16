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

"""
Modul Pelindung Kuota & Pembatas Kecepatan (Rate Limiter).
Mencegah akun JobStreet/Glints/Dealls terkena shadowban atau pemblokiran akibat
melamar terlalu cepat atau melebihi batas wajar harian.
"""

import json
import os
import threading
import time

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
QUOTA_FILE = os.path.join(DATA_DIR, ".rate_limits.json")

_quota_lock = threading.Lock()

DEFAULT_LIMITS = {
    "jobstreet": {"max_per_hour": 15, "max_per_day": 40},
    "glints": {"max_per_hour": 15, "max_per_day": 40},
    "dealls": {"max_per_hour": 15, "max_per_day": 35},
    "maganghub": {"max_per_hour": 10, "max_per_day": 25},
}


class SafeRateLimiter:
    def __init__(self, quota_file: str = QUOTA_FILE):
        self.quota_file = quota_file
        self.limits = DEFAULT_LIMITS.copy()

    def _load_records(self) -> dict:
        if not os.path.exists(self.quota_file):
            return {}
        try:
            with open(self.quota_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_records(self, data: dict):
        os.makedirs(os.path.dirname(self.quota_file), exist_ok=True)
        try:
            with open(self.quota_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def check_quota(self, platform: str) -> tuple[bool, str, dict]:
        """
        Memeriksa apakah platform masih dalam batas aman untuk melamar.
        Returns: (is_allowed: bool, reason: str, stats: dict)
        """
        plat = platform.lower().strip()
        limit = self.limits.get(plat, {"max_per_hour": 15, "max_per_day": 40})
        now = time.time()
        one_hour_ago = now - 3600
        one_day_ago = now - 86400

        with _quota_lock:
            records = self._load_records()
            plat_records = records.get(plat, [])

            # Bersihkan record lebih lama dari 24 jam
            fresh_records = [ts for ts in plat_records if ts > one_day_ago]
            records[plat] = fresh_records
            self._save_records(records)

            hour_count = sum(1 for ts in fresh_records if ts > one_hour_ago)
            day_count = len(fresh_records)

            stats = {
                "platform": plat,
                "hour_count": hour_count,
                "hour_limit": limit["max_per_hour"],
                "day_count": day_count,
                "day_limit": limit["max_per_day"],
            }

            if day_count >= limit["max_per_day"]:
                msg = (
                    f"Batas aman harian {limit['max_per_day']} lamaran tercapai untuk {plat.title()}. "
                    "Sistem membatasi ini agar akun Anda tidak diblokir/dibatasi oleh portal kerja. Coba lagi besok."
                )
                return False, msg, stats

            if hour_count >= limit["max_per_hour"]:
                msg = (
                    f"Batas aman per jam {limit['max_per_hour']} lamaran tercapai untuk {plat.title()}. "
                    "Silakan istirahat sebentar beberapa menit sebelum melanjutkan."
                )
                return False, msg, stats

            return True, "Kuota aman.", stats

    def record_application(self, platform: str):
        plat = platform.lower().strip()
        now = time.time()
        with _quota_lock:
            records = self._load_records()
            plat_records = records.get(plat, [])
            plat_records.append(now)
            records[plat] = plat_records
            self._save_records(records)

    def get_all_quotas(self) -> dict:
        now = time.time()
        one_hour_ago = now - 3600
        one_day_ago = now - 86400

        with _quota_lock:
            records = self._load_records()
            summary = {}
            for plat, limit in self.limits.items():
                plat_records = records.get(plat, [])
                fresh = [ts for ts in plat_records if ts > one_day_ago]
                summary[plat] = {
                    "hour_count": sum(1 for ts in fresh if ts > one_hour_ago),
                    "hour_limit": limit["max_per_hour"],
                    "day_count": len(fresh),
                    "day_limit": limit["max_per_day"],
                }
            return summary


_default_limiter = SafeRateLimiter()

def get_limiter() -> SafeRateLimiter:
    return _default_limiter
