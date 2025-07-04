from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from kreuzberg._types import Entity
from kreuzberg.exceptions import MissingDependencyError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


@dataclass(unsafe_hash=True, frozen=True)
class SpacyEntityExtractionConfig:
    """Configuration for spaCy-based entity extraction."""

    model_cache_dir: str | Path | None = None
    """Directory to cache spaCy models. If None, uses spaCy's default."""

    language_models: dict[str, str] | tuple[tuple[str, str], ...] | None = None
    """Mapping of language codes to spaCy model names.

    If None, uses default mappings:
    - en: en_core_web_sm
    - de: de_core_news_sm
    - fr: fr_core_news_sm
    - es: es_core_news_sm
    - pt: pt_core_news_sm
    - it: it_core_news_sm
    - nl: nl_core_news_sm
    - zh: zh_core_web_sm
    - ja: ja_core_news_sm
    """

    fallback_to_multilingual: bool = True
    """If True and language-specific model fails, try xx_ent_wiki_sm (multilingual)."""

    max_doc_length: int = 1000000
    """Maximum document length for spaCy processing."""

    batch_size: int = 1000
    """Batch size for processing multiple texts."""

    def __post_init__(self) -> None:
        if self.language_models is None:
            object.__setattr__(self, "language_models", self._get_default_language_models())

        if isinstance(self.language_models, dict):
            object.__setattr__(self, "language_models", tuple(sorted(self.language_models.items())))

    @staticmethod
    def _get_default_language_models() -> dict[str, str]:
        """Get default language model mappings based on available spaCy models."""
        return {
            "en": "en_core_web_sm",
            "de": "de_core_news_sm",
            "fr": "fr_core_news_sm",
            "es": "es_core_news_sm",
            "pt": "pt_core_news_sm",
            "it": "it_core_news_sm",
            "nl": "nl_core_news_sm",
            "zh": "zh_core_web_sm",
            "ja": "ja_core_news_sm",
            "ko": "ko_core_news_sm",
            "ru": "ru_core_news_sm",
            "pl": "pl_core_news_sm",
            "ro": "ro_core_news_sm",
            "el": "el_core_news_sm",
            "da": "da_core_news_sm",
            "fi": "fi_core_news_sm",
            "nb": "nb_core_news_sm",
            "sv": "sv_core_news_sm",
            "ca": "ca_core_news_sm",
            "hr": "hr_core_news_sm",
            "lt": "lt_core_news_sm",
            "mk": "mk_core_news_sm",
            "sl": "sl_core_news_sm",
            "uk": "uk_core_news_sm",
        }

    def get_model_for_language(self, language_code: str) -> str | None:
        """Get the appropriate spaCy model for a language code."""
        if not self.language_models:
            return None

        models_dict = dict(self.language_models) if isinstance(self.language_models, tuple) else self.language_models

        if language_code in models_dict:
            return models_dict[language_code]

        base_lang = language_code.split("-")[0].lower()
        if base_lang in models_dict:
            return models_dict[base_lang]

        return None

    def get_fallback_model(self) -> str | None:
        """Get fallback multilingual model if enabled."""
        return "xx_ent_wiki_sm" if self.fallback_to_multilingual else None


def extract_entities(
    text: str,
    entity_types: Sequence[str] = ("PERSON", "ORGANIZATION", "LOCATION", "DATE", "EMAIL", "PHONE"),
    custom_patterns: frozenset[tuple[str, str]] | None = None,
    languages: list[str] | None = None,
    spacy_config: SpacyEntityExtractionConfig | None = None,
) -> list[Entity]:
    """Extract entities from text using custom regex patterns and/or a NER model.

    Args:
        text: The input text to extract entities from.
        entity_types: List of entity types to extract using the NER model.
        custom_patterns: Tuple mapping entity types to regex patterns for custom extraction.
        languages: List of detected languages to choose appropriate spaCy models.
        spacy_config: Configuration for spaCy entity extraction.

    Returns:
        list[Entity]: A list of extracted Entity objects with type, text, start, and end positions.

    Raises:
        MissingDependencyError: If `spacy` is not installed.
    """
    entities: list[Entity] = []
    if custom_patterns:
        custom_patterns_dict = dict(custom_patterns)
        for ent_type, pattern in custom_patterns_dict.items():
            entities.extend(
                Entity(type=ent_type, text=match.group(), start=match.start(), end=match.end())
                for match in re.finditer(pattern, text)
            )

    if spacy_config is None:
        spacy_config = SpacyEntityExtractionConfig()

    try:
        import spacy  # noqa: F401
    except ImportError as e:
        raise MissingDependencyError.create_for_package(
            package_name="spacy",
            dependency_group="entity-extraction",
            functionality="Entity Extraction",
        ) from e

    model_name = _select_spacy_model(languages, spacy_config)
    if not model_name:
        return entities

    nlp = _load_spacy_model(model_name, spacy_config)
    if not nlp:
        return entities

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
    """Load a spaCy model with caching."""
    try:
        import spacy

        if spacy_config.model_cache_dir:
            import os

            os.environ["SPACY_DATA"] = str(spacy_config.model_cache_dir)

        nlp = spacy.load(model_name)

        nlp.max_length = spacy_config.max_doc_length

        return nlp
    except (OSError, ImportError):
        return None


def _select_spacy_model(languages: list[str] | None, spacy_config: SpacyEntityExtractionConfig) -> str | None:
    """Select the best spaCy model based on detected languages."""
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

        kw_model = KeyBERT()
        keywords = kw_model.extract_keywords(text, top_n=keyword_count)
        return [(kw, float(score)) for kw, score in keywords]
    except (RuntimeError, OSError, ValueError):
        return []
    except ImportError as e:
        raise MissingDependencyError.create_for_package(
            package_name="keybert",
            dependency_group="entity-extraction",
            functionality="Keyword Extraction",
        ) from e
