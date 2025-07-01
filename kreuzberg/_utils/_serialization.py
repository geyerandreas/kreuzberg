"""Fast serialization utilities using msgspec."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, TypeVar

from msgspec import MsgspecError
from msgspec.msgpack import decode, encode

T = TypeVar("T")


def encode_hook(obj: Any) -> Any:
    """Custom encoder for complex objects."""
    if callable(obj):
        return None

    if isinstance(obj, Exception):
        return {"message": str(obj), "type": type(obj).__name__}

    # Handle objects with serialization methods
    for key in (
        "to_dict",
        "as_dict",
        "dict",
        "model_dump",
        "json",
        "to_list",
        "tolist",
    ):
        if hasattr(obj, key) and callable(getattr(obj, key)):
            return getattr(obj, key)()

    # Handle dataclasses
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: v if not isinstance(v, Enum) else v.value for (k, v) in asdict(obj).items()}

    # Handle PIL Images (skip them)
    if hasattr(obj, "save") and hasattr(obj, "format"):
        return None

    # Handle pandas DataFrames
    if hasattr(obj, "to_dict"):
        try:
            return {"__dataframe__": obj.to_dict()}
        except Exception:
            pass

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
        return decode(value, type=target_type, strict=False)
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
        # Merge additional data
        value = value | kwargs

    try:
        return encode(value, enc_hook=encode_hook)
    except MsgspecError as e:
        raise ValueError(f"Failed to serialize {type(value).__name__}: {e}") from e


def serialize_to_str(value: Any, **kwargs: Any) -> str:
    """Serialize value to string.

    Args:
        value: Object to serialize
        **kwargs: Additional data to merge with value if it's a dict

    Returns:
        Serialized string
    """
    return serialize(value, **kwargs).decode("utf-8")


def deserialize_from_str(value: str, target_type: type[T]) -> T:
    """Deserialize string to target type.

    Args:
        value: Serialized string
        target_type: Type to deserialize to

    Returns:
        Deserialized object
    """
    return deserialize(value.encode("utf-8"), target_type)
