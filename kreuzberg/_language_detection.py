from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from kreuzberg.exceptions import MissingDependencyError

if TYPE_CHECKING:
    from fast_langdetect import LangDetectConfig as FastLangDetectConfig

try:
    from fast_langdetect import LangDetectConfig as FastLangDetectConfig
    from fast_langdetect import detect, detect_multilingual

    HAS_FAST_LANGDETECT = True
except ImportError:
    HAS_FAST_LANGDETECT = False
    detect = None
    detect_multilingual = None
    FastLangDetectConfig = None

_CACHE_SIZE = 128


@dataclass(frozen=True)
class LanguageDetectionConfig:
    """Configuration for language detection.

    Attributes:
        low_memory: If True, uses a smaller model (~200MB). If False, uses a larger, more accurate model.
            Defaults to True for better memory efficiency.
        top_k: Maximum number of languages to return for multilingual detection. Defaults to 3.
        multilingual: If True, uses multilingual detection to handle mixed-language text.
            If False, uses single language detection. Defaults to False.
        cache_dir: Custom directory for model cache. If None, uses system default.
        allow_fallback: If True, falls back to small model if large model fails. Defaults to True.
    """

    low_memory: bool = True
    top_k: int = 3
    multilingual: bool = False
    cache_dir: str | None = None
    allow_fallback: bool = True


def _create_fast_langdetect_config(config: LanguageDetectionConfig) -> FastLangDetectConfig | None:
    """Create FastLangDetectConfig from our config."""
    if not HAS_FAST_LANGDETECT or FastLangDetectConfig is None:
        return None

    kwargs: dict[str, Any] = {
        "allow_fallback": config.allow_fallback,
    }
    if config.cache_dir is not None:
        kwargs["cache_dir"] = config.cache_dir

    return FastLangDetectConfig(**kwargs)


@lru_cache(maxsize=_CACHE_SIZE)
def detect_languages(text: str, config: LanguageDetectionConfig | None = None) -> list[str] | None:
    """Detect the most probable languages in the given text using fast-langdetect.

    Args:
        text: The text to analyze.
        config: Configuration for language detection. If None, uses defaults.

    Returns:
        A list of detected language codes in lowercase (e.g., ['en', 'de', 'fr']),
        or None if detection fails.

    Raises:
        MissingDependencyError: If fast-langdetect is not installed.
    """
    if not HAS_FAST_LANGDETECT or detect is None or detect_multilingual is None:
        raise MissingDependencyError.create_for_package(
            dependency_group="langdetect", functionality="language detection", package_name="fast-langdetect"
        )

    if config is None:
        config = LanguageDetectionConfig()

    try:
        if config.multilingual:
            results = detect_multilingual(text, low_memory=config.low_memory, k=config.top_k)

            return [result["lang"].lower() for result in results if result.get("lang")]

        result = detect(text, low_memory=config.low_memory)
        if result and result.get("lang"):
            return [result["lang"].lower()]
        return None
    except Exception:  # noqa: BLE001
        return None
