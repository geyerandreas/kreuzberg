"""Reference container for managing singleton instances without global variables."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar, cast

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


class Ref(Generic[T]):
    """A reference container that manages singleton instances without global variables.

    This provides a clean alternative to global variables by using a registry pattern
    with type safety.
    """

    _instances: ClassVar[dict[str, Any]] = {}

    def __init__(self, name: str, factory: Callable[[], T]) -> None:
        """Initialize a reference container.

        Args:
            name: Unique name for this reference
            factory: Factory function to create the instance when needed
        """
        self.name = name
        self.factory = factory

    def get(self) -> T:
        """Get the singleton instance, creating it if it doesn't exist."""
        if self.name not in self._instances:
            self._instances[self.name] = self.factory()
        return cast("T", self._instances[self.name])

    def clear(self) -> None:
        """Clear the singleton instance."""
        if self.name in self._instances:
            del self._instances[self.name]

    def is_initialized(self) -> bool:
        """Check if the singleton instance exists."""
        return self.name in self._instances

    @classmethod
    def clear_all(cls) -> None:
        """Clear all singleton instances."""
        cls._instances.clear()
