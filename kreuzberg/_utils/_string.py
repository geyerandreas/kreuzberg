from __future__ import annotations

import re
from contextlib import suppress

import chardetng_py

# Compile regex patterns once at module level for performance
_WHITESPACE_PATTERN = re.compile(r"[ \t\f\v\r]+")
_NEWLINES_PATTERN = re.compile(r"\n+")


def safe_decode(byte_data: bytes, encoding: str | None = None) -> str:
    """Decode a byte string safely, removing invalid sequences.

    Args:
        byte_data: The byte string to decode.
        encoding: The encoding to use when decoding the byte string.

    Returns:
        The decoded string.
    """
    if not byte_data:
        return ""

    # Try provided encoding first (fastest path)
    if encoding:
        with suppress(UnicodeDecodeError, LookupError):
            return byte_data.decode(encoding)

    # Use chardetng for better performance than charset-normalizer
    detected_encoding = chardetng_py.detect(byte_data)
    if detected_encoding:
        with suppress(UnicodeDecodeError, LookupError):
            return byte_data.decode(detected_encoding)

    # Fast fallback to UTF-8
    with suppress(UnicodeDecodeError):
        return byte_data.decode("utf-8")

    # Final fallback
    return byte_data.decode("latin-1", errors="replace")


def normalize_spaces(text: str) -> str:
    """Normalize spaces while preserving line breaks and paragraph structure.

    Args:
        text: The text to normalize.

    Returns:
        The normalized text with proper spacing.
    """
    if not text or not text.strip():
        return ""

    # Split by double newlines to preserve paragraph breaks
    paragraphs = text.split("\n\n")
    normalized_paragraphs = []

    for paragraph in paragraphs:
        # Use pre-compiled patterns for better performance
        # Replace multiple whitespace (except newlines) with single space
        cleaned = _WHITESPACE_PATTERN.sub(" ", paragraph)
        # Clean up multiple newlines within paragraph (keep single newlines)
        cleaned = _NEWLINES_PATTERN.sub("\n", cleaned)

        # Strip and filter empty lines efficiently
        lines = [line.strip() for line in cleaned.split("\n") if line.strip()]

        if lines:
            normalized_paragraphs.append("\n".join(lines))

    return "\n\n".join(normalized_paragraphs)
