# สถาปัตยกรรม OCR Playground

สถานะ: architecture ของ implementation สำหรับโปรเจกต์เครื่องเดียว ยังไม่มี performance benchmark อ้างอิง [ขอบเขต](project-scope.md) และ [สัญญา API](frontend-api.md)

## ปัญหา

ผู้ใช้ต้องการทดลอง OCR ภาษาไทยและอังกฤษบน CPU พร้อมติดตามสถานะรายหน้าและตรวจแก้ผล โดยไม่เก็บข้อมูลถาวร สถาปัตยกรรมต้องดูแลได้ง่ายและไม่ทำให้การประมวลผล OCR บล็อก API

## มุมมองผู้เรียก

Frontend ส่งไฟล์ด้วย `POST /api/v1/ocr/jobs` แล้วตรวจงานด้วย `GET /api/v1/ocr/jobs/{jobId}` จากนั้นดึงผลและภาพแต่ละหน้า สุดท้ายส่ง `DELETE /api/v1/ocr/jobs/{jobId}` เมื่อจบงาน รายละเอียดอยู่ในสัญญา API

ภายใน API ใช้บริการงานเพียงจุดเดียว ตัวอย่างต่อไปเป็นภาพร่าง ไม่ใช่โค้ดที่รันได้:

```python
job = jobs.submit(upload)
snapshot = jobs.get(job.id)
page = jobs.get_page(job.id, page_number=1)
jobs.delete(job.id)
```

## รูปแบบที่แนะนำ

ใช้ Python พร้อม FastAPI สำหรับ HTTP และ runtime Python ของ OpenThai OCR Text เริ่มจาก application เดียวที่มี API process และ OCR worker process จำนวนจำกัด ไม่ต้องตั้ง Redis หรือบริการคิวแยกสำหรับเวอร์ชันเครื่องเดียว รัน API เพียงหนึ่ง process เพื่อให้การจัดการงานและการลบมีเจ้าของเดียว

```text
Frontend -> HTTP API -> บริการงาน OCR -> process pool ที่จำกัดจำนวน
                              |                    |
                         ไฟล์ชั่วคราว        PDF/image + OpenThai
```

API process เป็นเจ้าของสถานะและที่เก็บข้อมูลชั่วคราวของงานทั้งหมด Worker รับงานรายหน้าและส่งผลกลับเท่านั้น ห้ามเขียนสถานะงานโดยตรง ให้จำกัดจำนวนงานที่ค้างและขนาดข้อมูลที่เข้าคิว API ไม่รอ OCR ใน request thread และเริ่มต้นโมเดลหนึ่งครั้งต่อ worker แทนการโหลดใหม่ทุกหน้า

เริ่มต้นด้วย worker หนึ่ง process และ inference หนึ่ง thread เป็น baseline หลังจากนั้นทดลองปรับจำนวน process และ thread ตาม CPU และ RAM จริง อย่าตีความคำแนะนำหนึ่ง process ต่อ core ของผู้พัฒนาโมเดลเป็นค่าเริ่มต้นที่เหมาะกับเครื่องทุกเครื่อง

## โมดูลและข้อมูล

การจัดไฟล์ใช้ชั้น `entities`, `repositories`, `services` และ `api/controllers` แบบ Splitbill โดยแต่ละไฟล์รับผิดชอบเรื่องของตัวเอง ดู [โครงสร้างโปรเจกต์](folder-structure.md) ซึ่งเป็นรายละเอียดที่ใช้แทนชื่อโมดูลทั่วไปด้านล่าง

- **HTTP** รับและตรวจข้อมูลขาเข้า แปลงผล domain เป็นสัญญา API
- **งาน OCR** เป็นเจ้าของวงจรชีวิตงาน การจัดคิว การรวมผลรายหน้า การลบ และหมดอายุ
- **เอกสาร** ตรวจและแปลงภาพหรือหน้า PDF โดยกำหนดขนาดและพิกัดภาพเดียวกับผล OCR
- **ตัวเชื่อม OCR** โหลด runtime รุ่นที่ตรึงไว้และแปลงผลโมเดลเป็นผลรายหน้า โดยเก็บข้อความ ลำดับ กรอบ และความมั่นใจเดิม

แบบชนิดข้อมูลต่อไปนี้เป็น pseudocode เพื่อสื่อขอบเขต ไม่ใช่ implementation:

```python
JobId = str
PageNumber = int  # เริ่มที่ 1; ตรวจตอนรับจากภายนอก

class Line:
    text: str
    confidence: float
    box: BoundingBox

class PageSucceeded:
    number: PageNumber
    original_text: str  # สตริงว่างได้เมื่อไม่พบข้อความ
    lines: list[Line]
    image_size: ImageSize

class PageFailed:
    number: PageNumber
    error: PageError

PageResult = PageSucceeded | PageFailed

class Jobs:
    def submit(self, upload: ValidatedUpload) -> JobSnapshot: ...
    def get(self, job_id: JobId) -> JobSnapshot: ...
    def list_pages(self, job_id: JobId) -> list[PageSnapshot]: ...
    def get_page(self, job_id: JobId, page_number: PageNumber) -> PageSnapshot: ...
    def get_page_image(self, job_id: JobId, page_number: PageNumber) -> PageImage: ...
    def delete(self, job_id: JobId) -> None: ...
```

implementation ปัจจุบันแยก HTTP schema จาก entities และคำนวณ progress จากสถานะหน้า ไม่เก็บตัวนับแยก หน้าว่างเป็น completed และหน้า failed มี error โดยไม่มี OCR result

Page response ใช้ pending, processing, completed หรือ failed เมื่อคิวเต็มจะคืน `503 JOB_QUEUE_FULL` พร้อม `Retry-After` ดู status code, JSON schema และ error code ที่ยืนยันแล้วใน [สัญญา API](frontend-api.md)

## วงจรชีวิตและกรณีแข่งขัน

- สถานะงานเป็น queued, processing, completed, partially_completed หรือ failed ตามสัญญา API หน้าที่ไม่มีข้อความยังเป็นหน้าสำเร็จ
- เมื่อลบหรือหมดอายุ ให้ owner ทำเครื่องหมายว่างานถูกลบก่อน แล้วปฏิเสธผล worker ที่กลับมาทีหลังและลบไฟล์หลัง worker เลิกใช้ ห้ามปล่อยให้ผลที่มาช้าสร้างงานกลับขึ้นมา
- ไม่รับประกันว่ายกเลิก native inference กลางคันได้ การลบต้องทำให้ข้อมูลเข้าถึงไม่ได้ทันทีและจัดการลบไฟล์เมื่อปลอดภัย
- เมื่อ process หยุดกะทันหัน ให้ล้างไฟล์ตกค้างจากรอบก่อนตอนเริ่มระบบ งานระหว่างทำหายได้เพราะไม่มีการเก็บถาวร
- จำกัดขนาดไฟล์ พิกเซลภาพ จำนวนงาน และอายุข้อมูลตามค่า local ที่บันทึกใน [runtime limits](runtime-limits.md) ไม่มีเพดานจำนวนหน้าแบบตายตัว; total-pixel budget จำกัดงานสะสม เริ่มใช้ loopback สำหรับการสาธิตบนเครื่อง

## เหตุผลและทางเลือก

Python ใช้ runtime ที่ผู้พัฒนาโมเดลเผยแพร่ได้โดยตรง ส่วน inference ใช้ ONNX ผ่าน OpenVINO หรือ ONNX Runtime ซึ่งเป็น native runtime การเขียน API ด้วยภาษา native จึงไม่ได้พิสูจน์ว่าจะทำให้ OCR ทั้งระบบเร็วขึ้น ผู้พัฒนาเตือนว่าการ port ต้องรักษา logic ภาษาไทยและลำดับการอ่าน ไม่ใช่เรียก ONNX อย่างเดียว [Model card รุ่น 2.1.4](https://huggingface.co/iapp/OpenThai2.1-OCR-Text-20261118/blob/v2.1/README.md)

ทางเลือก API ภาษา Go หรือ Rust ที่เรียก Python worker เพิ่ม protocol และการ deploy สอง runtime แต่ยังต้องใช้ Python OCR จึงยังไม่มีหลักฐานว่าคุ้มสำหรับ portfolio เครื่องเดียว การเขียน pipeline ใหม่ทั้งหมดด้วย Go หรือ Rust เสี่ยงเปลี่ยนคุณภาพผล OCR และต้องพิสูจน์ด้วย benchmark และชุดทดสอบข้อความจริง

เปรียบเทียบสองแบบแล้วเลือก Python เป็นฐาน เพราะ frontend ใช้ API เหมือนกันแต่ระบบมีขอบเขตและเทคโนโลยีที่ต้องดูแลน้อยกว่า นำหลักการจำกัดคิวและให้ owner คนเดียวจัดการสถานะจากทั้งสองแบบมาใช้ และเลือก process pool ขนาดเริ่มต้นหนึ่งจากแนวคิดแยกงาน CPU เพื่อไม่บล็อก API แบบ Go กับ Python แยกบริการยังไม่เหมาะจนกว่าจะมีข้อกำหนดด้าน isolation หรือผลวัดที่รองรับ ข้ามการ cross-judge ข้ามตระกูลโมเดลเพราะการตั้งค่าโครงการอนุญาตเฉพาะโมเดลตระกูล GPT

การใช้ process pool เพิ่มการใช้ RAM และความซับซ้อนของ lifecycle แลกกับการแยกงาน CPU จาก API และมีทางเพิ่ม throughput เมื่อวัดแล้วจำเป็น ผู้พัฒนาโมเดลรายงานผล benchmark บนฮาร์ดแวร์เฉพาะ ซึ่งใช้ประมาณการกับเครื่องนี้ไม่ได้

## การตรวจสอบและงานต่อไป

HTTP integration tests ใช้ OCR adapter จำลองควบคุมหน้าสำเร็จ ว่าง ล้มเหลว การลบระหว่างประมวลผล และหมดอายุ Real-model smoke ทดสอบภาพไทยสังเคราะห์และ PDF หลายหน้าบน CPU

วัด cold start และ warm run แยกกัน รวมเวลาทั้งอัปโหลด แปลง PDF OCR และดึงผล บันทึก CPU, RAM, เวอร์ชันโมเดล, runtime, จำนวน worker, thread และชุดเอกสาร เปรียบเทียบจำนวน worker พร้อมตรวจความถูกต้องของผล ก่อนตัดสินใจปรับ performance

Model smoke ยืนยัน revision `v2.1.4`, confidence ช่วง 0–1 และ box polygon สี่มุม จากนั้น backend แปลงเป็น axis-aligned `x1,y1,x2,y2` ตามภาพที่ส่งให้ frontend ใช้ การทดสอบนี้ยังไม่ใช่การวัด benchmark หรือคุณภาพบนเอกสารจริง
