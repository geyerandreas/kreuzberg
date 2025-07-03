from __future__ import annotations

import sys
from typing import Any

import pytest

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
def test_custom_entity_patterns(custom_patterns: frozenset[tuple[str, str]] | None, expected: list[Entity]) -> None:
    entities = ee.extract_entities(SAMPLE_TEXT, entity_types=(), custom_patterns=custom_patterns)
    assert all(isinstance(e, Entity) for e in entities)
    if expected:
        assert any(e.type == "EMAIL" and e.text == "john@example.com" for e in entities)
    else:
        assert entities == expected


def test_extract_entities_with_gliner() -> None:
    class DummyModel:
        def predict_entities(self, _text: str, _types: list[str]) -> list[dict[str, Any]]:
            return [
                {"label": "PERSON", "text": "John Doe", "start": 0, "end": 8},
                {"label": "LOCATION", "text": "Berlin", "start": 18, "end": 24},
            ]

    result = ee.extract_entities(SAMPLE_TEXT, entity_types=["PERSON", "LOCATION"], model=DummyModel())
    assert any(e.type == "PERSON" and e.text == "John Doe" for e in result)
    assert any(e.type == "LOCATION" and e.text == "Berlin" for e in result)
    assert all(isinstance(e, Entity) for e in result)


def test_extract_keywords_with_keybert() -> None:
    class DummyModel:
        def extract_keywords(self, _text: str, top_n: int = 10) -> list[tuple[str, float]]:
            if top_n == 2:
                return [("Berlin", 0.9), ("John Doe", 0.8)]
            return [("keyword", 0.5)] * top_n

    result = ee.extract_keywords(SAMPLE_TEXT, keyword_count=2, model=DummyModel())
    assert result == [("Berlin", 0.9), ("John Doe", 0.8)]


def test_extract_entities_missing_gliner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "gliner", None)
    result = ee.extract_entities(SAMPLE_TEXT, entity_types=["PERSON"])
    assert result == []


def test_extract_keywords_missing_keybert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "keybert", None)
    result = ee.extract_keywords(SAMPLE_TEXT, keyword_count=5)
    assert result == []
