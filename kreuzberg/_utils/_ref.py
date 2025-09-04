from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


class Ref(Generic[T]):
    _instances: ClassVar[dict[str, Any]] = {}

    def __init__(self, name: str, factory: Callable[[], T]) -> None:
        self.name = name
        self.factory = factory

    def get(self) -> T:
        if self.name not in self._instances:
            self._instances[self.name] = self.factory()
        return cast("T", self._instances[self.name])

    def clear(self) -> None:
        if self.name in self._instances:
            del self._instances[self.name]

    def is_initialized(self) -> bool:
        return self.name in self._instances

    @classmethod
    def clear_all(cls) -> None:
        cls._instances.clear()
