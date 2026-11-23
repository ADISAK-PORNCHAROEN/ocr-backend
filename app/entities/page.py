from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True, order=True)
class PageNumber:
    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValueError("Page number must be positive")


@dataclass(frozen=True, slots=True)
class ImageSize:
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1:
            raise ValueError("Image dimensions must be positive")


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        if self.x1 < 0 or self.y1 < 0 or self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError("Bounding box must use non-negative, ordered coordinates")


@dataclass(frozen=True, slots=True)
class OcrLine:
    text: str
    confidence: float
    box: BoundingBox

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("OCR confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class PageFailed:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class PageCompleted:
    original_text: str
    lines: tuple[OcrLine, ...]
    image_size: ImageSize


class PageStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class Page:
    number: PageNumber
    status: PageStatus = PageStatus.PENDING
    result: PageCompleted | None = None
    error: PageFailed | None = None
    ocr_duration_ms: float | None = None

    @property
    def has_text(self) -> bool | None:
        if self.status is not PageStatus.COMPLETED or self.result is None:
            return None
        return bool(self.result.original_text.strip())
