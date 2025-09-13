from __future__ import annotations

import base64
import json
from typing import Any

import msgspec
from mcp.server import FastMCP
from mcp.types import TextContent

from kreuzberg._config import discover_config
from kreuzberg._types import ExtractionConfig, OcrBackendType
from kreuzberg.extraction import extract_bytes_sync, extract_file_sync

mcp = FastMCP("Kreuzberg Text Extraction")


def _create_config_with_overrides(**kwargs: Any) -> ExtractionConfig:
    base_config = discover_config()

    if base_config is None:
        return ExtractionConfig(**kwargs)

    config_dict: dict[str, Any] = {
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
    )

    result = extract_bytes_sync(content_bytes, mime_type, config)
    return result.to_dict(include_none=True)


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
