"""The hourly ingest runner flags missing or stale scraper captures."""

import importlib.util
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("scheduled_ingest", ROOT / "scripts" / "scheduled_ingest.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
runner.faulthandler.cancel_dump_traceback_later()


class StaleCaptureTest(unittest.TestCase):
    def test_default_capture_age_matches_eight_hour_slo(self):
        with patch.dict(os.environ, {}, clear=True):
            isolated = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(isolated)
                self.assertEqual(isolated.MAX_CAPTURE_AGE_HOURS, 8)
            finally:
                isolated.faulthandler.cancel_dump_traceback_later()
                isolated._fault_log.close()

    def test_capture_age_can_be_overridden(self):
        with patch.dict(os.environ, {"BOOK_JOB_DATA_MAX_CAPTURE_AGE_HOURS": "4.5"}):
            isolated = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(isolated)
                self.assertEqual(isolated.MAX_CAPTURE_AGE_HOURS, 4.5)
            finally:
                isolated.faulthandler.cancel_dump_traceback_later()
                isolated._fault_log.close()

    def test_eight_hour_boundary(self):
        now = 1_800_000_000
        with tempfile.TemporaryDirectory() as tmp:
            for name, age in (("job_postings.csv", 8 * 3600), ("matched_jobs.csv", 8 * 3600 + 1)):
                capture = Path(tmp) / name
                capture.write_text("x", encoding="utf-8")
                os.utime(capture, (now - age, now - age))
            with patch.dict(os.environ, {"BOOK_JOB_SCRAPING_DATA_DIR": tmp}):
                self.assertEqual(runner.stale_captures(now), ["matched_jobs.csv 8.0h old"])

    def test_reports_missing_and_old_captures(self):
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "job_postings.csv"
            fresh.write_text("x", encoding="utf-8")
            old = time.time() - 20 * 3600
            os.utime(fresh, (old, old))
            with patch.dict(os.environ, {"BOOK_JOB_SCRAPING_DATA_DIR": tmp}):
                problems = runner.stale_captures()
        self.assertEqual(problems[0][:16], "job_postings.csv")
        self.assertIn("matched_jobs.csv missing", problems)

    def test_fresh_captures_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("job_postings.csv", "matched_jobs.csv"):
                (Path(tmp) / name).write_text("x", encoding="utf-8")
            with patch.dict(os.environ, {"BOOK_JOB_SCRAPING_DATA_DIR": tmp}):
                self.assertEqual(runner.stale_captures(), [])


if __name__ == "__main__":
    unittest.main()
