# Upgrade plan — book-job-data

Score: 5.5/10 -> 7/10 — the real lake test failed in CI: the pinned
`solo-empire-data-lake` runtime's `landing_object_bytes` requires a parent checkout
(`TypeError` on `None / "infra"`); no lint in CI.

## Backlog

- P0: Confirm the first CI run on GitHub is green; keep it required on `main`.
- P0 (upstream): fix `product_adapter.landing_object_bytes` in `solo-empire-data-lake`
  to read through `ObjectStore` without `load_ingest_runtime()`; then bump the pin and
  drop the local workaround in `lake.landing_object_bytes`.
- P1: Extend the real-lake test to read Bronze back and assert the privacy allowlist
  holds end to end (today allowlist/masking is tested on normalization only).
- P2: Add a `dev` extra (`pytest`, `ruff`) so CI and README share one install line.

## Done in this pass

- `lake.landing_object_bytes` reads via the adapter's `ObjectStore` and maps
  `StorageError` to `LakeIngestError`, so replay works with the standalone runtime.
- CI: `concurrency` + read-only `permissions`, `ruff check .`, `pytest -q -rs`.
- Removed unused imports flagged by ruff; README gained a "Tests" section.
- Verified: clean venv with `pip install -e ".[lake]" pytest` — 17/17 pass (was 16/17);
  also passes against the parent repo's adapter.
