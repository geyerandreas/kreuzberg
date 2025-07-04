from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

from kreuzberg import MissingDependencyError
from kreuzberg import _entity_extraction as ee
from kreuzberg._types import Entity

SAMPLE_TEXT = "John Doe visited Berlin on 2023-01-01. Contact: john@example.com or +49-123-4567."


@pytest.mark.parametrize(
    "custom_patterns,expected",
    [
        (None, []),
        ({"INVOICE_ID": r"INV-\d+"}, []),
        (
            {"EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"},
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
