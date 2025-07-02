"""Process pool manager for resource-aware multiprocessing."""

from __future__ import annotations

import asyncio
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING, Any, Callable, TypeVar

import psutil
from typing_extensions import Self

if TYPE_CHECKING:
    import types

T = TypeVar("T")


class ProcessPoolManager:
    """Resource-aware process pool manager for CPU-intensive tasks."""

    def __init__(
        self,
        max_processes: int | None = None,
        memory_limit_gb: float | None = None,
    ) -> None:
        """Initialize the process pool manager.

        Args:
            max_processes: Maximum number of processes. Defaults to CPU count.
            memory_limit_gb: Memory limit in GB. Defaults to 75% of available memory.
        """
        self.max_processes = max_processes or mp.cpu_count()

        # Set memory limit based on available system memory
        if memory_limit_gb is None:
            available_memory = psutil.virtual_memory().available
            self.memory_limit_bytes = int(available_memory * 0.75)  # Use 75% of available
        else:
            self.memory_limit_bytes = int(memory_limit_gb * 1024**3)

        self._executor: ProcessPoolExecutor | None = None
        self._active_tasks = 0

    def get_optimal_workers(self, task_memory_mb: float = 100) -> int:
        """Calculate optimal number of workers based on memory constraints.

        Args:
            task_memory_mb: Estimated memory usage per task in MB.

        Returns:
            Optimal number of workers.
        """
        task_memory_bytes = task_memory_mb * 1024**2
        memory_based_limit = max(1, int(self.memory_limit_bytes / task_memory_bytes))

        return min(self.max_processes, memory_based_limit)

    def _ensure_executor(self, max_workers: int | None = None) -> ProcessPoolExecutor:
        """Ensure process pool executor is initialized."""
        if self._executor is None or getattr(self._executor, "_max_workers", None) != max_workers:
            if self._executor is not None:
                self._executor.shutdown(wait=False)

            workers = max_workers or self.max_processes
            self._executor = ProcessPoolExecutor(max_workers=workers)

        return self._executor

    async def submit_task(
        self,
        func: Callable[..., T],
        *args: Any,
        task_memory_mb: float = 100,
        **_kwargs: Any,
    ) -> T:
        """Submit a task to the process pool.

        Args:
            func: Function to execute.
            *args: Positional arguments for the function.
            task_memory_mb: Estimated memory usage in MB.
            **kwargs: Keyword arguments for the function.

        Returns:
            Result of the function execution.
        """
        # Calculate optimal workers for this task
        workers = self.get_optimal_workers(task_memory_mb)
        executor = self._ensure_executor(workers)

        # Submit task and await result
        loop = asyncio.get_event_loop()
        self._active_tasks += 1

        try:
            return await loop.run_in_executor(executor, func, *args)
        finally:
            self._active_tasks -= 1

    async def submit_batch(
        self,
        func: Callable[..., T],
        arg_batches: list[tuple[Any, ...]],
        task_memory_mb: float = 100,
        max_concurrent: int | None = None,
    ) -> list[T]:
        """Submit a batch of tasks to the process pool.

        Args:
            func: Function to execute.
            arg_batches: List of argument tuples for each task.
            task_memory_mb: Estimated memory usage per task in MB.
            max_concurrent: Maximum concurrent tasks. Defaults to optimal workers.

        Returns:
            List of results in the same order as input.
        """
        if not arg_batches:
            return []

        # Calculate optimal concurrency
        workers = self.get_optimal_workers(task_memory_mb)
        max_concurrent = max_concurrent or workers

        executor = self._ensure_executor(workers)
        loop = asyncio.get_event_loop()

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def submit_single(args: tuple[Any, ...]) -> T:
            async with semaphore:
                self._active_tasks += 1
                try:
                    return await loop.run_in_executor(executor, func, *args)
                finally:
                    self._active_tasks -= 1

        # Submit all tasks and gather results
        tasks = [submit_single(args) for args in arg_batches]
        return await asyncio.gather(*tasks)

    def get_system_info(self) -> dict[str, Any]:
        """Get current system resource information."""
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)

        return {
            "cpu_count": mp.cpu_count(),
            "cpu_percent": cpu_percent,
            "memory_total": memory.total,
            "memory_available": memory.available,
            "memory_percent": memory.percent,
            "active_tasks": self._active_tasks,
            "max_processes": self.max_processes,
            "memory_limit": self.memory_limit_bytes,
        }

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the process pool."""
        if self._executor is not None:
            self._executor.shutdown(wait=wait)
            self._executor = None

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.shutdown()

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        self.shutdown()
