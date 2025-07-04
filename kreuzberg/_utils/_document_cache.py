"""Document-level caching to prevent pypdfium2 issues with duplicate processing."""

from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kreuzberg._types import ExtractionConfig, ExtractionResult


class DocumentCache:
    """Session-scoped cache for document extraction results.

    Ensures each unique document is processed only once per session,
    preventing pypdfium2 state corruption issues with repeated processing.
    """

    def __init__(self) -> None:
        """Initialize document cache."""
        self._cache: dict[str, ExtractionResult] = {}
        self._processing: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

        self._file_metadata: dict[str, dict[str, Any]] = {}

    def _get_cache_key(self, file_path: Path | str, config: ExtractionConfig | None = None) -> str:
        """Generate cache key for a file and config combination.

        Args:
            file_path: Path to the file
            config: Extraction configuration

        Returns:
            Unique cache key string
        """
        path = Path(file_path).resolve()

        try:
            stat = path.stat()
            file_info = {
                "path": str(path),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            }
        except OSError:
            file_info = {"path": str(path), "size": 0, "mtime": 0}

        config_info = {}
        if config:
            config_info = {
                "force_ocr": config.force_ocr,
                "ocr_backend": config.ocr_backend,
                "extract_tables": config.extract_tables,
                "chunk_content": config.chunk_content,
                "max_chars": config.max_chars,
                "max_overlap": config.max_overlap,
            }

        cache_data = {**file_info, **config_info}
        cache_str = str(sorted(cache_data.items()))

        return hashlib.sha256(cache_str.encode()).hexdigest()[:16]

    def _is_cache_valid(self, cache_key: str, file_path: Path | str) -> bool:
        """Check if cached result is still valid.

        Args:
            cache_key: The cache key to validate
            file_path: Path to the file

        Returns:
            True if cache is valid, False if invalidated
        """
        if cache_key not in self._file_metadata:
            return False

        path = Path(file_path)
        try:
            current_stat = path.stat()
            cached_metadata = self._file_metadata[cache_key]

            return bool(
                cached_metadata["size"] == current_stat.st_size and cached_metadata["mtime"] == current_stat.st_mtime
            )
        except OSError:
            return False

    def get(self, file_path: Path | str, config: ExtractionConfig | None = None) -> ExtractionResult | None:
        """Get cached extraction result if available and valid.

        Args:
            file_path: Path to the file
            config: Extraction configuration

        Returns:
            Cached result if available, None otherwise
        """
        cache_key = self._get_cache_key(file_path, config)

        with self._lock:
            if cache_key in self._cache:
                if self._is_cache_valid(cache_key, file_path):
                    return self._cache[cache_key]

                self._cache.pop(cache_key, None)
                self._file_metadata.pop(cache_key, None)

        return None

    def set(self, file_path: Path | str, config: ExtractionConfig | None, result: ExtractionResult) -> None:
        """Cache extraction result.

        Args:
            file_path: Path to the file
            config: Extraction configuration
            result: Extraction result to cache
        """
        cache_key = self._get_cache_key(file_path, config)
        path = Path(file_path)

        try:
            stat = path.stat()
            file_metadata = {
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "cached_at": time.time(),
            }
        except OSError:
            file_metadata = {
                "size": 0,
                "mtime": 0,
                "cached_at": time.time(),
            }

        with self._lock:
            self._cache[cache_key] = result
            self._file_metadata[cache_key] = file_metadata

    def is_processing(self, file_path: Path | str, config: ExtractionConfig | None = None) -> bool:
        """Check if file is currently being processed.

        Args:
            file_path: Path to the file
            config: Extraction configuration

        Returns:
            True if file is currently being processed
        """
        cache_key = self._get_cache_key(file_path, config)
        with self._lock:
            return cache_key in self._processing

    def mark_processing(self, file_path: Path | str, config: ExtractionConfig | None = None) -> threading.Event:
        """Mark file as being processed and return event to wait on.

        Args:
            file_path: Path to the file
            config: Extraction configuration

        Returns:
            Event that will be set when processing completes
        """
        cache_key = self._get_cache_key(file_path, config)

        with self._lock:
            if cache_key not in self._processing:
                self._processing[cache_key] = threading.Event()
            return self._processing[cache_key]

    def mark_complete(self, file_path: Path | str, config: ExtractionConfig | None = None) -> None:
        """Mark file processing as complete.

        Args:
            file_path: Path to the file
            config: Extraction configuration
        """
        cache_key = self._get_cache_key(file_path, config)

        with self._lock:
            if cache_key in self._processing:
                event = self._processing.pop(cache_key)
                event.set()

    def clear(self) -> None:
        """Clear all cached results."""
        with self._lock:
            self._cache.clear()
            self._file_metadata.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            return {
                "cached_documents": len(self._cache),
                "processing_documents": len(self._processing),
                "total_cache_size_mb": sum(len(result.content.encode("utf-8")) for result in self._cache.values())
                / 1024
                / 1024,
            }


_document_cache = DocumentCache()


def get_document_cache() -> DocumentCache:
    """Get the global document cache instance."""
    return _document_cache


def clear_document_cache() -> None:
    """Clear the global document cache."""
    _document_cache.clear()
