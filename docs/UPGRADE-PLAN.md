# Upgrade plan — book-job-data

Score: 7/10 -> 7.5/10 — standalone runtime pin bumped and the replay workaround removed.
Pass 1: 5.5/10 -> 7/10 — the real lake test failed in CI: the pinned
`solo-empire-data-lake` runtime's `landing_object_bytes` requires a parent checkout
(`TypeError` on `None / "infra"`); no lint in CI.

## Backlog

- P0: Confirm the first CI run on GitHub is green; keep it required on `main`.
- P1: When `solo-empire-data-lake` moves, bump the pinned commit in `[lake]` together with
  the other book-*-data repos (same SHA everywhere).
- P1: Extend the real-lake test to read Bronze back and assert the privacy allowlist
  holds end to end (today allowlist/masking is tested on normalization only).
- P2: Add a `dev` extra (`pytest`, `ruff`) so CI and README share one install line.

## Done in this pass (pass 2)

- Bumped the `[lake]` pin to `solo-empire-data-lake@68fb5a9`, which fixes
  `landing_object_bytes` upstream; `lake.landing_object_bytes` now delegates to the
  adapter again (local `ObjectStore` workaround removed).
- `[tool.ruff.lint] select = ["E4", "E7", "E9", "F"]`: unpinned ruff 0.16 widened its
  defaults (40 findings here) and would have failed `ruff check .` in CI.
- Verified: fresh venv `pip install -e ".[lake]"` from the pinned tarball — 17/17 pass;
  also with `SOLO_EMPIRE_ROOT=<parent>`; ruff 0.15 and 0.16 clean.

## Done in pass 1

- `lake.landing_object_bytes` reads via the adapter's `ObjectStore` and maps
  `StorageError` to `LakeIngestError`, so replay works with the standalone runtime.
- CI: `concurrency` + read-only `permissions`, `ruff check .`, `pytest -q -rs`.
- Removed unused imports flagged by ruff; README gained a "Tests" section.
- Verified: clean venv with `pip install -e ".[lake]" pytest` — 17/17 pass (was 16/17);
  also passes against the parent repo's adapter.
