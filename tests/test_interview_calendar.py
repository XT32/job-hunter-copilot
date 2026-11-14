import os
import tempfile
import unittest

from src.storage import set_interview_schedule, generate_interview_ics, load_history, record_job


class TestInterviewCalendar(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.ics_file = os.path.join(self.tmp_dir, "test_interview.ics")

    def tearDown(self):
        if os.path.exists(self.ics_file):
            try:
                os.remove(self.ics_file)
            except Exception:
                pass
        try:
            os.rmdir(self.tmp_dir)
        except Exception:
            pass

    def test_set_interview_schedule_and_generate_ics(self):
        test_url = "https://example.com/job/ppic-staff-interview-test"
        record_job(test_url, "PPIC Staff", "PT Industri Manufaktur", status="applied", source="ui")

        success = set_interview_schedule(
            job_url=test_url,
            interview_datetime="2026-11-20T10:00",
            location="https://meet.google.com/abc-defg-hij",
            notes="Wawancara dengan Plant Manager",
            source="ui",
        )
        self.assertTrue(success)

        hist = load_history()
        interview_jobs = [j for j in hist.get("interview", []) if j.get("url") == test_url]
        self.assertEqual(len(interview_jobs), 1)
        job_item = interview_jobs[0]
        self.assertIn("[Jadwal: 2026-11-20T10:00]", job_item.get("notes", ""))
        self.assertIn("[Lokasi: https://meet.google.com/abc-defg-hij]", job_item.get("notes", ""))

        # Ekspor .ics
        output_ics = generate_interview_ics(job_url=test_url, output_path=self.ics_file)
        self.assertTrue(os.path.exists(output_ics))

        with open(output_ics, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("BEGIN:VCALENDAR", content)
        self.assertIn("VERSION:2.0", content)
        self.assertIn("BEGIN:VEVENT", content)
        self.assertIn("SUMMARY:Interview PPIC Staff - PT Industri Manufaktur", content)
        self.assertIn("DTSTART:20261120T100000", content)
        self.assertIn("DTEND:20261120T110000", content)
        self.assertIn("LOCATION:https://meet.google.com/abc-defg-hij", content)
        self.assertIn("END:VEVENT", content)
        self.assertIn("END:VCALENDAR", content)


if __name__ == "__main__":
    unittest.main()
