"""Bronze-backed store; CSV is input/projection only, never API source."""
from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

from . import config, lake


def _product_store():
    current = config.PROJECT_ROOT.resolve()
    for parent in [current, *current.parents]:
        scripts = parent / "infra" / "scripts"
        if (scripts / "data_lake" / "product_store.py").is_file():
            if str(scripts) not in sys.path:
                sys.path.insert(0, str(scripts))
            break
    from data_lake import product_store  # type: ignore
    return product_store


_ps_module = None


def _ps():
    global _ps_module
    if _ps_module is None:
        _ps_module = _product_store()
    return _ps_module


def canonical_url(url: str) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw.rstrip("/").lower()
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", ""))


def stable_job_id(row: dict[str, Any]) -> str:
    url = canonical_url(str(row.get("url") or row.get("source_url") or row.get("link") or ""))
    if url:
        return "job:" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    basis = "|".join(str(row.get(k) or "").strip().lower() for k in ("source", "company", "title", "location"))
    return "job:" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:24]


def utc_now_iso() -> str:
    return _ps().utc_now_iso()


def _item_from_bronze(row: dict[str, Any], *, history: bool = False, history_idx: int = 0) -> dict[str, Any]:
    payload = lake.parse_payload_json(row)
    event_time = str(row.get("event_time") or payload.get("event_time") or "")
    item = dict(payload)
    item.update(
        {
            "record_id": stable_job_id(payload) + (f"#h{history_idx}" if history else ""),
            "event_time": event_time,
            "observed_at": str(payload.get("observed_at") or event_time),
            "ingest_run_id": str(row.get("ingest_run_id") or ""),
            "source_record_id": str(row.get("source_record_id") or payload.get("id") or ""),
            "raw_object_key": str(row.get("raw_object_key") or ""),
        }
    )
    return item


def _contract():
    from data_lake.product_adapter import LakeProductContract  # type: ignore

    return LakeProductContract(
        source=config.REPO_NAME,
        domain=config.DOMAIN,
        product_schema_version=config.SCHEMA_VERSION,
        privacy_class=config.PRIVACY_CLASS,
        retention_class=config.RETENTION_CLASS,
        bronze_schema_version=config.BRONZE_SCHEMA_VERSION,
        project_root=config.PROJECT_ROOT,
        data_lake_uri=config.DATA_LAKE_URI,
        solo_empire_root=config.SOLO_EMPIRE_ROOT,
        lineage_filename=config.LINEAGE_FILE,
        datasets=tuple(config.DATASETS.values()),
    )


def load_dataset(dataset: str, *, data_lake_uri: Optional[str] = None, latest_only: bool = True) -> dict[str, Any]:
    if dataset not in config.DATASETS.values():
        return {"items": [], "data_status": "malformed", "error": f"unknown dataset: {dataset}", "source_kind": "bronze_parquet"}
    return _ps().load_bronze_dataset(
        _contract(),
        dataset,
        data_lake_uri=data_lake_uri or lake.default_data_lake_uri(),
        latest_only=latest_only,
        id_fields=["url", "source_url", "link"],
        id_sep=":",
        stale_after_hours=config.STALE_AFTER_HOURS,
        item_builder=_item_from_bronze,
        read_mode=config.LAKE_READ_MODE,
        read_fallback=config.LAKE_READ_FALLBACK,
    )


def load_records(*, data_lake_uri: Optional[str] = None) -> dict[str, Any]:
    return load_dataset(config.DEFAULT_DATASET, data_lake_uri=data_lake_uri, latest_only=True)


def load_history(*, dataset: Optional[str] = None, data_lake_uri: Optional[str] = None) -> dict[str, Any]:
    return load_dataset(dataset or config.DEFAULT_HISTORY_DATASET, data_lake_uri=data_lake_uri, latest_only=False)


def get_record(record_id: str, *, data_lake_uri: Optional[str] = None) -> Optional[dict[str, Any]]:
    payload = load_records(data_lake_uri=data_lake_uri)
    for item in payload.get("items", []):
        if str(item.get("record_id")) == str(record_id):
            return item
    return None


def paginate(items: list[dict[str, Any]], *, limit: int = 50, cursor: Optional[str] = None) -> tuple[list[dict[str, Any]], Optional[str]]:
    return _ps().paginate(items, limit=limit, cursor=cursor)


def envelope(*, items: list[dict[str, Any]], data_status: str, next_cursor: Optional[str] = None, retrieved_at: Optional[str] = None, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    return _ps().envelope(
        schema_version=config.SCHEMA_VERSION,
        source=config.REPO_NAME,
        items=items,
        data_status=data_status,
        next_cursor=next_cursor,
        retrieved_at=retrieved_at,
        extra=extra,
    )


def project_csv(items: list[dict[str, Any]], *, path: Path) -> Path:
    """Explicit CLI projection; callers invoke only after all lake writes pass."""
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({key for item in items for key in item})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(items)
    return path
