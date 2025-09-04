from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from anyio import Path as AsyncPath

from kreuzberg._utils._sync import run_sync

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Coroutine


async def create_temp_file(
    extension: str, content: bytes | None = None
) -> tuple[Path, Callable[[], Coroutine[None, None, None]]]:
    file = await run_sync(NamedTemporaryFile, suffix=extension, delete=False)
    if content:
        await AsyncPath(file.name).write_bytes(content)
    await run_sync(file.close)

    async def unlink() -> None:
        with suppress(OSError, PermissionError):
            await AsyncPath(file.name).unlink(missing_ok=True)

    return Path(file.name), unlink
