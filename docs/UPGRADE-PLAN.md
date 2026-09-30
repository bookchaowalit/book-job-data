# Upgrade plan — book-job-data

Score: 7.5/10 -> 8/10 — the privacy allowlist is now proven end to end through Bronze and the API, captures are validated and read once, and projections are atomic.
Pass 2: 7/10 -> 7.5/10 — standalone runtime pin bumped and the replay workaround removed.
Pass 1: 5.5/10 -> 7/10 — the real lake test failed in CI: the pinned
`solo-empire-data-lake` runtime's `landing_object_bytes` requires a parent checkout
(`TypeError` on `None / "infra"`); no lint in CI.

## Backlog

- P0: Confirm the first CI run on GitHub is green; keep it required on `main`.
- P1: When `solo-empire-data-lake` moves, bump the pinned commit in `[lake]` together with
  the other book-*-data repos (same SHA everywhere).
- P1: Stop writing the absolute `input_path` into landing metadata (it records the
  operator's local filesystem layout); `input_name` is enough for lineage.
- P2: Add a `dev` extra (`pytest`, `ruff`) so CI and README share one install line.

## Done in this pass (pass 4: edge cases)

- Privacy leak fixed in `privacy.redact_text`: the phone pattern used `\w`
  boundaries, and Thai letters are `\w`, so numbers glued to Thai words
  (`โทร0812345678`, `ติดต่อ...ค่ะ`) and `Tel.0812345678` were never masked.
  Group separators now include no-break/thin spaces and Unicode dashes
  (`&nbsp;`, U+202F, U+2011, en dash, minus), and U+200B/U+2060/BOM/soft
  hyphen are removed first so they cannot split an email or phone number.
- Verified: `tests/test_redaction_edge_cases.py` (11 of 14 cases fail on the
  old code; the non-contact cases pass on both); full suite 27 passed; ruff
  0.15.8 + 0.16.9.
- Salary ranges glued with a dash (`30000-50000`, `25000–35000`,
  `เงินเดือน120000-170000บาท`) are no longer masked as phones: an ascending
  pair of 4+ digit amounts without a leading zero is kept (Thai numbers start
  with 0 or +66); `02-1234567`, `081-2345678` and toll-free `1800-123456`
  still mask. `30,000-50,000` and `฿30000-฿50000` are pinned as regressions.
  Verified: 3 of 5 new range cases fail on the old code; full suite 29
  passed; ruff 0.15.8 + 0.16.9.
- Bumped the `[lake]` pin `68fb5a9` -> `4c24c66` (NDJSON/BOM/U+2028/double-decode fixes); 29 passed with the new package; ruff 0.15.8 + 0.16.9 clean.

## Done in this pass (pass 3)

- `tests/test_end_to_end_quality.py`: ingest a capture with `email`/`contact`/`phone`
  columns and contacts in free text, then read Bronze (snapshot + history) and
  `load_records`/`load_history` back — only `ALLOWED_FIELDS` keys, no contact value
  survives, masks are in place, and the landing bytes still replay exactly.
- `normalize_rows` skips blank/empty-cell rows and surplus `None`-key cells, so a trailing
  `,,,` line no longer lands a ghost record; an all-blank capture fails before any write.
- CLI reads each capture once and passes the validated bytes/rows to `ingest_capture`
  (no second read), de-duplicates repeated `--input`s, and exits 2 on non-UTF-8 input.
- `store.project_csv` writes atomically (temp file + `os.replace`).
- README documents capture handling and the end-to-end privacy test.
- Verified: `pytest -q -rs` 23 passed, 0 skipped (was 17) with the `[lake]` venv; ruff
  0.15.8 and 0.16.9 clean.

## Done in pass 2

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
