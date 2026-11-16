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

import os
import random
import shutil
import time

USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "user_browser_data")

# Flag hemat RAM dan stealth untuk laptop spek standar / rendah
BROWSER_ARGS = [
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--renderer-process-limit=2",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=TranslateUI,OptimizationHints,MediaRouter",
    "--disable-sync",
    "--disable-blink-features=AutomationControlled",
    "--window-size=1280,860",
]

_cached_channel = False  # False = belum dicek, None = pakai chromium bawaan


def _detect_channel(playwright_instance):
    global _cached_channel
    if _cached_channel is not False:
        return _cached_channel

    # Cek cepat di Linux/macOS/Windows tanpa selalu spawn browser test
    if os.name == "posix":
        if shutil.which("google-chrome") or shutil.which("google-chrome-stable"):
            _cached_channel = "chrome"
            return _cached_channel
        if shutil.which("microsoft-edge"):
            _cached_channel = "msedge"
            return _cached_channel
        _cached_channel = None
        return None

    for ch in ["chrome", "msedge"]:
        try:
            test = playwright_instance.chromium.launch(channel=ch, headless=True)
            test.close()
            _cached_channel = ch
            return _cached_channel
        except Exception:
            continue
    _cached_channel = None
    return None


def get_user_data_dir(account_id: str = "default") -> str:
    """Mengembalikan direktori profil browser yang terisolasi per akun."""
    if not account_id or account_id == "default":
        return USER_DATA_DIR
    account_dir = os.path.join(USER_DATA_DIR, "profiles", str(account_id))
    os.makedirs(account_dir, exist_ok=True)
    return account_dir


def _cleanup_stale_singleton_locks(target_dir: str = USER_DATA_DIR):
    """Membersihkan lock file Chromium yang tertinggal jika browser sebelumnya tertutup paksa."""
    for lock_name in ["SingletonLock", "SingletonSocket", "SingletonCookie"]:
        p = os.path.join(target_dir, lock_name)
        if os.path.lexists(p):
            try:
                os.unlink(p)
            except Exception:
                pass


def get_browser_context(playwright_instance, headless=False, slow_mo=150, user_data_dir=None, account_id="default"):
    if user_data_dir is None:
        user_data_dir = get_user_data_dir(account_id)
    os.makedirs(user_data_dir, exist_ok=True)
    _cleanup_stale_singleton_locks(user_data_dir)

    channel = _detect_channel(playwright_instance)
    kwargs = {
        "user_data_dir": user_data_dir,
        "headless": headless,
        "slow_mo": slow_mo,
        "args": BROWSER_ARGS,
        "viewport": {"width": 1280, "height": 820},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    if channel:
        kwargs["channel"] = channel

    try:
        context = playwright_instance.chromium.launch_persistent_context(**kwargs)
    except Exception:
        # Fallback ke Chromium bawaan Playwright jika channel lokal gagal
        kwargs.pop("channel", None)
        context = playwright_instance.chromium.launch_persistent_context(**kwargs)

    context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        window.chrome = {
            runtime: {}
        };
        """
    )
    return context


def human_delay(min_sec=2, max_sec=4):
    time.sleep(random.uniform(min_sec, max_sec))
