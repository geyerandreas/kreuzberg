from __future__ import annotations

import os
import re
import subprocess
import sys
from functools import lru_cache
from itertools import chain
from typing import TYPE_CHECKING, Any

from kreuzberg._types import Entity, SpacyEntityExtractionConfig
from kreuzberg.exceptions import KreuzbergError, MissingDependencyError

if TYPE_CHECKING:
    from collections.abc import Sequence


def extract_entities(
    text: str,
    entity_types: Sequence[str] = ("PERSON", "ORGANIZATION", "LOCATION", "DATE", "EMAIL", "PHONE"),
    custom_patterns: frozenset[tuple[str, str]] | None = None,
    languages: list[str] | None = None,
    spacy_config: SpacyEntityExtractionConfig | None = None,
) -> list[Entity]:
    entities: list[Entity] = []
    if custom_patterns:
        entities.extend(
            chain.from_iterable(
                (
                    Entity(type=ent_type, text=match.group(), start=match.start(), end=match.end())
                    for match in re.finditer(pattern, text)
                )
                for ent_type, pattern in custom_patterns
            )
        )

    if spacy_config is None:
        spacy_config = SpacyEntityExtractionConfig()

    try:
        import spacy  # noqa: F401, PLC0415
    except ImportError as e:  # pragma: no cover
        raise MissingDependencyError.create_for_package(
            package_name="spacy",
            dependency_group="entity-extraction",
            functionality="Entity Extraction",
        ) from e

    model_name = _select_spacy_model(languages, spacy_config)
    if not model_name:
        return entities

    nlp = _load_spacy_model(model_name, spacy_config)

    if len(text) > spacy_config.max_doc_length:
        text = text[: spacy_config.max_doc_length]

    doc = nlp(text)

    entity_type_mapping = {etype.upper() for etype in entity_types}

    entities.extend(
        Entity(
            type=ent.label_,
            text=ent.text,
            start=ent.start_char,
            end=ent.end_char,
        )
        for ent in doc.ents
        if ent.label_ in entity_type_mapping or ent.label_.upper() in entity_type_mapping
    )

    return entities


@lru_cache(maxsize=32)
def _load_spacy_model(model_name: str, spacy_config: SpacyEntityExtractionConfig) -> Any:
    try:
        import spacy  # noqa: PLC0415
    except ImportError:
        return None

    if spacy_config.model_cache_dir:
        os.environ["SPACY_DATA"] = str(spacy_config.model_cache_dir)

    try:
        nlp = spacy.load(model_name)
    except OSError:
        result = subprocess.run(
            [sys.executable, "-m", "spacy", "download", model_name],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error_msg = (
                f"Failed to download spaCy model '{model_name}'. "
                f"Please install it manually with: python -m spacy download {model_name}"
            )
            if result.stderr:
                error_msg += f"\nError details: {result.stderr}"
            raise KreuzbergError(
                error_msg, context={"model": model_name, "stderr": result.stderr, "return_code": result.returncode}
            ) from None

        try:
            nlp = spacy.load(model_name)
        except OSError as e:
            raise KreuzbergError(
                f"Failed to load spaCy model '{model_name}' even after successful download. "
                f"Please verify your spaCy installation and try reinstalling the model.",
                context={"model": model_name, "error": str(e)},
            ) from e

    nlp.max_length = spacy_config.max_doc_length

    return nlp


def _select_spacy_model(languages: list[str] | None, spacy_config: SpacyEntityExtractionConfig) -> str | None:
    if not languages:
        return spacy_config.get_model_for_language("en")

    for lang in languages:
        model_name = spacy_config.get_model_for_language(lang)
        if model_name:
            return model_name

    return spacy_config.get_fallback_model()


def extract_keywords(
    text: str,
    keyword_count: int = 10,
) -> list[tuple[str, float]]:
    try:
        from keybert import KeyBERT  # noqa: PLC0415

        kw_model = KeyBERT()
        keywords = kw_model.extract_keywords(text, top_n=keyword_count)
        return [(kw, float(score)) for kw, score in keywords]
    except (RuntimeError, OSError, ValueError):
        return []
    except ImportError as e:  # pragma: no cover
        raise MissingDependencyError.create_for_package(
            package_name="keybert",
            dependency_group="entity-extraction",
            functionality="Keyword Extraction",
        ) from e
