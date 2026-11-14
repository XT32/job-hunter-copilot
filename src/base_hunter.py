import os
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
