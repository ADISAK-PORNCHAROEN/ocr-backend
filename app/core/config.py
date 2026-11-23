from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OCR_", env_file=".env.local", extra="ignore")

    model_id: str = "iapp/OpenThai2.1-OCR-Text-20261118"
    model_revision: str = "v2.1.4"
    model_cache_dir: Path | None = None
    storage_dir: Path = Path(gettempdir()) / "ocr-backend" / "jobs"
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, ge=1024)
    max_page_pixels: int = Field(default=25_000_000, ge=1_000_000)
    max_total_pixels: int = Field(default=80_000_000, ge=1_000_000)
    max_dimension: int = Field(default=12_000, ge=1000)
    pdf_dpi: int = Field(default=150, ge=72, le=300)
    max_queued_jobs: int = Field(default=2, ge=1, le=20)
    max_retained_jobs: int = Field(default=5, ge=1, le=100)
    job_ttl_seconds: int = Field(default=3600, ge=60, le=86_400)
    cleanup_interval_seconds: int = Field(default=30, ge=5, le=3600)
    model_threads: int = Field(default=1, ge=1, le=4)

    @field_validator("model_cache_dir", mode="before")
    @classmethod
    def empty_cache_dir_is_none(cls, value: object) -> object:
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
