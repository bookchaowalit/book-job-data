---
title: Book Job Data — Product Requirements (PRD)
doc_id: BJD-DOC-01
doc_type: prd
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
related: 00-product-card.md, 00-overview.md, 02-architecture.md, 03-nfr-security.md, 04-runbook.md
---

# Book Job Data — Product Requirements (PRD)

## 1. ปัญหาและเป้าหมาย

**ปัญหา:** ข้อมูลงานจาก scraper ต้องเก็บถาวร ตรวจย้อนได้ และให้ระบบอื่นอ่านได้ โดย scraper
ไม่ต้องรู้จัก API หรือฐานข้อมูลของระบบปลายทาง และข้อมูลติดต่อบุคคลในไฟล์ capture ต้องไม่หลุดไปถึง consumer

**เป้าหมาย:** เป็น boundary เดียวของ `job.v1` — รับ capture เข้า lake พร้อม lineage และเปิดอ่านผ่าน API
อ่านอย่างเดียวที่ไม่พึ่ง CSV

**เป้าหมายตาม roadmap (สถานะ `proposed`):** ภายใน 2026-12-31 cutover hosted lane ของ `job.v1`
ไปยัง service ของ repo นี้ ปลดสำเนาใน parent และให้ readiness gate ที่ตรงกับ SLO 8 ชั่วโมงของ
`job_postings` บล็อก consumer เมื่อ batch stale หรือยัง reconcile ไม่ได้

## 2. ผู้ใช้และ persona

| Persona | ความต้องการ | หลักฐาน |
|---|---|---|
| Operator | หางาน/โปรเจกต์ที่ตรงทักษะจากข้อมูลที่สดและตรวจย้อนได้ | ผู้ใช้จริงตาม product card |
| Consumer ภายใน | `job_client`, opportunity backlog, dashboard leads, `book-sales-jobsdb` | `scraping-data-coverage.yaml` |
| ผู้ชม portfolio | ดูตัวอย่าง lake-first data product | public repo; ไม่มีตัวเลขผู้ชม **[ต้องยืนยัน]** |

## 3. ขอบเขต

**In scope**

- ingest CSV จาก `book-job-scraping` (`job_postings.csv`, `matched_jobs.csv`, `leads.csv`, `pipeline.csv`, `exported/jobsdb_jobs.csv`)
- landing (exact bytes) → Bronze `job.v1` (snapshot + history) → manifest + lineage
- API อ่านอย่างเดียวจาก Bronze (local หรือ R2/S3), CSV projection แบบ optional
- privacy allowlist และ redaction อีเมล/เบอร์โทร

**Out of scope**

- การ scrape (เป็นของ `book-job-scraping`)
- การส่งงานเข้า `opportunity.v1`
- การเขียนเข้าฐานข้อมูล CRM/task ของระบบอื่น, การ refresh ผ่าน API
- consumer ภายนอก/multi-tenant SaaS

## 4. ฟีเจอร์หลักและลำดับความสำคัญ

| ID | ฟีเจอร์ | Priority | สถานะ |
|---|---|---|---|
| FR-01 | `book_job_data.ingest --input ...` ingest เข้า lake; ข้ามแถวว่าง, ปฏิเสธ non-UTF-8 (exit 2), ไฟล์ซ้ำ land ครั้งเดียว | Must | ทำแล้ว |
| FR-02 | `--dry-run` ตรวจ/normalize โดยไม่เขียน lake | Must | ทำแล้ว |
| FR-03 | `--project-csv` เขียน projection แบบ atomic หลังทุก capture land สำเร็จ | Should | ทำแล้ว |
| FR-04 | Datasets `job_postings`, `job_matches`, `job_leads` + history | Must | ทำแล้ว |
| FR-05 | API `GET /v1/records`, `/v1/history`, `/v1/records/<id>`, `/v1/metadata`, `/healthz` | Must | ทำแล้ว |
| FR-06 | `POST /v1/refresh` ถูกห้าม (403) | Must | ทำแล้ว |
| FR-07 | Token บังคับเมื่อ bind นอก loopback; cache TTL; rate limit | Must | ทำแล้ว |
| FR-08 | อ่าน Bronze จาก R2/S3 โดยตรง (`LAKE_READ_MODE=parquet`, `LAKE_READ_FALLBACK=error`) | Should | ทำแล้ว; verified กับ demo prefix |
| FR-09 | Ingest รายชั่วโมง + แจ้ง stale capture (exit 3) | Should | ทำแล้ว (Windows) |
| FR-10 | Threshold stale สอดคล้อง SLO 8h (`jd-g1`) | Must | ยังไม่ทำ (ค่า default 12h) |
| FR-11 | Cutover Render ไป HEAD ปัจจุบัน + ปลดสำเนา parent (`jd-g2`) | Must | ยังไม่ทำ |
| FR-12 | แก้ README ที่ยังอ้าง opportunity intelligence เป็น Gold product (`jd-g3`) | Could | ยังไม่ทำ |

## 5. ตัวชี้วัดความสำเร็จ

| ตัวชี้วัด | เป้าหมาย | ที่มา |
|---|---|---|
| `task data:job:readiness` รายงาน ok | 7 วันติด | `jd-g4` |
| Hosted verifier `status=verified` ที่ commit ปัจจุบัน | ผ่าน | `jd-t2` |
| สำเนาใน parent ถูกลบจาก `legacy_workspace_sources` | ใช่ | `jd-t3` |
| ไม่มีข้อมูลติดต่อหลุดใน Bronze/API | 0 กรณีใน test | `tests/test_end_to_end_quality.py` |

ไม่มีค่าฐานเรื่องปริมาณงานต่อวันหรือการใช้งาน consumer ใน repository **[ต้องยืนยัน]**

## 6. Roadmap / phase

| Phase | เนื้อหา | สถานะ |
|---|---|---|
| P0 | contract `job.v1`, ingest, Bronze, API local | เสร็จ |
| P1 | privacy allowlist/redaction, token, R2 read, Render blueprint, ingest รายชั่วโมง | เสร็จ |
| P2 | align SLO, redeploy Render ที่ HEAD, repoint consumers, ปลดสำเนา parent | วางแผน (2026-Q4) |
| P3 | สังเกต readiness 7 วัน | วางแผน |

## 7. Decision ที่ต้องยืนยัน

| ID | Decision | สถานะ |
|---|---|---|
| D-01 | repo นี้เป็น canonical ของ `job.v1`; สำเนา `book-apps/tools/book-job-data` เป็น compatibility mirror ชั่วคราว | เสนอใน product card **[ต้องยืนยัน]** |
| D-02 | ผู้อนุมัติและวันที่ repoint/ปิด Render service เดิม (การกระทำแบบ destructive) | **[ต้องยืนยัน]** (open question ใน roadmap) |
| D-03 | `job_leads` (มาจาก pipeline) คง internal-only หรือไม่ | **[ต้องยืนยัน]** |

## 8. ข้อสมมติฐานและความเสี่ยง

| ID | รายการ | ผลกระทบ | การลด |
|---|---|---|---|
| R-01 | สองสำเนา drift (โค้ด `src/` ต่างกันแล้ว) | bug fix/privacy fix ไม่ถึง service เดิม | cutover แล้วลบสำเนา (`jd-t3`) |
| R-02 | Render Free sleep และ filesystem ชั่วคราว | API ช้าครั้งแรก/ไม่มีข้อมูล local | R2 เป็นแหล่งถาวรเดียว |
| R-03 | Scraper หยุด → capture stale | consumer ได้ข้อมูลเก่า | alert stale (exit 3) + readiness gate |
| R-04 | Redaction พลาดรูปแบบเบอร์/อีเมลใหม่ | ข้อมูลส่วนบุคคลหลุด | allowlist + edge-case tests; ทบทวนเป็นระยะ |
| R-05 | ToS ของ job board ต้นทาง | ต้องหยุดเก็บบางแหล่ง | อยู่ในความรับผิดชอบของ `book-job-scraping` **[ต้องยืนยัน]** |
| A-01 | `solo-empire-data-lake` pin เดียวกันกับ repo `book-*-data` อื่น | อัปเดตต้องทำพร้อมกัน | backlog P1 |

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `docs/UPGRADE-PLAN.md`
- `src/book_job_data/ingest.py`
- `src/book_job_data/api.py`
- `scripts/scheduled_ingest.py`
- `tests/test_end_to_end_quality.py`
- `DOCPACK/00-product-card.md`
- `(solo-empire) repository-catalog/roadmaps/data-scrapers.yaml` (`jd-g1`–`jd-g4`, `jd-t1`–`jd-t5`)
- `(solo-empire) systems/ai-data/scraping-data-coverage.yaml`
