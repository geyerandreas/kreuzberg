from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from kreuzberg._token_reduction import StopwordsManager, get_reduction_stats, reduce_tokens
from kreuzberg._types import TokenReductionConfig
from kreuzberg.exceptions import ValidationError

if TYPE_CHECKING:
    from pathlib import Path


def test_reduce_tokens_off_mode_returns_original_text() -> None:
    config = TokenReductionConfig(mode="off")
    text = "This is a test with some stopwords and extra    spaces."

    result = reduce_tokens(text, config=config)

    assert result == text


def test_reduce_tokens_light_mode_normalizes_whitespace() -> None:
    config = TokenReductionConfig(mode="light", preserve_markdown=False)
    text = "This   has    multiple     spaces."

    result = reduce_tokens(text, config=config)

    assert result == "This has multiple spaces."


def test_reduce_tokens_light_mode_removes_html_comments() -> None:
    config = TokenReductionConfig(mode="light", preserve_markdown=False)
    text = "Text before <!-- comment --> text after."

    result = reduce_tokens(text, config=config)

    assert result == "Text before text after."


def test_reduce_tokens_light_mode_compresses_repeated_punctuation() -> None:
    config = TokenReductionConfig(mode="light", preserve_markdown=False)
    text = "Wait!!! What??? No way... Really,,,"

    result = reduce_tokens(text, config=config)

    assert result == "Wait! What? No way. Really,"


def test_reduce_tokens_light_mode_removes_excessive_newlines() -> None:
    config = TokenReductionConfig(mode="light", preserve_markdown=False)
    text = "Line 1\n\n\n\nLine 2\n\n\n\n\nLine 3"

    result = reduce_tokens(text, config=config)

    assert result == "Line 1\n\nLine 2\n\nLine 3"


def test_reduce_tokens_light_mode_preserves_markdown_when_enabled() -> None:
    config = TokenReductionConfig(mode="light", preserve_markdown=True)
    text = "# Header\n\nSome   text   with   spaces.\n\n```\ncode   block\n```"

    result = reduce_tokens(text, config=config)

    assert "# Header" in result
    assert "```\ncode   block\n```" in result
    assert "Some text with spaces." in result


def test_reduce_tokens_moderate_mode_removes_stopwords() -> None:
    config = TokenReductionConfig(mode="moderate", preserve_markdown=False)
    text = "The quick brown fox jumps over the lazy dog."

    result = reduce_tokens(text, config=config, language="en")

    assert "the" not in result.lower().split()
    assert "over" not in result.lower().split()
    assert "quick" in result.lower()
    assert "brown" in result.lower()
    assert "fox" in result.lower()


def test_reduce_tokens_moderate_mode_preserves_important_words() -> None:
    config = TokenReductionConfig(mode="moderate", preserve_markdown=False)
    text = "The API key is ABC123 and the URL is https://example.com"

    result = reduce_tokens(text, config=config, language="en")

    assert "API" in result
    assert "ABC123" in result
    assert "URL" in result


def test_reduce_tokens_moderate_mode_with_markdown_preservation() -> None:
    config = TokenReductionConfig(mode="moderate", preserve_markdown=True)
    text = """# Title

The quick brown fox jumps over the lazy dog.

- The first item
- The second item

```python
def the_function():
    pass
```"""

    result = reduce_tokens(text, config=config, language="en")

    assert "# Title" in result
    assert "- " in result
    assert "```python" in result
    assert "def the_function():" in result
    lines = result.split("\n")
    prose_line = next(line for line in lines if "fox" in line)
    assert "the" not in prose_line.lower().split()


def test_reduce_tokens_with_unsupported_language_falls_back_to_english() -> None:
    config = TokenReductionConfig(mode="moderate")
    text = "The quick brown fox jumps over the lazy dog."

    result = reduce_tokens(text, config=config, language="unsupported-lang")

    assert "the" not in result.lower().split()
    assert "quick" in result.lower()


def test_reduce_tokens_with_no_language_uses_english() -> None:
    config = TokenReductionConfig(mode="moderate")
    text = "The quick brown fox jumps over the lazy dog."

    result = reduce_tokens(text, config=config)

    assert "the" not in result.lower().split()
    assert "quick" in result.lower()


def test_get_reduction_stats_calculates_correctly() -> None:
    original = "The quick brown fox jumps over the lazy dog."
    reduced = "quick brown fox jumps lazy dog."

    stats = get_reduction_stats(original, reduced)

    assert stats["original_characters"] == len(original)
    assert stats["reduced_characters"] == len(reduced)
    assert stats["original_tokens"] == len(original.split())
    assert stats["reduced_tokens"] == len(reduced.split())
    assert stats["character_reduction_ratio"] > 0
    assert stats["token_reduction_ratio"] > 0


def test_get_reduction_stats_with_no_reduction() -> None:
    text = "Same text for both."

    stats = get_reduction_stats(text, text)

    assert stats["character_reduction_ratio"] == 0.0
    assert stats["token_reduction_ratio"] == 0.0
    assert stats["original_characters"] == stats["reduced_characters"]
    assert stats["original_tokens"] == stats["reduced_tokens"]


def test_get_reduction_stats_with_empty_original() -> None:
    stats = get_reduction_stats("", "")

    assert stats["character_reduction_ratio"] == 0.0
    assert stats["token_reduction_ratio"] == 0.0
    assert stats["original_characters"] == 0
    assert stats["reduced_characters"] == 0


def test_stopwords_manager_loads_english_stopwords() -> None:
    manager = StopwordsManager()

    stopwords = manager.get_stopwords("en")

    assert len(stopwords) > 0
    assert "the" in stopwords
    assert "and" in stopwords
    assert "is" in stopwords


def test_stopwords_manager_has_language_check() -> None:
    manager = StopwordsManager()

    assert manager.has_language("en") is True
    assert manager.has_language("nonexistent") is False


def test_stopwords_manager_supported_languages() -> None:
    manager = StopwordsManager()

    languages = manager.supported_languages()

    assert len(languages) > 0
    assert "en" in languages
    assert isinstance(languages, list)
    assert languages == sorted(languages)


def test_stopwords_manager_custom_stopwords() -> None:
    custom_stopwords = {"test": ["custom", "words"]}
    manager = StopwordsManager(custom_stopwords=custom_stopwords)

    stopwords = manager.get_stopwords("test")

    assert "custom" in stopwords
    assert "words" in stopwords


def test_reduce_tokens_empty_text_returns_empty() -> None:
    config = TokenReductionConfig(mode="light")

    result = reduce_tokens("", config=config)

    assert result == ""


def test_reduce_tokens_whitespace_only_text() -> None:
    config = TokenReductionConfig(mode="light")

    result = reduce_tokens("   \n\n   \t  ", config=config)

    assert result == ""


def test_reduce_tokens_moderate_mode_with_mixed_case() -> None:
    config = TokenReductionConfig(mode="moderate")
    text = "THE Quick BROWN fox"

    result = reduce_tokens(text, config=config, language="en")

    assert "Quick" in result
    assert "BROWN" in result
    assert "THE" in result.split()


def test_reduce_tokens_validation_raises_error_on_none_text() -> None:
    config = TokenReductionConfig(mode="light")

    with pytest.raises(ValidationError, match="Text cannot be None"):
        reduce_tokens(None, config=config)  # type: ignore[arg-type]


def test_reduce_tokens_validation_raises_error_on_none_config() -> None:
    with pytest.raises(ValidationError, match="Config cannot be None"):
        reduce_tokens("test", config=None)  # type: ignore[arg-type]


def test_reduce_tokens_validation_raises_error_on_invalid_text_type() -> None:
    config = TokenReductionConfig(mode="light")

    with pytest.raises(ValidationError, match="Text must be a string, got int"):
        reduce_tokens(123, config=config)  # type: ignore[arg-type]


def test_reduce_tokens_validation_raises_error_on_invalid_language_type() -> None:
    config = TokenReductionConfig(mode="moderate")

    with pytest.raises(ValidationError, match="Language must be a string or None, got int"):
        reduce_tokens("test", config=config, language=123)  # type: ignore[arg-type]


def test_reduce_tokens_validation_raises_error_on_empty_language() -> None:
    config = TokenReductionConfig(mode="moderate")

    with pytest.raises(ValidationError, match="Language cannot be empty or whitespace-only"):
        reduce_tokens("test", config=config, language="  ")


def test_reduce_tokens_handles_empty_text_gracefully() -> None:
    config = TokenReductionConfig(mode="light")

    result = reduce_tokens("", config=config)

    assert result == ""


def test_reduce_tokens_handles_whitespace_only_text_gracefully() -> None:
    config = TokenReductionConfig(mode="off")

    result = reduce_tokens("   \n\t  ", config=config)

    assert result == "   \n\t  "


def test_get_reduction_stats_validation_raises_error_on_none_original() -> None:
    with pytest.raises(ValidationError, match="Original text cannot be None"):
        get_reduction_stats(None, "test")  # type: ignore[arg-type]


def test_get_reduction_stats_validation_raises_error_on_none_reduced() -> None:
    with pytest.raises(ValidationError, match="Reduced text cannot be None"):
        get_reduction_stats("test", None)  # type: ignore[arg-type]


def test_get_reduction_stats_validation_raises_error_on_invalid_original_type() -> None:
    with pytest.raises(ValidationError, match="Original text must be a string, got int"):
        get_reduction_stats(123, "test")  # type: ignore[arg-type]


def test_get_reduction_stats_validation_raises_error_on_invalid_reduced_type() -> None:
    with pytest.raises(ValidationError, match="Reduced text must be a string, got list"):
        get_reduction_stats("test", ["test"])  # type: ignore[arg-type]


def test_reduce_tokens_security_raises_error_on_excessive_text_length() -> None:
    config = TokenReductionConfig(mode="light")
    large_text = "x" * 10_000_001

    with pytest.raises(ValidationError, match="Text too large"):
        reduce_tokens(large_text, config=config)


def test_reduce_tokens_security_raises_error_on_invalid_language_format() -> None:
    config = TokenReductionConfig(mode="moderate")

    with pytest.raises(ValidationError, match="Invalid language code format"):
        reduce_tokens("test", config=config, language="invalid/lang$code")


def test_reduce_tokens_security_accepts_valid_language_codes() -> None:
    config = TokenReductionConfig(mode="off")

    reduce_tokens("test", config=config, language="en")
    reduce_tokens("test", config=config, language="es")
    reduce_tokens("test", config=config, language="en-US")
    reduce_tokens("test", config=config, language="pt-BR")


def test_reduce_tokens_edge_case_unicode_characters() -> None:
    config = TokenReductionConfig(mode="light")
    text = "Hello 世界 🌍 café naïve résumé"

    result = reduce_tokens(text, config=config)

    assert "世界" in result
    assert "🌍" in result
    assert "café" in result


def test_reduce_tokens_edge_case_very_long_words() -> None:
    config = TokenReductionConfig(mode="moderate")
    long_word = "supercalifragilisticexpialidocious" * 10
    text = f"The {long_word} was amazing"

    result = reduce_tokens(text, config=config, language="en")

    assert long_word in result
    assert "the" not in result.lower()


def test_reduce_tokens_edge_case_numbers_and_symbols() -> None:
    config = TokenReductionConfig(mode="moderate")
    text = "The price is $123.45 and the date is 2024-01-01"

    result = reduce_tokens(text, config=config, language="en")

    assert "$123.45" in result
    assert "2024-01-01" in result
    assert "price" in result
    assert "the" not in result.lower()


def test_reduce_tokens_edge_case_mixed_languages() -> None:
    config = TokenReductionConfig(mode="moderate")
    text = "Hey mundo 世界 bonjour"

    result = reduce_tokens(text, config=config, language="en")

    assert "Hey" in result
    assert "mundo" in result
    assert "世界" in result
    assert "bonjour" in result


def test_reduce_tokens_edge_case_markdown_with_complex_nesting() -> None:
    config = TokenReductionConfig(mode="moderate", preserve_markdown=True)
    text = """# Header with the word the

This is a paragraph with the word the that should be reduced.

## Sub-header the

- Item the first
- Item the second
  - Nested item the third

```python
def the_function():
    # This the should be preserved
    return "the value"
```

| Column the | Another the |
|------------|-------------|
| Value the  | Data the    |
"""

    result = reduce_tokens(text, config=config, language="en")

    assert "# Header with the word the" in result
    assert "## Sub-header the" in result

    assert "def the_function():" in result
    assert "# This the should be preserved" in result

    assert "| Column the | Another the |" in result

    assert "- Item the first" in result

    lines = result.split("\n")
    prose_lines = [
        line
        for line in lines
        if line.strip() and not line.strip().startswith(("#", "-", "|", "```")) and "def " not in line
    ]
    for line in prose_lines:
        if "paragraph" in line.lower():
            assert "the" not in line.lower().split()


def test_reduce_tokens_edge_case_only_stopwords() -> None:
    config = TokenReductionConfig(mode="moderate")
    text = "the and or but"

    result = reduce_tokens(text, config=config, language="en")

    assert len(result.strip()) == 0 or result.strip() in ["", "and", "or", "but"]


def test_reduce_tokens_edge_case_repeated_punctuation_edge_cases() -> None:
    config = TokenReductionConfig(mode="light")
    text = "What?!?!?! No way.... Really,,, Wow!!! Amazing..."

    result = reduce_tokens(text, config=config)

    assert "?!?!?!" not in result
    assert "...." not in result
    assert ",,," not in result
    assert "!!!" not in result

    assert "What?" in result or "What!" in result
    assert "way." in result
    assert "Really," in result


def test_get_reduction_stats_edge_case_empty_strings() -> None:
    stats = get_reduction_stats("", "")

    assert stats["character_reduction_ratio"] == 0.0
    assert stats["token_reduction_ratio"] == 0.0
    assert stats["original_characters"] == 0
    assert stats["reduced_characters"] == 0
    assert stats["original_tokens"] == 0
    assert stats["reduced_tokens"] == 0


def test_get_reduction_stats_edge_case_expansion() -> None:
    original = "Hi"
    reduced = "Hello there"

    stats = get_reduction_stats(original, reduced)

    assert stats["character_reduction_ratio"] < 0
    assert stats["token_reduction_ratio"] < 0
    assert stats["original_characters"] == 2
    assert stats["reduced_characters"] == 11
    assert stats["original_tokens"] == 1
    assert stats["reduced_tokens"] == 2


def test_stopwords_manager_concurrent_access() -> None:
    """Test that StopwordsManager handles concurrent access correctly via LRU cache."""
    import concurrent.futures

    manager = StopwordsManager()
    languages = ["en", "es", "fr", "de", "it"]

    def load_language(lang: str) -> int:
        stopwords = manager.get_stopwords(lang)
        return len(stopwords)

    # Test concurrent loading of different languages
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(load_language, lang) for lang in languages * 3]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All results should be successful (non-zero lengths)
    assert all(r > 0 for r in results)
    assert len(results) == 15  # 5 languages * 3 repetitions


def test_stopwords_manager_handles_corrupted_file(tmp_path: Path) -> None:
    """Test that StopwordsManager handles corrupted JSON files gracefully."""
    from unittest.mock import patch

    # Create a corrupted stopwords file
    corrupted_dir = tmp_path / "stopwords"
    corrupted_dir.mkdir()
    corrupted_file = corrupted_dir / "xx_stopwords.json"
    corrupted_file.write_text("not valid json {[}")

    # Patch the stopwords directory to use our test directory
    with patch("kreuzberg._token_reduction._stopwords._STOPWORDS_DIR", corrupted_dir):
        manager = StopwordsManager()

        # Should return empty set for corrupted file (consistent with missing files)
        stopwords = manager.get_stopwords("xx")
        assert isinstance(stopwords, set)
        assert len(stopwords) == 0


def test_stopwords_manager_handles_missing_file() -> None:
    """Test that StopwordsManager returns empty set for missing language files."""
    manager = StopwordsManager()

    # Non-existent language should return empty set
    stopwords = manager.get_stopwords("zz_nonexistent")

    assert isinstance(stopwords, set)
    assert len(stopwords) == 0


def test_reduce_tokens_thread_safety() -> None:
    """Test that reduce_tokens is thread-safe."""
    import concurrent.futures

    config = TokenReductionConfig(mode="moderate")
    test_texts = [
        "The quick brown fox jumps over the lazy dog.",
        "This is another test sentence with stopwords.",
        "Multiple threads should handle this correctly.",
        "Each thread processes its own text independently.",
        "Thread safety is important for production use.",
    ]

    def process_text(text: str) -> str:
        return reduce_tokens(text, config=config, language="en")

    # Process texts concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_text, text) for text in test_texts * 3]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All results should be processed successfully
    assert len(results) == 15  # 5 texts * 3 repetitions
    assert all(isinstance(r, str) for r in results)
    assert all(len(r) > 0 for r in results)


def test_stopwords_manager_lru_cache_size() -> None:
    """Test that LRU cache maintains reasonable memory usage."""
    manager = StopwordsManager()

    # Load more than the cache size (16) to test eviction
    languages = [
        "en",
        "es",
        "fr",
        "de",
        "it",
        "pt",
        "nl",
        "sv",
        "no",
        "da",
        "fi",
        "pl",
        "cs",
        "sk",
        "hu",
        "ro",
        "bg",
        "hr",
        "sr",  # 19 languages total
    ]

    for lang in languages:
        if manager.has_language(lang):
            manager.get_stopwords(lang)

    # Cache should still work correctly after evictions
    # Re-load first language (should have been evicted)
    stopwords = manager.get_stopwords("en")
    assert "the" in stopwords
    assert len(stopwords) > 0


def test_reduce_tokens_with_custom_stopwords_thread_safety() -> None:
    """Test thread safety with custom stopwords."""
    import concurrent.futures

    config = TokenReductionConfig(
        mode="moderate",
        custom_stopwords={
            "en": ["customword", "special"],
            "es": ["personalizado", "especial"],
        },
    )

    test_cases = [
        ("Python customword programming has special features", "en"),
        ("Python personalizado programación tiene especial características", "es"),
    ]

    def process_with_custom(text: str, lang: str) -> str:
        return reduce_tokens(text, config=config, language=lang)

    # Process with custom stopwords concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_with_custom, text, lang) for text, lang in test_cases * 5]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Verify results are consistent and correct
    assert len(results) == 10  # 2 test cases * 5 repetitions

    for result in results:
        result_lower = result.lower()
        # Custom stopwords should be removed
        assert "customword" not in result_lower
        assert "special" not in result_lower
        assert "personalizado" not in result_lower
        assert "especial" not in result_lower

        # Content words like "Python" and "programming" should remain
        assert "python" in result_lower
        assert (
            "programming" in result_lower
            or "programación" in result_lower
            or "features" in result_lower
            or "características" in result_lower
        )


def test_short_stopwords_are_removed() -> None:
    """Test that common 2-letter stopwords are actually removed."""
    config = TokenReductionConfig(mode="moderate")
    # Common 2-letter stopwords that should be removed
    text = "It is an excellent document of the organization"

    result = reduce_tokens(text, config=config, language="en")

    # These 2-letter stopwords should be removed
    assert " is " not in f" {result} "
    assert " it " not in f" {result.lower()} "
    assert " an " not in f" {result.lower()} "
    assert " of " not in f" {result.lower()} "

    # Content words should remain (using words not in stopword list)
    assert "excellent" in result
    assert "document" in result
    assert "organization" in result


def test_single_letter_words_preserved() -> None:
    """Test that single letters like 'I' and 'a' are preserved."""
    config = TokenReductionConfig(mode="moderate")
    text = "I need a solution"

    result = reduce_tokens(text, config=config, language="en")

    # Single letters should be preserved
    assert "I" in result or "i" in result.lower()
    assert " a " in f" {result.lower()} " or result.lower().startswith("a ")

    # Other words preserved/removed appropriately
    assert "solution" in result


def test_markdown_table_detection_improved() -> None:
    """Test improved markdown table detection."""
    config = TokenReductionConfig(mode="moderate", preserve_markdown=True)

    # Real table - should be preserved
    table_text = """
| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
"""

    # Not a table - just text with pipes
    not_table = "This text has a pipe | but it's not a table"

    table_result = reduce_tokens(table_text, config=config, language="en")
    not_table_result = reduce_tokens(not_table, config=config, language="en")

    # Real table structure preserved
    assert "| Column 1 | Column 2 |" in table_result
    assert "|----------|----------|" in table_result

    # Pipe in regular text gets stopwords removed
    assert "pipe" in not_table_result
    assert "table" in not_table_result
    # "but" and "it's" should be removed as stopwords
    assert "but" not in not_table_result


def test_path_traversal_protection() -> None:
    """Test that path traversal attempts are blocked."""

    manager = StopwordsManager()

    # Try various path traversal patterns
    dangerous_codes = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "en/../../../etc/passwd",
        "en/../../secret",
    ]

    for dangerous_code in dangerous_codes:
        # Should safely return empty set
        stopwords = manager.get_stopwords(dangerous_code)
        assert stopwords == set()


def test_custom_stopwords_size_limits() -> None:
    """Test that custom stopwords have size limits."""
    # Test too many languages
    too_many_langs = {f"lang{i}": ["word"] for i in range(101)}

    with pytest.raises(ValidationError, match="Too many custom stopword languages"):
        StopwordsManager(custom_stopwords=too_many_langs)

    # Test too many words per language
    too_many_words = {"en": [f"word{i}" for i in range(10001)]}

    with pytest.raises(ValidationError, match="Too many custom stopwords for language"):
        StopwordsManager(custom_stopwords=too_many_words)


def test_add_custom_stopwords_limits() -> None:
    """Test that add_custom_stopwords enforces limits."""
    manager = StopwordsManager()

    # Add languages up to the limit
    for i in range(100):
        manager.add_custom_stopwords(f"lang{i}", ["word"])

    # Should fail when adding 101st language
    with pytest.raises(ValidationError, match="Cannot add more custom stopword languages"):
        manager.add_custom_stopwords("lang100", ["word"])

    # Test word limit per language
    manager2 = StopwordsManager()
    manager2.add_custom_stopwords("en", [f"word{i}" for i in range(9999)])

    # Should fail when exceeding word limit
    with pytest.raises(ValidationError, match="Too many custom stopwords for language"):
        manager2.add_custom_stopwords("en", ["word9999", "word10000"])


def test_empty_result_handling() -> None:
    """Test that completely filtered text returns empty string."""
    config = TokenReductionConfig(mode="moderate", custom_stopwords={"en": ["everything", "removed"]})
    text = "everything is removed"

    result = reduce_tokens(text, config=config, language="en")

    # Should return empty string, not crash
    assert result == ""


def test_thread_safe_ref_initialization() -> None:
    """Test that Ref class is thread-safe during initialization."""
    import concurrent.futures
    import time

    from kreuzberg._utils._ref import Ref

    call_count = 0

    def slow_factory() -> str:
        nonlocal call_count
        call_count += 1
        time.sleep(0.01)  # Simulate slow initialization
        return f"initialized_{call_count}"

    ref = Ref("test_ref", slow_factory)

    # Clear to ensure fresh test
    ref.clear()

    # Multiple threads try to initialize simultaneously
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(ref.get) for _ in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # Should only initialize once despite concurrent access
    assert call_count == 1
    assert all(r == "initialized_1" for r in results)

    # Cleanup
    ref.clear()
