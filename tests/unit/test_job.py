from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.entities.job import Job, JobStatus
from app.entities.page import (
    BoundingBox,
    ImageSize,
    OcrLine,
    PageCompleted,
    PageFailed,
    PageNumber,
)


def make_job(page_count: int = 2) -> Job:
    created_at = datetime(2026, 11, 22, tzinfo=UTC)
    return Job.create(
        job_id=uuid4(),
        source_name="document.png",
        media_type="image/png",
        page_count=page_count,
        created_at=created_at,
        expires_at=created_at + timedelta(hours=1),
    )


def test_new_job_is_queued_with_all_pages_pending() -> None:
    job = make_job()

    assert job.status is JobStatus.QUEUED
    assert job.progress.completed_pages == 0
    assert job.progress.failed_pages == 0
    assert job.progress.processed_pages == 0
    assert job.progress.total_pages == 2


def test_successful_blank_page_counts_as_completed() -> None:
    job = make_job(page_count=1)
    page_number = PageNumber(1)
    job.set_page_processing(page_number)
    job.complete_page(
        page_number,
        PageCompleted(original_text="", lines=(), image_size=ImageSize(800, 1100)),
    )

    assert job.status is JobStatus.COMPLETED
    assert job.progress.completed_pages == 1
    assert job.progress.failed_pages == 0
    assert job.pages[page_number].has_text is False


def test_job_status_and_progress_derive_from_page_states() -> None:
    job = make_job()
    first = PageNumber(1)
    second = PageNumber(2)
    job.set_page_processing(first)
    job.complete_page(
        first,
        PageCompleted(
            original_text="เอกสาร OCR",
            lines=(OcrLine("เอกสาร OCR", 0.9, BoundingBox(1, 2, 100, 20)),),
            image_size=ImageSize(800, 1100),
        ),
    )
    job.set_page_processing(second)
    job.fail_page(second, PageFailed("PAGE_PROCESSING_FAILED", "อ่านหน้านี้ไม่ได้"))

    assert job.status is JobStatus.PARTIALLY_COMPLETED
    assert job.progress.completed_pages == 1
    assert job.progress.failed_pages == 1
    assert job.progress.processed_pages == 2


def test_job_fails_when_every_page_fails() -> None:
    job = make_job(page_count=1)
    page_number = PageNumber(1)
    job.set_page_processing(page_number)
    job.fail_page(page_number, PageFailed("PAGE_PROCESSING_FAILED", "อ่านหน้านี้ไม่ได้"))

    assert job.status is JobStatus.FAILED


def test_page_cannot_be_completed_before_processing() -> None:
    job = make_job(page_count=1)

    with pytest.raises(ValueError, match="processing"):
        job.complete_page(
            PageNumber(1),
            PageCompleted(original_text="", lines=(), image_size=ImageSize(1, 1)),
        )


def test_job_does_not_allow_processing_twice() -> None:
    job = make_job(page_count=1)
    page_number = PageNumber(1)
    job.set_page_processing(page_number)

    with pytest.raises(ValueError, match="pending"):
        job.set_page_processing(page_number)


def test_page_number_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        PageNumber(0)
