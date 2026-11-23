# Security model

## ขอบเขตและหลักฐาน

สถานะ: backend PR #13 merged แล้ว; ผู้ใช้ขอให้ลบ GitHub Actions workflow และ deferred frontend work ไว้ภายหลัง ตรวจ local checks และ manual review แล้ว ทบทวน 2026-11-23

แหล่งอ้างอิงคือ [ขอบเขตโปรเจกต์](project-scope.md), [ข้อกำหนด](spec.md), [สถาปัตยกรรม](architecture.md), [โครงสร้างโค้ด](folder-structure.md), [คู่มือ frontend](frontend-guide.md) และ [สัญญา API](frontend-api.md) ตารางด้านล่างแยก controls ที่ implement และทดสอบแล้วออกจากช่องว่างที่ยังเหลือ

ระบบเป้าหมายเป็น portfolio บนเครื่องเดียว เริ่มสาธิตผ่าน loopback ไม่มีบัญชีและไม่เปิดใช้งานสาธารณะ การเผยแพร่หรือเพิ่มผู้ใช้หลายคนเปลี่ยนสมมติฐานนี้และต้องทบทวนแบบจำลองก่อน

## ข้อมูลและขอบเขตความเชื่อถือ

| ข้อมูลหรือผู้เกี่ยวข้อง | เจ้าของ | ขอบเขต |
| --- | --- | --- |
| เอกสารต้นฉบับ ภาพหน้า และผล OCR เดิม | API process จัดการสถานะและ artifacts ชั่วคราว | In-memory state, UUID folders, TTL, retained-job cap; no persistent database |
| ข้อความที่แก้และไฟล์ดาวน์โหลด | Frontend เก็บในหน่วยความจำและสร้างดาวน์โหลด | ไม่ส่งข้อความแก้กลับไปเก็บถาวรตามขอบเขตปัจจุบัน |
| ไฟล์ JPG, PNG และ PDF ที่ส่งเข้า | ข้อมูลภายนอกที่ต้องตรวจ | ผ่าน HTTP ไปยังตัวอ่านไฟล์และ native OCR runtime |
| OCR worker | รับข้อมูลหน้าและส่งผลกลับ | One ProcessPool worker loads the pinned Python runtime; API process alone updates job state |

เส้นทางตามแผน: `Frontend → HTTP API → บริการงาน → ตัวอ่านเอกสารและ OCR worker → ผลรายหน้า` API จัดการข้อมูลชั่วคราวและการลบ Frontend อ่านภาพและผลเพื่อแสดง แก้ และดาวน์โหลด

ไม่มีระบบตัวตนหรือการแยก tenant และไม่มี authorization สำหรับ job ID; deployment แบบ loopback เป็นเงื่อนไขที่ต้องคงไว้ ไม่ใช่หลักฐานว่ารองรับผู้ใช้หลายคน

## Invariants ที่ตกลงและวิธีพิสูจน์

ตารางนี้สรุป enforcement และหลักฐานปัจจุบัน ไม่ใช่การรับรองความปลอดภัยทั้งหมด

| ข้อกำหนด | เจ้าของตามแผนและหลักฐาน | กรณีทดสอบที่ต้องพิสูจน์ |
| --- | --- | --- |
| ตรวจ extension ให้ตรงกับ magic bytes และเนื้อหาที่ decode ได้ ขนาดหน้าและพิกเซลรวม; ปฏิเสธ PDF ติดรหัสผ่านหรือเปิดไม่ได้ | `app/documents/reader.py`; unit/API integration tests | Tested extension mismatch, unsupported signature, corrupt/empty documents, encrypted PDF, upload-byte/page-dimension/per-page-pixel/total-pixel bounds; no fixed page-count cap |
| จำกัดขนาดไฟล์ มิติ/พิกเซลของหน้า พิกเซลรวม คิว และจำนวนงานชั่วคราว | settings, document reader, job service and capabilities endpoint | Tests cover upload-byte, page-dimension, per-page/total-pixel bounds, queue full and retained-job cap; page count has no fixed ceiling |
| API process เป็นผู้เขียนสถานะและ artifacts เพียงรายเดียว | job service and injected-processor integration tests | HTTP tests cover queued, processing, blank success, partial and all-failed states |
| ลบหรือหมดอายุแล้วเข้าถึงงานไม่ได้ทันที ผล worker ที่มาช้าสร้างงานกลับไม่ได้ | job service and repository lifecycle | Tests cover delete/expiry during inference, 404 access, deferred cleanup and startup cleanup |
| ลบต้นฉบับ ภาพหน้า และผล OCR ไม่มีประวัติถาวร | delete endpoint, TTL loop, retained cap, shutdown/startup cleanup | Tests cover delete, automatic expiry, shutdown, failed staging cleanup and marker-owned stale directory cleanup |
| ข้อความแก้แยกจากผล OCR เดิม | Frontend session reducer และ export serializer แยกข้อมูลเดิมกับ draft | Vitest และ Playwright ครอบคลุมสลับหน้า ค่าว่าง คืนค่า และ JSON export |

## เส้นทางการใช้ผิดและข้อจำกัด

| อินพุตและเส้นทาง | ผลกระทบที่ต้องตรวจ | สิ่งที่ยังไม่พิสูจน์ |
| --- | --- | --- |
| ไฟล์ภายนอก → pypdf/Pillow/PDFium → native OCR runtime | parser/runtime flaws or resource exhaustion | Upload-byte, page-dimension, per-page/total-pixel limits and dependency lock exist; no fuzzing, inference timeout or native dependency audit; many very small PDF pages can still increase per-page memory/CPU work |
| Hugging Face pinned runtime files → worker process | supply-chain compromise or mutable model tag | `v2.1.4` is pinned and loaded only in the worker; artifact signature/hash verification is not implemented |
| delete/expiry → late worker result → repository | deleted data becomes accessible again | Race tests cover worker return after delete and expiry |
| `jobId` และเลขหน้าจาก HTTP → อ่านภาพ ผล หรือลบงาน | อ่านหรือลบงานโดยไม่มีเจ้าของที่ได้รับอนุญาต | UUID4 และ repository lookup ป้องกัน path traversal; ไม่มี authentication/authorization และยังอนุญาตเฉพาะ loopback |
| เนื้อหา OCR → frontend และข้อความ error | เนื้อหา OCR ถูกตีความเป็น markup หรือ error เปิดเผย path ภายใน | Frontend ใช้ React text/textarea; BFF จำกัดเส้นทางและส่งต่อข้อความ error จาก backend ที่กำหนดไว้ ไม่มีการใช้ raw HTML |

รายการนี้เป็นสถานการณ์สำหรับทบทวน ไม่ใช่ช่องโหว่ที่ยืนยันแล้ว Backend ไม่เปิด CORS หรือ authentication และให้ใช้เฉพาะ loopback. มีขีดจำกัด upload-byte/page-dimension/per-page-pixel/total-pixel/queue/retention แต่ไม่มี request หรือ inference timeout; BFF ใช้ route/method allow-list, mutation origin allow-list และ timeout 60 วินาที ไม่มีการตรวจ hash/signature ของ model artifact และ revision `v2.1.4` เป็น tag ที่เปลี่ยนปลายทางได้

## การทบทวนและหลักฐาน

### Incremental review: remove page-count ceiling and expose OCR timing (2026-11-23)

Reviewed the backend diff through `app/documents/reader.py`, `app/core/config.py`, `app/ocr/openthai.py`, the job/page entities and service, and the API schemas/controller. Manual checks confirmed that upload bytes, page dimensions, per-page pixels, cumulative PDF pixels, queue size and retained jobs remain enforced; unsupported, corrupt and empty files remain rejected. The timer wraps only `OpenThaiEngine.read`, is propagated on completed pages and inference failures, and remains null before an artifact is returned. The review considered [OWASP Top 10:2025 A06](https://top10.owasp.org/2025/A06_2025-Insecure_Design/), [ASVS v5.0.0 requirement 13.1.3](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x22-V13-Configuration.md) (document resource management), and [WSTG v4.2 WSTG-BUSL-08](https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/10-Business_Logic_Testing/08-Test_Upload_of_Unexpected_File_Types.html) (unexpected file types).

Removing a fixed page-count ceiling also removes one bound on per-page state and CPU overhead. The upload-byte and cumulative pixel budgets limit ordinary documents, but very small PDF pages can consume little of the pixel budget while still creating per-page state and inference work. This path was not stress-tested with adversarial tiny-page PDFs; the project remains a single-user loopback demo. No confirmed vulnerability was found in the reviewed diff. No automated scanner, fuzzing, memory stress test or native dependency audit was run.

การเปลี่ยนโค้ด dependency executable configuration หรือ CI ใช้ workflow ของ `.agents/skills/security-review/SKILL.md` เมื่อ setup ติดตั้ง package นั้นครบแล้ว ตรวจ diff และ boundary ที่กระทบ การสแกนทั้ง repository เป็นงานแยกจากการตั้งค่า workflow

บันทึกขอบเขต revision หรือ patch แหล่งโค้ด เส้นทางอินพุตสู่ผลกระทบ เงื่อนไข และผลทดสอบในรายงานงานนั้น แยก candidate, confirmed, fixed และ verified ใช้ข้อมูลและพื้นที่ชั่วคราวที่แยกจากเอกสารจริง ดู [การทดสอบ](TESTING.md) และ [นโยบายที่ยังต้องกำหนด](../SECURITY.md)

การทบทวนรอบนี้เป็น manual review ของ backend upload/job/OCR/temporary-storage boundaries และ frontend BFF/client/render/export flows. ไม่พบ confirmed vulnerability ในขอบเขตนี้ ไม่มีการรัน automated security scanner, fuzzing หรือ native dependency audit. ตรวจแนวทางที่เลือกจาก [OWASP ASVS 5.0.0 V5.1.1, V5.2.1, V5.2.2, V5.2.6, V5.3.2](https://github.com/OWASP/ASVS/blob/master/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) และ [OWASP WSTG-BUSL-08](https://wstg.owasp.org/latest/14-Business_Logic/08-Upload_of_Unexpected_File_Types/). นี่ไม่ใช่การอ้างว่าโปรเจกต์ผ่าน ASVS.
