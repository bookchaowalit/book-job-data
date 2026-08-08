"""Thin shared-adapter wrapper for book-job-data."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

from . import config


def _load_shared():
    try:
        from data_lake import product_adapter as adapter  # type: ignore

        return adapter
    except ModuleNotFoundError:
        pass
    current = config.PROJECT_ROOT.resolve()
    for parent in [current, *current.parents]:
        scripts = parent / "infra" / "scripts"
        if (scripts / "data_lake" / "product_adapter.py").is_file():
            if str(scripts) not in sys.path:
                sys.path.insert(0, str(scripts))
            break
    try:
        from data_lake import product_adapter as adapter  # type: ignore
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Shared lake runtime is not installed. Run python -m pip install -e .[lake] "
            "or provide the Solo Empire parent infra/scripts path."
        ) from exc
    return adapter


_adapter = None


def _pa():
    global _adapter
    if _adapter is None:
        _adapter = _load_shared()
    return _adapter


def _contract():
    return _pa().LakeProductContract(
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


def default_data_lake_uri() -> str:
    return _pa().default_data_lake_uri(
        data_lake_uri=config.DATA_LAKE_URI,
        project_root=config.PROJECT_ROOT,
        solo_empire_root=config.SOLO_EMPIRE_ROOT,
    )


def utc_now_iso() -> str:
    return _pa().utc_now_iso()


def ingest_to_lake(
    *,
    raw: bytes,
    records: list[dict[str, Any]],
    dataset: str,
    data_lake_uri: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    provider: str = "book-job-scraping",
) -> dict[str, Any]:
    return _pa().ingest_to_lake(
        _contract(),
        raw=raw,
        records=records,
        dataset=dataset,
        data_lake_uri=data_lake_uri or default_data_lake_uri(),
        metadata=metadata,
        content_type="text/csv",
        input_format="csv",
        provider=provider,
    )


def write_lineage(result: dict[str, Any], *, dataset: str, data_dir: Optional[Path] = None) -> Path:
    return _pa().write_lineage(
        _contract(), result, dataset=dataset, data_dir=Path(data_dir or config.DATA_DIR)
    )


def load_lineage(data_dir: Optional[Path] = None) -> Optional[dict[str, Any]]:
    return _pa().load_lineage(Path(data_dir or config.DATA_DIR), filename=config.LINEAGE_FILE)


def read_bronze_rows(dataset: str, *, data_lake_uri: Optional[str] = None, sql: str | None = None) -> list[dict[str, Any]]:
    return _pa().read_bronze_rows(_contract(), dataset, data_lake_uri=data_lake_uri or default_data_lake_uri(), sql=sql)


def read_iceberg_rows(dataset: str, *, data_lake_uri: Optional[str] = None, sql: str | None = None) -> list[dict[str, Any]]:
    return _pa().read_iceberg_rows(_contract(), dataset, data_lake_uri=data_lake_uri or default_data_lake_uri(), sql=sql)


def parse_payload_json(row: dict[str, Any]) -> dict[str, Any]:
    return _pa().parse_payload_json(row)


def select_latest_bronze_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _pa().select_latest_bronze_rows(rows)


def landing_object_bytes(raw_key: str, *, data_lake_uri: Optional[str] = None) -> bytes:
    return _pa().landing_object_bytes(data_lake_uri or default_data_lake_uri(), raw_key)


LakeUnavailable = RuntimeError
LakeIngestError = RuntimeError
