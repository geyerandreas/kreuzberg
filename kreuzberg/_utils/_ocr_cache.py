"""OCR result caching for expensive OCR operations."""

from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kreuzberg._types import ExtractionResult


class OcrCache:
    """File-based cache for OCR results.

    Caches OCR results to disk independently of document extraction,
    allowing reuse across sessions and different extraction configurations.
    """

    def __init__(
        self, cache_dir: Path | str | None = None, max_cache_size_mb: float = 500.0, max_age_days: int = 30
    ) -> None:
        """Initialize OCR cache.

        Args:
            cache_dir: Cache directory (defaults to .kreuzberg/ocr_cache in cwd)
            max_cache_size_mb: Maximum cache size in MB (default: 500MB)
            max_age_days: Maximum age of cached results in days (default: 30 days)
        """
        if cache_dir is None:
            cache_dir = Path.cwd() / ".kreuzberg" / "ocr_cache"

        self.cache_dir = Path(cache_dir)
        self.max_cache_size_mb = max_cache_size_mb
        self.max_age_days = max_age_days

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory tracking of processing state (session-scoped)
        self._processing: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def _get_cache_key(
        self,
        image_path: Path | str | None = None,
        image_content: bytes | None = None,
        ocr_backend: str | None = None,
        ocr_config: Any = None,
    ) -> str:
        """Generate cache key for OCR operation.

        Args:
            image_path: Path to image file (if processing file)
            image_content: Image content bytes (if processing in-memory)
            ocr_backend: OCR backend name
            ocr_config: OCR configuration object

        Returns:
            Unique cache key string
        """
        key_data = {}

        # Image identification
        if image_path:
            path = Path(image_path).resolve()
            try:
                stat = path.stat()
                key_data.update(
                    {
                        "type": "file",
                        "path": str(path),
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                    }
                )
            except OSError:
                key_data.update(
                    {
                        "type": "file",
                        "path": str(path),
                        "size": 0,
                        "mtime": 0,
                    }
                )
        elif image_content:
            # Hash the image content for in-memory images
            content_hash = hashlib.sha256(image_content).hexdigest()[:16]
            key_data.update(
                {
                    "type": "content",
                    "content_hash": content_hash,
                    "size": len(image_content),
                }
            )

        # OCR configuration
        key_data.update(
            {
                "ocr_backend": ocr_backend or "unknown",
                "ocr_config": str(ocr_config) if ocr_config else "default",
            }
        )

        # Create cache key
        cache_str = str(sorted(key_data.items()))
        return hashlib.sha256(cache_str.encode()).hexdigest()[:16]

    def _is_cache_valid(self, cache_key: str, image_path: Path | str | None = None) -> bool:
        """Check if cached OCR result is still valid.

        Args:
            cache_key: The cache key to validate
            image_path: Path to the image file (if applicable)

        Returns:
            True if cache is valid, False if invalidated
        """
        if cache_key not in self._image_metadata:
            return False

        # For file-based images, check if file has changed
        if image_path:
            path = Path(image_path)
            try:
                current_stat = path.stat()
                cached_metadata = self._image_metadata[cache_key]

                return (
                    cached_metadata.get("size") == current_stat.st_size
                    and cached_metadata.get("mtime") == current_stat.st_mtime
                )
            except OSError:
                return False

        # For content-based images, cache is always valid (content doesn't change)
        return True

    def get(
        self,
        image_path: Path | str | None = None,
        image_content: bytes | None = None,
        ocr_backend: str | None = None,
        ocr_config: Any = None,
    ) -> ExtractionResult | None:
        """Get cached OCR result if available and valid.

        Args:
            image_path: Path to image file
            image_content: Image content bytes
            ocr_backend: OCR backend name
            ocr_config: OCR configuration

        Returns:
            Cached OCR result if available, None otherwise
        """
        cache_key = self._get_cache_key(image_path, image_content, ocr_backend, ocr_config)

        with self._lock:
            if cache_key in self._cache:
                if self._is_cache_valid(cache_key, image_path):
                    return self._cache[cache_key]
                # Cache invalidated - remove stale entry
                self._cache.pop(cache_key, None)
                self._image_metadata.pop(cache_key, None)

        return None

    def set(
        self,
        result: ExtractionResult,
        image_path: Path | str | None = None,
        image_content: bytes | None = None,
        ocr_backend: str | None = None,
        ocr_config: Any = None,
    ) -> None:
        """Cache OCR result.

        Args:
            result: OCR result to cache
            image_path: Path to image file
            image_content: Image content bytes
            ocr_backend: OCR backend name
            ocr_config: OCR configuration
        """
        cache_key = self._get_cache_key(image_path, image_content, ocr_backend, ocr_config)

        # Store metadata for validation
        metadata = {"cached_at": time.time()}

        if image_path:
            path = Path(image_path)
            try:
                stat = path.stat()
                metadata.update(
                    {
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                    }
                )
            except OSError:
                metadata.update({"size": 0, "mtime": 0})
        elif image_content:
            metadata.update({"content_size": len(image_content)})

        with self._lock:
            self._cache[cache_key] = result
            self._image_metadata[cache_key] = metadata

    def is_processing(
        self,
        image_path: Path | str | None = None,
        image_content: bytes | None = None,
        ocr_backend: str | None = None,
        ocr_config: Any = None,
    ) -> bool:
        """Check if OCR is currently being processed for this image.

        Args:
            image_path: Path to image file
            image_content: Image content bytes
            ocr_backend: OCR backend name
            ocr_config: OCR configuration

        Returns:
            True if OCR is currently being processed
        """
        cache_key = self._get_cache_key(image_path, image_content, ocr_backend, ocr_config)
        with self._lock:
            return cache_key in self._processing

    def mark_processing(
        self,
        image_path: Path | str | None = None,
        image_content: bytes | None = None,
        ocr_backend: str | None = None,
        ocr_config: Any = None,
    ) -> threading.Event:
        """Mark OCR as being processed and return event to wait on.

        Args:
            image_path: Path to image file
            image_content: Image content bytes
            ocr_backend: OCR backend name
            ocr_config: OCR configuration

        Returns:
            Event that will be set when processing completes
        """
        cache_key = self._get_cache_key(image_path, image_content, ocr_backend, ocr_config)

        with self._lock:
            if cache_key not in self._processing:
                self._processing[cache_key] = threading.Event()
            return self._processing[cache_key]

    def mark_complete(
        self,
        image_path: Path | str | None = None,
        image_content: bytes | None = None,
        ocr_backend: str | None = None,
        ocr_config: Any = None,
    ) -> None:
        """Mark OCR processing as complete.

        Args:
            image_path: Path to image file
            image_content: Image content bytes
            ocr_backend: OCR backend name
            ocr_config: OCR configuration
        """
        cache_key = self._get_cache_key(image_path, image_content, ocr_backend, ocr_config)

        with self._lock:
            if cache_key in self._processing:
                event = self._processing.pop(cache_key)
                event.set()

    def clear(self) -> None:
        """Clear all cached OCR results."""
        with self._lock:
            self._cache.clear()
            self._image_metadata.clear()
            # Don't clear processing events as they might be waited on

    def get_stats(self) -> dict[str, Any]:
        """Get OCR cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_content_size = sum(
                len(result.content.encode("utf-8")) if hasattr(result, "content") else 0
                for result in self._cache.values()
            )

            return {
                "cached_ocr_results": len(self._cache),
                "processing_ocr_results": len(self._processing),
                "total_cache_size_mb": total_content_size / 1024 / 1024,
                "avg_result_size_kb": (total_content_size / len(self._cache) / 1024) if self._cache else 0,
            }


# Global session OCR cache instance
_ocr_cache = OcrCache()


def get_ocr_cache() -> OcrCache:
    """Get the global OCR cache instance."""
    return _ocr_cache


def clear_ocr_cache() -> None:
    """Clear the global OCR cache."""
    _ocr_cache.clear()
