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
import time
from abc import ABC, abstractmethod
from src.browser import human_delay

ATTACHMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "attachments")


class BaseJobHunter(ABC):
    def __init__(self, page, config):
        self.page = page
        self.config = config

    @abstractmethod
    def check_login_status(self) -> bool:
        """Memeriksa apakah sesi pengguna sudah login"""
        pass

    @abstractmethod
    def search_jobs(self, keywords=None) -> list:
        """Mencari daftar lowongan pekerjaan berdasarkan kata kunci"""
        pass

    @abstractmethod
    def inspect_and_apply(self, job_url: str) -> dict:
        """Membuka detail lowongan dan melakukan peninjauan/lamaran"""
        pass

    def _normalize_keywords(self, keywords=None, default=None) -> list:
        if not keywords:
            profile = self.config.get("profile", {})
            keywords = profile.get("target_keywords", default or ["Staff"])

        if isinstance(keywords, str):
            kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        elif isinstance(keywords, list):
            kw_list = [str(k).strip() for k in keywords if str(k).strip()]
        else:
            kw_list = [str(keywords)]

        return kw_list if kw_list else (default or ["Staff"])

    def _switch_to_latest_tab_if_opened(self, prev_count: int):
        try:
            pages = self.page.context.pages
            if len(pages) > prev_count:
                self.page = pages[-1]
                if hasattr(self, "screener") and self.screener is not None:
                    self.screener.page = self.page
                self.page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass

    def _get_active_cv_path(self) -> str:
        active_cv = self.config.get("active_cv", "CV.pdf")
        if active_cv:
            p = os.path.join(ATTACHMENTS_DIR, os.path.basename(active_cv))
            if os.path.exists(p):
                return p
        return ""

    def _upload_active_cv_if_present(self) -> bool:
        cv_path = self._get_active_cv_path()
        if not cv_path:
            return False
        try:
            file_inputs = self.page.locator("input[type='file']").all()
            for fi in file_inputs:
                accept = (fi.get_attribute("accept") or "").lower()
                if not accept or "pdf" in accept or "doc" in accept:
                    fi.set_input_files(cv_path)
                    human_delay(1.0, 1.8)
                    return True
        except Exception:
            pass
        return False

    def _page_has_text(self, patterns: list) -> bool:
        try:
            body_text = self.page.locator("body").inner_text(timeout=1500).lower()
            return any(p in body_text for p in patterns)
        except Exception:
            return False

    def _is_login_redirect(self) -> bool:
        try:
            current_url = (self.page.url or "").lower()
            return any(tok in current_url for tok in ["login.seek.com", "/login", "signin", "sign-in", "account.kemnaker.go.id"])
        except Exception:
            return False

    def _capture_failure_screenshot(self, platform_name: str = "portal", status: str = "failed") -> str:
        """Menyimpan tangkapan layar otomatis jika proses melamar terhambat atau butuh konfirmasi manual"""
        try:
            screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            filename = f"{platform_name.lower().replace(' ', '_')}_{int(time.time())}_{status}.png"
            target_path = os.path.join(screenshots_dir, filename)
            self.page.screenshot(path=target_path, timeout=3000)
            return filename
        except Exception:
            return ""
