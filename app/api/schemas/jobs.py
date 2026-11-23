from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.entities.job import Job, JobProgress, JobStatus
from app.entities.page import Page, PageStatus


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ProgressResponse(BaseModel):
    total_pages: int
    completed_pages: int
    failed_pages: int
    processing_pages: int
    processed_pages: int


class JobResponse(BaseModel):
    id: UUID
    filename: str
    media_type: Literal["image/jpeg", "image/png", "application/pdf"]
    status: JobStatus
    progress: ProgressResponse
    created_at: datetime
    expires_at: datetime


class BoundingBoxResponse(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class OcrLineResponse(BaseModel):
    text: str
    confidence: float
    box: BoundingBoxResponse


class ImageSizeResponse(BaseModel):
    width: int
    height: int


class PageErrorResponse(BaseModel):
    code: str
    message: str


class PageResponse(BaseModel):
    page_number: int
    status: PageStatus
    has_text: bool | None
    original_text: str | None = None
    lines: list[OcrLineResponse] | None = None
    image_size: ImageSizeResponse | None = None
    error: PageErrorResponse | None = None
    ocr_duration_ms: float | None
    image_url: str


class PagesResponse(BaseModel):
    pages: list[PageResponse]


class CapabilitiesResponse(BaseModel):
    supported_media_types: list[str]
    max_upload_bytes: int
    max_pages: int | None
    pdf_dpi: int
    max_page_pixels: int
    max_total_pixels: int
    max_pending_jobs: int
    max_retained_jobs: int
    worker_count: int
    job_ttl_seconds: int
    model_id: str
    model_revision: str


def to_progress(progress: JobProgress) -> ProgressResponse:
    return ProgressResponse(
        total_pages=progress.total_pages,
        completed_pages=progress.completed_pages,
        failed_pages=progress.failed_pages,
        processing_pages=progress.processing_pages,
        processed_pages=progress.processed_pages,
    )


def to_job_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        filename=job.source_name,
        media_type=job.media_type,
        status=job.status,
        progress=to_progress(job.progress),
        created_at=job.created_at,
        expires_at=job.expires_at,
    )


def to_page_response(job: Job, page: Page) -> PageResponse:
    result = page.result
    return PageResponse(
        page_number=page.number.value,
        status=page.status,
        has_text=page.has_text,
        original_text=result.original_text if result else None,
        lines=[
            OcrLineResponse(
                text=line.text,
                confidence=line.confidence,
                box=BoundingBoxResponse(
                    x1=line.box.x1,
                    y1=line.box.y1,
                    x2=line.box.x2,
                    y2=line.box.y2,
                ),
            )
            for line in result.lines
        ]
        if result
        else None,
        image_size=ImageSizeResponse(width=result.image_size.width, height=result.image_size.height)
        if result
        else None,
        error=PageErrorResponse(code=page.error.code, message=page.error.message)
        if page.error
        else None,
        ocr_duration_ms=page.ocr_duration_ms,
        image_url=f"/api/v1/ocr/jobs/{job.id}/pages/{page.number.value}/image",
    )
