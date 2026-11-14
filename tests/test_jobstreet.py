import unittest
from unittest.mock import MagicMock, patch
from src.jobstreet import JobstreetHunter


class _FakeLocator:
    def __init__(self, visible=False, text="", enabled=True):
        self._visible = visible
        self._text = text
        self._enabled = enabled
        self.clicked = False

    @property
    def first(self):
        return self

    def is_visible(self, timeout=0):
        return self._visible

    def is_enabled(self):
        return self._enabled

    def inner_text(self, timeout=0):
        return self._text

    def click(self):
        self.clicked = True

    def all(self):
        return []


class TestJobstreetHunter(unittest.TestCase):
    def setUp(self):
        self.config = {
            "profile": {
                "field_or_major": "Teknik Informatika",
                "target_keywords": ["Python Developer", "Backend"],
                "experience_level": "junior",
                "blacklist_keywords": ["Senior", "Manager"],
            },
            "screening_defaults": {
                "expected_salary": "6000000",
                "years_of_experience": "1",
                "domicile": "Jakarta",
                "confirm_before_submit": False,
            },
            "auto_skip_already_seen": True,
        }
        self.mock_page = MagicMock()
        self.hunter = JobstreetHunter(self.mock_page, self.config)

    def test_hunter_initialization(self):
        self.assertIsNotNone(self.hunter.matcher)
        self.assertEqual(self.hunter.config["profile"]["field_or_major"], "Teknik Informatika")

    def test_search_jobs_url_slug_generation(self):
        self.mock_page.locator.return_value.all.return_value = []
        self.mock_page.locator.return_value.first.is_visible.return_value = False

        self.hunter.search_jobs(["Software Engineer"])
        call_args = self.mock_page.goto.call_args[0][0]
        self.assertIn("id.jobstreet.com/id/software-engineer-jobs", call_args)

    @patch("src.jobstreet.human_delay", return_value=None)
    def test_wizard_4_steps_complete_apply(self, _mock_delay):
        # Simulasi urutan halaman wizard 4 tahap JobStreet
        step_bodies = iter([
            "Pilih dokumen dan surat lamaran",
            "Jawab pertanyaan perusahaan",
            "Perbarui profil JobStreet Anda",
            "Review dan kirim lamaran Anda",
        ])
        current_step = {"idx": 0, "text": next(step_bodies)}

        apply_btn = _FakeLocator(visible=True, text="Lamar cepat")
        continue_btn = _FakeLocator(visible=True, text="Lanjut")
        submit_btn = _FakeLocator(visible=True, text="Kirim lamaran")

        def advance_step():
            try:
                current_step["text"] = next(step_bodies)
                current_step["idx"] += 1
            except StopIteration:
                pass

        orig_continue_click = continue_btn.click
        def continue_click():
            orig_continue_click()
            advance_step()
        continue_btn.click = continue_click

        def locator_side_effect(selector):
            if selector == "body":
                return _FakeLocator(visible=True, text=current_step["text"])
            if "job-detail-apply" in selector:
                return apply_btn
            if "submit-button" in selector:
                return _FakeLocator(visible=(current_step["idx"] >= 3), text="Kirim lamaran")
            if "continue-button" in selector:
                return continue_btn
            return _FakeLocator(visible=False)

        self.mock_page.url = "https://id.jobstreet.com/id/job/12345"
        self.mock_page.context.pages = [self.mock_page]
        self.mock_page.locator.side_effect = locator_side_effect
        self.hunter.screener.auto_fill_form = MagicMock(return_value=1)

        res = self.hunter.inspect_and_apply("https://id.jobstreet.com/id/job/12345", job_title="PPIC Staff", company="PT Maju")
        self.assertEqual(res["status"], "success")
        self.assertEqual(current_step["idx"], 3)

    @patch("src.jobstreet.human_delay", return_value=None)
    def test_wizard_pauses_when_confirm_before_submit_enabled(self, _mock_delay):
        self.config["screening_defaults"]["confirm_before_submit"] = True
        hunter = JobstreetHunter(self.mock_page, self.config)

        apply_btn = _FakeLocator(visible=True, text="Lamar cepat")
        submit_btn = _FakeLocator(visible=True, text="Kirim lamaran")

        def locator_side_effect(selector):
            if selector == "body":
                return _FakeLocator(visible=True, text="Review dan kirim lamaran Anda")
            if "job-detail-apply" in selector:
                return apply_btn
            if "submit-button" in selector:
                return submit_btn
            return _FakeLocator(visible=False)

        self.mock_page.url = "https://id.jobstreet.com/id/job/12345/apply"
        self.mock_page.context.pages = [self.mock_page]
        self.mock_page.locator.side_effect = locator_side_effect

        res = hunter.inspect_and_apply("https://id.jobstreet.com/id/job/12345", job_title="PPIC Staff", company="PT Maju")
        self.assertEqual(res["status"], "manual_action_needed")
        self.assertFalse(submit_btn.clicked)


if __name__ == "__main__":
    unittest.main()
