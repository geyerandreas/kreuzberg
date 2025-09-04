from __future__ import annotations

from functools import partial
from inspect import isawaitable, iscoroutinefunction
from typing import TYPE_CHECKING, Any, TypeVar, cast

import anyio
from anyio import create_task_group
from anyio.to_thread import run_sync as any_io_run_sync

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Awaitable, Callable

from typing import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")


async def run_sync(sync_fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    if kwargs:
        handler = partial(sync_fn, **kwargs)
        return cast("T", await any_io_run_sync(handler, *args, abandon_on_cancel=True))  # pyright: ignore [reportCallIssue]
    return cast("T", await any_io_run_sync(sync_fn, *args, abandon_on_cancel=True))  # pyright: ignore [reportCallIssue]


async def run_taskgroup(*async_tasks: Awaitable[Any]) -> list[Any]:
    results: list[Any] = [None] * len(async_tasks)

    async def run_task(index: int, task: Awaitable[T]) -> None:
        results[index] = await task

    async with create_task_group() as tg:
        for i, t in enumerate(async_tasks):
            tg.start_soon(run_task, i, t)

    return results


async def run_taskgroup_batched(*async_tasks: Awaitable[Any], batch_size: int) -> list[Any]:
    results: list[Any] = []

    for i in range(0, len(async_tasks), batch_size):
        batch = async_tasks[i : i + batch_size]
        results.extend(await run_taskgroup(*batch))

    return results


async def run_maybe_sync(fn: Callable[P, T | Awaitable[T]], *args: P.args, **kwargs: P.kwargs) -> T:
    result = fn(*args, **kwargs)
    if isawaitable(result):
        return cast("T", await result)
    return result


def run_maybe_async(fn: Callable[P, T | Awaitable[T]], *args: P.args, **kwargs: P.kwargs) -> T:
    return cast("T", fn(*args, **kwargs) if not iscoroutinefunction(fn) else anyio.run(partial(fn, **kwargs), *args))


def run_sync_only(fn: Callable[P, T | Awaitable[T]], *args: P.args, **kwargs: P.kwargs) -> T:
    if iscoroutinefunction(fn):
        raise RuntimeError(f"Cannot run async function {fn.__name__} in sync-only context")
    return cast("T", fn(*args, **kwargs))
