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
Modul Pembaruan Aplikasi 1-Klik dari GitHub (tanpa perlu pengguna membuka GitHub manual).
Mendukung baik instalasi via Git maupun instalasi Download ZIP (untuk pengguna awam).
Data pribadi pengguna (data/, attachments/, user_browser_data/, .venv/, config.json)
tidak pernah ditimpa saat update berlangsung.
"""

import io
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile

REPO_OWNER = "XT32"
REPO_NAME = "job-hunter-copilot"
REPO_BRANCH = "main"

GITHUB_COMMIT_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{REPO_BRANCH}"
GITHUB_ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{REPO_BRANCH}.zip"
GITHUB_HTTPS_GIT = f"https://github.com/{REPO_OWNER}/{REPO_NAME}.git"

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
VERSION_FILE = os.path.join(ROOT_DIR, "data", ".app_version.json")

# Folder dan file pribadi pengguna yang HARUS dipertahankan saat update ZIP
PROTECTED_TOP_LEVEL = {
    "data",
    "attachments",
    "user_browser_data",
    ".venv",
    "venv",
    "env",
    ".git",
    "config.json",
    "__pycache__",
}


def _get_git_head_sha(root_dir: str = ROOT_DIR) -> str:
    git_dir = os.path.join(root_dir, ".git")
    if not os.path.isdir(git_dir):
        return ""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root_dir,
            stderr=subprocess.DEVNULL,
            timeout=4,
        )
        return out.decode("utf-8").strip()
    except Exception:
        return ""


def get_local_version_info(root_dir: str = ROOT_DIR) -> dict:
    ver_path = os.path.join(root_dir, "data", ".app_version.json")
    info = {}
    if os.path.exists(ver_path):
        try:
            with open(ver_path, "r", encoding="utf-8") as f:
                info = json.load(f)
        except Exception:
            info = {}

    git_sha = _get_git_head_sha(root_dir)
    if git_sha and not info.get("sha"):
        info["sha"] = git_sha

    info.setdefault("sha", "")
    info.setdefault("updated_at", "")
    info.setdefault("message", "")
    info["install_type"] = "git" if os.path.isdir(os.path.join(root_dir, ".git")) else "zip"
    return info


def _save_local_version_info(sha: str, message: str = "", date_str: str = "", root_dir: str = ROOT_DIR):
    ver_path = os.path.join(root_dir, "data", ".app_version.json")
    os.makedirs(os.path.dirname(ver_path), exist_ok=True)
    payload = {
        "sha": sha,
        "message": message,
        "commit_date": date_str,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(ver_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def fetch_remote_latest(timeout: int = 8) -> dict:
    req = urllib.request.Request(
        GITHUB_COMMIT_API,
        headers={
            "User-Agent": "loker-copilot-updater/1.0",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    sha = data.get("sha", "")
    commit = data.get("commit", {})
    message = (commit.get("message") or "").splitlines()[0]
    date_str = (commit.get("author") or {}).get("date", "")
    return {
        "sha": sha,
        "short_sha": sha[:7] if sha else "",
        "message": message,
        "date": date_str,
    }


def check_for_updates(root_dir: str = ROOT_DIR) -> dict:
    local = get_local_version_info(root_dir)
    try:
        remote = fetch_remote_latest()
    except Exception as e:
        return {
            "success": False,
            "error": f"Tidak bisa terhubung ke GitHub untuk cek update: {e}",
            "local": local,
        }

    local_sha = local.get("sha", "")
    remote_sha = remote.get("sha", "")
    up_to_date = bool(local_sha and remote_sha and local_sha == remote_sha)

    return {
        "success": True,
        "up_to_date": up_to_date,
        "update_available": not up_to_date,
        "local": local,
        "remote": remote,
        "repo_url": f"https://github.com/{REPO_OWNER}/{REPO_NAME}",
    }


def _try_git_pull(root_dir: str) -> tuple:
    git_dir = os.path.join(root_dir, ".git")
    if not os.path.isdir(git_dir):
        return False, "Bukan repositori Git"
    try:
        status_out = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=root_dir, timeout=5
        ).decode("utf-8").strip()
        if status_out:
            return False, "Ada perubahan lokal di folder Git; beralih ke metode aman."

        res = subprocess.run(
            ["git", "pull", "--ff-only", GITHUB_HTTPS_GIT, REPO_BRANCH],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if res.returncode == 0:
            return True, res.stdout.strip()
        return False, res.stderr.strip()
    except Exception as e:
        return False, str(e)


def _apply_zip_bytes_safely(zip_bytes: bytes, root_dir: str) -> int:
    """Mengekstrak isi arsip ZIP GitHub ke root_dir tanpa menimpa data pribadi pengguna."""
    updated_files = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # Validasi anti zip-slip
            for member in zf.infolist():
                target = os.path.abspath(os.path.join(tmpdir, member.filename))
                if not target.startswith(os.path.abspath(tmpdir)):
                    raise ValueError("Path arsip ZIP tidak aman")
            zf.extractall(tmpdir)

        entries = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
        if not entries:
            raise ValueError("Folder isi arsip update tidak ditemukan")
        src_root = os.path.join(tmpdir, entries[0])

        for item in os.listdir(src_root):
            if item in PROTECTED_TOP_LEVEL:
                continue
            src_path = os.path.join(src_root, item)
            dst_path = os.path.join(root_dir, item)

            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                updated_files += 1
            else:
                shutil.copy2(src_path, dst_path)
                updated_files += 1

    return updated_files


def apply_update(root_dir: str = ROOT_DIR) -> dict:
    """Mengunduh dan memasang versi terbaru dari GitHub tanpa menghapus data lokal."""
    try:
        remote = fetch_remote_latest()
    except Exception as e:
        return {"success": False, "error": f"Gagal memeriksa versi terbaru di GitHub: {e}"}

    method_used = "zip"
    git_ok, _ = _try_git_pull(root_dir)
    if git_ok:
        method_used = "git"
    else:
        try:
            req = urllib.request.Request(
                GITHUB_ZIP_URL,
                headers={"User-Agent": "loker-copilot-updater/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                zip_bytes = resp.read()
            _apply_zip_bytes_safely(zip_bytes, root_dir)
        except Exception as e:
            return {"success": False, "error": f"Gagal mengunduh/memasang pembaruan dari GitHub: {e}"}

    _save_local_version_info(
        sha=remote.get("sha", ""),
        message=remote.get("message", ""),
        date_str=remote.get("date", ""),
        root_dir=root_dir,
    )

    return {
        "success": True,
        "method": method_used,
        "remote": remote,
        "restart_required": True,
        "message": f"Aplikasi berhasil diperbarui ke versi terbaru ({remote.get('short_sha', 'latest')}: {remote.get('message', '')}). Klik 'Restart Aplikasi' agar perubahan aktif.",
    }
