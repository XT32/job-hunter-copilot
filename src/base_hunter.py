from abc import ABC, abstractmethod

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
