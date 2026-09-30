#!/usr/bin/env python3
"""Scheduled ingest tick: run book_job_data.ingest with output appended to data/ingest.log.

Meant for pythonw.exe under Windows Task Scheduler, where there is no console
and sys.stdout/sys.stderr are None.
"""
from __future__ import annotations

import faulthandler
import os
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "data" / "ingest.log"
# The scraper refreshes job_postings every 6 hours; this runs from a separate
# task, so it still notices when the scraper task stops entirely.
MAX_CAPTURE_AGE_HOURS = float(os.environ.get("BOOK_JOB_DATA_MAX_CAPTURE_AGE_HOURS", "12"))
STALE_EXIT_CODE = 3
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
# Record a stack dump if a scheduled run ever hangs (no console to inspect).
_fault_log = LOG_FILE.open("a", encoding="utf-8")
faulthandler.dump_traceback_later(900, repeat=False, file=_fault_log, exit=True)

sys.path.insert(0, str(ROOT / "src"))

from book_job_data import ingest  # noqa: E402


def stale_captures(now: float | None = None) -> list[str]:
    """Names of expected capture files that are missing or too old."""
    now = time.time() if now is None else now
    data = Path(os.environ.get("BOOK_JOB_SCRAPING_DATA_DIR", str(ingest.SCRAPER_REPO / "data")))
    problems = []
    for name in ("job_postings.csv", "matched_jobs.csv"):
        path = data / name
        if not path.is_file():
            problems.append(f"{name} missing")
            continue
        age_hours = (now - path.stat().st_mtime) / 3600
        if age_hours > MAX_CAPTURE_AGE_HOURS:
            problems.append(f"{name} {age_hours:.1f}h old")
    return problems


def main() -> int:
    with LOG_FILE.open("a", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log):
        print(f"=== ingest {datetime.now().isoformat(timespec='seconds')} ===", flush=True)
        try:
            code = ingest.main([])
        except Exception as exc:  # keep the failure in the log, not a lost console
            print(f"ingest crashed: {type(exc).__name__}: {exc}", flush=True)
            return 2
        stale = stale_captures()
        if stale:
            # Surfaces as the task's LastTaskResult (scheduled-ingest.ps1 status).
            print(f"ALERT stale scraper capture (> {MAX_CAPTURE_AGE_HOURS:g}h): {', '.join(stale)}", flush=True)
            return code or STALE_EXIT_CODE
        return code


if __name__ == "__main__":
    raise SystemExit(main())
