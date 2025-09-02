"""Configuration discovery and loading for Kreuzberg.

This module provides configuration loading from both kreuzberg.toml and pyproject.toml files.
Configuration is automatically discovered by searching up the directory tree from the current
working directory.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found]

from kreuzberg._gmft import GMFTConfig
from kreuzberg._ocr._easyocr import EasyOCRConfig
from kreuzberg._ocr._paddleocr import PaddleOCRConfig
from kreuzberg._ocr._tesseract import TesseractConfig
from kreuzberg._types import ExtractionConfig, HTMLToMarkdownConfig, OcrBackendType
from kreuzberg.exceptions import ValidationError

if TYPE_CHECKING:
    from collections.abc import MutableMapping

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

_VALID_OCR_BACKENDS = {"tesseract", "easyocr", "paddleocr"}


def _merge_file_config(config_dict: dict[str, Any], file_config: dict[str, Any]) -> None:
    if not file_config:
        return
    for field in _CONFIG_FIELDS:
        if field in file_config:
            config_dict[field] = file_config[field]


def _merge_cli_args(config_dict: dict[str, Any], cli_args: MutableMapping[str, Any]) -> None:
    for field in _CONFIG_FIELDS:
        if field in cli_args and cli_args[field] is not None:
            config_dict[field] = cli_args[field]


def _build_ocr_config_from_cli(
    ocr_backend: str, cli_args: MutableMapping[str, Any]
) -> TesseractConfig | EasyOCRConfig | PaddleOCRConfig | None:
    config_key = f"{ocr_backend}_config"
    if not cli_args.get(config_key):
        return None

    backend_args = cli_args[config_key]
    try:
        match ocr_backend:
            case "tesseract":
                return TesseractConfig(**backend_args)
            case "easyocr":
                return EasyOCRConfig(**backend_args)
            case "paddleocr":
                return PaddleOCRConfig(**backend_args)
            case _:
                return None
    except (TypeError, ValueError) as e:
        raise ValidationError(
            f"Invalid {ocr_backend} configuration from CLI: {e}",
            context={"backend": ocr_backend, "config": backend_args, "error": str(e)},
        ) from e


def _configure_ocr_backend(
    config_dict: dict[str, Any],
    file_config: dict[str, Any],
    cli_args: MutableMapping[str, Any],
) -> None:
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
    if not config_dict.get("extract_tables"):
        return

    gmft_config = None
    try:
        if cli_args.get("gmft_config"):
            gmft_config = GMFTConfig(**cli_args["gmft_config"])
        elif "gmft" in file_config and isinstance(file_config["gmft"], dict):
            gmft_config = GMFTConfig(**file_config["gmft"])
    except (TypeError, ValueError) as e:
        raise ValidationError(
            f"Invalid GMFT configuration: {e}",
            context={"gmft_config": cli_args.get("gmft_config") or file_config.get("gmft"), "error": str(e)},
        ) from e

    if gmft_config:
        config_dict["gmft_config"] = gmft_config


def _create_ocr_config(
    backend: str, backend_config: dict[str, Any]
) -> TesseractConfig | EasyOCRConfig | PaddleOCRConfig:
    match backend:
        case "tesseract":
            processed_config = backend_config.copy()
            if "psm" in processed_config and isinstance(processed_config["psm"], int):
                from kreuzberg._ocr._tesseract import PSMMode  # noqa: PLC0415

                try:
                    processed_config["psm"] = PSMMode(processed_config["psm"])
                except ValueError as e:
                    raise ValidationError(
                        f"Invalid PSM mode value: {processed_config['psm']}",
                        context={"psm_value": processed_config["psm"], "error": str(e)},
                    ) from e
            return TesseractConfig(**processed_config)
        case "easyocr":
            return EasyOCRConfig(**backend_config)
        case "paddleocr":
            return PaddleOCRConfig(**backend_config)
        case _:
            raise ValueError(f"Unknown backend: {backend}")


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

    if config_path.name == "pyproject.toml":
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

    Raises:
        ValidationError: If the backend configuration is invalid.
    """
    if backend not in config_dict:
        return None

    backend_config = config_dict[backend]
    if not isinstance(backend_config, dict):
        raise ValidationError(
            f"Invalid configuration for OCR backend '{backend}': expected dict, got {type(backend_config).__name__}",
            context={"backend": backend, "config_type": type(backend_config).__name__},
        )

    try:
        return _create_ocr_config(backend, backend_config)
    except (TypeError, ValueError) as e:
        raise ValidationError(
            f"Invalid configuration for OCR backend '{backend}': {e}",
            context={"backend": backend, "config": backend_config, "error": str(e)},
        ) from e


def build_extraction_config_from_dict(config_dict: dict[str, Any]) -> ExtractionConfig:
    """Build ExtractionConfig from a configuration dictionary.

    Args:
        config_dict: Configuration dictionary from TOML file.

    Returns:
        ExtractionConfig instance.

    Raises:
        ValidationError: If the configuration is invalid.
    """
    extraction_config: dict[str, Any] = {field: config_dict[field] for field in _CONFIG_FIELDS if field in config_dict}

    ocr_backend = extraction_config.get("ocr_backend")
    if ocr_backend and ocr_backend != "none":
        if ocr_backend not in _VALID_OCR_BACKENDS:
            raise ValidationError(
                f"Invalid OCR backend: {ocr_backend}. Must be one of: {', '.join(sorted(_VALID_OCR_BACKENDS))} or 'none'",
                context={"provided": ocr_backend, "valid": sorted(_VALID_OCR_BACKENDS)},
            )
        ocr_config = parse_ocr_backend_config(config_dict, ocr_backend)
        if ocr_config:
            extraction_config["ocr_config"] = ocr_config

    if extraction_config.get("extract_tables") and "gmft" in config_dict and isinstance(config_dict["gmft"], dict):
        try:
            extraction_config["gmft_config"] = GMFTConfig(**config_dict["gmft"])
        except (TypeError, ValueError) as e:
            raise ValidationError(
                f"Invalid GMFT configuration: {e}",
                context={"gmft_config": config_dict["gmft"], "error": str(e)},
            ) from e

    if "html_to_markdown" in config_dict and isinstance(config_dict["html_to_markdown"], dict):
        try:
            extraction_config["html_to_markdown_config"] = HTMLToMarkdownConfig(**config_dict["html_to_markdown"])
        except (TypeError, ValueError) as e:
            raise ValidationError(
                f"Invalid HTML to Markdown configuration: {e}",
                context={"html_to_markdown_config": config_dict["html_to_markdown"], "error": str(e)},
            ) from e

    if extraction_config.get("ocr_backend") == "none":
        extraction_config["ocr_backend"] = None

    try:
        return ExtractionConfig(**extraction_config)
    except (TypeError, ValueError) as e:
        raise ValidationError(
            f"Invalid extraction configuration: {e}",
            context={"config": extraction_config, "error": str(e)},
        ) from e


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

    Raises:
        ValidationError: If the combined configuration is invalid.
    """
    config_dict: dict[str, Any] = {}

    _merge_file_config(config_dict, file_config)
    _merge_cli_args(config_dict, cli_args)

    _configure_ocr_backend(config_dict, file_config, cli_args)
    _configure_gmft(config_dict, file_config, cli_args)

    if config_dict.get("ocr_backend") == "none":
        config_dict["ocr_backend"] = None

    try:
        return ExtractionConfig(**config_dict)
    except (TypeError, ValueError) as e:
        raise ValidationError(
            f"Invalid extraction configuration: {e}",
            context={"config": config_dict, "error": str(e)},
        ) from e


def find_config_file(start_path: Path | None = None) -> Path | None:
    """Find configuration file by searching up the directory tree.

    Searches for configuration files in the following order:
    1. kreuzberg.toml
    2. pyproject.toml (with [tool.kreuzberg] section)

    Args:
        start_path: Directory to start searching from. Defaults to current working directory.

    Returns:
        Path to the configuration file or None if not found.

    Raises:
        ValidationError: If a config file exists but cannot be read or has invalid TOML.
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
            except OSError as e:
                raise ValidationError(
                    f"Failed to read pyproject.toml: {e}",
                    context={"file": str(pyproject_toml), "error": str(e)},
                ) from e
            except tomllib.TOMLDecodeError as e:
                raise ValidationError(
                    f"Invalid TOML in pyproject.toml: {e}",
                    context={"file": str(pyproject_toml), "error": str(e)},
                ) from e

        current = current.parent
    return None


def load_default_config(start_path: Path | None = None) -> ExtractionConfig | None:
    """Load the default configuration from discovered config file.

    Args:
        start_path: Directory to start searching from. Defaults to current working directory.

    Returns:
        ExtractionConfig instance or None if no configuration found.

    Raises:
        ValidationError: If configuration file exists but contains invalid configuration.
    """
    config_path = find_config_file(start_path)
    if not config_path:
        return None

    config_dict = load_config_from_file(config_path)
    if not config_dict:
        return None
    return build_extraction_config_from_dict(config_dict)


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
    """Try to discover and load configuration, returning None if no config file found.

    If a config file is found, attempts to load it. Any errors during loading will bubble up.

    Args:
        start_path: Directory to start searching from. Defaults to current working directory.

    Returns:
        ExtractionConfig instance or None if no configuration file found.

    Raises:
        ValidationError: If a configuration file exists but is invalid.
    """
    search_path = Path(start_path) if start_path else None
    config_path = find_config_file(search_path)

    if not config_path:
        return None

    # Config file exists - load it and let any errors bubble up
    config_dict = load_config_from_file(config_path)
    if not config_dict:
        return None
    return build_extraction_config_from_dict(config_dict)


def find_default_config() -> Path | None:
    """Find the default configuration file (pyproject.toml).

    Returns:
        Path to the configuration file or None if not found.

    Note:
        This function is deprecated. Use find_config_file() instead.
    """
    return find_config_file()
