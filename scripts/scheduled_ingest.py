#!/usr/bin/env python3
"""Scheduled ingest tick: run book_job_data.ingest with output appended to data/ingest.log.

Meant for pythonw.exe under Windows Task Scheduler, where there is no console
and sys.stdout/sys.stderr are None.
"""
from __future__ import annotations

import faulthandler
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_FILE = ROOT / "data" / "ingest.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
# Record a stack dump if a scheduled run ever hangs (no console to inspect).
_fault_log = LOG_FILE.open("a", encoding="utf-8")
faulthandler.dump_traceback_later(900, repeat=False, file=_fault_log, exit=True)

sys.path.insert(0, str(ROOT / "src"))

from book_job_data import ingest  # noqa: E402


def main() -> int:
    with LOG_FILE.open("a", encoding="utf-8") as log, redirect_stdout(log), redirect_stderr(log):
        print(f"=== ingest {datetime.now().isoformat(timespec='seconds')} ===", flush=True)
        try:
            return ingest.main([])
        except Exception as exc:  # keep the failure in the log, not a lost console
            print(f"ingest crashed: {type(exc).__name__}: {exc}", flush=True)
            return 2


if __name__ == "__main__":
    raise SystemExit(main())
