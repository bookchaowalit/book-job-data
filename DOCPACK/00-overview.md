---
title: Book Job Data — ภาพรวมระบบและสารบัญเอกสาร
doc_id: BJD-DOC-00
doc_type: overview
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
related: 00-product-card.md, 01-prd.md, 02-architecture.md, 03-nfr-security.md, 04-runbook.md
---

# Book Job Data — ภาพรวมระบบและสารบัญเอกสาร

## 1. สรุประบบ

`book-job-data` (repo นี้ คือ public Track B ที่ remote `bookchaowalit/book-job-data`) เป็น data product
ฝั่งรับของ job pipeline: รับไฟล์ capture CSV ที่ `book-job-scraping` ผลิต เก็บ bytes ต้นฉบับใน landing
แปลงเป็น Bronze Parquet ตาม contract `job.v1` พร้อม manifest/lineage และเปิด API แบบอ่านอย่างเดียว
ที่พอร์ต `8109` ซึ่งอ่าน Bronze เท่านั้น (local หรือ R2/S3 ผ่าน DuckDB) มี field allowlist และการปิดบัง
อีเมล/เบอร์โทรทั้งตอน ingest และตอนตอบ API scraper เป็น collection-only และไม่เขียนฐานข้อมูลของระบบอื่น

## 2. สถานะปัจจุบัน

| รายการ | สถานะ (ตรวจจาก repository) |
|---|---|
| Contract | `job.v1`, `domain=jobs`, privacy class `internal` |
| Datasets | `job_postings`, `job_matches`, `job_leads` และ `*_history` |
| API | `book_job_data.api` (:8109) — `/healthz`, `/v1/metadata`, `/v1/records`, `/v1/history`, `/v1/records/<id>`; `POST /v1/refresh` ถูกห้าม |
| Schedule | Windows Task Scheduler ingest รายชั่วโมง (`ops/windows/scheduled-ingest.ps1`) |
| CI | GitHub Actions `ci.yml` (push `main`, PR, manual): ruff, pytest, compileall, CLI help |
| Deploy config | `Dockerfile`, `render.yaml` (Render Free, health `/healthz`) |
| Hosted | parallel Render service verified 2026-08-09 ที่ commit `6942dbf` กับ demo prefix 2 แถว; สถานะปัจจุบัน **[ต้องยืนยัน]** |
| Live URL | ไม่เก็บใน Git |

## 3. ความสัมพันธ์กับสำเนาใน parent

| | `book-apps/tools/book-job-data-public` (repo นี้) | `book-apps/tools/book-job-data` (สำเนาใน parent) |
|---|---|---|
| Git | nested repo, remote `book-job-data.git` (public) | ไฟล์ใน checkout ของ Solo Empire (ไม่มี `.git` ของตัวเอง) |
| บทบาท | canonical (ข้อเสนอใน product card) | compatibility mirror สำหรับ monorepo CI และ Render service เดิม |
| ส่วนที่มีเฉพาะที่นี่ | CI, `Dockerfile`, `render.yaml`, `ops/`, `docs/`, `LICENSE`, test `test_end_to_end_quality.py`, `test_redaction_edge_cases.py` | — |
| โค้ด `src/` | `api.py`, `ingest.py`, `lake.py`, `privacy.py`, `store.py` ต่างจาก parent แล้ว (drift) | ถูก grandfather ใน `runtime-boundaries.yaml` `legacy_workspace_sources` |

แผนตาม roadmap (`jd-g2`/`jd-t3`): cutover hosted lane ไป repo นี้ ชี้ consumer ใหม่ แล้วลบสำเนาใน parent
ออกจาก `legacy_workspace_sources` การตัดสินให้ repo นี้เป็น canonical ยังเป็น **[ต้องยืนยัน]** โดย Product owner

## 4. ผู้ใช้หลัก

- Operator ของ Solo Empire (หางาน/หาลูกค้า)
- Consumer ภายใน: `infra/scripts/utils/job_client.py`, opportunity backlog import, dashboard leads, `book-sales-jobsdb`
  (ตาม `scraping-data-coverage.yaml`)

## 5. รายการเอกสาร

| รหัส | ไฟล์ | ชื่อ | ผู้อ่านหลัก |
|---|---|---|---|
| CARD-book-job-data-public | `00-product-card.md` | Product Card (คำตัดสิน `invest`) | Product owner |
| BJD-DOC-00 | `00-overview.md` | ภาพรวมระบบและสารบัญเอกสาร | ทุกคน |
| BJD-DOC-01 | `01-prd.md` | Product Requirements (PRD) | Product owner |
| BJD-DOC-02 | `02-architecture.md` | System Architecture | Solution Architect, Data |
| BJD-DOC-03 | `03-nfr-security.md` | NFR และความปลอดภัย | Solution Architect, Security |
| BJD-DOC-04 | `04-runbook.md` | Runbook การติดตั้งและดูแลระบบ | DevOps / Operator |

## 6. วิธีอ่าน

1. อ่าน Product Card และหัวข้อ 3 ของเอกสารนี้ (ความสัมพันธ์กับสำเนาใน parent)
2. อ่าน PRD สำหรับขอบเขตและ decision ที่ต้องยืนยัน
3. อ่าน Architecture + NFR สำหรับ contract, เส้นทางข้อมูล, privacy และ freshness
4. ใช้ Runbook สำหรับ ingest, schedule, deploy Render และการแก้ปัญหา

ป้าย **[ต้องยืนยัน]** คือข้อเท็จจริงที่เจ้าของต้องยืนยัน และ **[สมมติฐาน]** คือสมมติฐานทำงาน

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `render.yaml`
- `Dockerfile`
- `.github/workflows/ci.yml`
- `src/book_job_data/api.py`
- `src/book_job_data/config.py`
- `DOCPACK/00-product-card.md`
- `(solo-empire) repository-catalog/registries/runtime-boundaries.yaml`
- `(solo-empire) repository-catalog/roadmaps/data-scrapers.yaml`
- `(solo-empire) operations/evidence/BOOK-JOB-DATA-RENDER-CUTOVER.md`
- `(solo-empire) systems/ai-data/scraping-data-coverage.yaml`
