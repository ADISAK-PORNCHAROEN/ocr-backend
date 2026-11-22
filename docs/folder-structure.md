# โครงสร้าง FastAPI และ uv

สถานะ: implementation ปัจจุบันของ backend จัดตามชั้นงานที่ตกลงไว้ โดยแต่ละไฟล์แยกตามความรับผิดชอบ

## การใช้งานจาก frontend

Frontend ส่งไฟล์ไปยัง `POST /api/v1/ocr/jobs` ตรวจสถานะงาน ดึงหน้าและผล แล้วลบงานเมื่อใช้งานเสร็จ ตาม [สัญญา API](frontend-api.md) การแก้ไขข้อความและสร้างไฟล์ดาวน์โหลดเป็นหน้าที่ frontend

## โครงสร้างที่เสนอ

```text
ocr-backend/
├── pyproject.toml                  # Python และ dependencies ที่ uv จัดการ
├── uv.lock                         # รุ่น dependency ที่ resolve แล้ว
├── .python-version                 # Python ที่เลือกหลังตรวจ compatibility
├── .gitignore
├── app/
│   ├── main.py                     # สร้าง FastAPI, lifespan และลงทะเบียน router
│   ├── core/                       # settings และ error types
│   ├── entities/                   # Job, Page, สถานะ, ผล OCR และ progress
│   ├── repositories/               # งานในหน่วยความจำและ artifacts ชั่วคราว
│   ├── services/                   # คิว, วงจรงาน, progress, delete และ expiry
│   ├── api/
│   │   ├── controllers/            # health และ OCR job endpoints
│   │   └── schemas/                # HTTP request/response แยกจาก entities
│   ├── documents/                  # ตรวจไฟล์และนับหน้า/ขนาดภาพ
│   └── ocr/                        # OpenThai process adapter และ mapping ผล
├── tests/
│   ├── integration/                # API และวงจรชีวิตงาน
│   ├── unit/                       # กฎที่ซับซ้อนและการแปลงผล
│   └── smoke/                      # OCR จริงด้วยภาพและ PDF สังเคราะห์
└── docs/
```

รายละเอียด runtime และ API อยู่ใน [สถาปัตยกรรม](architecture.md), [สัญญา API สำหรับ frontend](frontend-api.md) และ [ข้อจำกัด runtime](runtime-limits.md) โครงสร้างแสดงขอบเขตของไฟล์จริง; เพิ่ม `__init__.py` ตามความจำเป็น และไม่สร้าง layer ว่างที่ไม่มีหน้าที่

## หน้าที่และทิศทางการเรียก

`controller → service → repository` เป็นแนวเดียวกับ Splitbill โดย service เรียกตัวอ่านเอกสารและ OCR adapter ด้วย Controller รับ multipart และแปลง HTTP error ไม่รันโมเดลเอง Service เป็นเจ้าของนโยบายงาน การประมวลผลรายหน้า และการลบ Repository เป็นเจ้าของการเก็บและอ่านข้อมูลชั่วคราว ไม่กำหนดกฎ OCR ส่วน entity บรรยายข้อมูลและสถานะ ไม่จำเป็นต้องเป็น SQLAlchemy model เพราะเวอร์ชันนี้ไม่ใช้ฐานข้อมูลถาวร

ไฟล์ `jobs.py` ในแต่ละชั้นมีขอบเขตเฉพาะงาน OCR อย่านำ controller, repository หรือ service ของเรื่องใหม่มารวมไว้โดยอัตโนมัติ หากมี feature ใหม่ที่มีหน้าที่แยกชัด ให้เพิ่มไฟล์ของ feature นั้นในชั้นที่ต้องใช้จริง ไม่สร้าง repository แยกตามตารางหรือไฟล์เสมอไป และไม่แยก page เป็น service อีกตัวหากยังอยู่ในวงจรงานเดียวกัน

## ภาพร่าง interface

ตัวอย่างนี้อธิบายขอบเขตของ implementation:

```python
# controller เรียก service; HTTP types ไม่รั่วไปยัง entity
job = await jobs_service.submit(upload)
snapshot = jobs_service.get(job.id)
page = jobs_service.get_page(job.id, page_number=1)
await jobs_service.delete(job.id)

# jobs service เป็นเจ้าของการเปลี่ยนสถานะ
class JobsService:
    async def submit(self, upload: ValidatedUpload) -> JobSnapshot: ...
    def get(self, job_id: JobId) -> JobSnapshot: ...
    def list_pages(self, job_id: JobId) -> list[PageSnapshot]: ...
    def get_page(self, job_id: JobId, page_number: int) -> PageSnapshot: ...
    def get_page_image(self, job_id: JobId, page_number: int) -> PageImage: ...
    async def delete(self, job_id: JobId) -> None: ...

class JobsRepository:
    def get(self, job_id: JobId) -> Job: ...
    def save(self, job: Job) -> None: ...
    def delete(self, job_id: JobId) -> None: ...
```

Repository และ artifacts ต้องมีเจ้าของการเขียนที่ชัดเจน Worker process รับภาพและคืนผล ไม่แก้สถานะงานโดยตรง Service จำกัดคิวและ worker เริ่มต้นหนึ่ง worker และหนึ่ง inference thread จากนั้นวัดจริง ดูรายละเอียดการลบระหว่างประมวลผลใน [สถาปัตยกรรม](architecture.md)

## การใช้ uv

กำหนด dependencies ใน `pyproject.toml` และ commit `uv.lock` หลัง resolve สำเร็จ ใช้ `uv sync` ติดตั้ง environment และ `uv run` เรียกคำสั่งใน environment ของโปรเจกต์ ตัวอย่างเมื่อพัฒนาและติดตั้ง dependencies แล้ว:

```powershell
uv sync
uv run uvicorn app.main:app --reload
uv run pytest
```

`--reload` ใช้ระหว่างพัฒนาเท่านั้น และต้องรัน API หนึ่ง process สำหรับที่เก็บงานในหน่วยความจำ ดู [เอกสาร uv](https://docs.astral.sh/uv/guides/projects/) รุ่น Python และ dependencies ต้องตรวจความเข้ากันได้กับ runtime OCR และเครื่องเป้าหมายก่อนตรึง ไม่คัดลอกฐานข้อมูลหรือ migrations จาก Splitbill มาโดยไม่มีความจำเป็น

## เหตุผลที่เลือก

Splitbill ปัจจุบันแยกโฟลเดอร์ตามชั้นและใช้ชื่อ feature ซ้ำในแต่ละชั้น จึงเลือกแบบเดียวกันเพื่อให้ผู้ใช้ค้นหาโค้ดได้คุ้นเคย อีกทางเลือกคือรวมทุกชั้นเป็น `features/ocr/` ซึ่งทำให้ไฟล์ของ feature อยู่ติดกัน แต่ต่างจากโครงสร้าง Splitbill มากกว่า เมื่อโปรเจกต์มีเพียงงาน OCR การเพิ่มโฟลเดอร์ feature ซ้อนยังไม่เพิ่มประโยชน์พอที่จะเลือก
