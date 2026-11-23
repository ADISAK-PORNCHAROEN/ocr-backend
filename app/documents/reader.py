from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

import pypdfium2 as pdfium
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import Settings
from app.core.errors import DocumentError

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PDF_MAGIC = b"%PDF-"
MAX_FILE_NAME_LENGTH = 180


@dataclass(frozen=True, slots=True)
class StagedDocument:
    job_id: UUID
    source_name: str
    media_type: str
    source_path: Path
    job_dir: Path
    page_count: int


class DocumentReader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def prepare(self, source: BinaryIO, filename: str | None, job_id: UUID) -> StagedDocument:
        root = self.settings.storage_dir.resolve()
        root.mkdir(parents=True, exist_ok=True)
        job_dir = root / f"job-{job_id}"
        job_dir.mkdir()
        (job_dir / ".owned-by-ocr-backend").write_text("temporary OCR job data\n", encoding="utf-8")
        source_path = job_dir / "source.bin"
        try:
            self._copy_bounded(source, source_path)
            with source_path.open("rb") as staged:
                signature = staged.read(8)
            source_name = self._safe_name(filename)

            if signature.startswith(PDF_MAGIC):
                media_type = "application/pdf"
                page_count = self._validate_pdf(source_path)
            elif signature.startswith(PNG_MAGIC) or signature.startswith(b"\xff\xd8\xff"):
                media_type = "image/png" if signature.startswith(PNG_MAGIC) else "image/jpeg"
                page_count = self._validate_image(source_path)
            else:
                raise DocumentError(
                    "UNSUPPORTED_FILE_TYPE",
                    "รองรับเฉพาะไฟล์ JPG, PNG และ PDF",
                    415,
                )
            self._validate_extension(filename, media_type)
            return StagedDocument(job_id, source_name, media_type, source_path, job_dir, page_count)
        except BaseException:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise

    def _copy_bounded(self, source: BinaryIO, destination: Path) -> None:
        total = 0
        try:
            source.seek(0)
            with destination.open("xb") as output:
                while chunk := source.read(64 * 1024):
                    total += len(chunk)
                    if total > self.settings.max_upload_bytes:
                        raise DocumentError(
                            "FILE_TOO_LARGE",
                            f"ไฟล์มีขนาดเกิน {self.settings.max_upload_bytes // (1024 * 1024)} MiB",
                            413,
                        )
                    output.write(chunk)
        except OSError as exc:
            raise DocumentError("FILE_UNREADABLE", "อ่านไฟล์ที่อัปโหลดไม่ได้", 422) from exc
        if total == 0:
            raise DocumentError("EMPTY_FILE", "ไฟล์ไม่มีข้อมูล", 422)

    def _validate_image(self, path: Path) -> int:
        try:
            with Image.open(path) as image:
                if image.format not in {"JPEG", "PNG"}:
                    raise DocumentError(
                        "UNSUPPORTED_FILE_TYPE", "รองรับเฉพาะไฟล์ JPG, PNG และ PDF", 415
                    )
                self._check_page_size(image.width, image.height)
                image.load()
                normalized = ImageOps.exif_transpose(image)
                self._check_page_size(normalized.width, normalized.height)
        except DocumentError:
            raise
        except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            raise DocumentError("CORRUPT_IMAGE", "ไฟล์ภาพเสียหรืออ่านไม่ได้", 422) from exc
        return 1

    def _validate_pdf(self, path: Path) -> int:
        try:
            reader = PdfReader(path, strict=True)
            if reader.is_encrypted:
                raise DocumentError(
                    "PDF_PASSWORD_PROTECTED", "PDF นี้มีรหัสผ่าน โปรดเลือกไฟล์ที่ไม่ป้องกัน", 422
                )
            page_count = len(reader.pages)
            if page_count < 1:
                raise DocumentError("EMPTY_DOCUMENT", "เอกสารไม่มีหน้า", 422)
            scale = self.settings.pdf_dpi / 72
            total_pixels = 0
            for page in reader.pages:
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)
                if (
                    not math.isfinite(width)
                    or not math.isfinite(height)
                    or width <= 0
                    or height <= 0
                ):
                    raise DocumentError("CORRUPT_PDF", "PDF มีขนาดหน้าที่ไม่ถูกต้อง", 422)
                pixel_width = math.ceil(width * scale)
                pixel_height = math.ceil(height * scale)
                total_pixels += self._check_page_size(pixel_width, pixel_height, check_total=False)
                if total_pixels > self.settings.max_total_pixels:
                    raise DocumentError(
                        "PDF_PIXEL_LIMIT_EXCEEDED", "จำนวนพิกเซลรวมของ PDF เกินขีดจำกัด", 422
                    )
            with pdfium.PdfDocument(path) as document:
                if len(document) != page_count:
                    raise DocumentError("CORRUPT_PDF", "จำนวนหน้า PDF ไม่สอดคล้องกัน", 422)
                for index in range(page_count):
                    page = document[index]
                    try:
                        page.get_size()
                    finally:
                        page.close()
            return page_count
        except DocumentError:
            raise
        except (OSError, ValueError, PdfReadError, pdfium.PdfiumError, IndexError) as exc:
            raise DocumentError("CORRUPT_PDF", "PDF เสียหรืออ่านไม่ได้", 422) from exc

    def _check_page_size(self, width: int, height: int, *, check_total: bool = True) -> int:
        pixels = width * height
        if width > self.settings.max_dimension or height > self.settings.max_dimension:
            raise DocumentError(
                "PAGE_DIMENSION_LIMIT_EXCEEDED", "ขนาดด้านใดด้านหนึ่งของหน้าเกินขีดจำกัด", 422
            )
        if pixels > self.settings.max_page_pixels:
            raise DocumentError("PAGE_PIXEL_LIMIT_EXCEEDED", "จำนวนพิกเซลของหน้าเกินขีดจำกัด", 422)
        if check_total and pixels > self.settings.max_total_pixels:
            raise DocumentError(
                "DOCUMENT_PIXEL_LIMIT_EXCEEDED", "จำนวนพิกเซลรวมของเอกสารเกินขีดจำกัด", 422
            )
        return pixels

    @staticmethod
    def _safe_name(filename: str | None) -> str:
        raw = (filename or "document").replace("\\", "/").split("/")[-1]
        safe = "".join(character for character in raw if character.isprintable()).strip(" .")
        return (safe or "document")[:MAX_FILE_NAME_LENGTH]

    @staticmethod
    def _validate_extension(filename: str | None, media_type: str) -> None:
        raw = (filename or "").replace("\\", "/").split("/")[-1]
        expected_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
        }
        if expected_types.get(Path(raw).suffix.lower()) != media_type:
            raise DocumentError(
                "FILE_EXTENSION_MISMATCH",
                "นามสกุลไฟล์ไม่ตรงกับชนิดของเนื้อหา",
                415,
            )
