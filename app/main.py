from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.controllers.health import router as health_router
from app.api.controllers.jobs import router as jobs_router
from app.core.config import Settings, get_settings
from app.core.errors import ApplicationError
from app.core.middleware import UploadBodyLimitMiddleware
from app.documents.reader import DocumentReader
from app.ocr.openthai import OcrProcessor
from app.repositories.jobs import JobsRepository
from app.services.jobs import JobsService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await app.state.jobs_service.start()
    try:
        yield
    finally:
        await app.state.jobs_service.close()


def create_app(
    settings: Settings | None = None,
    processor: OcrProcessor | None = None,
    now: Callable[[], datetime] | None = None,
) -> FastAPI:
    configured = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = FastAPI(
        title="OCR Backend",
        description="Asynchronous Thai and English OCR playground using OpenThai OCR Text.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        UploadBodyLimitMiddleware,
        max_body_bytes=configured.max_upload_bytes + 1024 * 1024,
    )
    repository = JobsRepository(configured.storage_dir)
    app.state.settings = configured
    app.state.jobs_service = JobsService(
        configured,
        repository,
        DocumentReader(configured),
        processor=processor,
        now=now,
    )
    app.include_router(health_router)
    app.include_router(jobs_router)

    @app.exception_handler(ApplicationError)
    async def application_error_handler(_: Request, exc: ApplicationError) -> JSONResponse:
        headers = {"Retry-After": "5"} if exc.retryable else None
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "retryable": exc.retryable,
                }
            },
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, __: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "ข้อมูลคำขอไม่ถูกต้อง",
                    "retryable": False,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = {
            400: ("BAD_REQUEST", "คำขอไม่ถูกต้อง"),
            404: ("ROUTE_NOT_FOUND", "ไม่พบเส้นทางที่ร้องขอ"),
            405: ("METHOD_NOT_ALLOWED", "ไม่รองรับ method นี้"),
            413: ("FILE_TOO_LARGE", "ขนาด request เกินขีดจำกัด"),
        }.get(exc.status_code, ("HTTP_ERROR", "ไม่สามารถดำเนินการตามคำขอได้"))
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message, "retryable": False}},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logging.getLogger(__name__).exception("Unhandled request error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "เกิดข้อผิดพลาดภายในระบบ",
                    "retryable": True,
                }
            },
        )

    return app


app = create_app()
