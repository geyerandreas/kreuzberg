from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

from kreuzberg import MissingDependencyError
from kreuzberg import _entity_extraction as ee
from kreuzberg._entity_extraction import SpacyEntityExtractionConfig
from kreuzberg._types import Entity

SAMPLE_TEXT = "John Doe visited Berlin on 2023-01-01. Contact: john@example.com or +49-123-4567."


@pytest.mark.parametrize(
    "custom_patterns,expected",
    [
        (None, []),
        (frozenset([("INVOICE_ID", r"INV-\d+")]), []),
        (
            frozenset([("EMAIL", r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")]),
            [Entity(type="EMAIL", text="john@example.com", start=48, end=64)],
        ),
    ],
)
def test_custom_entity_patterns(
    custom_patterns: frozenset[tuple[str, str]] | None, expected: list[Entity], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "spacy", MagicMock())
    entities = ee.extract_entities(SAMPLE_TEXT, entity_types=(), custom_patterns=custom_patterns)
    assert all(isinstance(e, Entity) for e in entities)
    if expected:
        assert any(e.type == "EMAIL" and e.text == "john@example.com" for e in entities)
    else:
        assert entities == expected


def test_extract_entities_with_spacy(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyEnt:
        def __init__(self, label: str, text: str, start_char: int, end_char: int):
            self.label_ = label
            self.text = text
            self.start_char = start_char
            self.end_char = end_char

    class DummyDoc:
        def __init__(self, text: str):
            self.ents = [
                DummyEnt("PERSON", "John Doe", 0, 8),
                DummyEnt("GPE", "Berlin", 18, 24),
            ]

    class DummyNLP:
        max_length = 1000000

        def __call__(self, text: str) -> DummyDoc:
            return DummyDoc(text)

    def mock_load(_model_name: str) -> DummyNLP:
        return DummyNLP()

    mock_spacy = MagicMock()
    mock_spacy.load = mock_load
    monkeypatch.setitem(sys.modules, "spacy", mock_spacy)

    def mock_load_spacy_model(model_name: str, spacy_config: Any) -> DummyNLP:
        return DummyNLP()

    monkeypatch.setattr(ee, "_load_spacy_model", mock_load_spacy_model)

    result = ee.extract_entities(SAMPLE_TEXT, entity_types=["PERSON", "GPE"], languages=["en"])
    assert any(e.type == "PERSON" and e.text == "John Doe" for e in result)
    assert any(e.type == "GPE" and e.text == "Berlin" for e in result)
    assert all(isinstance(e, Entity) for e in result)


def test_extract_keywords_with_keybert(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyModel:
        def extract_keywords(self, _text: str, top_n: int = 10) -> list[tuple[str, float]]:
            if top_n == 2:
                return [("Berlin", 0.9), ("John Doe", 0.8)]
            return [("keyword", 0.5)] * top_n

    mock_keybert = MagicMock()
    mock_keybert.KeyBERT = DummyModel
    monkeypatch.setitem(sys.modules, "keybert", mock_keybert)

    result = ee.extract_keywords(SAMPLE_TEXT, keyword_count=2)
    assert result == [("Berlin", 0.9), ("John Doe", 0.8)]


def test_extract_entities_missing_spacy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "spacy", None)
    with pytest.raises(MissingDependencyError):
        ee.extract_entities(SAMPLE_TEXT, entity_types=["PERSON"])


def test_extract_keywords_missing_keybert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "keybert", None)
    with pytest.raises(MissingDependencyError):
        ee.extract_keywords(SAMPLE_TEXT, keyword_count=5)


def test_spacy_entity_extraction_config_defaults() -> None:
    """Test SpacyEntityExtractionConfig default values."""
    config = SpacyEntityExtractionConfig()
    assert config.language_models is not None
    assert isinstance(config.language_models, tuple)
    assert config.fallback_to_multilingual is True
    assert config.max_doc_length == 1000000
    assert config.batch_size == 1000


def test_spacy_entity_extraction_config_custom_models() -> None:
    """Test SpacyEntityExtractionConfig with custom language models."""
    custom_models = {"en": "en_core_web_lg", "fr": "fr_core_news_sm"}
    config = SpacyEntityExtractionConfig(language_models=custom_models)
    assert isinstance(config.language_models, tuple)
    assert dict(config.language_models) == custom_models


def test_spacy_entity_extraction_config_get_model_for_language() -> None:
    """Test get_model_for_language method."""
    config = SpacyEntityExtractionConfig()

    # Test exact match
    assert config.get_model_for_language("en") == "en_core_web_sm"
    assert config.get_model_for_language("de") == "de_core_news_sm"

    # Test base language fallback
    assert config.get_model_for_language("en-US") == "en_core_web_sm"
    assert config.get_model_for_language("de-DE") == "de_core_news_sm"

    # Test non-existent language
    assert config.get_model_for_language("xx") is None
    assert config.get_model_for_language("nonexistent") is None


def test_spacy_entity_extraction_config_get_fallback_model() -> None:
    """Test get_fallback_model method."""
    config_with_fallback = SpacyEntityExtractionConfig(fallback_to_multilingual=True)
    assert config_with_fallback.get_fallback_model() == "xx_ent_wiki_sm"

    config_without_fallback = SpacyEntityExtractionConfig(fallback_to_multilingual=False)
    assert config_without_fallback.get_fallback_model() is None


def test_spacy_entity_extraction_config_empty_models() -> None:
    """Test SpacyEntityExtractionConfig with empty language models."""
    config = SpacyEntityExtractionConfig(language_models={})
    assert config.get_model_for_language("en") is None


def test_spacy_entity_extraction_config_model_cache_dir() -> None:
    """Test SpacyEntityExtractionConfig with model cache directory."""
    import tempfile

    with tempfile.TemporaryDirectory() as temp_dir:
        config = SpacyEntityExtractionConfig(model_cache_dir=temp_dir)
        assert str(config.model_cache_dir) == temp_dir


def test_select_spacy_model_fallback() -> None:
    """Test _select_spacy_model with fallback behavior."""
    config = SpacyEntityExtractionConfig(language_models={"en": "en_core_web_sm"}, fallback_to_multilingual=True)

    # Test normal selection
    model = ee._select_spacy_model(["en"], config)
    assert model == "en_core_web_sm"

    # Test fallback when language not found
    model = ee._select_spacy_model(["nonexistent"], config)
    assert model == "xx_ent_wiki_sm"  # Should return fallback

    # Test no fallback when disabled
    config_no_fallback = SpacyEntityExtractionConfig(
        language_models={"en": "en_core_web_sm"}, fallback_to_multilingual=False
    )
    model = ee._select_spacy_model(["nonexistent"], config_no_fallback)
    assert model is None


def test_extract_entities_empty_input() -> None:
    """Test extract_entities with empty input."""
    result = ee.extract_entities("", entity_types=["PERSON"])
    assert result == []


def test_extract_entities_no_entities_types() -> None:
    """Test extract_entities with no entity types specified."""
    result = ee.extract_entities(SAMPLE_TEXT, entity_types=())
    assert isinstance(result, list)


def test_extract_keywords_with_default_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extract_keywords with default count."""

    class DummyModel:
        def extract_keywords(self, _text: str, top_n: int = 10) -> list[tuple[str, float]]:
            return [("keyword", 0.5)] * min(top_n, 3)

    mock_keybert = MagicMock()
    mock_keybert.KeyBERT = DummyModel
    monkeypatch.setitem(sys.modules, "keybert", mock_keybert)

    result = ee.extract_keywords(SAMPLE_TEXT)  # Default count is 10
    assert len(result) == 3  # But dummy only returns 3


def test_extract_keywords_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test extract_keywords with empty input."""

    class DummyModel:
        def extract_keywords(self, _text: str, top_n: int = 10) -> list[tuple[str, float]]:
            return []

    mock_keybert = MagicMock()
    mock_keybert.KeyBERT = DummyModel
    monkeypatch.setitem(sys.modules, "keybert", mock_keybert)

    result = ee.extract_keywords("")
    assert result == []


# =============================================================================
# COMPREHENSIVE TESTS (for improved coverage)
# =============================================================================


class TestSpacyEntityExtractionConfigComprehensive:
    """Test comprehensive SpacyEntityExtractionConfig scenarios."""

    def test_spacy_config_tuple_language_models(self) -> None:
        """Test SpacyEntityExtractionConfig with tuple language models."""
        models_tuple = (("en", "en_core_web_sm"), ("fr", "fr_core_news_sm"))
        config = SpacyEntityExtractionConfig(language_models=models_tuple)

        # Should remain a tuple
        assert isinstance(config.language_models, tuple)
        assert config.language_models == models_tuple

    def test_spacy_config_default_language_models_comprehensive(self) -> None:
        """Test that default language models include all expected languages."""
        config = SpacyEntityExtractionConfig()
        models_dict = (
            dict(config.language_models) if isinstance(config.language_models, tuple) else config.language_models
        )

        # Check some key languages are present
        expected_languages = ["en", "de", "fr", "es", "pt", "it", "nl", "zh", "ja", "ko", "ru"]
        assert models_dict is not None
        for lang in expected_languages:
            assert lang in models_dict
            assert models_dict[lang].endswith("_sm")

    def test_spacy_config_get_model_complex_language_codes(self) -> None:
        """Test get_model_for_language with complex language codes."""
        config = SpacyEntityExtractionConfig()

        # Test multiple hyphen-separated parts
        assert config.get_model_for_language("en-US-POSIX") == "en_core_web_sm"
        assert config.get_model_for_language("de-DE-1996") == "de_core_news_sm"

        # Test case insensitivity
        assert config.get_model_for_language("EN") == "en_core_web_sm"
        assert config.get_model_for_language("En-Us") == "en_core_web_sm"

    def test_spacy_config_no_language_models(self) -> None:
        """Test SpacyEntityExtractionConfig behavior when language_models is None after post_init."""
        # This should not happen in normal usage, but test edge case
        config = SpacyEntityExtractionConfig()
        # Simulate setting language_models to None after initialization
        object.__setattr__(config, "language_models", None)

        assert config.get_model_for_language("en") is None
        assert config.get_model_for_language("any") is None

    def test_spacy_config_pathlib_model_cache_dir(self) -> None:
        """Test SpacyEntityExtractionConfig with pathlib.Path model cache directory."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            path_dir = Path(temp_dir)
            config = SpacyEntityExtractionConfig(model_cache_dir=path_dir)
            assert config.model_cache_dir == path_dir


class TestEntityExtractionEdgeCases:
    """Test entity extraction edge cases."""

    def test_extract_entities_very_long_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_entities with text longer than max_doc_length."""

        class DummyDoc:
            def __init__(self, text: str):
                self.ents: list[Any] = []

        class DummyNLP:
            max_length = 1000000

            def __call__(self, text: str) -> DummyDoc:
                return DummyDoc(text)

        def mock_load_spacy_model(model_name: str, spacy_config: Any) -> DummyNLP:
            return DummyNLP()

        mock_spacy = MagicMock()
        monkeypatch.setitem(sys.modules, "spacy", mock_spacy)
        monkeypatch.setattr(ee, "_load_spacy_model", mock_load_spacy_model)

        # Create text longer than default max_doc_length (1,000,000)
        long_text = "a" * 1500000
        config = SpacyEntityExtractionConfig(max_doc_length=1000000)

        result = ee.extract_entities(long_text, entity_types=["PERSON"], spacy_config=config)
        assert isinstance(result, list)

    def test_extract_entities_custom_max_doc_length(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_entities with custom max_doc_length."""

        class DummyDoc:
            def __init__(self, text: str):
                self.ents: list[Any] = []

        class DummyNLP:
            max_length = 100

            def __call__(self, text: str) -> DummyDoc:
                # Verify truncation occurred
                assert len(text) <= 100
                return DummyDoc(text)

        def mock_load_spacy_model(model_name: str, spacy_config: Any) -> DummyNLP:
            return DummyNLP()

        mock_spacy = MagicMock()
        monkeypatch.setitem(sys.modules, "spacy", mock_spacy)
        monkeypatch.setattr(ee, "_load_spacy_model", mock_load_spacy_model)

        # Text longer than custom limit
        long_text = "This is a long text. " * 10  # Much longer than 100 chars
        config = SpacyEntityExtractionConfig(max_doc_length=100)

        result = ee.extract_entities(long_text, entity_types=["PERSON"], spacy_config=config)
        assert isinstance(result, list)

    def test_extract_entities_multiple_custom_patterns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_entities with multiple custom patterns."""
        mock_spacy = MagicMock()
        monkeypatch.setitem(sys.modules, "spacy", mock_spacy)

        text = "Invoice INV-001 dated 2023-01-01, email: test@example.com, phone: +1-555-123-4567"
        custom_patterns = frozenset(
            [
                ("INVOICE_ID", r"INV-\d+"),
                ("DATE", r"\d{4}-\d{2}-\d{2}"),
                ("EMAIL", r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
                ("PHONE", r"\+\d{1,3}-\d{3}-\d{3}-\d{4}"),
            ]
        )

        result = ee.extract_entities(text, entity_types=(), custom_patterns=custom_patterns)

        # Should find all patterns
        assert len(result) == 4
        entity_types = {e.type for e in result}
        assert entity_types == {"INVOICE_ID", "DATE", "EMAIL", "PHONE"}

    def test_extract_entities_overlapping_patterns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_entities with overlapping custom patterns."""
        mock_spacy = MagicMock()
        monkeypatch.setitem(sys.modules, "spacy", mock_spacy)

        text = "test@example.com"
        custom_patterns = frozenset(
            [
                ("EMAIL", r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
                ("DOMAIN", r"@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
                ("TLD", r"\.[a-zA-Z0-9-.]+$"),
            ]
        )

        result = ee.extract_entities(text, entity_types=(), custom_patterns=custom_patterns)

        # Should find all overlapping patterns
        assert len(result) == 3
        entity_types = {e.type for e in result}
        assert entity_types == {"EMAIL", "DOMAIN", "TLD"}

    def test_extract_entities_spacy_model_loading_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_entities when spaCy model loading fails."""
        mock_spacy = MagicMock()
        monkeypatch.setitem(sys.modules, "spacy", mock_spacy)

        def mock_load_spacy_model_fail(model_name: str, spacy_config: Any) -> None:
            return None  # Simulate model loading failure

        monkeypatch.setattr(ee, "_load_spacy_model", mock_load_spacy_model_fail)

        result = ee.extract_entities(SAMPLE_TEXT, entity_types=["PERSON"], languages=["en"])
        assert result == []  # Should return empty list when model loading fails

    def test_extract_entities_no_model_selected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_entities when no model is selected."""
        mock_spacy = MagicMock()
        monkeypatch.setitem(sys.modules, "spacy", mock_spacy)

        def mock_select_spacy_model_none(languages: list[str] | None, spacy_config: Any) -> None:
            return None  # Simulate no model selected

        monkeypatch.setattr(ee, "_select_spacy_model", mock_select_spacy_model_none)

        result = ee.extract_entities(SAMPLE_TEXT, entity_types=["PERSON"], languages=["unknown"])
        assert result == []  # Should return empty list when no model selected

    def test_extract_entities_case_insensitive_entity_types(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_entities with case-insensitive entity type matching."""

        class DummyEnt:
            def __init__(self, label: str, text: str, start_char: int, end_char: int):
                self.label_ = label
                self.text = text
                self.start_char = start_char
                self.end_char = end_char

        class DummyDoc:
            def __init__(self, text: str):
                self.ents = [
                    DummyEnt("person", "John Doe", 0, 8),  # lowercase label
                    DummyEnt("GPE", "Berlin", 18, 24),  # uppercase label
                    DummyEnt("Date", "2023-01-01", 28, 38),  # mixed case label
                ]

        class DummyNLP:
            max_length = 1000000

            def __call__(self, text: str) -> DummyDoc:
                return DummyDoc(text)

        def mock_load_spacy_model(model_name: str, spacy_config: Any) -> DummyNLP:
            return DummyNLP()

        mock_spacy = MagicMock()
        monkeypatch.setitem(sys.modules, "spacy", mock_spacy)
        monkeypatch.setattr(ee, "_load_spacy_model", mock_load_spacy_model)

        # Test case-insensitive matching
        result = ee.extract_entities(SAMPLE_TEXT, entity_types=["PERSON", "gpe", "date"], languages=["en"])

        # Should match regardless of case
        entity_types = {e.type for e in result}
        assert entity_types == {"person", "GPE", "Date"}


class TestSpacyModelSelectionComprehensive:
    """Test comprehensive spaCy model selection scenarios."""

    def test_select_spacy_model_empty_languages(self) -> None:
        """Test _select_spacy_model with empty languages list."""
        config = SpacyEntityExtractionConfig()

        # Empty list should default to English
        model = ee._select_spacy_model([], config)
        assert model == "en_core_web_sm"

    def test_select_spacy_model_multiple_languages_first_match(self) -> None:
        """Test _select_spacy_model returns first matching language."""
        config = SpacyEntityExtractionConfig()

        # Should return model for first matching language
        model = ee._select_spacy_model(["unknown", "de", "fr"], config)
        assert model == "de_core_news_sm"  # First match

    def test_select_spacy_model_base_language_fallback(self) -> None:
        """Test _select_spacy_model with base language fallback."""
        config = SpacyEntityExtractionConfig()

        # Should fallback to base language
        model = ee._select_spacy_model(["de-AT"], config)  # Austrian German
        assert model == "de_core_news_sm"  # Should match "de"

    def test_select_spacy_model_no_fallback_when_disabled(self) -> None:
        """Test _select_spacy_model without fallback when disabled."""
        config = SpacyEntityExtractionConfig(fallback_to_multilingual=False)

        # Should return None when no match and fallback disabled
        model = ee._select_spacy_model(["unknown"], config)
        assert model is None


class TestSpacyModelLoadingComprehensive:
    """Test comprehensive spaCy model loading scenarios."""

    def test_load_spacy_model_with_cache_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _load_spacy_model with custom cache directory."""
        import os
        import tempfile

        class DummyNLP:
            max_length = 1000000

        def mock_spacy_load(model_name: str) -> DummyNLP:
            return DummyNLP()

        mock_spacy = MagicMock()
        mock_spacy.load = mock_spacy_load
        monkeypatch.setitem(sys.modules, "spacy", mock_spacy)

        with tempfile.TemporaryDirectory() as temp_dir:
            config = SpacyEntityExtractionConfig(model_cache_dir=temp_dir, max_doc_length=500000)

            # Mock environment variable setting
            original_env = os.environ.get("SPACY_DATA")
            try:
                result = ee._load_spacy_model("en_core_web_sm", config)

                # Should set environment variable
                assert os.environ.get("SPACY_DATA") == temp_dir
                assert result is not None
                assert result.max_length == 500000  # Should set custom max_length
            finally:
                # Restore original environment
                if original_env:
                    os.environ["SPACY_DATA"] = original_env
                elif "SPACY_DATA" in os.environ:
                    del os.environ["SPACY_DATA"]

    def test_load_spacy_model_os_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _load_spacy_model with OSError."""

        def mock_spacy_load_error(model_name: str) -> None:
            raise OSError("Model not found")

        mock_spacy = MagicMock()
        mock_spacy.load = mock_spacy_load_error
        monkeypatch.setitem(sys.modules, "spacy", mock_spacy)

        config = SpacyEntityExtractionConfig()
        result = ee._load_spacy_model("nonexistent_model", config)
        assert result is None

    def test_load_spacy_model_import_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _load_spacy_model with ImportError during load."""

        def mock_spacy_load_error(model_name: str) -> None:
            raise ImportError("spaCy import error")

        mock_spacy = MagicMock()
        mock_spacy.load = mock_spacy_load_error
        monkeypatch.setitem(sys.modules, "spacy", mock_spacy)

        config = SpacyEntityExtractionConfig()
        result = ee._load_spacy_model("problematic_model", config)
        assert result is None


class TestKeywordExtractionComprehensive:
    """Test comprehensive keyword extraction scenarios."""

    def test_extract_keywords_runtime_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_keywords with RuntimeError from KeyBERT."""

        class DummyModel:
            def extract_keywords(self, _text: str, top_n: int = 10) -> None:
                raise RuntimeError("KeyBERT processing error")

        mock_keybert = MagicMock()
        mock_keybert.KeyBERT = DummyModel
        monkeypatch.setitem(sys.modules, "keybert", mock_keybert)

        result = ee.extract_keywords(SAMPLE_TEXT, keyword_count=5)
        assert result == []  # Should return empty list on RuntimeError

    def test_extract_keywords_os_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_keywords with OSError from KeyBERT."""

        class DummyModel:
            def extract_keywords(self, _text: str, top_n: int = 10) -> None:
                raise OSError("Model file not found")

        mock_keybert = MagicMock()
        mock_keybert.KeyBERT = DummyModel
        monkeypatch.setitem(sys.modules, "keybert", mock_keybert)

        result = ee.extract_keywords(SAMPLE_TEXT, keyword_count=5)
        assert result == []  # Should return empty list on OSError

    def test_extract_keywords_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_keywords with ValueError from KeyBERT."""

        class DummyModel:
            def extract_keywords(self, _text: str, top_n: int = 10) -> None:
                raise ValueError("Invalid input parameters")

        mock_keybert = MagicMock()
        mock_keybert.KeyBERT = DummyModel
        monkeypatch.setitem(sys.modules, "keybert", mock_keybert)

        result = ee.extract_keywords(SAMPLE_TEXT, keyword_count=5)
        assert result == []  # Should return empty list on ValueError

    def test_extract_keywords_zero_count(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_keywords with zero keyword count."""

        class DummyModel:
            def extract_keywords(self, _text: str, top_n: int = 10) -> list[tuple[str, float]]:
                return [] if top_n == 0 else [("keyword", 0.5)]

        mock_keybert = MagicMock()
        mock_keybert.KeyBERT = DummyModel
        monkeypatch.setitem(sys.modules, "keybert", mock_keybert)

        result = ee.extract_keywords(SAMPLE_TEXT, keyword_count=0)
        assert result == []

    def test_extract_keywords_float_conversion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test extract_keywords properly converts scores to float."""

        class DummyModel:
            def extract_keywords(self, _text: str, top_n: int = 10) -> list[tuple[str, Any]]:
                # Return various numeric types
                return [
                    ("keyword1", 0.95),  # float
                    ("keyword2", 85),  # int
                    ("keyword3", "0.75"),  # string number
                ]

        mock_keybert = MagicMock()
        mock_keybert.KeyBERT = DummyModel
        monkeypatch.setitem(sys.modules, "keybert", mock_keybert)

        result = ee.extract_keywords(SAMPLE_TEXT, keyword_count=3)

        # Should convert all to float
        assert len(result) == 3
        assert all(isinstance(score, float) for _, score in result)
        assert result == [("keyword1", 0.95), ("keyword2", 85.0), ("keyword3", 0.75)]


class TestEntityExtractionConfigurationEdgeCases:
    """Test entity extraction configuration edge cases."""

    def test_spacy_config_post_init_dict_conversion(self) -> None:
        """Test SpacyEntityExtractionConfig __post_init__ dict to tuple conversion."""
        # Test that dict gets converted to sorted tuple
        models_dict = {"fr": "fr_core_news_sm", "en": "en_core_web_sm", "de": "de_core_news_sm"}
        config = SpacyEntityExtractionConfig(language_models=models_dict)

        # Should be converted to sorted tuple
        assert isinstance(config.language_models, tuple)
        expected_tuple = tuple(sorted(models_dict.items()))
        assert config.language_models == expected_tuple

    def test_spacy_config_post_init_none_to_defaults(self) -> None:
        """Test SpacyEntityExtractionConfig __post_init__ None to defaults conversion."""
        config = SpacyEntityExtractionConfig(language_models=None)

        # Should be set to default models
        assert config.language_models is not None
        assert isinstance(config.language_models, tuple)
        assert len(config.language_models) > 0

    def test_spacy_config_immutability(self) -> None:
        """Test SpacyEntityExtractionConfig is properly frozen."""
        config = SpacyEntityExtractionConfig()

        # Should raise AttributeError when trying to modify
        with pytest.raises(AttributeError):
            config.max_doc_length = 500000  # type: ignore[misc]

        with pytest.raises(AttributeError):
            config.fallback_to_multilingual = False  # type: ignore[misc]
