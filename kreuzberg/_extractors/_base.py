from __future__ import annotations

import io
import logging
import time
import zlib
from abc import ABC, abstractmethod
from dataclasses import asdict
from multiprocessing import cpu_count
from typing import TYPE_CHECKING, Any, ClassVar

from PIL import Image

from kreuzberg._ocr import get_ocr_backend
from kreuzberg._types import (
    EasyOCRConfig,
    ExtractedImage,
    ExtractionResult,
    ImageOCRResult,
    PaddleOCRConfig,
    TesseractConfig,
    normalize_metadata,
)
from kreuzberg._utils._quality import calculate_quality_score, clean_extracted_text
from kreuzberg._utils._sync import run_taskgroup_batched

if TYPE_CHECKING:
    from pathlib import Path

    from kreuzberg._types import ExtractionConfig

# Memory limits for image processing (in bytes)
MAX_TOTAL_IMAGE_SIZE_MB = 100
MAX_SINGLE_IMAGE_SIZE_MB = 50
MAX_TOTAL_IMAGE_SIZE = MAX_TOTAL_IMAGE_SIZE_MB * 1024 * 1024
MAX_SINGLE_IMAGE_SIZE = MAX_SINGLE_IMAGE_SIZE_MB * 1024 * 1024

logger = logging.getLogger(__name__)


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

        deduplicated_images = self._deduplicate_images(result.images) if result.images else []

        return ExtractionResult(
            content=cleaned_content,
            mime_type=result.mime_type,
            metadata=normalize_metadata(enhanced_metadata),
            tables=result.tables,
            chunks=result.chunks,
            images=deduplicated_images,
            image_ocr_results=result.image_ocr_results,
            entities=result.entities,
            keywords=result.keywords,
            detected_languages=result.detected_languages,
            document_type=result.document_type,
            document_type_confidence=result.document_type_confidence,
            layout=result.layout,
        )

    def _check_image_memory_limits(self, images: list[ExtractedImage]) -> list[ExtractedImage]:
        """Filter images based on memory safety limits."""
        if not images:
            return []

        # Calculate sizes once and create tuples for efficient processing
        images_with_sizes = [(img, len(img.data)) for img in images]

        # Filter out images exceeding single image limit
        valid_images = []
        for img, size in images_with_sizes:
            if size <= MAX_SINGLE_IMAGE_SIZE:
                valid_images.append((img, size))
            else:
                logger.warning(
                    "Skipping image %s: size %d MB exceeds limit of %d MB",
                    img.filename or "unknown",
                    size // (1024 * 1024),
                    MAX_SINGLE_IMAGE_SIZE_MB,
                )

        total_size = sum(size for _, size in valid_images)

        # If total is within limits, return all valid images
        if total_size <= MAX_TOTAL_IMAGE_SIZE:
            return [img for img, _ in valid_images]

        # Need to select subset - sort by size and greedily add smallest first
        logger.warning(
            "Total image size %d MB exceeds limit of %d MB, selecting subset",
            total_size // (1024 * 1024),
            MAX_TOTAL_IMAGE_SIZE_MB,
        )

        sorted_images = sorted(valid_images, key=lambda x: x[1])
        selected = []
        current_size = 0

        for img, img_size in sorted_images:
            if current_size + img_size <= MAX_TOTAL_IMAGE_SIZE:
                selected.append(img)
                current_size += img_size
            else:
                logger.debug("Skipping image %s: would exceed total memory limit", img.filename or "unknown")

        return selected

    # Deduplication constants
    _SMALL_IMAGE_THRESHOLD = 1024  # 1KB - hash entire content below this
    _HASH_SAMPLE_SIZE = 512  # Bytes to sample from start/end for hash

    def _compute_image_hash(self, img: ExtractedImage) -> int:
        """Compute hash for image deduplication using progressive hashing.

        For small images (<1KB), hash the entire content.
        For larger images, use size + first/last bytes for quick comparison.

        Args:
            img: Image to hash

        Returns:
            Hash value for deduplication
        """
        data_len = len(img.data)

        # For small images, hash everything
        if data_len < self._SMALL_IMAGE_THRESHOLD:
            return zlib.crc32(img.data) & 0xFFFFFFFF

        # For larger images, use progressive hashing:
        # Size + first N bytes + last N bytes + format
        hash_components = [
            str(data_len).encode(),
            img.data[: self._HASH_SAMPLE_SIZE],
            img.data[-self._HASH_SAMPLE_SIZE :],
            img.format.encode() if img.format else b"",
        ]

        # Combine components for hash
        combined = b"".join(hash_components)
        return zlib.crc32(combined) & 0xFFFFFFFF

    def _deduplicate_images(self, images: list[ExtractedImage]) -> list[ExtractedImage]:
        if not self.config.deduplicate_images or not images:
            return images

        seen_hashes = set()
        unique_images = []

        for img in images:
            img_hash = self._compute_image_hash(img)
            if img_hash not in seen_hashes:
                seen_hashes.add(img_hash)
                unique_images.append(img)
            else:
                logger.debug("Filtered duplicate image: %s", img.filename)

        if len(unique_images) < len(images):
            logger.info("Deduplicated %d images to %d unique", len(images), len(unique_images))

        return unique_images

    def _prepare_ocr_config(self, backend_name: str) -> dict[str, Any]:
        """Prepare OCR configuration for the specified backend.

        Args:
            backend_name: Name of the OCR backend

        Returns:
            Configuration dictionary for the backend
        """
        default_config: TesseractConfig | EasyOCRConfig | PaddleOCRConfig
        config_class: type[TesseractConfig | EasyOCRConfig | PaddleOCRConfig]

        if backend_name == "tesseract":
            default_config = TesseractConfig()
            config_class = TesseractConfig
        elif backend_name == "easyocr":
            default_config = EasyOCRConfig()
            config_class = EasyOCRConfig
        elif backend_name == "paddleocr":
            default_config = PaddleOCRConfig()
            config_class = PaddleOCRConfig
        else:
            raise ValueError(f"Unknown OCR backend: {backend_name}")

        cfg: dict[str, Any] = asdict(default_config)

        # Update with user config if compatible
        if self.config.ocr_config and isinstance(self.config.ocr_config, config_class):
            user_cfg: dict[str, Any] = asdict(self.config.ocr_config)
            cfg.update(user_cfg)

        cfg["use_cache"] = self.config.use_cache
        return cfg

    def _validate_image_for_ocr(self, img: ExtractedImage) -> str | None:
        """Validate if an image is suitable for OCR processing.

        Args:
            img: Image to validate

        Returns:
            Reason for skipping if invalid, None if valid
        """
        # Check format
        fmt = img.format.lower()
        if fmt not in self.config.image_ocr_formats:
            return f"Unsupported format: {img.format}"

        # Check dimensions if available
        if img.dimensions is not None:
            w, h = img.dimensions
            min_w, min_h = self.config.image_ocr_min_dimensions
            max_w, max_h = self.config.image_ocr_max_dimensions

            if w < min_w or h < min_h:
                return f"Too small: {w}x{h}"
            if w > max_w or h > max_h:
                return f"Too large: {w}x{h}"

        return None

    async def _ocr_single_image(self, target: ExtractedImage, backend: Any, cfg: dict[str, Any]) -> ImageOCRResult:
        """Process a single image with OCR.

        Args:
            target: Image to process
            backend: OCR backend instance
            cfg: Configuration for the backend

        Returns:
            OCR result for the image
        """
        try:
            start = time.time()
            pil_img = Image.open(io.BytesIO(target.data))
            ocr_res = await backend.process_image(pil_img, **cfg)
            duration = time.time() - start
            return ImageOCRResult(
                image=target,
                ocr_result=ocr_res,
                confidence_score=None,
                processing_time=duration,
            )
        except (OSError, ValueError) as e:  # pragma: no cover
            # Image decoding or OCR processing errors
            return ImageOCRResult(
                image=target,
                ocr_result=ExtractionResult(content="", mime_type="text/plain", metadata={}),
                skipped_reason=f"OCR failed: {type(e).__name__}: {e}",
            )
        except (RuntimeError, TypeError) as e:  # pragma: no cover
            # OCR backend errors
            return ImageOCRResult(
                image=target,
                ocr_result=ExtractionResult(content="", mime_type="text/plain", metadata={}),
                skipped_reason=f"Backend error: {type(e).__name__}: {e}",
            )

    async def _process_images_with_ocr(self, images: list[ExtractedImage]) -> list[ImageOCRResult]:
        """Process multiple images with OCR.

        Args:
            images: List of images to process

        Returns:
            List of OCR results
        """
        if not images or not self.config.ocr_extracted_images:
            return []

        # Preprocess images
        images = self._deduplicate_images(images)
        images = self._check_image_memory_limits(images)

        # Get backend
        backend_name = self.config.image_ocr_backend or self.config.ocr_backend
        if backend_name is None:
            return []

        # Prepare configuration and backend
        cfg = self._prepare_ocr_config(backend_name)
        backend = get_ocr_backend(backend_name)

        results: list[ImageOCRResult] = []
        tasks = []

        # Validate and prepare tasks
        for img in images:
            skip_reason = self._validate_image_for_ocr(img)
            if skip_reason:
                results.append(
                    ImageOCRResult(
                        image=img,
                        ocr_result=ExtractionResult(content="", mime_type="text/plain", metadata={}),
                        skipped_reason=skip_reason,
                    )
                )
            else:
                tasks.append(self._ocr_single_image(img, backend, cfg))

        # Process valid images in batches
        if tasks:
            batch_size = max(1, min(len(tasks), cpu_count()))
            results.extend(await run_taskgroup_batched(*tasks, batch_size=batch_size))

        return results
