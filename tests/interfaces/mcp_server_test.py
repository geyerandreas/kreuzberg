"""Tests for MCP server batch processing functionality."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    from pathlib import Path

from kreuzberg._mcp.server import batch_extract_bytes, batch_extract_document
from kreuzberg._types import ExtractionResult


def test_batch_extract_document_single_file(tmp_path: Path) -> None:
    """Test batch document extraction with a single file."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, world!")

    # Mock the batch extraction function
    with patch("kreuzberg._mcp.server.batch_extract_file_sync") as mock_batch:
        mock_result = ExtractionResult(
            content="Hello, world!",
            mime_type="text/plain",
            metadata={},
            chunks=[],
        )
        mock_batch.return_value = [mock_result]

        result = batch_extract_document([str(test_file)])

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["content"] == "Hello, world!"
        assert result[0]["mime_type"] == "text/plain"


def test_batch_extract_document_multiple_files(tmp_path: Path) -> None:
    """Test batch document extraction with multiple files."""
    # Create test files
    test_files = []
    for i in range(3):
        test_file = tmp_path / f"test{i}.txt"
        test_file.write_text(f"Content {i}")
        test_files.append(str(test_file))

    # Mock the batch extraction function
    with patch("kreuzberg._mcp.server.batch_extract_file_sync") as mock_batch:
        mock_results = [
            ExtractionResult(
                content=f"Content {i}",
                mime_type="text/plain",
                metadata={},
                chunks=[],
            )
            for i in range(3)
        ]
        mock_batch.return_value = mock_results

        result = batch_extract_document(test_files)

        assert isinstance(result, list)
        assert len(result) == 3
        for i, res in enumerate(result):
            assert res["content"] == f"Content {i}"
            assert res["mime_type"] == "text/plain"


def test_batch_extract_bytes_single_item() -> None:
    """Test batch bytes extraction with a single item."""
    content = b"Hello, world!"
    content_base64 = base64.b64encode(content).decode("ascii")
    content_items = [{"content_base64": content_base64, "mime_type": "text/plain"}]

    # Mock the batch extraction function
    with patch("kreuzberg._mcp.server.batch_extract_bytes_sync") as mock_batch:
        mock_result = ExtractionResult(
            content="Hello, world!",
            mime_type="text/plain",
            metadata={},
            chunks=[],
        )
        mock_batch.return_value = [mock_result]

        result = batch_extract_bytes(content_items)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["content"] == "Hello, world!"
        assert result[0]["mime_type"] == "text/plain"


def test_batch_extract_bytes_multiple_items() -> None:
    """Test batch bytes extraction with multiple items."""
    content_items = []
    for i in range(3):
        content = f"Content {i}".encode()
        content_base64 = base64.b64encode(content).decode("ascii")
        content_items.append({"content_base64": content_base64, "mime_type": "text/plain"})

    # Mock the batch extraction function
    with patch("kreuzberg._mcp.server.batch_extract_bytes_sync") as mock_batch:
        mock_results = [
            ExtractionResult(
                content=f"Content {i}",
                mime_type="text/plain",
                metadata={},
                chunks=[],
            )
            for i in range(3)
        ]
        mock_batch.return_value = mock_results

        result = batch_extract_bytes(content_items)

        assert isinstance(result, list)
        assert len(result) == 3
        for i, res in enumerate(result):
            assert res["content"] == f"Content {i}"
            assert res["mime_type"] == "text/plain"


def test_batch_extract_document_with_config_parameters() -> None:
    """Test that configuration parameters are passed correctly."""
    test_files = ["/tmp/test.txt"]

    with patch("kreuzberg._mcp.server.batch_extract_file_sync") as mock_batch:
        with patch("kreuzberg._mcp.server._create_config_with_overrides") as mock_config:
            mock_result = ExtractionResult(
                content="Test content",
                mime_type="text/plain",
                metadata={},
                chunks=[],
            )
            mock_batch.return_value = [mock_result]

            # Call with custom parameters
            batch_extract_document(
                test_files,
                force_ocr=True,
                chunk_content=True,
                extract_tables=True,
                max_chars=500,
            )

            # Verify config creation was called with correct parameters
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["force_ocr"] is True
            assert call_kwargs["chunk_content"] is True
            assert call_kwargs["extract_tables"] is True
            assert call_kwargs["max_chars"] == 500


def test_batch_extract_bytes_with_config_parameters() -> None:
    """Test that configuration parameters are passed correctly for bytes extraction."""
    content = b"Test content"
    content_base64 = base64.b64encode(content).decode("ascii")
    content_items = [{"content_base64": content_base64, "mime_type": "text/plain"}]

    with patch("kreuzberg._mcp.server.batch_extract_bytes_sync") as mock_batch:
        with patch("kreuzberg._mcp.server._create_config_with_overrides") as mock_config:
            mock_result = ExtractionResult(
                content="Test content",
                mime_type="text/plain",
                metadata={},
                chunks=[],
            )
            mock_batch.return_value = [mock_result]

            # Call with custom parameters
            batch_extract_bytes(
                content_items,
                force_ocr=True,
                extract_keywords=True,
                auto_detect_language=True,
                keyword_count=20,
            )

            # Verify config creation was called with correct parameters
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["force_ocr"] is True
            assert call_kwargs["extract_keywords"] is True
            assert call_kwargs["auto_detect_language"] is True
            assert call_kwargs["keyword_count"] == 20
