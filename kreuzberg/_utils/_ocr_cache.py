"""Shared utilities for OCR backend caching.

This module provides common caching functionality that can be used by all OCR backends
(Tesseract, EasyOCR, PaddleOCR) to ensure consistent behavior and eliminate code duplication.
"""

from __future__ import annotations

import hashlib
import io
from typing import TYPE_CHECKING, Any

import anyio

from kreuzberg._utils._cache import get_ocr_cache

if TYPE_CHECKING:
    from pathlib import Path

    from PIL.Image import Image as PILImage

    from kreuzberg._types import ExtractionResult


def get_file_info(path: Path) -> dict[str, Any]:
    """Get file information for caching.

    Args:
        path: Path to the file

    Returns:
        Dictionary with file path, size, and modification time
    """
    from pathlib import Path as PathType  # noqa: PLC0415

    path_obj = PathType(path) if not isinstance(path, PathType) else path

    try:
        stat = path_obj.stat()
        return {
            "path": str(path_obj.resolve()),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }
    except OSError:
        return {
            "path": str(path_obj),
            "size": 0,
            "mtime": 0,
        }


def generate_image_hash(image: PILImage) -> str:
    """Generate consistent hash for image content.

    Args:
        image: PIL Image object

    Returns:
        SHA256 hash of image content (truncated to 16 chars)
    """
    save_image = image
    if image.mode not in ("RGB", "RGBA", "L", "LA", "P", "1"):
        save_image = image.convert("RGB")

    image_buffer = io.BytesIO()
    save_image.save(image_buffer, format="PNG")
    image_content = image_buffer.getvalue()

    return hashlib.sha256(image_content).hexdigest()[:16]


def build_cache_kwargs(
    backend_name: str,
    config_dict: dict[str, Any],
    image_hash: str | None = None,
    file_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build cache kwargs for OCR operation.

    Args:
        backend_name: Name of the OCR backend (tesseract, easyocr, paddleocr)
        config_dict: Configuration parameters for the OCR operation
        image_hash: Hash of image content (for image processing)
        file_info: File information dictionary (for file processing)

    Returns:
        Dictionary of cache kwargs suitable for KreuzbergCache operations
    """
    cache_kwargs = {
        "ocr_backend": backend_name,
        "ocr_config": str(sorted(config_dict.items())),
    }

    if image_hash:
        cache_kwargs["image_hash"] = image_hash
    if file_info:
        cache_kwargs["file_info"] = str(sorted(file_info.items()))

    return cache_kwargs


async def handle_cache_lookup_async(cache_kwargs: dict[str, Any]) -> ExtractionResult | None:
    """Handle cache lookup before processing (async).

    This function implements the complete cache lookup flow including:
    - Check for existing cached result
    - Handle concurrent processing (wait if another process is working on same operation)
    - Mark current operation as processing if no cache hit

    Args:
        cache_kwargs: Cache key parameters

    Returns:
        Cached ExtractionResult if found, None if cache miss or processing should continue
    """
    ocr_cache = get_ocr_cache()

    cached_result = await ocr_cache.aget(**cache_kwargs)
    if cached_result is not None:
        return cached_result

    if ocr_cache.is_processing(**cache_kwargs):
        event = ocr_cache.mark_processing(**cache_kwargs)
        await anyio.to_thread.run_sync(event.wait)

        cached_result = await ocr_cache.aget(**cache_kwargs)
        if cached_result is not None:
            return cached_result

    ocr_cache.mark_processing(**cache_kwargs)
    return None


def handle_cache_lookup_sync(cache_kwargs: dict[str, Any]) -> ExtractionResult | None:
    """Handle cache lookup before processing (sync).

    Sync version of handle_cache_lookup_async with identical logic.

    Args:
        cache_kwargs: Cache key parameters

    Returns:
        Cached ExtractionResult if found, None if cache miss or processing should continue
    """
    ocr_cache = get_ocr_cache()

    cached_result = ocr_cache.get(**cache_kwargs)
    if cached_result is not None:
        return cached_result

    if ocr_cache.is_processing(**cache_kwargs):
        event = ocr_cache.mark_processing(**cache_kwargs)
        event.wait()

        cached_result = ocr_cache.get(**cache_kwargs)
        if cached_result is not None:
            return cached_result

    ocr_cache.mark_processing(**cache_kwargs)
    return None


async def cache_and_complete_async(
    result: ExtractionResult,
    cache_kwargs: dict[str, Any],
    use_cache: bool,
) -> None:
    """Cache result and mark processing complete (async).

    Args:
        result: The OCR result to cache
        cache_kwargs: Cache key parameters
        use_cache: Whether caching is enabled
    """
    ocr_cache = get_ocr_cache()

    if use_cache:
        await ocr_cache.aset(result, **cache_kwargs)

    ocr_cache.mark_complete(**cache_kwargs)


def cache_and_complete_sync(
    result: ExtractionResult,
    cache_kwargs: dict[str, Any],
    use_cache: bool,
) -> None:
    """Cache result and mark processing complete (sync).

    Args:
        result: The OCR result to cache
        cache_kwargs: Cache key parameters
        use_cache: Whether caching is enabled
    """
    ocr_cache = get_ocr_cache()

    if use_cache:
        ocr_cache.set(result, **cache_kwargs)

    ocr_cache.mark_complete(**cache_kwargs)


def mark_processing_complete(cache_kwargs: dict[str, Any]) -> None:
    """Mark processing as complete without caching (for error cases).

    This is useful when an error occurs during processing and we need to
    release any waiting processes without caching a result.

    Args:
        cache_kwargs: Cache key parameters
    """
    ocr_cache = get_ocr_cache()
    ocr_cache.mark_complete(**cache_kwargs)
