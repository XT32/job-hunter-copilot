import json
import os

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

DEFAULT_CONFIG = {
    "profile": {
        "field_or_major": "Teknik Informatika",
        "target_keywords": ["Backend Developer", "Python", "Software Engineer"],
        "experience_level": "junior",
        "work_type": "all",
        "preferred_locations": [],
        "blacklist_keywords": ["Senior", "Lead", "Manager", "Head of", "Director", "SPG", "Sales Lapangan", "Asuransi", "Canvasser"]
    },
    "country": "ID",
    "min_delay_sec": 2,
    "max_delay_sec": 4,
    "auto_skip_already_seen": True,
    "slow_mo_ms": 150
}

def load_config(file_path=DEFAULT_CONFIG_PATH):
    if not os.path.exists(file_path):
        save_config(DEFAULT_CONFIG, file_path)
        return DEFAULT_CONFIG.copy()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg, file_path=DEFAULT_CONFIG_PATH):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
