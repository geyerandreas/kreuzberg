from __future__ import annotations

import re
from typing import TYPE_CHECKING

from kreuzberg import MissingDependencyError
from kreuzberg._types import Entity

if TYPE_CHECKING:
    from collections.abc import Sequence


def extract_entities(
    text: str,
    entity_types: Sequence[str] = ("PERSON", "ORGANIZATION", "LOCATION", "DATE", "EMAIL", "PHONE"),
    custom_patterns: frozenset[tuple[str, str]] | None = None,
) -> list[Entity]:
    """Extract entities from text using custom regex patterns and/or a NER model.

    Args:
        text: The input text to extract entities from.
        entity_types: List of entity types to extract using the NER model.
        custom_patterns: Tuple mapping entity types to regex patterns for custom extraction.

    Returns:
        list[Entity]: A list of extracted Entity objects with type, text, start, and end positions.

    Raises:
        MissingDependencyError: If `gliner` is not installed.
    """
    entities: list[Entity] = []
    if custom_patterns:
        custom_patterns_dict = dict(custom_patterns)
        for ent_type, pattern in custom_patterns_dict.items():
            entities.extend(
                Entity(type=ent_type, text=match.group(), start=match.start(), end=match.end())
                for match in re.finditer(pattern, text)
            )

    try:
        from gliner import GLiNER
    except ImportError as e:
        raise MissingDependencyError.create_for_package(
            package_name="gliner",
            dependency_group="entity-extraction",
            functionality="Entity Extraction",
        ) from e

    try:
        ner_model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
        results = ner_model.predict_entities(text, list(entity_types))
        entities.extend(
            Entity(
                type=ent["label"],
                text=ent["text"],
                start=ent["start"],
                end=ent["end"],
            )
            for ent in results
        )
    except (RuntimeError, OSError, ValueError):
        pass
    return entities


def extract_keywords(
    text: str,
    keyword_count: int = 10,
) -> list[tuple[str, float]]:
    """Extract keywords from text using the KeyBERT model.

    Args:
        text: The input text to extract keywords from.
        keyword_count: Number of top keywords to return. Defaults to 10.

    Returns:
        list[tuple[str, float]]: A list of tuples containing keywords and their relevance scores.

    Raises:
        MissingDependencyError: If `keybert` is not installed.
    """
    try:
        from keybert import KeyBERT
    except ImportError as e:
        raise MissingDependencyError.create_for_package(
            package_name="keybert",
            dependency_group="entity-extraction",
            functionality="Keyword Extraction",
        ) from e

    try:
        kw_model = KeyBERT()
        keywords = kw_model.extract_keywords(text, top_n=keyword_count)
        return [(kw, float(score)) for kw, score in keywords]
    except (RuntimeError, OSError, ValueError):
        return []
