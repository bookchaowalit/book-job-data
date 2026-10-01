from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from book_job_data import config, lake
from book_job_data.ingest import ingest_capture, normalize_rows
from book_job_data.store import canonical_url, load_records, stable_job_id


SAMPLE = "title,company,url,source,scraped_at\nData Engineer,Example,https://EXAMPLE.com/jobs/data?utm_source=x,RemoteOK,2026-08-08T00:00:00Z\n"


def _shared_runtime_available() -> bool:
    try:
        lake._load_shared()  # type: ignore[attr-defined]
    except (ImportError, ModuleNotFoundError):
        return False
    return True


class JobNormalizationTests(unittest.TestCase):
    def test_canonical_url_and_stable_id_drop_tracking_query(self):
        self.assertEqual(canonical_url("https://EXAMPLE.com/jobs/data?utm_source=x"), "https://example.com/jobs/data")
        self.assertEqual(stable_job_id({"url": "https://example.com/jobs/data?x=1"}), stable_job_id({"url": "https://example.com/jobs/data?x=2"}))

    def test_normalize_rows_adds_lineage_fields_and_deduplicates(self):
        rows = [{"title": "Old", "url": "https://example.com/job"}, {"title": "New", "url": "https://example.com/job"}]
        result = normalize_rows(rows, provider="fixture", input_name="jobs.csv")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "New")
        for key in ("id", "event_time", "observed_at", "provider", "input_name"):
            self.assertIn(key, result[0])


class LakeFirstTests(unittest.TestCase):
    def test_lake_failure_happens_before_any_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "job_postings.csv"
            source.write_text(SAMPLE, encoding="utf-8")
            with mock.patch.object(lake, "ingest_to_lake", side_effect=lake.LakeIngestError("blocked")):
                with self.assertRaises(lake.LakeIngestError):
                    ingest_capture(source, data_lake_uri=str(Path(tmp) / "lake"))
            self.assertFalse((Path(tmp) / "data" / "job_postings.csv").exists())

    @unittest.skipUnless(
        _shared_runtime_available(),
        "Solo Empire shared data_lake adapter not found",
    )
    def test_real_lake_landing_bronze_manifest_and_replay(self):
        try:
            import pyarrow  # noqa: F401
            import duckdb  # noqa: F401
        except ImportError:
            self.skipTest("pyarrow/duckdb not installed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "job_postings.csv"
            raw = SAMPLE.encode("utf-8")
            source.write_bytes(raw)
            with mock.patch.object(config, "DATA_DIR", root / "projection"):
                result = ingest_capture(source, data_lake_uri=str(root / "lake"), provider="fixture")
            snapshot = result["snapshot"]
            self.assertEqual((root / "lake" / snapshot["raw_key"]).read_bytes(), raw)
            self.assertTrue(snapshot["bronze_key"].startswith("bronze/"))
            self.assertTrue(snapshot["manifest_key"].startswith("control/"))
            self.assertEqual(lake.landing_object_bytes(snapshot["raw_key"], data_lake_uri=str(root / "lake")), raw)
            with mock.patch.object(config, "DATA_LAKE_URI", str(root / "lake")):
                loaded = load_records()
            self.assertEqual(loaded["source_kind"], "bronze_parquet")
            self.assertEqual(len(loaded["items"]), 1)
            self.assertEqual(loaded["items"][0]["title"], "Data Engineer")


class ContractTests(unittest.TestCase):
    def test_track_b_contract(self):
        self.assertEqual(config.SCHEMA_VERSION, "job.v1")
        self.assertEqual(config.API_PORT, 8109)
        self.assertTrue(config.FREE_ONLY)
        self.assertFalse(config.ALLOW_REFRESH)
        self.assertIn("job_leads", config.DATASETS.values())


if __name__ == "__main__":
    unittest.main()
