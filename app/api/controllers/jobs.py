from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, File, Request, Response, UploadFile, status

from app.api.schemas.jobs import (
    CapabilitiesResponse,
    JobResponse,
    PageResponse,
    PagesResponse,
    to_job_response,
    to_page_response,
)
from app.services.jobs import JobsService

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])


def _service(request: Request) -> JobsService:
    return cast(JobsService, request.app.state.jobs_service)


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities(request: Request) -> CapabilitiesResponse:
    settings = request.app.state.settings
    return CapabilitiesResponse(
        supported_media_types=["image/jpeg", "image/png", "application/pdf"],
        max_upload_bytes=settings.max_upload_bytes,
        max_pages=settings.max_pages,
        pdf_dpi=settings.pdf_dpi,
        max_page_pixels=settings.max_page_pixels,
        max_total_pixels=settings.max_total_pixels,
        max_pending_jobs=settings.max_queued_jobs,
        max_retained_jobs=settings.max_retained_jobs,
        worker_count=1,
        job_ttl_seconds=settings.job_ttl_seconds,
        model_id=settings.model_id,
        model_revision=settings.model_revision,
    )


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    request: Request,
    file: Annotated[UploadFile, File(description="One JPG, PNG or PDF file")],
    response: Response,
) -> JobResponse:
    try:
        job = await _service(request).submit(file.file, file.filename)
    finally:
        await file.close()
    response.headers["Location"] = f"/api/v1/ocr/jobs/{job.id}"
    response.headers["Cache-Control"] = "no-store"
    return to_job_response(job)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, request: Request, response: Response) -> JobResponse:
    response.headers["Cache-Control"] = "no-store"
    return to_job_response(_service(request).get(job_id))


@router.get("/jobs/{job_id}/pages", response_model=PagesResponse)
async def get_pages(job_id: UUID, request: Request, response: Response) -> PagesResponse:
    service = _service(request)
    job = service.get(job_id)
    pages = service.get_pages(job_id)
    response.headers["Cache-Control"] = "no-store"
    return PagesResponse(pages=[to_page_response(job, page) for page in pages.values()])


@router.get("/jobs/{job_id}/pages/{page_number}", response_model=PageResponse)
async def get_page(
    job_id: UUID, page_number: int, request: Request, response: Response
) -> PageResponse:
    service = _service(request)
    job = service.get(job_id)
    page = service.get_page(job_id, page_number)
    response.headers["Cache-Control"] = "no-store"
    return to_page_response(job, page)


@router.get("/jobs/{job_id}/pages/{page_number}/image")
async def get_page_image(job_id: UUID, page_number: int, request: Request) -> Response:
    image = _service(request).get_page_image(job_id, page_number)
    return Response(image, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: UUID, request: Request) -> Response:
    await _service(request).delete(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Cache-Control": "no-store"})
