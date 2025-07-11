"""Kreuzberg MCP server implementation."""

from __future__ import annotations

import base64
from typing import Any

from mcp.server import FastMCP
from mcp.types import TextContent

from kreuzberg._types import ExtractionConfig, OcrBackendType
from kreuzberg.extraction import extract_bytes_sync, extract_file_sync

# Create the MCP server
mcp = FastMCP("Kreuzberg Text Extraction")


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
    """Extract text content from a document file.

    Args:
        file_path: Path to the document file
        mime_type: MIME type of the document (auto-detected if not provided)
        force_ocr: Force OCR even for text-based documents
        chunk_content: Split content into chunks
        extract_tables: Extract tables from the document
        extract_entities: Extract named entities
        extract_keywords: Extract keywords
        ocr_backend: OCR backend to use (tesseract, easyocr, paddleocr)
        max_chars: Maximum characters per chunk
        max_overlap: Character overlap between chunks
        keyword_count: Number of keywords to extract
        auto_detect_language: Auto-detect document language

    Returns:
        Extracted content with metadata, tables, chunks, entities, and keywords
    """
    config = ExtractionConfig(
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
    return result.to_dict()


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
    """Extract text content from document bytes.

    Args:
        content_base64: Base64-encoded document content
        mime_type: MIME type of the document
        force_ocr: Force OCR even for text-based documents
        chunk_content: Split content into chunks
        extract_tables: Extract tables from the document
        extract_entities: Extract named entities
        extract_keywords: Extract keywords
        ocr_backend: OCR backend to use (tesseract, easyocr, paddleocr)
        max_chars: Maximum characters per chunk
        max_overlap: Character overlap between chunks
        keyword_count: Number of keywords to extract
        auto_detect_language: Auto-detect document language

    Returns:
        Extracted content with metadata, tables, chunks, entities, and keywords
    """
    content_bytes = base64.b64decode(content_base64)

    config = ExtractionConfig(
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
    return result.to_dict()


@mcp.tool()
def extract_simple(
    file_path: str,
    mime_type: str | None = None,
) -> str:
    """Simple text extraction from a document file.

    Args:
        file_path: Path to the document file
        mime_type: MIME type of the document (auto-detected if not provided)

    Returns:
        Extracted text content as a string
    """
    config = ExtractionConfig()
    result = extract_file_sync(file_path, mime_type, config)
    return result.content


@mcp.resource("config://default")
def get_default_config() -> str:
    """Get the default extraction configuration."""
    config = ExtractionConfig()
    return str(config.__dict__)


@mcp.resource("config://available-backends")
def get_available_backends() -> str:
    """Get available OCR backends."""
    return "tesseract, easyocr, paddleocr"


@mcp.resource("extractors://supported-formats")
def get_supported_formats() -> str:
    """Get supported document formats."""
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
    """Extract text from a document and provide a summary prompt.

    Args:
        file_path: Path to the document file

    Returns:
        Extracted content with summarization prompt
    """
    result = extract_file_sync(file_path, None, ExtractionConfig())

    return [
        TextContent(
            type="text",
            text=f"Document Content:\n{result.content}\n\nPlease provide a concise summary of this document.",
        )
    ]


@mcp.prompt()
def extract_structured(file_path: str) -> list[TextContent]:
    """Extract text with structured analysis prompt.

    Args:
        file_path: Path to the document file

    Returns:
        Extracted content with structured analysis prompt
    """
    config = ExtractionConfig(
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


def main() -> None:
    """Main entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
