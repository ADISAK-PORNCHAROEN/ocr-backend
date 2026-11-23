from __future__ import annotations

import asyncio
import importlib
import io
import logging
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Protocol, cast

import pypdfium2 as pdfium
from huggingface_hub import snapshot_download
from PIL import Image, ImageOps

from app.core.config import Settings
from app.entities.page import BoundingBox, ImageSize, OcrLine, PageCompleted

_engine: OpenThaiEngine | None = None


@dataclass(frozen=True, slots=True)
class PageArtifact:
    image_png: bytes
    result: PageCompleted | None
    error_code: str | None = None
    ocr_duration_ms: float | None = None


class OcrProcessor(Protocol):
    async def process_page(
        self, source_path: Path, media_type: str, page_number: int
    ) -> PageArtifact: ...

    async def close(self) -> None: ...


class OpenThaiEngine(Protocol):
    def read(self, image: Image.Image) -> dict[str, Any]: ...


class OpenThaiProcessor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._executor = ProcessPoolExecutor(
            max_workers=1,
            initializer=_initialize_worker,
            initargs=(
                settings.model_id,
                settings.model_revision,
                settings.model_cache_dir,
                settings.model_threads,
            ),
        )
        self._closed = False

    async def process_page(
        self, source_path: Path, media_type: str, page_number: int
    ) -> PageArtifact:
        if self._closed:
            raise RuntimeError("OCR processor is closed")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            _process_page,
            str(source_path),
            media_type,
            page_number,
            self.settings.pdf_dpi,
        )

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await asyncio.to_thread(self._executor.shutdown, wait=True, cancel_futures=True)


def _initialize_worker(model_id: str, revision: str, cache_dir: Path | None, threads: int) -> None:
    global _engine
    model_path = snapshot_download(
        repo_id=model_id,
        revision=revision,
        cache_dir=str(cache_dir) if cache_dir else None,
        allow_patterns=[
            "config.json",
            "det.onnx",
            "det.yml",
            "rec.onnx",
            "rec2.onnx",
            "rec_dict.txt",
            "runtime/*.py",
        ],
    )
    if model_path not in sys.path:
        sys.path.insert(0, model_path)
    runtime = importlib.import_module("runtime.line_engine")
    _engine = cast(OpenThaiEngine, runtime.LineOCR(model_path, threads=threads))


def _process_page(
    source_path: str, media_type: str, page_number: int, pdf_dpi: int
) -> PageArtifact:
    image = _render_page(Path(source_path), media_type, page_number, pdf_dpi)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False)
    image_png = buffer.getvalue()
    if _engine is None:
        raise RuntimeError("OpenThai OCR runtime was not initialized")
    ocr_duration_ms: float | None = None
    try:
        inference_started_at = perf_counter_ns()
        try:
            raw = _engine.read(image)
        finally:
            ocr_duration_ms = (perf_counter_ns() - inference_started_at) / 1_000_000
        raw_lines = raw.get("lines", [])
        lines = tuple(
            OcrLine(
                text=str(line.get("text", "")),
                confidence=float(line.get("confidence", 0.0)),
                box=_axis_aligned_box(line["box"], image.width, image.height),
            )
            for line in raw_lines
            if len(line.get("box", ())) >= 4
        )
        result = PageCompleted(
            original_text=str(raw.get("text", "")),
            lines=lines,
            image_size=ImageSize(image.width, image.height),
        )
        return PageArtifact(
            image_png=image_png,
            result=result,
            ocr_duration_ms=ocr_duration_ms,
        )
    except Exception:
        logging.getLogger(__name__).exception("OpenThai inference failed for a rendered page")
        return PageArtifact(
            image_png=image_png,
            result=None,
            error_code="PAGE_PROCESSING_FAILED",
            ocr_duration_ms=ocr_duration_ms,
        )


def _axis_aligned_box(points: list[list[float]], width: int, height: int) -> BoundingBox:
    coordinates = [(float(point[0]), float(point[1])) for point in points]
    if len(coordinates) < 4 or any(
        not math.isfinite(value) for point in coordinates for value in point
    ):
        raise ValueError("OpenThai OCR returned an invalid line polygon")
    xs = [point[0] for point in coordinates]
    ys = [point[1] for point in coordinates]
    return BoundingBox(
        min(max(min(xs), 0), width),
        min(max(min(ys), 0), height),
        min(max(max(xs), 0), width),
        min(max(max(ys), 0), height),
    )


def _render_page(source_path: Path, media_type: str, page_number: int, pdf_dpi: int) -> Image.Image:
    if media_type == "application/pdf":
        with pdfium.PdfDocument(source_path) as document:
            page = document[page_number - 1]
            try:
                bitmap = page.render(scale=pdf_dpi / 72)
                try:
                    rendered = bitmap.to_pil()
                    image = ImageOps.exif_transpose(rendered).convert("RGB")
                finally:
                    bitmap.close()
                return image
            finally:
                page.close()
    with Image.open(source_path) as original:
        if page_number != 1:
            raise ValueError("Image documents contain exactly one page")
        oriented = ImageOps.exif_transpose(original)
        if "A" in oriented.getbands():
            rgba = oriented.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.getchannel("A"))
            return background
        return oriented.convert("RGB")
