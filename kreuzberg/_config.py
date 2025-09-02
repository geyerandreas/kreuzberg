"""Configuration discovery and loading for Kreuzberg.

This module provides configuration loading from both kreuzberg.toml and pyproject.toml files.
Configuration is automatically discovered by searching up the directory tree from the current
working directory.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found]

from kreuzberg._gmft import GMFTConfig
from kreuzberg._ocr._easyocr import EasyOCRConfig
from kreuzberg._ocr._paddleocr import PaddleOCRConfig
from kreuzberg._ocr._tesseract import TesseractConfig
from kreuzberg._types import ExtractionConfig, OcrBackendType
from kreuzberg.exceptions import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, MutableMapping


@dataclass(frozen=True)
class HTMLToMarkdownConfig:
    """Configuration for HTML to Markdown conversion.

    This configuration class provides fine-grained control over how HTML content
    is converted to Markdown format. Most fields have sensible defaults that work
    well for typical document extraction scenarios.
    """

    stream_processing: bool = False
    """Enable streaming mode for processing large HTML documents."""

    chunk_size: int = 1024
    """Size of chunks when stream_processing is enabled."""

    chunk_callback: Callable[[str], None] | None = None
    """Callback function invoked for each chunk during stream processing."""

    progress_callback: Callable[[int, int], None] | None = None
    """Callback function for progress updates (current, total)."""

    parser: str | None = None
    """BeautifulSoup parser to use (e.g., 'html.parser', 'lxml')."""

    autolinks: bool = True
    """Convert URLs to clickable links automatically."""

    bullets: str = "*+-"
    """Characters to use for unordered list bullets."""

    code_language: str = ""
    """Default language for code blocks."""

    code_language_callback: Callable[[Any], str] | None = None
    """Callback to determine code language dynamically."""

    convert: str | Iterable[str] | None = None
    """HTML tags to convert. If None, all supported tags are converted."""

    convert_as_inline: bool = False
    """Convert block elements as inline elements."""

    custom_converters: Mapping[Any, Any] | None = None
    """Custom converters for specific HTML elements."""

    default_title: bool = False
    """Use a default title if none is found."""

    escape_asterisks: bool = True
    """Escape asterisks in text to prevent unintended emphasis."""

    escape_misc: bool = True
    """Escape miscellaneous characters that have special meaning in Markdown."""

    escape_underscores: bool = True
    """Escape underscores in text to prevent unintended emphasis."""

    extract_metadata: bool = True
    """Extract metadata from HTML head section."""

    heading_style: Literal["underlined", "atx", "atx_closed"] = "underlined"
    """Style for markdown headings."""

    highlight_style: Literal["double-equal", "html", "bold"] = "double-equal"
    """Style for highlighting text."""

    keep_inline_images_in: Iterable[str] | None = None
    """HTML tags where inline images should be preserved."""

    newline_style: Literal["spaces", "backslash"] = "spaces"
    """Style for line breaks in markdown."""

    strip: str | Iterable[str] | None = None
    """HTML tags to strip completely from output."""

    strip_newlines: bool = False
    """Strip newlines from the output."""

    strong_em_symbol: Literal["*", "_"] = "*"
    """Symbol to use for strong/emphasis formatting."""

    sub_symbol: str = ""
    """Symbol to use for subscript text."""

    sup_symbol: str = ""
    """Symbol to use for superscript text."""

    wrap: bool = False
    """Enable text wrapping."""

    wrap_width: int = 80
    """Width for text wrapping when wrap is True."""

    preprocess_html: bool = True
    """Enable HTML preprocessing to clean up the input."""

    preprocessing_preset: Literal["minimal", "standard", "aggressive"] = "aggressive"
    """Preprocessing level for cleaning HTML."""

    remove_navigation: bool = True
    """Remove navigation elements from HTML."""

    remove_forms: bool = True
    """Remove form elements from HTML."""

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for passing to convert_to_markdown.

        Excludes None values and handles special cases.
        """
        return {key: value for key, value in self.__dict__.items() if value is not None}


def load_config_from_file(config_path: Path) -> dict[str, Any]:
    """Load configuration from a TOML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Dictionary containing the loaded configuration.

    Raises:
        ValidationError: If the file cannot be read or parsed.
    """
    try:
        with config_path.open("rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError as e:
        raise ValidationError(f"Configuration file not found: {config_path}") from e
    except tomllib.TOMLDecodeError as e:
        raise ValidationError(f"Invalid TOML in configuration file: {e}") from e

    if config_path.name == "kreuzberg.toml":
        return data  # type: ignore[no-any-return]

    if config_path.name == "pyproject.toml" or ("tool" in data and "kreuzberg" in data.get("tool", {})):
        return data.get("tool", {}).get("kreuzberg", {})  # type: ignore[no-any-return]

    return data  # type: ignore[no-any-return]


def merge_configs(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge two configuration dictionaries recursively.

    Args:
        base: Base configuration dictionary.
        override: Configuration dictionary to override base values.

    Returns:
        Merged configuration dictionary.
    """
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def parse_ocr_backend_config(
    config_dict: dict[str, Any], backend: OcrBackendType
) -> TesseractConfig | EasyOCRConfig | PaddleOCRConfig | None:
    """Parse OCR backend-specific configuration.

    Args:
        config_dict: Configuration dictionary.
        backend: The OCR backend type.

    Returns:
        Backend-specific configuration object or None.
    """
    if backend not in config_dict:
        return None

    backend_config = config_dict[backend]
    if not isinstance(backend_config, dict):
        return None

    match backend:
        case "tesseract":
            processed_config = backend_config.copy()
            if "psm" in processed_config and isinstance(processed_config["psm"], int):
                from kreuzberg._ocr._tesseract import PSMMode  # noqa: PLC0415

                processed_config["psm"] = PSMMode(processed_config["psm"])
            return TesseractConfig(**processed_config)
        case "easyocr":
            return EasyOCRConfig(**backend_config)
        case "paddleocr":
            return PaddleOCRConfig(**backend_config)
        case _:
            return None


def build_extraction_config_from_dict(config_dict: dict[str, Any]) -> ExtractionConfig:
    """Build ExtractionConfig from a configuration dictionary.

    Args:
        config_dict: Configuration dictionary from TOML file.

    Returns:
        ExtractionConfig instance.
    """
    extraction_config: dict[str, Any] = {}

    basic_fields = {
        "force_ocr",
        "chunk_content",
        "extract_tables",
        "max_chars",
        "max_overlap",
        "ocr_backend",
        "extract_entities",
        "extract_keywords",
        "auto_detect_language",
        "enable_quality_processing",
        "auto_detect_document_type",
        "document_type_confidence_threshold",
        "document_classification_mode",
        "keyword_count",
    }
    extraction_config = extraction_config | {
        field: config_dict[field] for field in basic_fields if field in config_dict
    }

    ocr_backend = extraction_config.get("ocr_backend")
    if ocr_backend and ocr_backend != "none":
        valid_backends = {"tesseract", "easyocr", "paddleocr"}
        if ocr_backend not in valid_backends:
            raise ValidationError(
                f"Invalid OCR backend: {ocr_backend}. Must be one of: {', '.join(sorted(valid_backends))} or 'none'",
                context={"provided": ocr_backend, "valid": sorted(valid_backends)},
            )
        ocr_config = parse_ocr_backend_config(config_dict, ocr_backend)
        if ocr_config:
            extraction_config["ocr_config"] = ocr_config

    if extraction_config.get("extract_tables") and "gmft" in config_dict and isinstance(config_dict["gmft"], dict):
        extraction_config["gmft_config"] = GMFTConfig(**config_dict["gmft"])

    if "html_to_markdown" in config_dict and isinstance(config_dict["html_to_markdown"], dict):
        extraction_config["html_to_markdown_config"] = HTMLToMarkdownConfig(**config_dict["html_to_markdown"])

    if extraction_config.get("ocr_backend") == "none":
        extraction_config["ocr_backend"] = None

    return ExtractionConfig(**extraction_config)


def find_config_file(start_path: Path | None = None) -> Path | None:
    """Find configuration file by searching up the directory tree.

    Searches for configuration files in the following order:
    1. kreuzberg.toml
    2. pyproject.toml (with [tool.kreuzberg] section)

    Args:
        start_path: Directory to start searching from. Defaults to current working directory.

    Returns:
        Path to the configuration file or None if not found.
    """
    current = start_path or Path.cwd()

    while current != current.parent:
        kreuzberg_toml = current / "kreuzberg.toml"
        if kreuzberg_toml.exists():
            return kreuzberg_toml

        pyproject_toml = current / "pyproject.toml"
        if pyproject_toml.exists():
            try:
                with pyproject_toml.open("rb") as f:
                    data = tomllib.load(f)
                if "tool" in data and "kreuzberg" in data["tool"]:
                    return pyproject_toml
            except Exception:  # noqa: BLE001
                pass

        current = current.parent
    return None


def load_default_config(start_path: Path | None = None) -> ExtractionConfig | None:
    """Load the default configuration from discovered config file.

    Args:
        start_path: Directory to start searching from. Defaults to current working directory.

    Returns:
        ExtractionConfig instance or None if no configuration found.
    """
    config_path = find_config_file(start_path)
    if not config_path:
        return None

    try:
        config_dict = load_config_from_file(config_path)
        if not config_dict:
            return None
        return build_extraction_config_from_dict(config_dict)
    except Exception:  # noqa: BLE001
        return None


def load_config_from_path(config_path: Path | str) -> ExtractionConfig:
    """Load configuration from a specific file path.

    Args:
        config_path: Path to the configuration file.

    Returns:
        ExtractionConfig instance.

    Raises:
        ValidationError: If the file cannot be read, parsed, or is invalid.
    """
    path = Path(config_path)
    config_dict = load_config_from_file(path)
    return build_extraction_config_from_dict(config_dict)


def discover_and_load_config(start_path: Path | str | None = None) -> ExtractionConfig:
    """Load configuration by discovering config files in the directory tree.

    Args:
        start_path: Directory to start searching from. Defaults to current working directory.

    Returns:
        ExtractionConfig instance.

    Raises:
        ValidationError: If no configuration file is found or if the file is invalid.
    """
    search_path = Path(start_path) if start_path else None
    config_path = find_config_file(search_path)

    if not config_path:
        raise ValidationError(
            "No configuration file found. Searched for 'kreuzberg.toml' and 'pyproject.toml' with [tool.kreuzberg] section.",
            context={"search_path": str(search_path or Path.cwd())},
        )

    config_dict = load_config_from_file(config_path)
    if not config_dict:
        raise ValidationError(
            f"Configuration file found but contains no Kreuzberg configuration: {config_path}",
            context={"config_path": str(config_path)},
        )

    return build_extraction_config_from_dict(config_dict)


def try_discover_config(start_path: Path | str | None = None) -> ExtractionConfig | None:
    """Try to discover and load configuration, returning None if not found.

    Args:
        start_path: Directory to start searching from. Defaults to current working directory.

    Returns:
        ExtractionConfig instance or None if no configuration found.
    """
    try:
        return discover_and_load_config(start_path)
    except ValidationError:
        return None


_CONFIG_FIELDS = [
    "force_ocr",
    "chunk_content",
    "extract_tables",
    "max_chars",
    "max_overlap",
    "ocr_backend",
    "extract_entities",
    "extract_keywords",
    "auto_detect_language",
    "enable_quality_processing",
    "auto_detect_document_type",
    "document_type_confidence_threshold",
    "document_classification_mode",
    "keyword_count",
]


def _merge_file_config(config_dict: dict[str, Any], file_config: dict[str, Any]) -> None:
    """Merge file configuration into config dictionary."""
    if not file_config:
        return

    for field in _CONFIG_FIELDS:
        if field in file_config:
            config_dict[field] = file_config[field]


def _merge_cli_args(config_dict: dict[str, Any], cli_args: MutableMapping[str, Any]) -> None:
    """Merge CLI arguments into config dictionary."""
    for field in _CONFIG_FIELDS:
        if field in cli_args and cli_args[field] is not None:
            config_dict[field] = cli_args[field]


def _build_ocr_config_from_cli(
    ocr_backend: str, cli_args: MutableMapping[str, Any]
) -> TesseractConfig | EasyOCRConfig | PaddleOCRConfig | None:
    """Build OCR config from CLI arguments."""
    config_key = f"{ocr_backend}_config"
    if not cli_args.get(config_key):
        return None

    backend_args = cli_args[config_key]
    if ocr_backend == "tesseract":
        return TesseractConfig(**backend_args)
    if ocr_backend == "easyocr":
        return EasyOCRConfig(**backend_args)
    if ocr_backend == "paddleocr":
        return PaddleOCRConfig(**backend_args)
    return None


def _configure_ocr_backend(
    config_dict: dict[str, Any],
    file_config: dict[str, Any],
    cli_args: MutableMapping[str, Any],
) -> None:
    """Configure OCR backend in config dictionary."""
    ocr_backend = config_dict.get("ocr_backend")
    if not ocr_backend or ocr_backend == "none":
        return

    ocr_config = _build_ocr_config_from_cli(ocr_backend, cli_args)
    if not ocr_config and file_config:
        ocr_config = parse_ocr_backend_config(file_config, ocr_backend)

    if ocr_config:
        config_dict["ocr_config"] = ocr_config


def _configure_gmft(
    config_dict: dict[str, Any],
    file_config: dict[str, Any],
    cli_args: MutableMapping[str, Any],
) -> None:
    """Configure GMFT in config dictionary."""
    if not config_dict.get("extract_tables"):
        return

    gmft_config = None
    if cli_args.get("gmft_config"):
        gmft_config = GMFTConfig(**cli_args["gmft_config"])
    elif "gmft" in file_config and isinstance(file_config["gmft"], dict):
        gmft_config = GMFTConfig(**file_config["gmft"])

    if gmft_config:
        config_dict["gmft_config"] = gmft_config


def build_extraction_config(
    file_config: dict[str, Any],
    cli_args: MutableMapping[str, Any],
) -> ExtractionConfig:
    """Build ExtractionConfig from file config and CLI arguments.

    Args:
        file_config: Configuration loaded from file.
        cli_args: CLI arguments.

    Returns:
        ExtractionConfig instance.
    """
    config_dict: dict[str, Any] = {}

    _merge_file_config(config_dict, file_config)
    _merge_cli_args(config_dict, cli_args)

    _configure_ocr_backend(config_dict, file_config, cli_args)
    _configure_gmft(config_dict, file_config, cli_args)

    if config_dict.get("ocr_backend") == "none":
        config_dict["ocr_backend"] = None

    return ExtractionConfig(**config_dict)


def find_default_config() -> Path | None:
    """Find the default configuration file (pyproject.toml).

    Returns:
        Path to the configuration file or None if not found.

    Note:
        This function is deprecated. Use find_config_file() instead.
    """
    return find_config_file()
