from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import statistics
import tempfile
from io import BytesIO
from pathlib import Path
from time import perf_counter

from app.core.config import Settings
from app.ocr.openthai import OpenThaiProcessor
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.utils import ImageReader  # type: ignore[import-untyped]
from reportlab.pdfgen.canvas import Canvas  # type: ignore[import-untyped]

IMAGE_SIZE = (1800, 320)
SAMPLE_TEXT = "สวัสดีครับ OCR 123"
EXPECTED_TEXT = "สวัสดี"
PDF_DPI = 150


def create_sample_pdf(path: Path, page_count: int, font_path: Path) -> None:
    image = Image.new("RGB", IMAGE_SIZE, "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 90), SAMPLE_TEXT, font=ImageFont.truetype(font_path, 72), fill="black")
    png = BytesIO()
    image.save(png, format="PNG")
    png.seek(0)

    page_width = image.width * 72 / PDF_DPI
    page_height = image.height * 72 / PDF_DPI
    pdf = Canvas(str(path), pagesize=(page_width, page_height), pageCompression=1)
    page_image = ImageReader(png)
    for _ in range(page_count):
        pdf.drawImage(page_image, 0, 0, width=page_width, height=page_height)
        pdf.showPage()
        png.seek(0)
    pdf.save()


async def benchmark(warmup_pages: int, sample_pages: int, font_path: Path) -> dict[str, object]:
    page_count = warmup_pages + sample_pages
    with tempfile.TemporaryDirectory(prefix="ocr-timing-") as temp_dir:
        root = Path(temp_dir)
        pdf_path = root / "synthetic-thai.pdf"
        create_sample_pdf(pdf_path, page_count, font_path)

        settings = Settings(storage_dir=root / "jobs")
        processor = OpenThaiProcessor(settings)
        first_call_wall_ms: float | None = None
        sample_durations_ms: list[float] = []
        successful_pages = 0
        try:
            for page_number in range(1, page_count + 1):
                started = perf_counter()
                artifact = await processor.process_page(pdf_path, "application/pdf", page_number)
                wall_ms = (perf_counter() - started) * 1000
                if page_number == 1:
                    first_call_wall_ms = wall_ms
                if artifact.result is None or artifact.ocr_duration_ms is None:
                    raise RuntimeError(f"OCR failed on page {page_number}: {artifact.error_code}")
                if EXPECTED_TEXT not in artifact.result.original_text:
                    raise RuntimeError(
                        f"Expected Thai text was not recognized on page {page_number}: "
                        f"{artifact.result.original_text!r}"
                    )
                successful_pages += 1
                if page_number > warmup_pages:
                    sample_durations_ms.append(artifact.ocr_duration_ms)
        finally:
            await processor.close()

    return {
        "cpu": platform.processor(),
        "logical_processors": os.cpu_count(),
        "model_id": settings.model_id,
        "model_revision": settings.model_revision,
        "input": (
            f"{page_count}-page PDF; repeated {IMAGE_SIZE[0]}x{IMAGE_SIZE[1]} synthetic "
            f"Tahoma image at {PDF_DPI} DPI with a Thai greeting and 'OCR 123'"
        ),
        "warmup_pages": warmup_pages,
        "sample_pages": len(sample_durations_ms),
        "successful_pages": successful_pages,
        "first_call_wall_ms_including_worker_initialization_render_and_ipc": round(
            first_call_wall_ms or 0, 2
        ),
        "inference_median_ms": round(statistics.median(sample_durations_ms), 2),
        "inference_min_ms": round(min(sample_durations_ms), 2),
        "inference_max_ms": round(max(sample_durations_ms), 2),
        "inference_sample_ms": [round(value, 2) for value in sample_durations_ms],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure per-page OpenThai inference time on synthetic Thai PDF pages."
    )
    parser.add_argument("--warmup-pages", type=int, default=1)
    parser.add_argument("--sample-pages", type=int, default=9)
    parser.add_argument(
        "--font",
        type=Path,
        default=Path(os.getenv("OCR_SMOKE_FONT", r"C:\Windows\Fonts\tahoma.ttf")),
    )
    args = parser.parse_args()
    if args.warmup_pages < 1 or args.sample_pages < 1:
        parser.error("warmup and sample page counts must both be positive")
    if not args.font.is_file():
        parser.error(f"Thai-capable font not found: {args.font}")
    result = asyncio.run(benchmark(args.warmup_pages, args.sample_pages, args.font))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
