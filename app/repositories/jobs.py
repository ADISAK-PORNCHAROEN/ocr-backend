from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.documents.reader import StagedDocument
from app.entities.job import Job
from app.entities.page import PageNumber
from app.ocr.openthai import PageArtifact


@dataclass(slots=True)
class StoredJob:
    job: Job
    document: StagedDocument
    page_images: dict[PageNumber, Path] = field(default_factory=dict)


class JobsRepository:
    def __init__(self, storage_root: Path) -> None:
        self.storage_root = storage_root.resolve()
        self._jobs: dict[UUID, StoredJob] = {}

    def add(self, job: Job, document: StagedDocument) -> None:
        if job.id in self._jobs:
            raise ValueError("Job already exists")
        self._jobs[job.id] = StoredJob(job, document)

    def get(self, job_id: UUID) -> StoredJob | None:
        return self._jobs.get(job_id)

    def save_page_artifact(
        self,
        job_id: UUID,
        page_number: PageNumber,
        artifact: PageArtifact,
    ) -> None:
        stored = self.get(job_id)
        if stored is None:
            return
        target = stored.document.job_dir / f"page-{page_number.value:04}.png"
        temporary = target.with_suffix(".png.tmp")
        temporary.write_bytes(artifact.image_png)
        temporary.replace(target)
        stored.page_images[page_number] = target

    def get_page_image(self, job_id: UUID, page_number: PageNumber) -> bytes | None:
        stored = self.get(job_id)
        if stored is None:
            return None
        path = stored.page_images.get(page_number)
        return path.read_bytes() if path and path.is_file() else None

    def delete(self, job_id: UUID) -> StoredJob | None:
        return self._jobs.pop(job_id, None)

    def remove_expired(self, now: datetime) -> list[StoredJob]:
        expired = [job_id for job_id, stored in self._jobs.items() if stored.job.expires_at <= now]
        removed: list[StoredJob] = []
        for job_id in expired:
            stored = self._jobs.pop(job_id, None)
            if stored is not None:
                removed.append(stored)
        return removed

    def is_available(self, job_id: UUID, now: datetime) -> bool:
        stored = self._jobs.get(job_id)
        return stored is not None and stored.job.expires_at > now

    def remove_document(self, document: StagedDocument) -> None:
        target = document.job_dir.resolve()
        if target.parent != self.storage_root or not target.name.startswith("job-"):
            raise ValueError("Refusing to remove a directory outside the application job root")
        if (target / ".owned-by-ocr-backend").is_file():
            shutil.rmtree(target, ignore_errors=True)

    def cleanup_orphans(self) -> int:
        self.storage_root.mkdir(parents=True, exist_ok=True)
        removed = 0
        for child in self.storage_root.iterdir():
            if (
                not child.is_symlink()
                and child.is_dir()
                and re.fullmatch(r"job-[0-9a-fA-F-]{36}", child.name)
                and (child / ".owned-by-ocr-backend").is_file()
            ):
                shutil.rmtree(child)
                removed += 1
        return removed

    def all_jobs(self) -> list[StoredJob]:
        return list(self._jobs.values())

    def clear(self) -> None:
        self._jobs.clear()
