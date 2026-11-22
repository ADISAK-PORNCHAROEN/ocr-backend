# การทดสอบ OCR Playground

## สถานะและแหล่งอ้างอิง

ทบทวน 2026-11-22: repository มีเอกสารวางแผน ยังไม่มี source, `pyproject.toml`, `uv.lock`, `tests/`, test runner, coverage configuration หรือ CI ที่รันได้ จึงยังไม่มี test baseline หรือ mandatory native command ที่ตรวจจาก configuration ได้

แนวทางที่ตกลงอยู่ใน [ข้อกำหนด ส่วน Testing Decisions](spec.md#testing-decisions), [สถาปัตยกรรม](architecture.md) และ [โครงสร้างที่เสนอ](folder-structure.md) ตัวอย่าง `uv sync`, `uv run uvicorn app.main:app --reload` และ `uv run pytest` ในโครงสร้างเป็นคำสั่งสำหรับหลังพัฒนาและติดตั้ง dependencies ไม่ใช่คำสั่งที่ยืนยันว่ารันได้ตอนนี้

## เลือกการทดสอบตามพฤติกรรม

| ขอบเขตที่เปลี่ยน | ชั้นทดสอบและผลที่ต้องตรวจ | หลักฐานความต้องการ |
| --- | --- | --- |
| HTTP และการรับไฟล์ | Integration ผ่าน HTTP ใช้ OCR adapter จำลองเพื่อคุมผล ตรวจ JPG, PNG, PDF หลายหน้า ไฟล์เสีย ชนิดไม่ตรง PDF มีรหัสผ่าน และขอบค่าขีดจำกัดเมื่อกำหนดแล้ว | [API ฉบับร่าง](frontend-api.md), [PRODUCT.md](../PRODUCT.md) |
| สถานะและการประมวลผลหน้า | Integration ตรวจรอ ประมวลผล สำเร็จทั้งหมด บางส่วน และล้มเหลว หน้าว่างสำเร็จต้องต่างจากหน้าล้มเหลว ตรวจจำนวนหน้ากับสถานะจริง | [API ฉบับร่าง](frontend-api.md), [สถาปัตยกรรม](architecture.md) |
| วงจรชีวิตข้อมูล | Integration ตรวจลบ หมดอายุ worker คืนผลหลังลบ ไฟล์เลิกใช้แล้วจึงลบ และการล้างไฟล์ตกค้างตอนเริ่มระบบ | [Security model](SECURITY-MODEL.md) |
| กฎและการแปลงผล | Unit สำหรับกฎที่ซับซ้อน การรวมสถานะ และ mapping ผล OCR หลังทราบรูปแบบจริง | [โครงสร้างที่เสนอ](folder-structure.md) |
| โมเดลและ PDF จริง | Smoke แยกจาก tests จำลอง ใช้ภาพและ PDF ตัวอย่างไทยและอังกฤษบน CPU ตรวจข้อความ ลำดับการอ่าน พิกัด และภาพที่ endpoint ส่ง | [ข้อกำหนด](spec.md), [สถาปัตยกรรม](architecture.md) |
| Frontend ในโปรเจกต์แยก | ตรวจ flow อัปโหลด ติดตามผล สลับหน้า แก้ คัดลอก ยืนยันคืนค่า ดาวน์โหลดทุกหน้าสำเร็จ เตือนผลบางส่วน และเริ่มใหม่ | [คู่มือ frontend](frontend-guide.md), [DESIGN.md](../DESIGN.md) |
| เอกสารและ workflow | อ่านเทียบแหล่งอ้างอิง ตรวจลิงก์ สถานะข้อเสนอ และแยกสิ่งที่ตกลงจากสิ่งที่ยังไม่พัฒนา | เอกสาร canonical ที่เปลี่ยน |

Tests จำลองพิสูจน์ HTTP และ lifecycle ภายใต้ผลที่ควบคุมได้ ไม่พิสูจน์คุณภาพ ความเข้ากันได้ หรือ performance ของโมเดลจริง API ยังเป็นฉบับร่าง ต้องยืนยันช่วงความมั่นใจ พิกัด และ error เมื่อคิวเต็มก่อนกำหนด assertions เหล่านั้นเป็นสัญญาถาวร

งาน implementation ใช้ `.agents/skills/test-engineering/SKILL.md` เมื่อ setup ติดตั้ง package ครบแล้ว และใช้คำสั่งจาก manifest และ CI ที่สร้างจริง เพิ่มการตรวจตามพฤติกรรมที่เปลี่ยนโดยไม่ถือว่าการมีไฟล์ skill เป็นผลทดสอบแอป

## ข้อมูลและการแยกสภาพแวดล้อม

Fixtures ต้องแยกจากเอกสารส่วนตัวและข้อมูลใช้งานจริง ใช้พื้นที่ชั่วคราวที่ test เป็นเจ้าของ และเก็บกวาดต้นฉบับ ภาพ ผล OCR และ process ของรอบทดสอบนั้น ตรวจ loopback address, port, temp root และเจ้าของ process ก่อนเริ่ม integration หรือ smoke run

ทดสอบการหมดอายุและผล worker มาช้าด้วยเงื่อนไขที่ควบคุมได้ หลีกเลี่ยงการอาศัยจังหวะเครื่องเพียงอย่างเดียว ไม่ลบพื้นที่ของผู้ใช้เพื่อพิสูจน์ cleanup

## Coverage และ performance

ยังไม่มี coverage tool, denominator, exclusion หรือ threshold ที่ตกลง เจ้าของโปรเจกต์กำหนดเมื่อมี production source และ baseline โดยต้องไม่ซ่อน logic สำคัญที่ยังไม่ถูกทดสอบ การครอบคลุมข้อกำหนดกับ code coverage เป็นคนละหลักฐาน

ยังไม่มีผลวัดหรือเกณฑ์ความเร็วและคุณภาพ OCR การวัดในอนาคตแยก cold start กับ warm run และรวมอัปโหลด แปลง PDF OCR และดึงผล บันทึก CPU, RAM, รุ่นโมเดล, runtime, worker, inference thread และชุดเอกสารตามสถาปัตยกรรม ตรวจความถูกต้องของผลร่วมด้วยก่อนใช้ตัวเลขตัดสินใจ

## บันทึกผลและช่องว่าง

แต่ละรอบบันทึกคำสั่งจริง revision หรือ dirty scope จำนวนและผลทดสอบ เวลา ตำแหน่ง artifact ถ้ามี ข้อจำกัด และการเก็บกวาดทรัพยากร แยก harness failure จาก application failure เมื่อมี frontend ให้ระบุโปรเจกต์ revision และสถานะที่ตรวจด้วย

การตั้งค่าเอกสารครั้งนี้ไม่รันทดสอบแอป เพราะยังไม่มี implementation และ dependencies ไม่สร้างตัวเลข coverage ภาพ visual baseline หรือรายงาน smoke ที่ยังไม่ได้รัน เมื่อเริ่มโค้ด ให้เพิ่ม manifest, lockfile และ runner ที่เลือกจริง แล้วปรับหน้านี้ให้ชี้คำสั่งและรายงานของโปรเจกต์
