"""Configuration parsing for the CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

from kreuzberg._gmft import GMFTConfig
from kreuzberg._ocr._easyocr import EasyOCRConfig
from kreuzberg._ocr._paddleocr import PaddleOCRConfig
from kreuzberg._ocr._tesseract import TesseractConfig
from kreuzberg._types import ExtractionConfig, OcrBackendType
from kreuzberg.exceptions import ValidationError

if TYPE_CHECKING:
    from collections.abc import MutableMapping


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

    return data.get("tool", {}).get("kreuzberg", {})  # type: ignore[no-any-return]


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

    if backend == "tesseract":
        return TesseractConfig(**backend_config)
    if backend == "easyocr":
        return EasyOCRConfig(**backend_config)
    if backend == "paddleocr":
        return PaddleOCRConfig(**backend_config)
    return None


def build_extraction_config(  # noqa: C901, PLR0912
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

    if file_config:
        for field in ["force_ocr", "chunk_content", "extract_tables", "max_chars", "max_overlap", "ocr_backend"]:
            if field in file_config:
                config_dict[field] = file_config[field]

    for field in ["force_ocr", "chunk_content", "extract_tables", "max_chars", "max_overlap", "ocr_backend"]:
        cli_key = field
        if cli_key in cli_args and cli_args[cli_key] is not None:
            config_dict[field] = cli_args[cli_key]

    ocr_backend = config_dict.get("ocr_backend")
    if ocr_backend and ocr_backend != "none":
        ocr_config = None

        if cli_args.get(f"{ocr_backend}_config"):
            backend_args = cli_args[f"{ocr_backend}_config"]
            if ocr_backend == "tesseract":
                ocr_config = TesseractConfig(**backend_args)
            elif ocr_backend == "easyocr":
                ocr_config = EasyOCRConfig(**backend_args)  # type: ignore[assignment]
            elif ocr_backend == "paddleocr":
                ocr_config = PaddleOCRConfig(**backend_args)  # type: ignore[assignment]

        if not ocr_config and file_config:
            ocr_config = parse_ocr_backend_config(file_config, ocr_backend)  # type: ignore[assignment]

        if ocr_config:
            config_dict["ocr_config"] = ocr_config

    if config_dict.get("extract_tables"):
        gmft_config = None

        if cli_args.get("gmft_config"):
            gmft_config = GMFTConfig(**cli_args["gmft_config"])

        elif "gmft" in file_config and isinstance(file_config["gmft"], dict):
            gmft_config = GMFTConfig(**file_config["gmft"])

        if gmft_config:
            config_dict["gmft_config"] = gmft_config

    if config_dict.get("ocr_backend") == "none":
        config_dict["ocr_backend"] = None

    return ExtractionConfig(**config_dict)


def find_default_config() -> Path | None:
    """Find the default configuration file (pyproject.toml).

    Returns:
        Path to the configuration file or None if not found.
    """
    current = Path.cwd()
    while current != current.parent:
        config_path = current / "pyproject.toml"
        if config_path.exists():
            try:
                with config_path.open("rb") as f:
                    data = tomllib.load(f)
                if "tool" in data and "kreuzberg" in data["tool"]:
                    return config_path
            except Exception:  # noqa: BLE001
                pass
        current = current.parent
    return None
