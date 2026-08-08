"""Read-only job.v1 API backed by Bronze Parquet/DuckDB."""
from __future__ import annotations

import json
import hmac
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from . import config
from .lake import load_lineage
from .store import envelope, get_record, load_dataset, paginate, utc_now_iso

_LOCAL_ORIGIN_RE = re.compile(r"^https?://(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$", re.I)


def _json_response(handler: BaseHTTPRequestHandler, status: int, body: dict[str, Any]) -> None:
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.send_header("Cache-Control", "no-store")
    origin = handler.headers.get("Origin", "")
    if _LOCAL_ORIGIN_RE.match(origin):
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")
    handler.end_headers()
    handler.wfile.write(payload)


def _dataset(qs: dict[str, list[str]], default: str) -> str:
    value = qs.get("dataset", [default])[0]
    return value if value in config.DATASETS.values() else default


def _limit(qs: dict[str, list[str]]) -> int:
    try:
        return max(1, min(int(qs.get("limit", ["50"])[0]), 500))
    except ValueError:
        return 50


def _storage_model(source_kind: Any) -> str:
    kind = str(source_kind or "")
    if kind.startswith("iceberg_"):
        return "lake_first_job_iceberg_rest_duckdb"
    if kind.startswith("bronze_s3_parquet"):
        return "lake_first_job_bronze_s3_duckdb"
    return "lake_first_job_bronze_duckdb"


def _authorized(handler: BaseHTTPRequestHandler) -> bool:
    expected = config.API_READ_TOKEN
    if not expected:
        return True
    supplied = handler.headers.get("Authorization", "")
    return hmac.compare_digest(supplied, f"Bearer {expected}")


class Handler(BaseHTTPRequestHandler):
    server_version = "book-job-data-api/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_OPTIONS(self) -> None:  # noqa: N802
        origin = self.headers.get("Origin", "")
        if not _LOCAL_ORIGIN_RE.match(origin):
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Accept, Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/v1/refresh":
            _json_response(self, 403, envelope(items=[], data_status="forbidden", extra={"error": "refresh disabled"}))
            return
        _json_response(self, 405, envelope(items=[], data_status="forbidden", extra={"error": "GET only"}))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)
        if path != "/healthz" and not _authorized(self):
            return _json_response(
                self,
                401,
                envelope(
                    items=[],
                    data_status="forbidden",
                    extra={"error": "read token required"},
                ),
            )
        if path == "/healthz":
            payload = load_dataset(config.DEFAULT_DATASET)
            return _json_response(self, 200, {"status": "ok", "repository": config.REPO_NAME, "domain": config.DOMAIN, "data_status": payload["data_status"], "storage_model": _storage_model(payload.get("source_kind")), "api_bind": f"{config.API_HOST}:{config.API_PORT}"})
        if path == "/v1/metadata":
            datasets = {name: load_dataset(name, latest_only=name not in {config.DEFAULT_HISTORY_DATASET, "job_matches_history", "job_leads_history"}) for name in config.DATASETS.values()}
            record_payload = datasets[config.DEFAULT_DATASET]
            item = {"repository": config.REPO_NAME, "domain": config.DOMAIN, "schema_version": config.SCHEMA_VERSION, "port": config.API_PORT, "storage_model": _storage_model(record_payload.get("source_kind")), "records_source_kind": record_payload.get("source_kind"), "dataset_counts": {name: len(value.get("items", [])) for name, value in datasets.items()}, "lake_lineage": load_lineage(), "scraper_boundary": "file_capture_only", "api_bind": f"{config.API_HOST}:{config.API_PORT}"}
            return _json_response(self, 200, envelope(items=[item], data_status=record_payload["data_status"], retrieved_at=record_payload.get("retrieved_at")))
        if path == "/v1/records":
            payload = load_dataset(_dataset(qs, config.DEFAULT_DATASET), latest_only=True)
            page, cursor = paginate(payload["items"], limit=_limit(qs), cursor=qs.get("cursor", [None])[0])
            return _json_response(self, 200, envelope(items=page, data_status=payload["data_status"], next_cursor=cursor, retrieved_at=payload.get("retrieved_at")))
        if path == "/v1/history":
            dataset = _dataset(qs, config.DEFAULT_HISTORY_DATASET)
            if not dataset.endswith("_history"):
                dataset = f"{dataset}_history" if f"{dataset}_history" in config.DATASETS.values() else config.DEFAULT_HISTORY_DATASET
            payload = load_dataset(dataset, latest_only=False)
            page, cursor = paginate(payload["items"], limit=_limit(qs), cursor=qs.get("cursor", [None])[0])
            return _json_response(self, 200, envelope(items=page, data_status=payload["data_status"], next_cursor=cursor, retrieved_at=payload.get("retrieved_at")))
        if path.startswith("/v1/records/"):
            record_id = unquote(path[len("/v1/records/"):])
            item = get_record(record_id)
            if item is None:
                return _json_response(self, 404, envelope(items=[], data_status="not_found", extra={"error": "record not found"}))
            return _json_response(self, 200, envelope(items=[item], data_status="ok"))
        return _json_response(self, 404, envelope(items=[], data_status="not_found", extra={"error": "unknown endpoint"}))


def main() -> None:
    server = ThreadingHTTPServer((config.API_HOST, config.API_PORT), Handler)
    print(f"book-job-data API listening on http://{config.API_HOST}:{config.API_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
