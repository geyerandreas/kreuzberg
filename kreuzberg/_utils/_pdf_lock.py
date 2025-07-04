"""PDF processing lock utilities for thread-safe pypdfium2 operations."""

from __future__ import annotations

import hashlib
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any
from weakref import WeakValueDictionary

if TYPE_CHECKING:
    from collections.abc import Generator


_PYPDFIUM_LOCK = threading.RLock()


_FILE_LOCKS_CACHE = WeakValueDictionary[str, threading.RLock]()
_FILE_LOCKS_LOCK = threading.Lock()


def _get_file_key(file_path: Path | str) -> str:
    """Get a consistent key for a file path."""
    path_str = str(Path(file_path).resolve())
    return hashlib.md5(path_str.encode()).hexdigest()  # noqa: S324


def _get_file_lock(file_path: Path | str) -> threading.RLock:
    """Get or create a lock for a specific file."""
    file_key = _get_file_key(file_path)

    with _FILE_LOCKS_LOCK:
        if file_key in _FILE_LOCKS_CACHE:
            return _FILE_LOCKS_CACHE[file_key]

        lock = threading.RLock()
        _FILE_LOCKS_CACHE[file_key] = lock
        return lock


@contextmanager
def pypdfium_lock() -> Generator[None, None, None]:
    """Context manager for thread-safe pypdfium2 operations.

    This prevents segmentation faults on macOS where pypdfium2
    is not fork-safe when used concurrently.
    """
    with _PYPDFIUM_LOCK:
        yield


@contextmanager
def pypdfium_file_lock(file_path: Path | str) -> Generator[None, None, None]:
    """Context manager for per-file pypdfium2 operations.

    This allows concurrent processing of different files while
    preventing segfaults. Document caching handles same-file issues.
    """
    lock = _get_file_lock(file_path)
    with lock:
        yield


def with_pypdfium_lock(func: Any) -> Any:
    """Decorator to wrap functions with pypdfium2 lock."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with pypdfium_lock():
            return func(*args, **kwargs)

    return wrapper
