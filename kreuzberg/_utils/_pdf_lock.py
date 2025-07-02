"""PDF processing lock utilities for thread-safe pypdfium2 operations."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

# Global lock for pypdfium2 operations to prevent segfaults on macOS
_PYPDFIUM_LOCK = threading.RLock()


@contextmanager
def pypdfium_lock() -> Generator[None, None, None]:
    """Context manager for thread-safe pypdfium2 operations.

    This prevents segmentation faults on macOS where pypdfium2
    is not fork-safe when used concurrently.
    """
    with _PYPDFIUM_LOCK:
        yield


def with_pypdfium_lock(func: Any) -> Any:
    """Decorator to wrap functions with pypdfium2 lock."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with pypdfium_lock():
            return func(*args, **kwargs)

    return wrapper
