# Graphify ในโปรเจกต์

ติดตั้งชุดคำสั่ง Graphify ระดับโปรเจกต์ที่ `.agents/skills/graphify/` จาก Foundation และติดตั้ง CLI `graphifyy==0.9.80` แยกใน `.graphify-venv/` ตามคำขอ โดยไม่เปลี่ยนเครื่องมือระดับผู้ใช้ โฟลเดอร์ environment และ `graphify-out/` ไม่เข้า Git

ติดตั้ง environment นี้ใน Windows อีกครั้งด้วย:

```powershell
uv venv .graphify-venv
uv pip install --python .graphify-venv\Scripts\python.exe 'graphifyy==0.9.80'
.\.graphify-venv\Scripts\graphify.exe --help
```

## Git post-commit

ใน checkout ปัจจุบันมี `.git/hooks/post-commit` ซึ่งเรียก `.graphify-venv/Scripts/graphify.exe update <project-root>` หลัง commit โดยใช้ Git hooks ตามปกติ หากไม่พบ executable จะแจ้งเตือนและไม่ขัดขวาง commit Hook เป็น local Git metadata ไม่ถูกส่งไปกับ Git clone และไม่ได้ตั้ง `core.hooksPath` หรือ `post-checkout`

`graphify update` อัปเดตส่วนที่ดึงจากโค้ดโดยไม่ใช้ LLM ไม่ได้แทนการตรวจ semantic ของเอกสาร ในวันที่ตั้งค่า repository ยังไม่มี application code จึงไม่ควรใช้ graph เป็นหลักฐานว่า feature OCR ทำงานอยู่ `.graphifyignore` ไม่รวมชุด project skills และประวัติคำสั่งเก่า เพื่อลดข้อมูลที่ไม่ใช่ application source

เมื่อย้าย checkout ให้ติดตั้ง CLI แยกและกำหนด hook ตามคำขอที่ชัดเจนของเจ้าของเครื่องผ่าน `.agents/skills/hook-management/SKILL.md` โดยตรวจ hook เดิมก่อนเสมอ หากต้องการปิด hook ที่ตั้งในการติดตั้งนี้ ให้ตรวจไฟล์ `.git/hooks/post-commit` แล้วนำออกเมื่อยืนยันว่าเป็น hook นี้
