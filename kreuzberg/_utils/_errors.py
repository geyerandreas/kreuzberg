"""Enhanced error handling utilities."""

from __future__ import annotations

import platform
import traceback
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import psutil

if TYPE_CHECKING:
    from pathlib import Path


def create_error_context(
    *,
    operation: str,
    file_path: Path | str | None = None,
    error: Exception | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Create comprehensive error context.

    Args:
        operation: The operation being performed (e.g., "extract_file", "convert_pdf_to_images")
        file_path: The file being processed, if applicable
        error: The original exception, if any
        **extra: Additional context fields

    Returns:
        Dictionary with error context including system info
    """
    context: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
    }

    if file_path:
        from pathlib import Path

        path = Path(file_path) if isinstance(file_path, str) else file_path
        context["file"] = {
            "path": str(path),
            "name": path.name,
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else None,
        }

    if error:
        context["error"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exception_only(type(error), error),
        }

    if (
        any(keyword in str(error).lower() for keyword in ["memory", "resource", "process", "thread"])
        if error
        else False
    ):
        try:
            mem = psutil.virtual_memory()
            context["system"] = {
                "memory_available_mb": mem.available / 1024 / 1024,
                "memory_percent": mem.percent,
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "process_count": len(psutil.pids()),
                "platform": platform.platform(),
            }
        except Exception:  # noqa: BLE001
            pass

    context.update(extra)

    return context


def is_transient_error(error: Exception) -> bool:
    """Check if an error is likely transient and worth retrying.

    Args:
        error: The exception to check

    Returns:
        True if the error is likely transient
    """
    transient_types = (
        OSError,
        PermissionError,
        TimeoutError,
        ConnectionError,
        BrokenPipeError,
    )

    if isinstance(error, transient_types):
        return True

    transient_patterns = [
        "temporary",
        "locked",
        "in use",
        "access denied",
        "permission",
        "timeout",
        "connection",
        "network",
        "too many open files",
        "cannot allocate memory",
        "resource temporarily unavailable",
        "broken pipe",
        "subprocess",
        "signal",
    ]

    error_str = str(error).lower()
    return any(pattern in error_str for pattern in transient_patterns)


def is_resource_error(error: Exception) -> bool:
    """Check if an error is related to system resources.

    Args:
        error: The exception to check

    Returns:
        True if the error is resource-related
    """
    resource_patterns = [
        "memory",
        "out of memory",
        "cannot allocate",
        "too many open files",
        "file descriptor",
        "resource",
        "exhausted",
        "limit",
        "cpu",
        "thread",
        "process",
    ]

    error_str = str(error).lower()
    return any(pattern in error_str for pattern in resource_patterns)


def should_retry(error: Exception, attempt: int, max_attempts: int = 3) -> bool:
    """Determine if an operation should be retried.

    Args:
        error: The exception that occurred
        attempt: Current attempt number (1-based)
        max_attempts: Maximum number of attempts

    Returns:
        True if the operation should be retried
    """
    if attempt >= max_attempts:
        return False

    from kreuzberg.exceptions import ValidationError

    if isinstance(error, ValidationError):
        return False

    return is_transient_error(error)


class BatchExtractionResult:
    """Result container for batch operations with partial success support."""

    def __init__(self) -> None:
        """Initialize batch result container."""
        self.successful: list[tuple[int, Any]] = []
        self.failed: list[tuple[int, dict[str, Any]]] = []
        self.total_count: int = 0

    def add_success(self, index: int, result: Any) -> None:
        """Add a successful result."""
        self.successful.append((index, result))

    def add_failure(self, index: int, error: Exception, context: dict[str, Any]) -> None:
        """Add a failed result with context."""
        error_info = {
            "error": {
                "type": type(error).__name__,
                "message": str(error),
            },
            "context": context,
        }
        self.failed.append((index, error_info))

    @property
    def success_count(self) -> int:
        """Number of successful operations."""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Number of failed operations."""
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100

    def get_ordered_results(self) -> list[Any | None]:
        """Get results in original order with None for failures."""
        results = [None] * self.total_count
        for index, result in self.successful:
            results[index] = result
        return results

    def get_summary(self) -> dict[str, Any]:
        """Get summary of batch operation."""
        return {
            "total": self.total_count,
            "successful": self.success_count,
            "failed": self.failure_count,
            "success_rate": f"{self.success_rate:.1f}%",
            "failures": [
                {
                    "index": idx,
                    "error": info["error"]["type"],
                    "message": info["error"]["message"],
                }
                for idx, info in self.failed
            ],
        }
