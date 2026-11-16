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
Modul Background Scheduler Otomatis.
Menjalankan pemindaian lowongan kerja secara berkala di latar belakang (headless),
mengevaluasi indikasi red flags/penipuan, dan mengirimkan notifikasi instan via Telegram
ketika ditemukan lowongan baru yang cocok dengan kriteria profil pengguna.
"""

import threading
import time
from playwright.sync_api import sync_playwright

from src.browser import get_browser_context
from src.notifier import send_telegram_alert
from src.scam_detector import check_for_red_flags
from src.storage import is_job_recorded, load_history


class AutoHuntScheduler:
    def __init__(self, hunter_map: dict, config_loader, log_callback=None, playwright_lock=None):
        self.hunter_map = hunter_map
        self.config_loader = config_loader
        self.log_callback = log_callback
        self.playwright_lock = playwright_lock or threading.Lock()
        self.running = False
        self.thread = None
        self.last_run = None
        self.interval_minutes = 120
        self.total_discovered = 0
        self.last_summary = {}
        self._seen_urls = set()
        self._load_initial_seen()

    def _log(self, msg: str, level: str = "info"):
        if self.log_callback:
            try:
                self.log_callback(msg, level)
            except Exception:
                pass
        try:
            print(f"[Scheduler] {msg}")
        except Exception:
            pass

    def _load_initial_seen(self):
        try:
            hist = load_history()
            for items in hist.values():
                for it in items:
                    u = it.get("url")
                    if u:
                        self._seen_urls.add(u)
        except Exception:
            pass

    def start(self, interval_minutes: int = 120) -> bool:
        if self.running:
            return False

        self.interval_minutes = interval_minutes
        self.running = True

        def loop():
            self._log(f"Background scheduler diaktifkan (interval: {interval_minutes} menit).", "info")
            while self.running:
                try:
                    self._run_scan_cycle()
                except Exception as e:
                    self._log(f"Kesalahan dalam siklus pemindaian latar belakang: {e}", "danger")

                # Tidur selama interval_minutes dengan pemeriksaan status interupsi per detik
                for _ in range(max(10, interval_minutes * 60)):
                    if not self.running:
                        break
                    time.sleep(1)

            self._log("Background scheduler dinonaktifkan.", "info")

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()
        return True

    def _run_scan_cycle(self):
        cfg = self.config_loader()
        profile = cfg.get("profile", {})
        keywords = profile.get("target_keywords", [])
        tg_cfg = cfg.get("telegram", {})
        tg_enabled = tg_cfg.get("enabled", False) and bool(tg_cfg.get("bot_token")) and bool(tg_cfg.get("chat_id"))

        if not keywords:
            self._log("Kata kunci profil kosong, pemindaian latar belakang dilewati.", "warning")
            return

        self.last_run = time.strftime("%Y-%m-%d %H:%M:%S")
        self._log(f"Memulai siklus pemindaian otomatis untuk keywords: {', '.join(keywords[:3])}...", "info")

        cycle_discovered = 0
        cycle_summary = {}

        # Gunakan lock Playwright agar tidak tabrakan dengan aksi user di Web UI
        with self.playwright_lock:
            with sync_playwright() as p:
                context = None
                try:
                    context = get_browser_context(p, headless=True, slow_mo=50)
                    page = context.new_page()

                    for p_name, (HunterClass, label) in self.hunter_map.items():
                        if not self.running:
                            break

                        portal_found = 0
                        try:
                            hunter = HunterClass(page, cfg)
                            jobs = hunter.search_jobs(keywords=keywords)

                            for job in jobs:
                                url = job.get("url")
                                if not url or url in self._seen_urls or is_job_recorded(url):
                                    continue

                                self._seen_urls.add(url)
                                portal_found += 1
                                cycle_discovered += 1
                                self.total_discovered += 1

                                # Periksa red flag / scam
                                rf = check_for_red_flags(
                                    title=job.get("title", ""),
                                    company=job.get("company", ""),
                                    description=job.get("description", ""),
                                    location=job.get("location", ""),
                                )

                                # Kirim alert Telegram jika diaktifkan & tidak terindikasi scam berat
                                if tg_enabled:
                                    tag = ""
                                    if rf.get("is_red_flag"):
                                        tag = " 🚨 [BAHAYA SCAM]" if rf.get("risk_level") == "danger" else " ⚠️ [Periksa Red Flag]"
                                    send_telegram_alert(
                                        title=f"{job.get('title')}{tag}",
                                        company=job.get("company", "Perusahaan"),
                                        url=url,
                                        platform=label,
                                        salary=job.get("salary", "Tidak dicantumkan"),
                                        bot_token=tg_cfg.get("bot_token", ""),
                                        chat_id=tg_cfg.get("chat_id", ""),
                                    )

                            cycle_summary[p_name] = portal_found
                        except Exception as e:
                            self._log(f"Gagal memindai portal {label}: {e}", "warning")
                            cycle_summary[p_name] = 0
                finally:
                    if context:
                        try:
                            context.close()
                        except Exception:
                            pass

        self.last_summary = cycle_summary
        if cycle_discovered > 0:
            self._log(
                f"Siklus pemindaian selesai: Menemukan {cycle_discovered} lowongan baru yang cocok!",
                "success",
            )
        else:
            self._log("Siklus pemindaian selesai: Belum ada lowongan baru yang belum tercatat.", "info")

    def stop(self) -> bool:
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        return True

    def get_status(self) -> dict:
        return {
            "active": self.running,
            "interval_minutes": getattr(self, "interval_minutes", 120),
            "last_run": self.last_run or "Belum pernah berjalan",
            "total_discovered": self.total_discovered,
            "last_summary": self.last_summary,
        }
