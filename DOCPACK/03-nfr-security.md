---
title: Book Job Data — NFR และความปลอดภัย
doc_id: BJD-DOC-03
doc_type: nfr-security
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: Solution Architect + Security (Book Dev)
related: 00-overview.md, 01-prd.md, 02-architecture.md, 04-runbook.md
---

# Book Job Data — NFR และความปลอดภัย

## 1. สรุป

ความเสี่ยงหลักของ product นี้คือข้อมูลส่วนบุคคล (ผู้ติดต่อ/ผู้สรรหา) ในไฟล์ capture และความสดของข้อมูล
ที่ขึ้นกับ scraper ต้นทาง ค่าที่ระบุว่า "บังคับใช้" มาจากโค้ด ค่าอื่นเป็นเป้าหมาย

## 2. เป้าหมาย NFR ที่วัดได้

| ID | หมวด | ข้อกำหนด | ค่าเป้าหมาย | สถานะ / หลักฐาน |
|---|---|---|---|---|
| NFR-01 | Freshness | `job_postings` capture ไม่เก่ากว่า max_age | 8 ชั่วโมง | SLO ใน parent `scraping-data-coverage.yaml` |
| NFR-02 | Freshness | scheduled ingest แจ้ง stale เมื่อ `job_postings.csv`/`matched_jobs.csv` หายหรือเก่าเกิน | default 12 ชั่วโมง (`BOOK_JOB_DATA_MAX_CAPTURE_AGE_HOURS`), exit 3 | บังคับใช้; **ไม่ตรงกับ NFR-01** (`jd-g1`) |
| NFR-03 | Freshness | ingest cadence | ทุก 1 ชั่วโมง (scraper รีเฟรชทุก 6 ชม.) | `ops/windows/scheduled-ingest.ps1` |
| NFR-04 | Performance | cache dataset ใน API | TTL 300 วินาที (`BOOK_JOB_DATA_CACHE_TTL_SECONDS`) | บังคับใช้ |
| NFR-05 | Performance | `/healthz` ไม่อ่าน lake | — | บังคับใช้ (`data_status=not_loaded` จนกว่าจะ warm) |
| NFR-06 | Abuse | rate limit ต่อ client | 120 req/นาที (`BOOK_JOB_DATA_RATE_LIMIT_PER_MINUTE`), เกิน → 429 | บังคับใช้ (key จาก `X-Forwarded-For` ตัวขวาสุด) |
| NFR-07 | Availability | hosted บน Render Free | best effort; sleep เมื่อไม่มีการใช้งาน | ไม่มี SLA; สถานะ service ปัจจุบัน **[ต้องยืนยัน]** |
| NFR-08 | Data quality | ไฟล์ไม่มีแถวจริงล้มก่อนเขียน lake; non-UTF-8 exit 2; ไฟล์ซ้ำ land ครั้งเดียว; batch idempotent | 100% | tests `test_lake_first.py`, `test_end_to_end_quality.py` |
| NFR-09 | Data quality | Bronze/API มีเฉพาะ `ALLOWED_FIELDS` และไม่มีค่าติดต่อจาก capture | 0 การรั่วใน test | `tests/test_end_to_end_quality.py`, `test_redaction_edge_cases.py` |
| NFR-10 | Lineage | ทุกแถว Bronze มี `source_record_id`, `event_time`, `ingest_run_id`, `raw_object_key` | 100% | README Contract |
| NFR-11 | Readiness | `task data:job:readiness` ok | 7 วันติด | เป้าหมาย `jd-g4` |

## 3. Scalability

- ปริมาณข้อมูลจริงต่อวันไม่ได้บันทึกใน repository **[ต้องยืนยัน]**
- API โหลด dataset ทั้งชุดเข้า memory ผ่าน cache; เหมาะกับข้อมูลระดับ personal pipeline ไม่ใช่ multi-tenant **[สมมติฐาน]**
- R2 อ่านด้วย bounded Parquet glob ไม่ดาวน์โหลด mirror

## 4. Licensing / ToS ของแหล่ง

- repo นี้ไม่ได้ดึงข้อมูลจากเว็บโดยตรง แหล่ง job board อยู่ใน `book-job-scraping`
- parent registry ระบุ permission `status: bounded`, `classification: public_source_with_terms`,
  basis "Public job APIs and bounded public-board reads with attribution and rate limits"
- รายชื่อ job board และเงื่อนไขรายแหล่งต้องยืนยันจาก `book-job-scraping` **[ต้องยืนยัน]**
- ไม่ควรเปิด API ให้ภายนอก/สาธารณะโดยไม่ทบทวนเงื่อนไขการ redistribute ของแหล่ง **[สมมติฐาน]**
- โค้ด repo นี้ใช้ MIT License (`LICENSE`); license ของโค้ดไม่ครอบคลุมสิทธิ์ในข้อมูลงานจากแหล่งต้นทาง

## 5. Security controls

- API ปฏิเสธการ start เมื่อ bind นอก loopback โดยไม่มี `BOOK_JOB_DATA_API_TOKEN`; ทุก endpoint ยกเว้น `/healthz` ต้องมี Bearer token
- `POST /v1/refresh` → 403, method อื่นนอกจาก GET → 405
- Credential R2 (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) และ token ฉีดจาก secret manager (Infisical/Render env `sync: false`); ไม่อยู่ใน YAML, README หรือ manifest
- Client ส่ง token โดยไม่ log
- CI: `permissions: contents: read`, `FREE_ONLY=true`, `ALLOW_EXTERNAL_NETWORK=false`, `ALLOW_PAID_PROVIDER=false`
- Flags ปลอดภัยโดย default: `ALLOW_REFRESH`, `ALLOW_EXTERNAL_WRITES`, `ALLOW_PAID_PROVIDERS` = false; R2 write ต้องตั้ง `DATA_LAKE_CLOUD_WRITE_ENABLED=true` อย่างชัดเจน
- `.gitignore` กัน `.env` และ `data/*`

## 6. Privacy / PDPA

- Privacy class `internal`; ข้อมูลอาจมีข้อมูลส่วนบุคคลของผู้สรรหา/ผู้ติดต่อในไฟล์ `pipeline.csv`/`leads.csv`
- การควบคุม: allowlist ตัดคอลัมน์ `contact`/`email` ก่อนเข้า Bronze; mask อีเมลและเบอร์โทร (รวมเบอร์ไทยติดตัวอักษรไทย,
  ตัวคั่น Unicode) ใน free-text ทั้งตอน ingest และตอนตอบ API; ช่วงเงินเดือนไม่ถูก mask ผิด
- **ข้อยกเว้นสำคัญ:** landing เก็บ exact bytes ของ capture รวมข้อมูลติดต่อเดิมเป็น replay evidence ใน internal landing zone
  ต้องกำหนดผู้มีสิทธิ์เข้าถึงและระยะเก็บ **[ต้องยืนยัน]** (retention class `operational`, ไม่มีจำนวนวัน)
- landing metadata ยังบันทึก `input_path` แบบ absolute (เปิดเผยโครงสร้าง filesystem ของ operator) — backlog P1
- ฐานทางกฎหมาย PDPA สำหรับการประมวลผลข้อมูลผู้ติดต่อใน `job_leads` **[ต้องยืนยัน]**; ควรคง `job_leads` เป็น internal-only (D-03 ใน PRD)

## 7. Observability

- `data/ingest.log` (ต่อท้าย) บันทึกทุก tick, crash และ `ALERT stale scraper capture`; ไม่มี rotation ที่ระบุ **[ต้องยืนยัน]**
- `faulthandler` dump stack เมื่อ tick ค้างเกิน 900 วินาที แล้วจบ process
- `LastTaskResult` ของ Task Scheduler สะท้อน exit code (0 ok, 2 crash/input error, 3 stale)
- `/v1/metadata` แสดง `dataset_counts`, `storage_model`, `records_source_kind`, lineage
- Parent: `task data:job:readiness` reconcile Bronze batches และ freshness (read-only)
- ไม่มี alert ไปช่องทางภายนอก **[ต้องยืนยัน]**

## 8. Backup / DR

- Hosted: R2 เป็นแหล่งถาวรเดียว; Render filesystem ชั่วคราว — กู้ service ด้วยการ deploy ใหม่จาก Git
- Local lake: ไม่มีขั้นตอน backup ใน repository **[ต้องยืนยัน]** (parent มี `task db:backup` สำหรับ SQLite ไม่ใช่ lake)
- Replay: landing bytes replay ได้ตรงทุก byte (verified ใน `r2_parity.py` และ test)
- RPO/RTO ไม่ได้กำหนด **[ต้องยืนยัน]**

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Solution Architect (Book Dev) | รอพิจารณา | — | ________ |
| Security reviewer | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `render.yaml`
- `.gitignore`
- `.github/workflows/ci.yml`
- `docs/UPGRADE-PLAN.md`
- `src/book_job_data/config.py`
- `src/book_job_data/privacy.py`
- `src/book_job_data/api.py`
- `scripts/scheduled_ingest.py`
- `ops/windows/scheduled-ingest.ps1`
- `tests/test_end_to_end_quality.py`, `tests/test_redaction_edge_cases.py`
- `(solo-empire) systems/ai-data/scraping-data-coverage.yaml`
- `(solo-empire) repository-catalog/roadmaps/data-scrapers.yaml`
