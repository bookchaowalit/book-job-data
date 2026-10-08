---
title: Book Job Data — Product Card
doc_id: CARD-book-job-data-public
doc_type: product-card
verdict: invest
version: 0.1
date: 2026-10-08
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
---

# Book Job Data — Product Card

## 1. สรุปคุณค่าในหนึ่งประโยค

รับ capture จาก `book-job-scraping` เข้า data lake (landing → Bronze `job.v1`) พร้อม lineage และให้ API อ่านอย่างเดียว ทำให้ข้อมูลงานตรวจย้อนได้และไม่ผูกกับตัว scraper

## 2. ปัญหาและผู้ใช้เป้าหมาย

- ปัญหา: ข้อมูลงานจาก scraper ต้องเก็บถาวร ตรวจย้อน และให้ระบบอื่นอ่านได้โดยไม่เขียน DB ของกันและกัน
- ผู้ใช้: operator และ consumer ภายใน Solo Empire (เช่น `job_client`)

## 3. สิ่งที่ทำได้จริงตอนนี้

- `book_job_data.ingest`: รับ CSV, ข้ามแถวว่าง, ปฏิเสธ non-UTF-8, กันไฟล์ซ้ำ, `--dry-run`, `--project-csv` แบบ atomic
- datasets `job_postings`, `job_matches`, `job_leads` (+ history)
- `book_job_data.api` (:8109) อ่าน Bronze เท่านั้น, refresh ถูกห้าม; มี privacy redaction
- Dockerfile + `render.yaml` (free plan, health `/healthz`), Windows scheduled ingest รายชั่วโมง

## 4. หลักฐานสถานะ

| รายการ | ค่า (ตรวจจาก repository) |
|---|---|
| Stack | Python |
| Commits | 18 (แรก 2026-08-08 → ล่าสุด 2026-10-01) |
| Source | 14 ไฟล์ / 1,453 บรรทัด |
| Tests | 5 ไฟล์ |
| CI | 1 workflow |
| Deploy config | `render.yaml`, `Dockerfile` |
| Live URL | ไม่มี |
| README | 206 บรรทัด (`book-job-data`) |
| โครงสร้างซ้ำ (template family) | 1 repo ที่มี structure signature เดียวกัน |

repo นี้คือ public Track B (remote `book-job-data.git`) เป็น superset ของสำเนาใน parent ที่ `book-apps/tools/book-job-data` (สำเนานั้นไม่มี CI, Dockerfile, `render.yaml` และ test 2 ไฟล์ และโค้ด `src/` ต่างกัน)

## 5. คุณค่าและจุดต่าง

- เป็นครึ่งหลังของ job pipeline ที่เป็น Tier A — ทำให้ข้อมูลงานใช้ซ้ำได้โดยไม่ผูกกับ scraper
- ใช้ `solo-empire-data-lake` แบบ public pin จึงรันนอก parent ได้
- มุมรายได้: ไม่มีทางตรง; คุณค่าอยู่ที่การหางาน/หาลูกค้าของเจ้าของ **[สมมติฐาน]**

## 6. ช่องว่างสำคัญ

- สองสำเนา (public กับ parent) โค้ดต่างกันแล้ว เสี่ยง drift
- ยังไม่ยืนยันว่า Render service ทำงานอยู่ **[ต้องยืนยัน]**
- ไม่มี consumer ภายนอก

## 7. คำตัดสิน

**`invest`** — เป็นส่วนสำคัญของ job pipeline ที่มีผู้ใช้จริง (เจ้าของ) มี test, CI และ deploy config จึงลงทุนต่อร่วมกับ `book-job-scraping` ให้ repo นี้เป็น canonical และให้สำเนาใน parent เป็นเพียง compatibility mirror จะลดเป็น `showcase` ถ้าเลิกใช้ job pipeline

## 8. ขั้นต่อไป

1. ประกาศให้ repo นี้เป็น canonical และวางแผนให้ parent copy ตาม (หรือเลิกใช้)
2. ตรวจสถานะ Render service และ `task data:job:readiness`
3. บันทึก CSV contract ร่วมกับ `book-job-scraping`

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `render.yaml`
- `Dockerfile`
- `src/book_job_data/api.py`
- `src/book_job_data/ingest.py`
- `(book-dev) bookchaowalit/book-apps/tools/book-job-data/`
