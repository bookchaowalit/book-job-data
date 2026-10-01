"""End-to-end privacy through Bronze, capture validation and CLI robustness."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from book_job_data import config, ingest, lake
from book_job_data.privacy import ALLOWED_FIELDS, EMAIL_MASK, PHONE_MASK
from book_job_data.store import load_history, load_records, project_csv

CAPTURE = (
    "title,company,url,source,scraped_at,description,email,contact,phone,notes_internal\n"
    "Data Engineer,Acme,https://acme.example/jobs/1?utm_source=x,RemoteOK,2026-08-08T00:00:00Z,"
    "\"Email jobs@acme.example or call +66 81 234 5678\",hr@acme.example,Jane Doe,+66812345678,secret\n"
    ",,,,,,,,,\n"
    "\n"
    "Analyst,Beta,https://beta.example/jobs/2,RemoteOK,2026-08-08T01:00:00Z,Remote role,,,,\n"
)
PII = ("jobs@acme.example", "hr@acme.example", "Jane Doe", "234 5678", "+66812345678", "secret")


def _runtime_ready() -> bool:
    try:
        lake._load_shared()  # type: ignore[attr-defined]
        import duckdb  # noqa: F401
        import pyarrow  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(_runtime_ready(), "shared data_lake runtime / pyarrow / duckdb not installed")
class BronzePrivacyTests(unittest.TestCase):
    def test_allowlist_and_masking_hold_in_bronze_and_api_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            uri = str(root / "lake")
            source = root / "job_postings.csv"
            source.write_text(CAPTURE, encoding="utf-8")
            with mock.patch.object(config, "DATA_DIR", root / "projection"):
                result = ingest.ingest_capture(source, data_lake_uri=uri, provider="fixture")
            self.assertEqual(result["records"], 2)  # blank rows dropped

            for dataset in (result["dataset"], result["history_dataset"]):
                rows = lake.read_bronze_rows(dataset, data_lake_uri=uri)
                self.assertEqual(len(rows), 2, dataset)
                for row in rows:
                    payload = lake.parse_payload_json(row)
                    self.assertLessEqual(set(payload), ALLOWED_FIELDS, dataset)
                    blob = json.dumps(payload, ensure_ascii=False)
                    for secret in PII:
                        self.assertNotIn(secret, blob, dataset)
                    self.assertTrue(payload.get("title"))

            with mock.patch.object(config, "DATA_LAKE_URI", uri):
                current = load_records()
                history = load_history()
            for payload in (current, history):
                self.assertEqual(len(payload["items"]), 2)
                blob = json.dumps(payload["items"], ensure_ascii=False)
                for secret in PII:
                    self.assertNotIn(secret, blob)
            acme = next(i for i in current["items"] if i["company"] == "Acme")
            self.assertEqual(acme["description"], f"Email {EMAIL_MASK} or call {PHONE_MASK}")
            self.assertEqual(acme["canonical_url"], "https://acme.example/jobs/1")

            # The exact source bytes stay in the internal landing zone as replay evidence.
            self.assertEqual(
                lake.landing_object_bytes(result["snapshot"]["raw_key"], data_lake_uri=uri),
                CAPTURE.encode("utf-8"),
            )

    def test_cli_lands_the_bytes_it_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "job_postings.csv"
            source.write_text(CAPTURE, encoding="utf-8")
            real_read = ingest.read_capture
            calls: list[Path] = []

            def counting_read(path):
                calls.append(path)
                return real_read(path)

            out = io.StringIO()
            with mock.patch.object(config, "DATA_DIR", root / "projection"), \
                    mock.patch.object(ingest, "read_capture", side_effect=counting_read), \
                    contextlib.redirect_stdout(out):
                code = ingest.main(
                    ["--input", str(source), "--input", str(source),
                     "--data-lake-uri", str(root / "lake"), "--project-csv"]
                )
            self.assertEqual(code, 0)
            self.assertEqual(calls, [source])  # read once, even when repeated
            summary = json.loads(out.getvalue())
            self.assertEqual([c["records"] for c in summary["captures"]], [2])
            projection = root / "projection" / "job_postings.csv"
            self.assertTrue(projection.is_file())
            self.assertEqual([p.name for p in projection.parent.iterdir()].count("job_postings.csv"), 1)
            self.assertFalse([p for p in projection.parent.iterdir() if p.suffix == ".tmp"])


class CaptureValidationTests(unittest.TestCase):
    def test_blank_rows_and_surplus_cells_are_ignored(self):
        rows = [
            {"title": "", "url": ""},
            {"title": "Dev", "url": "https://e.example/1", None: ["extra", "cells"]},
        ]
        result = ingest.normalize_rows(rows, provider="fixture", input_name="job_postings.csv")
        self.assertEqual([r["title"] for r in result], ["Dev"])
        self.assertNotIn("None", result[0])

    def test_all_blank_capture_fails_before_lake_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "job_postings.csv"
            source.write_text("title,url\n,\n\n", encoding="utf-8")
            with mock.patch.object(lake, "ingest_to_lake") as write, self.assertRaises(RuntimeError):
                ingest.ingest_capture(source, data_lake_uri=str(Path(tmp) / "lake"))
            write.assert_not_called()

    def test_non_utf8_capture_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "job_postings.csv"
            source.write_bytes(b"title,url\n\xff\xfe,\n")
            err = io.StringIO()
            with contextlib.redirect_stderr(err), \
                    mock.patch.object(lake, "default_data_lake_uri", return_value=str(Path(tmp) / "lake")):
                self.assertEqual(ingest.main(["--input", str(source), "--dry-run"]), 2)
            self.assertIn("not a UTF-8 CSV", err.getvalue())


class ProjectionTests(unittest.TestCase):
    def test_failed_projection_keeps_previous_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "job_postings.csv"
            project_csv([{"title": "Old"}], path=path)
            before = path.read_bytes()

            class Boom(dict):
                def get(self, *_a, **_k):
                    raise OSError("disk full")

            with self.assertRaises(OSError):
                project_csv([Boom(title="New")], path=path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["job_postings.csv"])


if __name__ == "__main__":
    unittest.main()
