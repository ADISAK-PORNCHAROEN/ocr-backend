import os
from pathlib import Path

import pytest
from app.core.config import Settings
from app.ocr.openthai import OpenThaiProcessor
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfWriter

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(
    os.getenv("OCR_RUN_MODEL_SMOKE") != "1",
    reason="set OCR_RUN_MODEL_SMOKE=1 to download and run the pinned OCR model",
)
async def test_real_model_reads_synthetic_thai_and_english_on_cpu(tmp_path: Path) -> None:
    font_path = Path(os.getenv("OCR_SMOKE_FONT", r"C:\Windows\Fonts\tahoma.ttf"))
    if not font_path.is_file():
        pytest.skip("set OCR_SMOKE_FONT to a Thai-capable TrueType font")

    sample = tmp_path / "synthetic.png"
    image = Image.new("RGB", (1800, 320), "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 90), "สวัสดีครับ OCR 123", font=ImageFont.truetype(font_path, 72), fill="black")
    image.save(sample)

    processor = OpenThaiProcessor(Settings(storage_dir=tmp_path / "jobs"))
    try:
        result = await processor.process_page(sample, "image/png", 1)
    finally:
        await processor.close()

    assert result.result is not None
    assert "สวัสดี" in result.result.original_text
    assert result.ocr_duration_ms is not None and result.ocr_duration_ms > 0
    assert result.result.lines
    assert result.image_png.startswith(b"\x89PNG\r\n\x1a\n")
    assert all(0.0 <= line.confidence <= 1.0 for line in result.result.lines)
    assert all(line.box.x2 <= 1800 and line.box.y2 <= 320 for line in result.result.lines)


@pytest.mark.skipif(
    os.getenv("OCR_RUN_MODEL_SMOKE") != "1",
    reason="set OCR_RUN_MODEL_SMOKE=1 to download and run the pinned OCR model",
)
async def test_real_model_renders_each_pdf_page_on_cpu(tmp_path: Path) -> None:
    pdf_path = tmp_path / "synthetic.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    with pdf_path.open("wb") as output:
        writer.write(output)

    processor = OpenThaiProcessor(Settings(storage_dir=tmp_path / "jobs"))
    try:
        first = await processor.process_page(pdf_path, "application/pdf", 1)
        second = await processor.process_page(pdf_path, "application/pdf", 2)
    finally:
        await processor.close()

    assert first.result is not None and second.result is not None
    assert first.ocr_duration_ms is not None and first.ocr_duration_ms > 0
    assert second.ocr_duration_ms is not None and second.ocr_duration_ms > 0
    assert first.result.original_text == second.result.original_text == ""
    assert first.result.image_size.width == second.result.image_size.width
    assert first.result.image_size.height == second.result.image_size.height
