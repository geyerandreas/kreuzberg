from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING, TypedDict

from kreuzberg._token_reduction._stopwords import get_default_stopwords_manager
from kreuzberg.exceptions import ValidationError

if TYPE_CHECKING:
    from kreuzberg._types import TokenReductionConfig


class ReductionStats(TypedDict):
    """Statistics about token reduction operation."""

    character_reduction_ratio: float
    token_reduction_ratio: float
    original_characters: int
    reduced_characters: int
    original_tokens: int
    reduced_tokens: int


# Pre-compiled regex patterns for performance
HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.DOTALL)
REPEATED_PUNCTUATION_PATTERNS = (
    re.compile(r"([!?.]){2,}"),
    re.compile(r"(,){2,}"),
)
EXCESSIVE_NEWLINES_PATTERN = re.compile(r"\n{3,}")
WHITESPACE_PATTERN = re.compile(r"[ \t]+")
MARKDOWN_LIST_PATTERNS = (
    re.compile(r"^\s*[-*+]\s"),  # Bullet lists
    re.compile(r"^\s*\d+\.\s"),  # Numbered lists
)
WORD_CLEAN_PATTERN = re.compile(r"[^\w]")
LANGUAGE_CODE_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")

# Size limits
MAX_TEXT_LENGTH = 10_000_000  # 10MB approximate limit


def _normalize_newlines(text: str) -> str:
    """Remove excessive newlines, keeping at most double newlines."""
    return EXCESSIVE_NEWLINES_PATTERN.sub("\n\n", text)


def _is_markdown_structural_line(line: str, in_code_block: bool) -> bool:
    """Check if a line contains markdown structural elements that should be preserved."""
    if in_code_block:
        return True

    stripped = line.strip()

    # Check for headers
    if stripped.startswith("#"):
        return True

    # Check for tables (must have at least 2 pipes and look like a table)
    if "|" in line:
        pipe_count = line.count("|")
        # Table rows typically have at least 2 pipes (for 2+ columns)
        # and often start/end with pipes or have consistent spacing
        if pipe_count >= 2 and (line.strip().startswith("|") or line.strip().endswith("|") or " | " in line):
            return True

    # Check for lists
    return (
        MARKDOWN_LIST_PATTERNS[0].match(line) is not None  # Bullet lists
        or MARKDOWN_LIST_PATTERNS[1].match(line) is not None  # Numbered lists
    )


@lru_cache(maxsize=64)
def _get_stopwords_with_custom(language: str, custom_words_tuple: tuple[str, ...] | None = None) -> set[str]:
    """Get stopwords for a language, optionally with custom additions.

    The caching happens in _load_language_stopwords, so we don't double-cache here.
    """
    manager = get_default_stopwords_manager()
    base_stopwords = manager.get_stopwords(language)

    if custom_words_tuple:
        return base_stopwords | set(custom_words_tuple)
    return base_stopwords


def reduce_tokens(
    text: str,
    *,
    config: TokenReductionConfig,
    language: str | None = None,
) -> str:
    """Reduce tokens in text based on the specified configuration.

    Args:
        text: The text to reduce.
        config: Configuration for token reduction.
        language: Optional language code for stopword selection.

    Returns:
        The reduced text.

    Raises:
        ValidationError: If inputs are invalid.
    """
    # Validate inputs
    if config is None:
        raise ValidationError("Config cannot be None")

    if text is None:
        raise ValidationError("Text cannot be None")

    if not isinstance(text, str):
        raise ValidationError(f"Text must be a string, got {type(text).__name__}")

    if language is not None and not isinstance(language, str):
        raise ValidationError(f"Language must be a string or None, got {type(language).__name__}")

    if language is not None and len(language.strip()) == 0:
        raise ValidationError("Language cannot be empty or whitespace-only")

    # Early return for off mode
    if config.mode == "off":
        return text

    # Check text size before processing (memory protection)
    if len(text) > MAX_TEXT_LENGTH:
        raise ValidationError(f"Text too large: {len(text)} characters (max {MAX_TEXT_LENGTH:,})")

    # Validate language code format if provided
    if language and not LANGUAGE_CODE_PATTERN.match(language):
        raise ValidationError(f"Invalid language code format: {language}")

    # Handle empty text
    if not text or not text.strip():
        return ""

    # Apply reduction based on mode
    if config.mode == "light":
        return _apply_light_reduction(text, preserve_markdown=config.preserve_markdown)

    if config.mode == "moderate":
        return _apply_moderate_reduction(
            text,
            config=config,
            language=language,
        )

    # Should never reach here due to typing, but for safety
    return text


def _apply_light_reduction(text: str, *, preserve_markdown: bool) -> str:
    """Apply light reduction (formatting only)."""
    if preserve_markdown:
        return _apply_light_reduction_markdown_aware(text)
    return _apply_light_reduction_plain(text)


def _apply_light_reduction_plain(text: str) -> str:
    """Apply light reduction to plain text."""
    # Remove HTML comments
    text = HTML_COMMENT_PATTERN.sub("", text)

    # Compress repeated punctuation
    text = REPEATED_PUNCTUATION_PATTERNS[0].sub(r"\1", text)
    text = REPEATED_PUNCTUATION_PATTERNS[1].sub(r"\1", text)

    # Normalize whitespace
    text = EXCESSIVE_NEWLINES_PATTERN.sub("\n\n", text)
    text = WHITESPACE_PATTERN.sub(" ", text)

    return text.strip()


def _apply_light_reduction_markdown_aware(text: str) -> str:
    """Apply light reduction preserving markdown structure."""
    lines = text.split("\n")
    processed_lines = []
    in_code_block = False

    for line in lines:
        # Track code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            processed_lines.append(line)
            continue

        # Preserve markdown structural elements
        if _is_markdown_structural_line(line, in_code_block):
            processed_lines.append(line)
            continue

        # Apply light reduction to prose lines
        if line.strip():
            reduced = _apply_light_reduction_plain(line)
            processed_lines.append(reduced)
        else:
            processed_lines.append(line)

    # Remove excessive empty lines and return
    result = "\n".join(processed_lines)
    return _normalize_newlines(result).strip()


def _apply_moderate_reduction(
    text: str,
    *,
    config: TokenReductionConfig,
    language: str | None = None,
) -> str:
    """Apply moderate reduction (formatting + stopwords)."""
    # First apply light reduction
    text = _apply_light_reduction(text, preserve_markdown=config.preserve_markdown)

    # Determine language for stopword removal
    lang = language or config.language_hint or "en"

    # Check if language is supported
    manager = get_default_stopwords_manager()
    if not manager.has_language(lang):
        # Fallback to English if language not supported
        lang = "en"

    if not manager.has_language(lang):
        # No stopwords available, return light reduction only
        return text

    # Get stopwords (with custom if provided)
    custom_words_tuple = None
    if config.custom_stopwords and lang in config.custom_stopwords:
        custom_words_tuple = tuple(sorted(config.custom_stopwords[lang]))

    stopwords = _get_stopwords_with_custom(lang, custom_words_tuple)

    # Apply stopword reduction
    if config.preserve_markdown:
        return _apply_stopword_reduction_markdown_aware(text, stopwords=stopwords)
    return _apply_stopword_reduction_plain(text, stopwords=stopwords)


def _apply_stopword_reduction_plain(text: str, *, stopwords: set[str]) -> str:
    """Apply stopword reduction to plain text."""
    words = text.split()
    filtered_words = []

    for word in words:
        # Clean word for stopword checking
        clean_word = WORD_CLEAN_PATTERN.sub("", word.lower())

        # Skip empty cleaned words
        if not clean_word:
            filtered_words.append(word)
            continue

        # Check if word should be kept
        should_keep = (
            clean_word not in stopwords  # Not a stopword
            or (len(clean_word) <= 1)  # Keep single letters (I, a as in "a priori")
            or (word.isupper() and len(word) > 1)  # Keep acronyms (but not single caps)
            or any(char.isdigit() for char in word)  # Keep words with numbers
        )

        if should_keep:
            filtered_words.append(word)

    # Return the filtered result, or empty string if all words removed
    return " ".join(filtered_words) if filtered_words else ""


def _apply_stopword_reduction_markdown_aware(text: str, *, stopwords: set[str]) -> str:
    """Apply stopword reduction preserving markdown structure."""
    lines = text.split("\n")
    processed_lines = []
    in_code_block = False

    for line in lines:
        # Track code blocks
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            processed_lines.append(line)
            continue

        # Preserve markdown structural elements
        if _is_markdown_structural_line(line, in_code_block):
            processed_lines.append(line)
            continue

        # Apply stopword reduction to prose lines
        if line.strip():
            reduced = _apply_stopword_reduction_plain(line, stopwords=stopwords)
            processed_lines.append(reduced)
        else:
            processed_lines.append(line)

    # Remove excessive empty lines and return
    result = "\n".join(processed_lines)
    return _normalize_newlines(result).strip()


def get_reduction_stats(original: str, reduced: str) -> ReductionStats:
    """Get detailed statistics about the reduction.

    Args:
        original: The original text.
        reduced: The reduced text.

    Returns:
        Statistics about the reduction.

    Raises:
        ValidationError: If inputs are invalid.
    """
    if original is None:
        raise ValidationError("Original text cannot be None")

    if reduced is None:
        raise ValidationError("Reduced text cannot be None")

    if not isinstance(original, str):
        raise ValidationError(f"Original text must be a string, got {type(original).__name__}")

    if not isinstance(reduced, str):
        raise ValidationError(f"Reduced text must be a string, got {type(reduced).__name__}")

    original_chars = len(original)
    reduced_chars = len(reduced)
    original_tokens = len(original.split()) if original else 0
    reduced_tokens = len(reduced.split()) if reduced else 0

    char_reduction = (original_chars - reduced_chars) / original_chars if original_chars > 0 else 0.0
    token_reduction = (original_tokens - reduced_tokens) / original_tokens if original_tokens > 0 else 0.0

    return ReductionStats(
        character_reduction_ratio=char_reduction,
        token_reduction_ratio=token_reduction,
        original_characters=original_chars,
        reduced_characters=reduced_chars,
        original_tokens=original_tokens,
        reduced_tokens=reduced_tokens,
    )
