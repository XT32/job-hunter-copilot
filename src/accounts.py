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
Modul Manajemen Multi-Account / Multi-Profile untuk Job Hunter Copilot.
Memungkinkan pengguna mengelola lebih dari satu profil akun (target posisi berbeda,
CV berbeda, dan sesi login browser yang terisolasi sepenuhnya).
"""

import copy
import re
import time
import uuid


def _generate_account_id(prefix: str = "acc") -> str:
    timestamp = int(time.time())
    rand_hex = uuid.uuid4().hex[:6]
    return f"{prefix}_{timestamp}_{rand_hex}"


def _sanitize_name(name: str) -> str:
    clean = re.sub(r"[^\w\s\-\.\(\)]", "", str(name or "")).strip()
    return clean[:50] or "Akun Baru"


def ensure_accounts_initialized(cfg: dict) -> dict:
    """
    Memastikan struktur accounts dan active_account_id ada dalam konfigurasi.
    Secara otomatis memigrasikan config profil tunggal menjadi akun 'default' (Akun Utama).
    """
    if not isinstance(cfg, dict):
        cfg = {}

    accounts = cfg.get("accounts")
    if not isinstance(accounts, list) or len(accounts) == 0:
        default_account = {
            "id": "default",
            "name": "Akun Utama",
            "profile": copy.deepcopy(cfg.get("profile", {})),
            "screening_defaults": copy.deepcopy(cfg.get("screening_defaults", {})),
            "active_cv": cfg.get("active_cv", ""),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        cfg["accounts"] = [default_account]
        cfg["active_account_id"] = "default"

    active_id = cfg.get("active_account_id")
    account_map = {acc["id"]: acc for acc in cfg["accounts"] if isinstance(acc, dict) and "id" in acc}

    if active_id not in account_map:
        # Jika active_account_id tidak valid, fallback ke akun pertama yang ada
        active_id = cfg["accounts"][0]["id"]
        cfg["active_account_id"] = active_id

    active_acc = account_map[active_id]

    # Pastikan data level atas (top-level profile, screening, active_cv) tersinkronisasi
    if "profile" not in cfg or not cfg["profile"]:
        cfg["profile"] = copy.deepcopy(active_acc.get("profile", {}))
    if "screening_defaults" not in cfg or not cfg["screening_defaults"]:
        cfg["screening_defaults"] = copy.deepcopy(active_acc.get("screening_defaults", {}))
    if "active_cv" not in cfg or not cfg["active_cv"]:
        cfg["active_cv"] = active_acc.get("active_cv", "")

    return cfg


def sync_active_account_data(cfg: dict) -> dict:
    """
    Menyimpan perubahan nilai top-level profile, screening_defaults, dan active_cv
    kembali ke record akun yang sedang aktif di cfg["accounts"].
    """
    ensure_accounts_initialized(cfg)
    active_id = cfg.get("active_account_id", "default")
    for acc in cfg["accounts"]:
        if acc.get("id") == active_id:
            if "profile" in cfg and isinstance(cfg["profile"], dict):
                acc["profile"] = copy.deepcopy(cfg["profile"])
            if "screening_defaults" in cfg and isinstance(cfg["screening_defaults"], dict):
                acc["screening_defaults"] = copy.deepcopy(cfg["screening_defaults"])
            acc["active_cv"] = cfg.get("active_cv", "")
            acc["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            break
    return cfg


def get_active_account(cfg: dict) -> dict:
    """Mengembalikan data akun yang saat ini aktif."""
    ensure_accounts_initialized(cfg)
    active_id = cfg.get("active_account_id", "default")
    for acc in cfg["accounts"]:
        if acc.get("id") == active_id:
            return copy.deepcopy(acc)
    return copy.deepcopy(cfg["accounts"][0])


def list_accounts(cfg: dict) -> list:
    """Mengembalikan daftar akun dengan metadata ringkas untuk UI."""
    ensure_accounts_initialized(cfg)
    active_id = cfg.get("active_account_id", "default")
    results = []
    for acc in cfg["accounts"]:
        prof = acc.get("profile", {})
        results.append({
            "id": acc.get("id"),
            "name": acc.get("name", "Akun"),
            "active": (acc.get("id") == active_id),
            "field_or_major": prof.get("field_or_major", "Umum"),
            "target_keywords": prof.get("target_keywords", []),
            "experience_level": prof.get("experience_level", "fresh_graduate"),
            "active_cv": acc.get("active_cv", ""),
            "created_at": acc.get("created_at", ""),
        })
    return results


def create_account(
    cfg: dict,
    name: str,
    clone_current: bool = False,
    field_or_major: str = None,
    target_keywords: list = None,
    experience_level: str = None,
    active_cv: str = None,
) -> tuple:
    """
    Membuat profil akun baru.
    Mengembalikan (new_account_dict, updated_cfg).
    """
    ensure_accounts_initialized(cfg)
    clean_name = _sanitize_name(name)
    new_id = _generate_account_id()

    active_acc = get_active_account(cfg)
    if clone_current:
        new_profile = copy.deepcopy(active_acc.get("profile", {}))
        new_screening = copy.deepcopy(active_acc.get("screening_defaults", {}))
        new_cv = active_cv or active_acc.get("active_cv", "")
    else:
        new_profile = copy.deepcopy(cfg.get("profile", {}))
        new_screening = copy.deepcopy(cfg.get("screening_defaults", {}))
        new_cv = active_cv or ""

    if field_or_major is not None:
        new_profile["field_or_major"] = str(field_or_major).strip()
    if target_keywords is not None and isinstance(target_keywords, list):
        new_profile["target_keywords"] = [str(k).strip() for k in target_keywords if str(k).strip()]
    if experience_level is not None:
        new_profile["experience_level"] = str(experience_level).strip()

    new_account = {
        "id": new_id,
        "name": clean_name,
        "profile": new_profile,
        "screening_defaults": new_screening,
        "active_cv": new_cv,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    cfg["accounts"].append(new_account)
    return new_account, cfg


def switch_account(cfg: dict, target_account_id: str) -> tuple:
    """
    Beralih ke profil akun lain.
    Menyimpan profil aktif saat ini terlebih dahulu, lalu memuat profil target
    ke level atas (top-level profile, screening_defaults, active_cv).
    Mengembalikan (target_account_dict, updated_cfg).
    """
    ensure_accounts_initialized(cfg)
    sync_active_account_data(cfg)

    target_acc = None
    for acc in cfg["accounts"]:
        if acc.get("id") == target_account_id:
            target_acc = acc
            break

    if not target_acc:
        raise ValueError(f"Akun dengan ID '{target_account_id}' tidak ditemukan.")

    cfg["active_account_id"] = target_account_id
    cfg["profile"] = copy.deepcopy(target_acc.get("profile", {}))
    cfg["screening_defaults"] = copy.deepcopy(target_acc.get("screening_defaults", {}))
    cfg["active_cv"] = target_acc.get("active_cv", "")

    return copy.deepcopy(target_acc), cfg


def update_account(cfg: dict, account_id: str, updates: dict) -> tuple:
    """
    Memperbarui nama atau pengaturan suatu akun.
    Mengembalikan (updated_account_dict, updated_cfg).
    """
    ensure_accounts_initialized(cfg)
    target_acc = None
    for acc in cfg["accounts"]:
        if acc.get("id") == account_id:
            target_acc = acc
            break

    if not target_acc:
        raise ValueError(f"Akun dengan ID '{account_id}' tidak ditemukan.")

    if "name" in updates:
        target_acc["name"] = _sanitize_name(updates["name"])
    if "active_cv" in updates:
        target_acc["active_cv"] = updates["active_cv"]
    if "profile" in updates and isinstance(updates["profile"], dict):
        target_acc.setdefault("profile", {}).update(updates["profile"])
    if "screening_defaults" in updates and isinstance(updates["screening_defaults"], dict):
        target_acc.setdefault("screening_defaults", {}).update(updates["screening_defaults"])

    target_acc["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Jika akun yang diupdate adalah akun yang sedang aktif, sinkronkan ke top-level
    if account_id == cfg.get("active_account_id"):
        cfg["profile"] = copy.deepcopy(target_acc.get("profile", {}))
        cfg["screening_defaults"] = copy.deepcopy(target_acc.get("screening_defaults", {}))
        cfg["active_cv"] = target_acc.get("active_cv", "")

    return copy.deepcopy(target_acc), cfg


def delete_account(cfg: dict, account_id: str) -> tuple:
    """
    Menghapus akun.
    Tidak mengizinkan menghapus jika hanya tersisa 1 akun.
    Jika menghapus akun yang sedang aktif, otomatis beralih ke akun lain terlebih dahulu.
    Mengembalikan (deleted_account_dict, updated_cfg).
    """
    ensure_accounts_initialized(cfg)

    if len(cfg["accounts"]) <= 1:
        raise ValueError("Tidak dapat menghapus satu-satunya akun yang tersisa.")

    target_index = None
    target_acc = None
    for idx, acc in enumerate(cfg["accounts"]):
        if acc.get("id") == account_id:
            target_index = idx
            target_acc = acc
            break

    if target_acc is None:
        raise ValueError(f"Akun dengan ID '{account_id}' tidak ditemukan.")

    is_active = (cfg.get("active_account_id") == account_id)
    deleted = cfg["accounts"].pop(target_index)

    if is_active:
        # Beralih ke akun pertama yang tersisa
        fallback_acc = cfg["accounts"][0]
        cfg["active_account_id"] = fallback_acc["id"]
        cfg["profile"] = copy.deepcopy(fallback_acc.get("profile", {}))
        cfg["screening_defaults"] = copy.deepcopy(fallback_acc.get("screening_defaults", {}))
        cfg["active_cv"] = fallback_acc.get("active_cv", "")

    return deleted, cfg
