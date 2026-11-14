import json
import os

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

DEFAULT_CONFIG = {
    "profile": {
        "field_or_major": "Akuntansi",
        "target_keywords": ["Staff Akuntansi", "Finance Staff", "Tax Officer"],
        "experience_level": "fresh_graduate",
        "work_type": "all",
        "preferred_locations": ["Jakarta", "Remote"],
        "blacklist_keywords": ["Senior", "Lead", "Manager", "Head of", "Director", "SPG", "Sales Lapangan", "Asuransi", "Canvasser"],
        "applicant_name": "Nama Lengkap Kamu",
        "contact_info": "+62 812-xxxx-xxxx | linkedin.com/in/username"
    },
    "screening_defaults": {
        "expected_salary": "6000000",
        "notice_period": "Immediately",
        "years_of_experience": "1",
        "willing_to_wfo": True,
        "willing_to_relocate": True,
        "domicile": "Jakarta"
    },
    "smtp": {
        "host": "smtp.gmail.com",
        "port": 465,
        "email": "",
        "password": "",
        "sender_name": "",
        "cv_path": "attachments/CV.pdf"
    },
    "telegram": {
        "bot_token": "",
        "chat_id": "",
        "enabled": False
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
            data = json.load(f)
            # Ensure new keys are populated if upgrading from older config
            for key, val in DEFAULT_CONFIG.items():
                if key not in data:
                    data[key] = val
            return data
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg, file_path=DEFAULT_CONFIG_PATH):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
