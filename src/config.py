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

import copy
import json
import os
from src.local_db import LocalSecureDB, DEFAULT_DB_PATH, TamperDetectedError

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

DEFAULT_CONFIG = {
    "profile": {
        "field_or_major": "Akuntansi",
        "target_keywords": ["Staff Akuntansi", "Finance Staff", "Tax Officer"],
        "experience_level": "fresh_graduate",
        "work_type": "all",
        "preferred_locations": ["Jakarta", "Remote"],
        "blacklist_keywords": [
            "Senior",
            "Lead",
            "Manager",
            "Head of",
            "Director",
            "SPG",
            "Sales Lapangan",
            "Asuransi",
            "Canvasser",
        ],
        "applicant_name": "Nama Lengkap Kamu",
        "contact_info": "+62 812-xxxx-xxxx | linkedin.com/in/username",
    },
    "screening_defaults": {
        "expected_salary": "6000000",
        "notice_period": "Immediately",
        "years_of_experience": "1",
        "education_level": "S1",
        "willing_to_wfo": True,
        "willing_to_relocate": True,
        "domicile": "Jakarta",
        "confirm_before_submit": False,
        "custom_qa": [],
    },
    "smtp": {
        "host": "smtp.gmail.com",
        "port": 465,
        "email": "",
        "password": "",
        "sender_name": "",
        "cv_path": "attachments/CV.pdf",
    },
    "telegram": {
        "bot_token": "",
        "chat_id": "",
        "enabled": False,
    },
    "country": "ID",
    "min_delay_sec": 2,
    "max_delay_sec": 4,
    "auto_skip_already_seen": True,
    "browser_headless": False,
    "slow_mo_ms": 150,
}


def _merge_defaults(data: dict) -> dict:
    merged = copy.deepcopy(DEFAULT_CONFIG)
    if not isinstance(data, dict):
        return merged
    for key, val in data.items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key].update(val)
        else:
            merged[key] = val
    return merged


def _get_config_db(file_path=DEFAULT_CONFIG_PATH) -> LocalSecureDB:
    if os.path.abspath(file_path) == os.path.abspath(DEFAULT_CONFIG_PATH):
        db = LocalSecureDB(DEFAULT_DB_PATH)
    else:
        db = LocalSecureDB(file_path)
    db.ensure_initialized()
    return db


def load_config(file_path=DEFAULT_CONFIG_PATH):
    db = _get_config_db(file_path)
    try:
        stored = db.get_config("main_config")
        if stored is not None:
            return _merge_defaults(stored)

        # Migrasi satu kali jika file config.json lama masih ada
        initial = copy.deepcopy(DEFAULT_CONFIG)
        if os.path.abspath(file_path) == os.path.abspath(DEFAULT_CONFIG_PATH) and os.path.exists(DEFAULT_CONFIG_PATH):
            try:
                with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                    initial = _merge_defaults(json.load(f))
            except Exception:
                pass
        db.save_config(initial, key_name="main_config", source="system_migration")
        return initial
    except TamperDetectedError:
        raise
    except Exception:
        return copy.deepcopy(DEFAULT_CONFIG)


def save_config(cfg, file_path=DEFAULT_CONFIG_PATH, source="ui"):
    db = _get_config_db(file_path)
    merged = _merge_defaults(cfg)
    db.save_config(merged, key_name="main_config", source=source)
