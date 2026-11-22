from __future__ import annotations

import asyncio
import threading
import time
from io import BytesIO
from pathlib import Path

from app.core.config import Settings
from app.entities.page import BoundingBox, ImageSize, OcrLine, PageCompleted
from app.main import create_app
from app.ocr.openthai import PageArtifact
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 50), "white").save(output, format="PNG")
    return output.getvalue()


def jpeg_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 50), "white").save(output, format="JPEG")
    return output.getvalue()


def pdf_bytes(page_count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class FakeProcessor:
    def __init__(self, release: threading.Event | None = None) -> None:
        self.release = release
        self.closed = False

    async def process_page(
        self, source_path: Path, media_type: str, page_number: int
    ) -> PageArtifact:
        if self.release:
            await asyncio.to_thread(self.release.wait)
        image = png_bytes()
        result = PageCompleted(
            original_text="สวัสดี OCR",
            lines=(OcrLine("สวัสดี OCR", 0.98, BoundingBox(2, 4, 70, 20)),),
            image_size=ImageSize(80, 50),
        )
        return PageArtifact(image, result)

    async def close(self) -> None:
        self.closed = True


def make_client(tmp_path, processor: FakeProcessor | None = None, **overrides) -> TestClient:
    settings = Settings(storage_dir=tmp_path, **overrides)
    return TestClient(create_app(settings, processor or FakeProcessor()))


def upload_image(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/ocr/jobs",
        files={"file": ("scan.png", png_bytes(), "text/plain")},
    )
    assert response.status_code == 202
    assert response.headers["location"].endswith(response.json()["id"])
    return response.json()


def wait_for_status(client: TestClient, job_id: str, statuses: set[str]) -> dict:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        result = client.get(f"/api/v1/ocr/jobs/{job_id}")
        assert result.status_code == 200
        if result.json()["status"] in statuses:
            return result.json()
        time.sleep(0.02)
    raise AssertionError(f"Job did not reach one of the statuses: {statuses}")


def test_upload_status_pages_page_image_and_delete(tmp_path) -> None:
    processor = FakeProcessor()
    with make_client(tmp_path, processor) as client:
        job = upload_image(client)
        completed = wait_for_status(client, job["id"], {"completed"})

        assert completed["progress"] == {
            "total_pages": 1,
            "completed_pages": 1,
            "failed_pages": 0,
            "processing_pages": 0,
            "processed_pages": 1,
        }
        pages = client.get(f"/api/v1/ocr/jobs/{job['id']}/pages").json()["pages"]
        assert pages[0]["original_text"] == "สวัสดี OCR"
        assert pages[0]["lines"][0]["confidence"] == 0.98
        assert pages[0]["image_url"].endswith("/pages/1/image")
        image = client.get(pages[0]["image_url"])
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/png"
        assert image.headers["cache-control"] == "no-store"
        assert Image.open(BytesIO(image.content)).size == (80, 50)
        assert client.delete(f"/api/v1/ocr/jobs/{job['id']}").status_code == 204
        assert client.get(f"/api/v1/ocr/jobs/{job['id']}").status_code == 404
        assert list(tmp_path.iterdir()) == []
    assert processor.closed


def test_blank_page_is_successful_not_failed(tmp_path) -> None:
    class BlankProcessor(FakeProcessor):
        async def process_page(
            self, source_path: Path, media_type: str, page_number: int
        ) -> PageArtifact:
            return PageArtifact(png_bytes(), PageCompleted("", (), ImageSize(80, 50)))

    with make_client(tmp_path, BlankProcessor()) as client:
        job = upload_image(client)
        result = wait_for_status(client, job["id"], {"completed"})
        page = client.get(f"/api/v1/ocr/jobs/{job['id']}/pages/1").json()

    assert result["progress"]["completed_pages"] == 1
    assert result["progress"]["failed_pages"] == 0
    assert page["has_text"] is False
    assert page["original_text"] == ""


def test_invalid_page_numbers_return_job_not_found(tmp_path) -> None:
    with make_client(tmp_path) as client:
        job = upload_image(client)
        wait_for_status(client, job["id"], {"completed"})

        for page_number in (0, -1):
            response = client.get(f"/api/v1/ocr/jobs/{job['id']}/pages/{page_number}")
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "JOB_NOT_FOUND"

            image_response = client.get(
                f"/api/v1/ocr/jobs/{job['id']}/pages/{page_number}/image"
            )
            assert image_response.status_code == 404
            assert image_response.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_jpeg_is_detected_from_bytes_when_client_type_is_generic(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("scan.jpg", jpeg_bytes(), "application/octet-stream")},
        )
        assert response.status_code == 202
        assert response.json()["media_type"] == "image/jpeg"
        wait_for_status(client, response.json()["id"], {"completed"})


def test_file_extension_must_match_detected_content(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("scan.jpg", png_bytes(), "image/jpeg")},
        )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "FILE_EXTENSION_MISMATCH"


def test_job_is_failed_when_every_page_fails(tmp_path) -> None:
    class FailingProcessor(FakeProcessor):
        async def process_page(
            self, source_path: Path, media_type: str, page_number: int
        ) -> PageArtifact:
            return PageArtifact(png_bytes(), None, "PAGE_PROCESSING_FAILED")

    with make_client(tmp_path, FailingProcessor()) as client:
        job = upload_image(client)
        result = wait_for_status(client, job["id"], {"failed"})
        page = client.get(f"/api/v1/ocr/jobs/{job['id']}/pages/1").json()

    assert result["progress"]["failed_pages"] == 1
    assert page["status"] == "failed"
    assert page["error"]["code"] == "PAGE_PROCESSING_FAILED"


def test_retained_job_limit_requires_delete_before_new_upload(tmp_path) -> None:
    with make_client(tmp_path, max_retained_jobs=1) as client:
        first = upload_image(client)
        wait_for_status(client, first["id"], {"completed"})
        limited = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("again.png", png_bytes(), "image/png")},
        )
        assert limited.status_code == 409
        assert limited.json()["error"]["code"] == "JOB_STORAGE_LIMIT_REACHED"
        assert client.delete(f"/api/v1/ocr/jobs/{first['id']}").status_code == 204

        second = upload_image(client)
        assert second["id"] != first["id"]
        wait_for_status(client, second["id"], {"completed"})


def test_file_validation_errors_use_stable_error_envelope(tmp_path) -> None:
    with make_client(tmp_path) as client:
        unsupported = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("scan.png", b"not an image", "image/png")},
        )
        assert unsupported.status_code == 415
        assert unsupported.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

        corrupt = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("scan.png", b"\x89PNG\r\n\x1a\ninvalid", "image/png")},
        )
        assert corrupt.status_code == 422
        assert corrupt.json()["error"]["code"] == "CORRUPT_IMAGE"

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt("secret")
        protected = BytesIO()
        writer.write(protected)
        encrypted = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("locked.pdf", protected.getvalue(), "application/pdf")},
        )
        assert encrypted.status_code == 422
        assert encrypted.json()["error"]["code"] == "PDF_PASSWORD_PROTECTED"


def test_capabilities_reflect_configured_limits(tmp_path) -> None:
    with make_client(tmp_path, max_pages=3, max_upload_bytes=4096) as client:
        response = client.get("/api/v1/ocr/capabilities")

    assert response.status_code == 200
    assert response.json()["max_pages"] == 3
    assert response.json()["max_upload_bytes"] == 4096
    assert response.json()["worker_count"] == 1
    assert response.json()["max_retained_jobs"] == 5
    assert "application/pdf" in response.json()["supported_media_types"]


def test_unknown_routes_use_safe_error_envelope(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/not-a-route")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "ROUTE_NOT_FOUND",
            "message": "ไม่พบเส้นทางที่ร้องขอ",
            "retryable": False,
        }
    }


def test_api_reports_upload_and_page_limit_errors(tmp_path) -> None:
    with make_client(tmp_path, max_upload_bytes=1024) as client:
        too_large = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("large.pdf", b"A" * 1025, "application/pdf")},
        )
        assert too_large.status_code == 413
        assert too_large.json()["error"]["code"] == "FILE_TOO_LARGE"

        request_too_large = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("large.pdf", b"A" * (2 * 1024 * 1024), "application/pdf")},
        )
        assert request_too_large.status_code == 413
        assert request_too_large.json()["error"]["code"] == "FILE_TOO_LARGE"

    with make_client(tmp_path, max_pages=1) as client:
        too_many_pages = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("two-pages.pdf", pdf_bytes(2), "application/pdf")},
        )
        assert too_many_pages.status_code == 422
        assert too_many_pages.json()["error"]["code"] == "PAGE_LIMIT_EXCEEDED"


def test_multipage_pdf_returns_blank_and_failed_pages_separately(tmp_path) -> None:
    class PartialProcessor(FakeProcessor):
        async def process_page(
            self, source_path: Path, media_type: str, page_number: int
        ) -> PageArtifact:
            image = png_bytes()
            if page_number == 1:
                return PageArtifact(image, PageCompleted("", (), ImageSize(80, 50)))
            return PageArtifact(image, None, "PAGE_PROCESSING_FAILED")

    with make_client(tmp_path, PartialProcessor()) as client:
        response = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("two-pages.pdf", pdf_bytes(2), "application/pdf")},
        )
        assert response.status_code == 202
        job = response.json()
        completed = wait_for_status(client, job["id"], {"partially_completed"})
        pages = client.get(f"/api/v1/ocr/jobs/{job['id']}/pages").json()["pages"]
        first_image = client.get(pages[0]["image_url"])
        second_image = client.get(pages[1]["image_url"])

    assert completed["progress"]["completed_pages"] == 1
    assert completed["progress"]["failed_pages"] == 1
    assert pages[0]["status"] == "completed"
    assert pages[0]["has_text"] is False
    assert pages[1]["status"] == "failed"
    assert pages[1]["error"]["code"] == "PAGE_PROCESSING_FAILED"
    assert first_image.status_code == second_image.status_code == 200


def test_expired_job_is_unavailable_and_its_data_is_removed(tmp_path) -> None:
    from datetime import UTC, datetime, timedelta

    current = [datetime(2026, 11, 23, tzinfo=UTC)]
    app = create_app(
        Settings(storage_dir=tmp_path, job_ttl_seconds=60, cleanup_interval_seconds=5),
        FakeProcessor(),
        now=lambda: current[0],
    )
    with TestClient(app) as client:
        job = upload_image(client)
        assert list(tmp_path.iterdir())
        current[0] += timedelta(minutes=2)
        deadline = time.monotonic() + 7
        while time.monotonic() < deadline and list(tmp_path.iterdir()):
            time.sleep(0.05)
        assert list(tmp_path.iterdir()) == []
        expired = client.get(f"/api/v1/ocr/jobs/{job['id']}")
        assert expired.status_code == 404
        assert expired.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_expiry_during_processing_discards_late_result(tmp_path) -> None:
    from datetime import UTC, datetime, timedelta

    current = [datetime(2026, 11, 23, tzinfo=UTC)]
    release = threading.Event()
    app = create_app(
        Settings(storage_dir=tmp_path, job_ttl_seconds=60),
        FakeProcessor(release),
        now=lambda: current[0],
    )
    with TestClient(app) as client:
        job = upload_image(client)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = client.get(f"/api/v1/ocr/jobs/{job['id']}").json()
            if result["progress"]["processing_pages"]:
                break
            time.sleep(0.02)
        else:
            raise AssertionError("Job never reached processing")

        current[0] += timedelta(minutes=2)
        assert client.get(f"/api/v1/ocr/jobs/{job['id']}").status_code == 404
        release.set()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and list(tmp_path.iterdir()):
            time.sleep(0.02)
        assert list(tmp_path.iterdir()) == []


def test_queue_is_bounded_and_deleted_worker_result_is_discarded(tmp_path) -> None:
    release = threading.Event()
    processor = FakeProcessor(release)
    with make_client(tmp_path, processor, max_queued_jobs=1) as client:
        first = upload_image(client)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = client.get(f"/api/v1/ocr/jobs/{first['id']}").json()
            if result["progress"]["processing_pages"] == 1:
                break
            time.sleep(0.02)
        else:
            raise AssertionError("First job never reached processing")
        not_ready = client.get(f"/api/v1/ocr/jobs/{first['id']}/pages/1/image")
        assert not_ready.status_code == 409
        assert not_ready.json()["error"]["code"] == "PAGE_IMAGE_NOT_READY"

        second = upload_image(client)
        assert client.get(f"/api/v1/ocr/jobs/{second['id']}").json()["status"] == "queued"
        full = client.post(
            "/api/v1/ocr/jobs",
            files={"file": ("scan.png", png_bytes(), "image/png")},
        )
        assert full.status_code == 503
        assert full.json()["error"]["code"] == "JOB_QUEUE_FULL"

        assert client.delete(f"/api/v1/ocr/jobs/{first['id']}").status_code == 204
        release.set()
        assert client.get(f"/api/v1/ocr/jobs/{first['id']}").status_code == 404
        wait_for_status(client, second["id"], {"completed"})

    assert not list(tmp_path.iterdir())
