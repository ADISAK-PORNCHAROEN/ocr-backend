from __future__ import annotations

import asyncio
import threading
from io import BytesIO
from pathlib import Path

import pytest
from app.core.config import Settings
from app.documents.reader import DocumentReader
from app.repositories.jobs import JobsRepository
from app.services.jobs import JobsService
from PIL import Image


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 8), "white").save(output, format="PNG")
    return output.getvalue()


class Processor:
    async def process_page(self, source_path: Path, media_type: str, page_number: int):
        raise AssertionError("No job should reach the processor in these tests")

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_staging_is_removed_when_repository_registration_fails(tmp_path, monkeypatch) -> None:
    repository = JobsRepository(tmp_path)
    reader = DocumentReader(Settings(storage_dir=tmp_path))
    service = JobsService(Settings(storage_dir=tmp_path), repository, reader, Processor())

    def fail_add(job, document) -> None:
        raise RuntimeError("repository unavailable")

    monkeypatch.setattr(repository, "add", fail_add)

    with pytest.raises(RuntimeError, match="repository unavailable"):
        await service.submit(BytesIO(png_bytes()), "scan.png")

    assert list(tmp_path.iterdir()) == []
    assert repository.all_jobs() == []
    assert not service._admitted
    await service.close()


@pytest.mark.asyncio
async def test_cancelling_file_staging_waits_for_cleanup(tmp_path) -> None:
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    reader = DocumentReader(Settings(storage_dir=tmp_path))

    class BlockingReader:
        def prepare(self, source, filename, job_id):
            started.set()
            release.wait(timeout=3)
            try:
                return reader.prepare(source, filename, job_id)
            finally:
                finished.set()

    repository = JobsRepository(tmp_path)
    service = JobsService(Settings(storage_dir=tmp_path), repository, BlockingReader(), Processor())
    submission = asyncio.create_task(service.submit(BytesIO(png_bytes()), "scan.png"))

    assert await asyncio.to_thread(started.wait, 2)
    submission.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await submission

    assert await asyncio.to_thread(finished.wait, 2)
    assert list(tmp_path.iterdir()) == []
    assert repository.all_jobs() == []
    assert not service._admitted
    await service.close()


def test_startup_cleanup_ignores_symlinked_job_directory(tmp_path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / ".owned-by-ocr-backend"
    marker.write_text("marker", encoding="utf-8")
    sentinel = outside / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    job_link = tmp_path / "job-00000000-0000-0000-0000-000000000000"
    try:
        job_link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Directory symlinks are unavailable: {error}")

    removed = JobsRepository(tmp_path).cleanup_orphans()

    assert removed == 0
    assert sentinel.read_text(encoding="utf-8") == "keep"
