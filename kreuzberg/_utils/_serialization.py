"""Fast serialization utilities using msgspec."""

from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any, TypeVar, cast

import msgspec
from msgspec import MsgspecError
from msgspec.msgpack import decode, encode

T = TypeVar("T")


_DICT_METHOD_NAMES = (
    "to_dict",
    "as_dict",
    "dict",
    "model_dump",
    "json",
    "to_list",
    "tolist",
)


def encode_hook(obj: Any) -> Any:
    """Custom encoder for complex objects."""
    if callable(obj):
        return None

    if isinstance(obj, Exception):
        return {"message": str(obj), "type": type(obj).__name__}

    for attr_name in _DICT_METHOD_NAMES:
        method = getattr(obj, attr_name, None)
        if method is not None and callable(method):
            return method()

    if is_dataclass(obj) and not isinstance(obj, type):
        return msgspec.to_builtins(obj)

    if hasattr(obj, "save") and hasattr(obj, "format"):
        return None

    raise TypeError(f"Unsupported type: {type(obj)!r}")


def deserialize(value: str | bytes, target_type: type[T]) -> T:
    """Deserialize bytes/string to target type.

    Args:
        value: Serialized data
        target_type: Type to deserialize to

    Returns:
        Deserialized object

    Raises:
        ValueError: If deserialization fails
    """
    try:
        return decode(cast("bytes", value), type=target_type, strict=False)
    except MsgspecError as e:
        raise ValueError(f"Failed to deserialize to {target_type.__name__}: {e}") from e


def serialize(value: Any, **kwargs: Any) -> bytes:
    """Serialize value to bytes.

    Args:
        value: Object to serialize
        **kwargs: Additional data to merge with value if it's a dict

    Returns:
        Serialized bytes

    Raises:
        ValueError: If serialization fails
    """
    if isinstance(value, dict) and kwargs:
        value = value | kwargs

    try:
        return encode(value, enc_hook=encode_hook)
    except (MsgspecError, TypeError) as e:
        raise ValueError(f"Failed to serialize {type(value).__name__}: {e}") from e
