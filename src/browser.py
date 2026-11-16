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
COMMON_BROWSER_ARGS = [
    "--disable-dev-shm-usage",
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
    "--mute-audio",
    "--disable-speech-api",
    "--disk-cache-size=33554432",
    "--media-cache-size=16777216",
    "--js-flags=--max-old-space-size=512",
    "--window-size=1280,860",
]

# Backward compatibility alias
BROWSER_ARGS = list(COMMON_BROWSER_ARGS)

BLOCKED_MEDIA_TYPES = {"image", "media", "font"}
BLOCKED_TRACKER_DOMAINS = [
    "google-analytics.com",
    "googletagmanager.com",
    "googleads.",
    "doubleclick.net",
    "facebook.net",
    "connect.facebook.net",
    "hotjar.com",
    "sentry.io",
    "datadoghq-browser-agent.com",
    "browser-intake-datadoghq.com",
    "segment.io",
    "segment.com",
    "amplitude.com",
    "mixpanel.com",
    "clarity.ms",
    "criteo.net",
    "adnxs.com",
    "pubmatic.com",
    "scorecardresearch.com",
    "advertising.",
    "telemetry.",
]


def optimize_page_resources(page, block_media=True):
    """
    Mengoptimalkan konsumsi RAM, CPU, dan bandwidth pada halaman Playwright.
    - Memblokir tracker, telemetri, dan script analitik berat yang memakan resource laptop.
    - Jika block_media=True (default untuk scraping), memblokir pemuatan gambar,
      video, dan webfont pihak ketiga agar scraping berjalan instan dan hemat memori.
    - Jika block_media=False (mode visual/login), gambar dan styling tetap aktif.
    """
    def _route_filter(route):
        try:
            req = route.request
            res_type = req.resource_type
            url = req.url.lower()

            # 1. Selalu blokir tracker / ads / telemetri pihak ketiga
            if any(dom in url for dom in BLOCKED_TRACKER_DOMAINS):
                return route.abort()

            # 2. Blokir media berat saat background scraping
            if block_media and res_type in BLOCKED_MEDIA_TYPES:
                return route.abort()

            return route.continue_()
        except Exception:
            try:
                route.continue_()
            except Exception:
                pass

    try:
        page.route("**/*", _route_filter)
    except Exception:
        pass

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

    # Di mode visual (headless=False), HINDARI --disable-gpu agar GPU laptop merender window secara mulus
    # tanpa membebani 100% CPU untuk software-rasterization (SwiftShader/llvmpipe).
    active_args = list(COMMON_BROWSER_ARGS)
    if headless:
        active_args.append("--disable-gpu")

    kwargs = {
        "user_data_dir": user_data_dir,
        "headless": headless,
        "slow_mo": slow_mo,
        "args": active_args,
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
        // 1. Sembunyikan navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        // 2. Emulasi antarmuka window.chrome lengkap
        window.chrome = {
            app: { isInstalled: false },
            runtime: {},
            loadTimes: function() {},
            csi: function() {}
        };

        // 3. Emulasi plugins dan bahasa browser agar tidak terbaca bot kosong
        try {
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['id-ID', 'id', 'en-US', 'en']
            });
        } catch (e) {}
        """
    )
    return context


def find_system_browser_executable() -> tuple[str, str]:
    """
    Menemukan executable browser resmi (Google Chrome / Edge / Brave / Chromium)
    pada Linux, Windows, atau macOS.
    Returns: (executable_path, browser_name)
    """
    candidates = [
        ("google-chrome", "Google Chrome"),
        ("google-chrome-stable", "Google Chrome"),
        ("microsoft-edge", "Microsoft Edge"),
        ("microsoft-edge-stable", "Microsoft Edge"),
        ("brave-browser", "Brave Browser"),
        ("chromium", "Chromium"),
        ("chromium-browser", "Chromium"),
        ("chrome", "Google Chrome"),
        ("msedge", "Microsoft Edge"),
    ]
    for binary, name in candidates:
        p = shutil.which(binary)
        if p and os.path.isfile(p):
            return p, name

    if os.name == "nt":
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")

        windows_paths = [
            (os.path.join(prog_files, "Google", "Chrome", "Application", "chrome.exe"), "Google Chrome"),
            (os.path.join(prog_files_x86, "Google", "Chrome", "Application", "chrome.exe"), "Google Chrome"),
            (os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"), "Google Chrome"),
            (os.path.join(prog_files, "Microsoft", "Edge", "Application", "msedge.exe"), "Microsoft Edge"),
            (os.path.join(prog_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"), "Microsoft Edge"),
            (os.path.join(prog_files, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"), "Brave Browser"),
        ]
        for p, name in windows_paths:
            if os.path.isfile(p):
                return p, name

    mac_paths = [
        ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "Google Chrome"),
        ("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "Microsoft Edge"),
        ("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser", "Brave Browser"),
        ("/Applications/Chromium.app/Contents/MacOS/Chromium", "Chromium"),
    ]
    for p, name in mac_paths:
        if os.path.isfile(p):
            return p, name

    return "", ""


def launch_native_login_browser(target_url: str, account_id: str = "default") -> dict:
    """
    Meluncurkan browser resmi sistem (Google Chrome / Edge) sebagai proses murni OS (non-Playwright),
    menggunakan direktori profil data Copilot yang terisolasi.
    Hal ini memungkinkan pengguna melakukan 'Sign in with Google' secara 100% normal
    tanpa pernah diblokir atau dideteksi sebagai bot automasi oleh Google Accounts.
    """
    browser_exe, browser_name = find_system_browser_executable()
    if not browser_exe:
        return {
            "success": False,
            "error": "Tidak ditemukan Google Chrome atau Microsoft Edge resmi di sistem. Silakan pasang Google Chrome atau gunakan login email/password."
        }

    user_data_dir = get_user_data_dir(account_id)
    os.makedirs(user_data_dir, exist_ok=True)
    _cleanup_stale_singleton_locks(user_data_dir)

    cmd = [
        browser_exe,
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        target_url,
    ]

    try:
        import subprocess
        if os.name == "nt":
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            subprocess.Popen(cmd, creationflags=creationflags)
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

        return {
            "success": True,
            "browser_name": browser_name,
            "url": target_url,
            "message": f"Browser {browser_name} resmi berhasil dibuka. Silakan lakukan 'Masuk dengan Google' di halaman tersebut, lalu tutup browser setelah selesai."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Gagal meluncurkan {browser_name}: {str(e)}"
        }


def human_delay(min_sec=2, max_sec=4):
    time.sleep(random.uniform(min_sec, max_sec))
