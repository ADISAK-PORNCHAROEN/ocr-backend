from __future__ import annotations

from pathlib import Path

from app.ocr import openthai
from PIL import Image


class FailingEngine:
    def read(self, image: Image.Image) -> dict[str, object]:
        raise RuntimeError("model inference failed")


def test_failed_model_inference_still_reports_its_duration(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (80, 50), "white").save(image_path)
    monkeypatch.setattr(openthai, "_engine", FailingEngine())

    artifact = openthai._process_page(str(image_path), "image/png", 1, 150)

    assert artifact.result is None
    assert artifact.error_code == "PAGE_PROCESSING_FAILED"
    assert artifact.ocr_duration_ms is not None
    assert artifact.ocr_duration_ms >= 0
