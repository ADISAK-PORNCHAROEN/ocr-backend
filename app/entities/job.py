from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.entities.page import (
    Page,
    PageCompleted,
    PageFailed,
    PageNumber,
    PageStatus,
)


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JobProgress:
    total_pages: int
    completed_pages: int
    failed_pages: int
    processing_pages: int

    @property
    def processed_pages(self) -> int:
        return self.completed_pages + self.failed_pages


@dataclass(slots=True)
class Job:
    id: UUID
    source_name: str
    media_type: str
    created_at: datetime
    expires_at: datetime
    pages: dict[PageNumber, Page] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        source_name: str,
        media_type: str,
        page_count: int,
        created_at: datetime,
        expires_at: datetime,
    ) -> Job:
        if page_count < 1:
            raise ValueError("A job must contain at least one page")
        pages = {
            number: Page(number) for number in (PageNumber(i) for i in range(1, page_count + 1))
        }
        return cls(job_id, source_name, media_type, created_at, expires_at, pages)

    @property
    def status(self) -> JobStatus:
        statuses = {page.status for page in self.pages.values()}
        if PageStatus.PROCESSING in statuses:
            return JobStatus.PROCESSING
        if PageStatus.PENDING in statuses:
            return JobStatus.QUEUED
        if statuses == {PageStatus.COMPLETED}:
            return JobStatus.COMPLETED
        if statuses == {PageStatus.FAILED}:
            return JobStatus.FAILED
        return JobStatus.PARTIALLY_COMPLETED

    @property
    def progress(self) -> JobProgress:
        counts = {
            status: sum(page.status is status for page in self.pages.values())
            for status in PageStatus
        }
        return JobProgress(
            total_pages=len(self.pages),
            completed_pages=counts[PageStatus.COMPLETED],
            failed_pages=counts[PageStatus.FAILED],
            processing_pages=counts[PageStatus.PROCESSING],
        )

    def set_page_processing(self, page_number: PageNumber) -> None:
        page = self._page(page_number)
        if page.status is not PageStatus.PENDING:
            raise ValueError("Only pending pages can start processing")
        page.status = PageStatus.PROCESSING

    def complete_page(
        self,
        page_number: PageNumber,
        result: PageCompleted,
        *,
        ocr_duration_ms: float | None = None,
    ) -> None:
        page = self._page(page_number)
        if page.status is not PageStatus.PROCESSING:
            raise ValueError("Only processing pages can be completed")
        page.status = PageStatus.COMPLETED
        page.result = result
        page.error = None
        page.ocr_duration_ms = ocr_duration_ms

    def fail_page(
        self,
        page_number: PageNumber,
        error: PageFailed,
        *,
        ocr_duration_ms: float | None = None,
    ) -> None:
        page = self._page(page_number)
        if page.status is not PageStatus.PROCESSING:
            raise ValueError("Only processing pages can fail")
        page.status = PageStatus.FAILED
        page.error = error
        page.result = None
        page.ocr_duration_ms = ocr_duration_ms

    def _page(self, page_number: PageNumber) -> Page:
        try:
            return self.pages[page_number]
        except KeyError as exc:
            raise ValueError("Page does not belong to this job") from exc
