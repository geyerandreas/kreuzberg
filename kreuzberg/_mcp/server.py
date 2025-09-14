from __future__ import annotations

import base64
import contextlib
import json
from typing import Any

import msgspec
from mcp.server import FastMCP
from mcp.types import TextContent

from kreuzberg._config import discover_config
from kreuzberg._types import ExtractionConfig, OcrBackendType, PSMMode, TesseractConfig
from kreuzberg.extraction import (
    batch_extract_bytes_sync,
    batch_extract_file_sync,
    extract_bytes_sync,
    extract_file_sync,
)

mcp = FastMCP("Kreuzberg Text Extraction")


def _create_config_with_overrides(**kwargs: Any) -> ExtractionConfig:
    base_config = discover_config()

    # Extract Tesseract-specific parameters from kwargs first
    tesseract_lang = kwargs.pop("tesseract_lang", None)
    tesseract_psm = kwargs.pop("tesseract_psm", None)
    tesseract_output_format = kwargs.pop("tesseract_output_format", None)
    enable_table_detection = kwargs.pop("enable_table_detection", None)

    if base_config is None:
        config_dict = kwargs
    else:
        config_dict = {
            "force_ocr": base_config.force_ocr,
            "chunk_content": base_config.chunk_content,
            "extract_tables": base_config.extract_tables,
            "extract_entities": base_config.extract_entities,
            "extract_keywords": base_config.extract_keywords,
            "ocr_backend": base_config.ocr_backend,
            "max_chars": base_config.max_chars,
            "max_overlap": base_config.max_overlap,
            "keyword_count": base_config.keyword_count,
            "auto_detect_language": base_config.auto_detect_language,
            "ocr_config": base_config.ocr_config,
            "gmft_config": base_config.gmft_config,
        }
        config_dict = config_dict | kwargs

    # Handle Tesseract OCR configuration
    ocr_backend = config_dict.get("ocr_backend")
    if ocr_backend == "tesseract" and (
        tesseract_lang or tesseract_psm is not None or tesseract_output_format or enable_table_detection
    ):
        tesseract_config_dict = {}

        if tesseract_lang:
            tesseract_config_dict["language"] = tesseract_lang
        if tesseract_psm is not None:
            with contextlib.suppress(ValueError):
                tesseract_config_dict["psm"] = PSMMode(tesseract_psm)
        if tesseract_output_format:
            tesseract_config_dict["output_format"] = tesseract_output_format
        if enable_table_detection:
            tesseract_config_dict["enable_table_detection"] = True

        if tesseract_config_dict:
            # Merge with existing tesseract config if present
            existing_ocr_config = config_dict.get("ocr_config")
            if existing_ocr_config and isinstance(existing_ocr_config, TesseractConfig):
                # Convert existing config to dict, merge, and recreate
                existing_dict = existing_ocr_config.to_dict()
                merged_dict = existing_dict | tesseract_config_dict
                config_dict["ocr_config"] = TesseractConfig(**merged_dict)
            else:
                config_dict["ocr_config"] = TesseractConfig(**tesseract_config_dict)

    return ExtractionConfig(**config_dict)


@mcp.tool()
def extract_document(  # noqa: PLR0913
    file_path: str,
    mime_type: str | None = None,
    force_ocr: bool = False,
    chunk_content: bool = False,
    extract_tables: bool = False,
    extract_entities: bool = False,
    extract_keywords: bool = False,
    ocr_backend: OcrBackendType = "tesseract",
    max_chars: int = 1000,
    max_overlap: int = 200,
    keyword_count: int = 10,
    auto_detect_language: bool = False,
    tesseract_lang: str | None = None,
    tesseract_psm: int | None = None,
    tesseract_output_format: str | None = None,
    enable_table_detection: bool | None = None,
) -> dict[str, Any]:
    config = _create_config_with_overrides(
        force_ocr=force_ocr,
        chunk_content=chunk_content,
        extract_tables=extract_tables,
        extract_entities=extract_entities,
        extract_keywords=extract_keywords,
        ocr_backend=ocr_backend,
        max_chars=max_chars,
        max_overlap=max_overlap,
        keyword_count=keyword_count,
        auto_detect_language=auto_detect_language,
        tesseract_lang=tesseract_lang,
        tesseract_psm=tesseract_psm,
        tesseract_output_format=tesseract_output_format,
        enable_table_detection=enable_table_detection,
    )

    result = extract_file_sync(file_path, mime_type, config)
    return result.to_dict(include_none=True)


@mcp.tool()
def extract_bytes(  # noqa: PLR0913
    content_base64: str,
    mime_type: str,
    force_ocr: bool = False,
    chunk_content: bool = False,
    extract_tables: bool = False,
    extract_entities: bool = False,
    extract_keywords: bool = False,
    ocr_backend: OcrBackendType = "tesseract",
    max_chars: int = 1000,
    max_overlap: int = 200,
    keyword_count: int = 10,
    auto_detect_language: bool = False,
    tesseract_lang: str | None = None,
    tesseract_psm: int | None = None,
    tesseract_output_format: str | None = None,
    enable_table_detection: bool | None = None,
) -> dict[str, Any]:
    content_bytes = base64.b64decode(content_base64)

    config = _create_config_with_overrides(
        force_ocr=force_ocr,
        chunk_content=chunk_content,
        extract_tables=extract_tables,
        extract_entities=extract_entities,
        extract_keywords=extract_keywords,
        ocr_backend=ocr_backend,
        max_chars=max_chars,
        max_overlap=max_overlap,
        keyword_count=keyword_count,
        auto_detect_language=auto_detect_language,
        tesseract_lang=tesseract_lang,
        tesseract_psm=tesseract_psm,
        tesseract_output_format=tesseract_output_format,
        enable_table_detection=enable_table_detection,
    )

    result = extract_bytes_sync(content_bytes, mime_type, config)
    return result.to_dict(include_none=True)


@mcp.tool()
def batch_extract_document(  # noqa: PLR0913
    file_paths: list[str],
    force_ocr: bool = False,
    chunk_content: bool = False,
    extract_tables: bool = False,
    extract_entities: bool = False,
    extract_keywords: bool = False,
    ocr_backend: OcrBackendType = "tesseract",
    max_chars: int = 1000,
    max_overlap: int = 200,
    keyword_count: int = 10,
    auto_detect_language: bool = False,
    tesseract_lang: str | None = None,
    tesseract_psm: int | None = None,
    tesseract_output_format: str | None = None,
    enable_table_detection: bool | None = None,
) -> list[dict[str, Any]]:
    config = _create_config_with_overrides(
        force_ocr=force_ocr,
        chunk_content=chunk_content,
        extract_tables=extract_tables,
        extract_entities=extract_entities,
        extract_keywords=extract_keywords,
        ocr_backend=ocr_backend,
        max_chars=max_chars,
        max_overlap=max_overlap,
        keyword_count=keyword_count,
        auto_detect_language=auto_detect_language,
        tesseract_lang=tesseract_lang,
        tesseract_psm=tesseract_psm,
        tesseract_output_format=tesseract_output_format,
        enable_table_detection=enable_table_detection,
    )

    results = batch_extract_file_sync(file_paths, config)
    return [result.to_dict(include_none=True) for result in results]


@mcp.tool()
def batch_extract_bytes(  # noqa: PLR0913
    content_items: list[dict[str, str]],
    force_ocr: bool = False,
    chunk_content: bool = False,
    extract_tables: bool = False,
    extract_entities: bool = False,
    extract_keywords: bool = False,
    ocr_backend: OcrBackendType = "tesseract",
    max_chars: int = 1000,
    max_overlap: int = 200,
    keyword_count: int = 10,
    auto_detect_language: bool = False,
    tesseract_lang: str | None = None,
    tesseract_psm: int | None = None,
    tesseract_output_format: str | None = None,
    enable_table_detection: bool | None = None,
) -> list[dict[str, Any]]:
    config = _create_config_with_overrides(
        force_ocr=force_ocr,
        chunk_content=chunk_content,
        extract_tables=extract_tables,
        extract_entities=extract_entities,
        extract_keywords=extract_keywords,
        ocr_backend=ocr_backend,
        max_chars=max_chars,
        max_overlap=max_overlap,
        keyword_count=keyword_count,
        auto_detect_language=auto_detect_language,
        tesseract_lang=tesseract_lang,
        tesseract_psm=tesseract_psm,
        tesseract_output_format=tesseract_output_format,
        enable_table_detection=enable_table_detection,
    )

    # Convert list of dicts to list of tuples (bytes, mime_type)
    contents = []
    for item in content_items:
        content_base64 = item["content_base64"]
        mime_type = item["mime_type"]
        content_bytes = base64.b64decode(content_base64)
        contents.append((content_bytes, mime_type))

    results = batch_extract_bytes_sync(contents, config)
    return [result.to_dict(include_none=True) for result in results]


@mcp.tool()
def extract_simple(
    file_path: str,
    mime_type: str | None = None,
) -> str:
    config = _create_config_with_overrides()
    result = extract_file_sync(file_path, mime_type, config)
    return result.content


@mcp.resource("config://default")
def get_default_config() -> str:
    config = ExtractionConfig()
    return json.dumps(msgspec.to_builtins(config, order="deterministic"), indent=2)


@mcp.resource("config://discovered")
def get_discovered_config() -> str:
    config = discover_config()
    if config is None:
        return "No configuration file found"
    return json.dumps(msgspec.to_builtins(config, order="deterministic"), indent=2)


@mcp.resource("config://available-backends")
def get_available_backends() -> str:
    return "tesseract, easyocr, paddleocr"


@mcp.resource("extractors://supported-formats")
def get_supported_formats() -> str:
    return """
    Supported formats:
    - PDF documents
    - Images (PNG, JPG, JPEG, TIFF, BMP, WEBP)
    - Office documents (DOCX, PPTX, XLSX)
    - HTML files
    - Text files (TXT, CSV, TSV)
    - And more...
    """


@mcp.prompt()
def extract_and_summarize(file_path: str) -> list[TextContent]:
    result = extract_file_sync(file_path, None, _create_config_with_overrides())

    return [
        TextContent(
            type="text",
            text=f"Document Content:\n{result.content}\n\nPlease provide a concise summary of this document.",
        )
    ]


@mcp.prompt()
def extract_structured(file_path: str) -> list[TextContent]:
    config = _create_config_with_overrides(
        extract_entities=True,
        extract_keywords=True,
        extract_tables=True,
    )
    result = extract_file_sync(file_path, None, config)

    content = f"Document Content:\n{result.content}\n\n"

    if result.entities:
        content += f"Entities: {[f'{e.text} ({e.type})' for e in result.entities]}\n\n"

    if result.keywords:
        content += f"Keywords: {[f'{kw[0]} ({kw[1]:.2f})' for kw in result.keywords]}\n\n"

    if result.tables:
        content += f"Tables found: {len(result.tables)}\n\n"

    content += "Please analyze this document and provide structured insights."

    return [TextContent(type="text", text=content)]


def main() -> None:  # pragma: no cover
    mcp.run()


if __name__ == "__main__":
    main()
