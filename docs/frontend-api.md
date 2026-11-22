# สัญญา API สำหรับ frontend

สถานะ: ข้อเสนอสำหรับเวอร์ชันแรก ยังไม่มี API ที่ติดตั้งใช้งาน ต้องตรวจรูปแบบผลลัพธ์จริงของโมเดลและกำหนดขีดจำกัดก่อนพัฒนา อ้างอิง [ขอบเขตโปรเจกต์](project-scope.md) และ [คู่มือ frontend](frontend-guide.md)

Base path: `/api/v1` เวลาใช้รูปแบบ ISO 8601 พร้อม timezone เลขหน้าเริ่มที่ 1 รูปภาพมีหนึ่งหน้า

## สร้างงาน

`POST /api/v1/ocr/jobs` รับ `multipart/form-data` โดย field `file` เป็น JPG, PNG หรือ PDF หนึ่งไฟล์

ตัวอย่าง `202 Accepted`:

```json
{
  "jobId": "7a0d4c31-3281-4c37-895e-23a33be75946",
  "status": "queued",
  "createdAt": "2026-11-22T10:00:00Z",
  "expiresAt": "2026-11-22T11:00:00Z"
}
```

เวลาหมดอายุในตัวอย่างไม่ใช่ค่าที่กำหนดจริง Backend ตรวจเนื้อหาไฟล์ ขนาด จำนวนหน้า และ PDF ที่ติดรหัสผ่านก่อนรับงาน

## ตรวจสถานะงาน

`GET /api/v1/ocr/jobs/{jobId}` คืน `200 OK`:

```json
{
  "jobId": "7a0d4c31-3281-4c37-895e-23a33be75946",
  "status": "processing",
  "file": { "name": "document.pdf", "mediaType": "application/pdf", "pageCount": 10 },
  "progress": { "completedPages": 3, "failedPages": 1, "processedPages": 4, "totalPages": 10 },
  "createdAt": "2026-11-22T10:00:00Z",
  "expiresAt": "2026-11-22T11:00:00Z"
}
```

`processedPages` รวมหน้าสำเร็จและล้มเหลว Frontend ตรวจสถานะเป็นระยะ เช่น ทุก 1–2 วินาที และหยุดเมื่อถึงสถานะสิ้นสุด

| สถานะ | ความหมาย |
| --- | --- |
| `queued` | รับงานแล้ว รอประมวลผล |
| `processing` | กำลังประมวลผล |
| `completed` | ทุกหน้าสำเร็จ รวมถึงหน้าที่ไม่พบข้อความ |
| `partially_completed` | ประมวลผลครบ แต่บางหน้าล้มเหลว |
| `failed` | ไม่มีหน้าสำเร็จ หรือเกิดข้อผิดพลาดระดับงาน |

สามสถานะท้ายเป็นสถานะสิ้นสุด

## รายการหน้า

`GET /api/v1/ocr/jobs/{jobId}/pages` คืน `200 OK`:

```json
{
  "pages": [
    { "pageNumber": 1, "status": "completed", "hasText": true },
    { "pageNumber": 2, "status": "completed", "hasText": false },
    { "pageNumber": 3, "status": "failed", "hasText": null,
      "error": { "code": "PAGE_PROCESSING_FAILED", "message": "ไม่สามารถประมวลผลหน้านี้ได้" } },
    { "pageNumber": 4, "status": "pending", "hasText": null }
  ]
}
```

สถานะหน้าเป็น `pending`, `processing`, `completed` หรือ `failed` หน้าว่างที่อ่านสำเร็จใช้ `completed` และ `hasText: false`

## ผล OCR รายหน้า

`GET /api/v1/ocr/jobs/{jobId}/pages/{pageNumber}` คืน `200 OK` ตัวอย่างหน้าสำเร็จ:

```json
{
  "pageNumber": 1,
  "status": "completed",
  "hasText": true,
  "originalText": "หนังสือรับรอง",
  "image": { "width": 1200, "height": 1800 },
  "lines": [
    { "text": "หนังสือรับรอง", "confidence": 0.98,
      "boundingBox": { "x": 120, "y": 180, "width": 310, "height": 42 } }
  ]
}
```

`originalText` และ `lines` เป็นผล OCR เดิม หน้าที่ไม่พบข้อความใช้ `originalText: ""` และ `lines: []` หน้า `pending`, `processing` หรือ `failed` คืนเลขหน้าและสถานะ โดยหน้า `failed` มี `error` และยังไม่มีผล OCR

สัญญาที่เสนอใช้ `confidence` ช่วง 0–1 และ `boundingBox` เป็นพิกเซลจากมุมซ้ายบนเทียบกับภาพที่ส่งโดย endpoint ภาพ ต้องตรวจและแปลงผลจริงของโมเดลให้ตรงก่อนยืนยันสัญญานี้

## ภาพรายหน้า

`GET /api/v1/ocr/jobs/{jobId}/pages/{pageNumber}/image` คืน `200 OK` และข้อมูลภาพ เช่น `Content-Type: image/png` PDF ใช้ภาพที่แปลงจากหน้าที่เลือก ส่วนภาพต้นฉบับใช้หน้า 1 ขนาดและแนวภาพต้องตรงกับพิกัดผล OCR ที่ส่งออก

## ลบงาน

`DELETE /api/v1/ocr/jobs/{jobId}` ลบไฟล์ต้นฉบับ ภาพหน้า และผล OCR ชั่วคราว แล้วคืน `204 No Content` Frontend ส่งเมื่อเริ่มใหม่หรือจบงาน Backend ต้องลบงานหมดอายุด้วย เพราะปิดแท็บอาจส่งคำขอลบไม่สำเร็จ

## รูปแบบ JSON สำหรับดาวน์โหลด

Frontend สร้างไฟล์จากผลทุกหน้าที่สำเร็จและข้อความที่แก้ในหน่วยความจำ ข้อมูล OCR และพิกัดเป็นของข้อความเดิม ไม่ใช่ข้อความที่แก้:

```json
{
  "schemaVersion": "1.0",
  "sourceFile": "document.pdf",
  "jobStatus": "partially_completed",
  "pages": [
    {
      "pageNumber": 1,
      "status": "completed",
      "editedText": "ข้อความที่แก้ไขแล้ว",
      "ocr": {
        "originalText": "ข้อความเดิมจาก OCR",
        "image": { "width": 1200, "height": 1800 },
        "lines": [{ "text": "ข้อความเดิมจาก OCR", "confidence": 0.94,
          "boundingBox": { "x": 120, "y": 180, "width": 590, "height": 42 } }]
      }
    },
    { "pageNumber": 2, "status": "failed",
      "error": { "code": "PAGE_PROCESSING_FAILED", "message": "ไม่สามารถประมวลผลหน้านี้ได้" } }
  ]
}
```

## ข้อผิดพลาด

ข้อผิดพลาดระดับ HTTP ใช้รูปแบบเดียวกัน:

```json
{ "error": { "code": "UNSUPPORTED_FILE_TYPE", "message": "รองรับเฉพาะไฟล์ JPG, PNG และ PDF" } }
```

| HTTP | Code | ความหมาย |
| --- | --- | --- |
| 400 | `INVALID_FILE` | ไฟล์ไม่ถูกต้องหรือเปิดไม่ได้ |
| 400 | `PDF_PASSWORD_PROTECTED` | PDF มีรหัสผ่าน |
| 413 | `FILE_TOO_LARGE` | ไฟล์เกินขนาดที่รองรับ |
| 415 | `UNSUPPORTED_FILE_TYPE` | ชนิดไฟล์ไม่รองรับ |
| 422 | `PAGE_LIMIT_EXCEEDED` | จำนวนหน้าเกินที่รองรับ |
| 404 | `JOB_NOT_FOUND` | งานไม่พบ ถูกลบ หรือหมดอายุ |
| 404 | `PAGE_NOT_FOUND` | ไม่พบหน้าที่ระบุ |
| 500 | `INTERNAL_ERROR` | ข้อผิดพลาดภายใน |
