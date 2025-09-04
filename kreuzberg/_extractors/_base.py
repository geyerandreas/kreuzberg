from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from kreuzberg._types import ExtractionResult, normalize_metadata
from kreuzberg._utils._quality import calculate_quality_score, clean_extracted_text

if TYPE_CHECKING:
    from pathlib import Path

    from kreuzberg._types import ExtractionConfig


class Extractor(ABC):
    __slots__ = ("config", "mime_type")

    SUPPORTED_MIME_TYPES: ClassVar[set[str]]

    def __init__(self, mime_type: str, config: ExtractionConfig) -> None:
        self.mime_type = mime_type
        self.config = config

    @abstractmethod
    async def extract_bytes_async(self, content: bytes) -> ExtractionResult: ...

    @abstractmethod
    async def extract_path_async(self, path: Path) -> ExtractionResult: ...

    @abstractmethod
    def extract_bytes_sync(self, content: bytes) -> ExtractionResult: ...

    @abstractmethod
    def extract_path_sync(self, path: Path) -> ExtractionResult: ...

    @classmethod
    def supports_mimetype(cls, mime_type: str) -> bool:
        return mime_type in cls.SUPPORTED_MIME_TYPES or any(
            mime_type.startswith(supported_type) for supported_type in cls.SUPPORTED_MIME_TYPES
        )

    def _apply_quality_processing(self, result: ExtractionResult) -> ExtractionResult:
        if not self.config.enable_quality_processing:
            return result

        if not result.content:
            return result

        cleaned_content = clean_extracted_text(result.content)

        quality_score = calculate_quality_score(cleaned_content, dict(result.metadata) if result.metadata else None)

        enhanced_metadata = (dict(result.metadata) if result.metadata else {}) | {"quality_score": quality_score}

        return ExtractionResult(
            content=cleaned_content,
            mime_type=result.mime_type,
            metadata=normalize_metadata(enhanced_metadata),
            chunks=result.chunks,
            detected_languages=result.detected_languages,
            tables=result.tables,
        )
