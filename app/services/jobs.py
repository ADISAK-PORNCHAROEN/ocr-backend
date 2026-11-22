from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import BinaryIO
from uuid import UUID, uuid4

from app.core.config import Settings
from app.core.errors import DocumentError, JobNotFound, JobStorageLimitReached, QueueFull
from app.documents.reader import DocumentReader, StagedDocument
from app.entities.job import Job
from app.entities.page import Page, PageFailed, PageNumber
from app.ocr.openthai import OcrProcessor, OpenThaiProcessor
from app.repositories.jobs import JobsRepository

logger = logging.getLogger(__name__)


class JobsService:
    def __init__(
        self,
        settings: Settings,
        repository: JobsRepository,
        document_reader: DocumentReader,
        processor: OcrProcessor | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.document_reader = document_reader
        self.processor = processor or OpenThaiProcessor(settings)
        self._now = now or (lambda: datetime.now(UTC))
        self._queue: asyncio.Queue[UUID] = asyncio.Queue(maxsize=settings.max_queued_jobs)
        self._active: set[UUID] = set()
        self._admitted: set[UUID] = set()
        self._staging: set[UUID] = set()
        self._deferred_cleanup: dict[UUID, StagedDocument] = {}
        self._worker: asyncio.Task[None] | None = None
        self._expiry_worker: asyncio.Task[None] | None = None
        self._closed = False

    async def start(self) -> None:
        self.repository.cleanup_orphans()
        self._worker = asyncio.create_task(self._process_queue(), name="ocr-job-worker")
        self._expiry_worker = asyncio.create_task(self._expire_jobs(), name="ocr-job-expiry")

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._expiry_worker:
            self._expiry_worker.cancel()
            await asyncio.gather(self._expiry_worker, return_exceptions=True)
        await self._queue.join()
        if self._worker:
            self._worker.cancel()
            await asyncio.gather(self._worker, return_exceptions=True)
        await self.processor.close()
        for stored in self.repository.all_jobs():
            self.repository.remove_document(stored.document)
        self.repository.clear()
        for document in self._deferred_cleanup.values():
            self.repository.remove_document(document)
        self._deferred_cleanup.clear()

    async def submit(self, source: BinaryIO, filename: str | None) -> Job:
        self._expire_due_jobs()
        if self._queue.full() or len(self._admitted) >= self.settings.max_queued_jobs + 1:
            raise QueueFull()
        if len(self.repository.all_jobs()) + len(self._staging) >= self.settings.max_retained_jobs:
            raise JobStorageLimitReached()
        job_id = uuid4()
        self._admitted.add(job_id)
        self._staging.add(job_id)
        staging = asyncio.create_task(
            asyncio.to_thread(
                self.document_reader.prepare,
                source,
                filename,
                job_id,
            )
        )
        try:
            document = await asyncio.shield(staging)
        except asyncio.CancelledError:
            try:
                document = await asyncio.shield(staging)
            except Exception:
                pass
            else:
                self.repository.remove_document(document)
            finally:
                self._admitted.discard(job_id)
            raise
        except DocumentError:
            self._admitted.discard(job_id)
            raise
        except Exception as exc:
            self._admitted.discard(job_id)
            logger.exception("Document staging failed")
            raise DocumentError("FILE_UNREADABLE", "อ่านไฟล์ที่อัปโหลดไม่ได้", 422) from exc
        finally:
            self._staging.discard(job_id)
        try:
            created_at = self._now()
            job = Job.create(
                job_id=job_id,
                source_name=document.source_name,
                media_type=document.media_type,
                page_count=document.page_count,
                created_at=created_at,
                expires_at=created_at + timedelta(seconds=self.settings.job_ttl_seconds),
            )
            self.repository.add(job, document)
            self._queue.put_nowait(job_id)
        except BaseException as exc:
            self.repository.delete(job_id)
            try:
                self.repository.remove_document(document)
            except Exception:
                logger.exception("Failed to clean staged document for job %s", job_id)
            finally:
                self._admitted.discard(job_id)
            if isinstance(exc, asyncio.QueueFull):
                raise QueueFull() from exc
            raise
        return job

    def get(self, job_id: UUID) -> Job:
        stored = self.repository.get(job_id)
        if stored is None or stored.job.expires_at <= self._now():
            self._remove_expired_job(job_id)
            raise JobNotFound()
        return stored.job

    def get_pages(self, job_id: UUID) -> dict[PageNumber, Page]:
        return self.get(job_id).pages

    def get_page(self, job_id: UUID, page_number: int) -> Page:
        job = self.get(job_id)
        try:
            return job.pages[PageNumber(page_number)]
        except KeyError as exc:
            raise JobNotFound() from exc

    def get_page_image(self, job_id: UUID, page_number: int) -> bytes:
        self.get_page(job_id, page_number)
        image = self.repository.get_page_image(job_id, PageNumber(page_number))
        if image is None:
            raise DocumentError("PAGE_IMAGE_NOT_READY", "ภาพหน้านี้ยังไม่พร้อม", 409)
        return image

    async def delete(self, job_id: UUID) -> None:
        stored = self.repository.delete(job_id)
        if stored is None:
            raise JobNotFound()
        if job_id in self._active:
            self._deferred_cleanup[job_id] = stored.document
        else:
            self._admitted.discard(job_id)
            self.repository.remove_document(stored.document)

    async def _process_queue(self) -> None:
        while True:
            job_id = await self._queue.get()
            stored = self.repository.get(job_id)
            if stored is None:
                self._admitted.discard(job_id)
                self._queue.task_done()
                continue
            self._active.add(job_id)
            try:
                for page_number in stored.job.pages:
                    if not self.repository.is_available(job_id, self._now()):
                        break
                    stored.job.set_page_processing(page_number)
                    try:
                        artifact = await self.processor.process_page(
                            stored.document.source_path,
                            stored.job.media_type,
                            page_number.value,
                        )
                        if not self.repository.is_available(job_id, self._now()):
                            break
                        self.repository.save_page_artifact(job_id, page_number, artifact)
                        if artifact.result is None:
                            stored.job.fail_page(
                                page_number,
                                PageFailed("PAGE_PROCESSING_FAILED", "อ่านหน้านี้ไม่ได้"),
                            )
                        else:
                            stored.job.complete_page(page_number, artifact.result)
                    except Exception:
                        logger.exception(
                            "OCR page processing failed for job %s page %s",
                            job_id,
                            page_number.value,
                        )
                        if self.repository.is_available(job_id, self._now()):
                            stored.job.fail_page(
                                page_number,
                                PageFailed("PAGE_PROCESSING_FAILED", "อ่านหน้านี้ไม่ได้"),
                            )
                logger.info("OCR job processing finished: %s", job_id)
            except asyncio.CancelledError:
                raise
            finally:
                self._active.discard(job_id)
                deferred = self._deferred_cleanup.pop(job_id, None)
                if deferred:
                    self.repository.remove_document(deferred)
                elif not self.repository.is_available(job_id, self._now()):
                    self.repository.remove_document(stored.document)
                self._admitted.discard(job_id)
                self._queue.task_done()

    async def _expire_jobs(self) -> None:
        while True:
            await asyncio.sleep(self.settings.cleanup_interval_seconds)
            self._expire_due_jobs()

    def _expire_due_jobs(self) -> None:
        for stored in self.repository.remove_expired(self._now()):
            job_id = stored.job.id
            if job_id in self._active:
                self._deferred_cleanup[job_id] = stored.document
            else:
                self._admitted.discard(job_id)
                self.repository.remove_document(stored.document)
            logger.info("OCR job expired: %s", job_id)

    def _remove_expired_job(self, job_id: UUID) -> None:
        stored = self.repository.delete(job_id)
        if stored is None:
            return
        if job_id in self._active:
            self._deferred_cleanup[job_id] = stored.document
        else:
            self._admitted.discard(job_id)
            self.repository.remove_document(stored.document)
