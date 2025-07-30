"""Comprehensive tests for kreuzberg._extractors._pandoc module."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kreuzberg._extractors._pandoc import (
    BibliographyExtractor,
    EbookExtractor,
    LaTeXExtractor,
    MarkdownExtractor,
    MiscFormatExtractor,
    OfficeDocumentExtractor,
    PandocExtractor,
    StructuredTextExtractor,
    TabularDataExtractor,
    XMLBasedExtractor,
)
from kreuzberg._mime_types import MARKDOWN_MIME_TYPE
from kreuzberg._types import ExtractionConfig, ExtractionResult
from kreuzberg.exceptions import MissingDependencyError, ParsingError, ValidationError


class TestPandocExtractor:
    """Test PandocExtractor class."""

    def test_supported_mime_types_mapping(self) -> None:
        """Test that MIME type mappings are properly defined."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())

        # Check specific mappings exist
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in extractor.MIMETYPE_TO_PANDOC_TYPE_MAPPING
        )
        assert "text/x-markdown" in extractor.MIMETYPE_TO_PANDOC_TYPE_MAPPING
        assert "application/epub+zip" in extractor.MIMETYPE_TO_PANDOC_TYPE_MAPPING

        # Check file extension mappings
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in extractor.MIMETYPE_TO_FILE_EXTENSION_MAPPING
        )
        assert (
            extractor.MIMETYPE_TO_FILE_EXTENSION_MAPPING[
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ]
            == "docx"
        )

    def test_get_pandoc_type_from_mime_type_valid(self) -> None:
        """Test getting Pandoc type from valid MIME types."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())

        assert extractor._get_pandoc_type_from_mime_type("text/x-markdown") == "markdown"
        assert (
            extractor._get_pandoc_type_from_mime_type(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            == "docx"
        )
        assert extractor._get_pandoc_type_from_mime_type("text/markdown") == "markdown"  # Special case

    def test_get_pandoc_type_from_mime_type_invalid(self) -> None:
        """Test getting Pandoc type from invalid MIME type."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())

        with pytest.raises(ValidationError, match="Unsupported mime type"):
            extractor._get_pandoc_type_from_mime_type("application/unknown")

    def test_get_pandoc_key_mappings(self) -> None:
        """Test metadata key mapping functionality."""
        assert PandocExtractor._get_pandoc_key("abstract") == "summary"
        assert PandocExtractor._get_pandoc_key("date") == "created_at"
        assert PandocExtractor._get_pandoc_key("author") == "authors"
        assert PandocExtractor._get_pandoc_key("contributors") == "authors"
        assert PandocExtractor._get_pandoc_key("institute") == "organization"
        assert PandocExtractor._get_pandoc_key("title") == "title"  # Direct mapping
        assert PandocExtractor._get_pandoc_key("unknown_key") is None

    @pytest.mark.anyio
    async def test_extract_bytes_async(self) -> None:
        """Test async bytes extraction."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        content = b"# Test Markdown\n\nThis is a test."

        with (
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch("kreuzberg._extractors._pandoc.create_temp_file") as mock_temp_file,
            patch.object(extractor, "extract_path_async") as mock_extract_path,
        ):
            # Mock temp file creation
            mock_unlink = AsyncMock()
            temp_path = "/tmp/test.md"
            mock_temp_file.return_value = (temp_path, mock_unlink)

            # Mock file writing
            mock_path = AsyncMock()
            mock_path.write_bytes = AsyncMock()

            with patch("kreuzberg._extractors._pandoc.AsyncPath", return_value=mock_path):
                mock_result = ExtractionResult(content="Test", mime_type=MARKDOWN_MIME_TYPE, metadata={})
                mock_extract_path.return_value = mock_result

                result = await extractor.extract_bytes_async(content)

                assert result == mock_result
                mock_path.write_bytes.assert_called_once_with(content)
                mock_extract_path.assert_called_once_with(temp_path)
                mock_unlink.assert_called_once()

    def test_extract_bytes_sync(self) -> None:
        """Test sync bytes extraction."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        content = b"# Test Markdown\n\nThis is a test."

        with (
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch("tempfile.mkstemp") as mock_mkstemp,
            patch("os.fdopen") as mock_fdopen,
            patch.object(extractor, "extract_path_sync") as mock_extract_path,
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            # Mock temp file creation
            mock_fd = 3
            temp_path = "/tmp/test.md"
            mock_mkstemp.return_value = (mock_fd, temp_path)

            # Mock file writing
            mock_file = Mock()
            mock_fdopen.return_value.__enter__.return_value = mock_file

            mock_result = ExtractionResult(content="Test", mime_type=MARKDOWN_MIME_TYPE, metadata={})
            mock_extract_path.return_value = mock_result

            result = extractor.extract_bytes_sync(content)

            assert result == mock_result
            mock_mkstemp.assert_called_once_with(suffix=".markdown")
            mock_fdopen.assert_called_once_with(mock_fd, "wb")
            mock_file.write.assert_called_once_with(content)
            mock_extract_path.assert_called_once_with(Path(temp_path))
            mock_unlink.assert_called_once()

    @pytest.mark.anyio
    async def test_extract_path_async_success(self) -> None:
        """Test successful async path extraction."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        test_path = Path("/test/file.md")

        with (
            patch.object(extractor, "_validate_pandoc_version", return_value=None) as mock_validate,
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch("kreuzberg._extractors._pandoc.run_taskgroup") as mock_taskgroup,
        ):
            mock_metadata = {"title": "Test"}
            mock_content = "# Test Content"
            mock_taskgroup.return_value = (mock_metadata, mock_content)

            result = await extractor.extract_path_async(test_path)

            assert isinstance(result, ExtractionResult)
            assert result.content == "# Test Content"
            assert result.metadata == mock_metadata
            assert result.mime_type == MARKDOWN_MIME_TYPE
            mock_validate.assert_called_once()

    @pytest.mark.anyio
    async def test_extract_path_async_failure(self) -> None:
        """Test failed async path extraction."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        test_path = Path("/test/file.md")

        with (
            patch.object(extractor, "_validate_pandoc_version", return_value=None),
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch("kreuzberg._extractors._pandoc.run_taskgroup") as mock_taskgroup,
        ):
            mock_error = Exception("Test error")

            # Create a mock ExceptionGroup for testing
            class MockExceptionGroupError(Exception):
                def __init__(self, message: str, exceptions: list[Exception]) -> None:
                    super().__init__(message)
                    self.exceptions = exceptions

            mock_taskgroup.side_effect = MockExceptionGroupError("Multiple errors", [mock_error])

            with pytest.raises(ParsingError, match="Failed to process file"):
                await extractor.extract_path_async(test_path)

    def test_extract_path_sync_success(self) -> None:
        """Test successful sync path extraction."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        test_path = Path("/test/file.md")

        with (
            patch.object(extractor, "_validate_pandoc_version_sync", return_value=None) as mock_validate,
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch.object(extractor, "_extract_metadata_sync", return_value={"title": "Test"}) as mock_metadata,
            patch.object(extractor, "_extract_file_sync", return_value="# Test Content") as mock_content,
        ):
            result = extractor.extract_path_sync(test_path)

            assert isinstance(result, ExtractionResult)
            assert result.content == "# Test Content"
            assert result.metadata == {"title": "Test"}
            assert result.mime_type == MARKDOWN_MIME_TYPE
            mock_validate.assert_called_once()
            mock_metadata.assert_called_once_with(test_path)
            mock_content.assert_called_once_with(test_path)

    def test_extract_path_sync_failure(self) -> None:
        """Test failed sync path extraction."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        test_path = Path("/test/file.md")

        with (
            patch.object(extractor, "_validate_pandoc_version_sync", return_value=None),
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch.object(extractor, "_extract_metadata_sync", side_effect=Exception("Test error")),
        ):
            with pytest.raises(ParsingError, match="Failed to process file"):
                extractor.extract_path_sync(test_path)


class TestPandocVersionValidation:
    """Test Pandoc version validation."""

    @pytest.mark.anyio
    async def test_validate_pandoc_version_already_checked(self) -> None:
        """Test that validation is skipped if already checked."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        extractor._checked_version = True

        # Should not call pandoc
        with patch("kreuzberg._extractors._pandoc.run_process") as mock_run:
            await extractor._validate_pandoc_version()
            mock_run.assert_not_called()

    @pytest.mark.anyio
    async def test_validate_pandoc_version_valid(self) -> None:
        """Test successful version validation."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        extractor._checked_version = False

        mock_result = Mock()
        mock_result.stdout = b"pandoc 3.1.2\nCompiled with pandoc-types..."

        with patch("kreuzberg._extractors._pandoc.run_process", return_value=mock_result):
            await extractor._validate_pandoc_version()
            assert extractor._checked_version is True

    @pytest.mark.anyio
    async def test_validate_pandoc_version_alternative_formats(self) -> None:
        """Test version validation with different output formats."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())

        # Test different version string formats
        version_strings = [
            b"pandoc version 3.1.2",
            b"pandoc (version 3.1.2)",
            b"pandoc-3.1.2",
            b"3.1.2\nSome other text",
            b"Some text 3.1.2 more text",
        ]

        for version_string in version_strings:
            extractor._checked_version = False
            mock_result = Mock()
            mock_result.stdout = version_string

            with patch("kreuzberg._extractors._pandoc.run_process", return_value=mock_result):
                await extractor._validate_pandoc_version()
                assert extractor._checked_version is True

    @pytest.mark.anyio
    async def test_validate_pandoc_version_token_parsing(self) -> None:
        """Test version validation using token parsing fallback."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        extractor._checked_version = False

        mock_result = Mock()
        mock_result.stdout = b"Some line\nAnother line with 3.1.2 token\nMore lines"

        with patch("kreuzberg._extractors._pandoc.run_process", return_value=mock_result):
            await extractor._validate_pandoc_version()
            assert extractor._checked_version is True

    @pytest.mark.anyio
    async def test_validate_pandoc_version_old_version(self) -> None:
        """Test validation failure with old version."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        extractor._checked_version = False

        mock_result = Mock()
        mock_result.stdout = b"pandoc 1.19.2"

        with patch("kreuzberg._extractors._pandoc.run_process", return_value=mock_result):
            with pytest.raises(MissingDependencyError, match="Pandoc version 2 or above"):
                await extractor._validate_pandoc_version()

    @pytest.mark.anyio
    async def test_validate_pandoc_version_no_version_found(self) -> None:
        """Test validation failure when no version is found."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        extractor._checked_version = False

        mock_result = Mock()
        mock_result.stdout = b"Some output without version numbers"

        with patch("kreuzberg._extractors._pandoc.run_process", return_value=mock_result):
            with pytest.raises(MissingDependencyError, match="Pandoc version 2 or above"):
                await extractor._validate_pandoc_version()

    @pytest.mark.anyio
    async def test_validate_pandoc_version_file_not_found(self) -> None:
        """Test validation failure when pandoc is not installed."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        extractor._checked_version = False

        with patch("kreuzberg._extractors._pandoc.run_process", side_effect=FileNotFoundError):
            with pytest.raises(MissingDependencyError, match="Pandoc version 2 or above"):
                await extractor._validate_pandoc_version()

    def test_validate_pandoc_version_sync_success(self) -> None:
        """Test successful sync version validation."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        extractor._checked_version = False

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "pandoc 3.1.2\nCompiled with pandoc-types..."

        with patch("subprocess.run", return_value=mock_result):
            extractor._validate_pandoc_version_sync()
            assert extractor._checked_version is True

    def test_validate_pandoc_version_sync_failure(self) -> None:
        """Test sync version validation failure."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        extractor._checked_version = False

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(MissingDependencyError, match="Pandoc version 2 or above"):
                extractor._validate_pandoc_version_sync()

    def test_validate_pandoc_version_sync_subprocess_error(self) -> None:
        """Test sync version validation with subprocess error."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        extractor._checked_version = False

        with patch("subprocess.run", side_effect=subprocess.SubprocessError):
            with pytest.raises(MissingDependencyError, match="Pandoc version 2 or above"):
                extractor._validate_pandoc_version_sync()


class TestPandocMetadataExtraction:
    """Test metadata extraction functionality."""

    def test_extract_metadata_empty(self) -> None:
        """Test metadata extraction with empty input."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        result = extractor._extract_metadata({})
        assert result == {}

    def test_extract_metadata_with_citations(self) -> None:
        """Test metadata extraction with citations."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        raw_meta = {
            "citations": [
                {"citationId": "cite1"},
                {"citationId": "cite2"},
                {"invalid": "entry"},  # Missing citationId
                "string_entry",  # Not a dict
            ]
        }

        result = extractor._extract_metadata(raw_meta)
        assert result["citations"] == ["cite1", "cite2"]

    def test_extract_metadata_with_standard_fields(self) -> None:
        """Test metadata extraction with standard fields."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        raw_meta = {
            "title": {"t": "MetaString", "c": "Test Title"},
            "abstract": {"t": "MetaString", "c": "Test Abstract"},
            "date": {"t": "MetaString", "c": "2023-01-01"},
            "author": {"t": "MetaString", "c": "Test Author"},
            "institute": {"t": "MetaString", "c": "Test Organization"},
            "unknown_field": {"t": "MetaString", "c": "Should be ignored"},
        }

        result = extractor._extract_metadata(raw_meta)
        assert result["title"] == "Test Title"
        assert result["summary"] == "Test Abstract"  # Mapped from abstract
        assert result["created_at"] == "2023-01-01"  # Mapped from date
        assert result["authors"] == ["Test Author"]  # Wrapped in list
        assert result["organization"] == "Test Organization"  # Mapped from institute
        assert "unknown_field" not in result

    def test_extract_metadata_with_valid_field(self) -> None:
        """Test metadata extraction with special 'valid' field."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        raw_meta = {"valid": {"t": "MetaString", "c": "true"}}

        result = extractor._extract_metadata(raw_meta)
        # Note: 'valid' is not in Metadata TypedDict but is handled specially
        assert "valid" in result
        assert result.get("valid") == "true"

    def test_extract_metadata_with_blocks_citations(self) -> None:
        """Test metadata extraction with citations from blocks."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        raw_meta = {
            "blocks": [
                {"t": "Cite", "c": [[{"citationId": "block_cite1"}, {"citationId": "block_cite2"}], []]},
                {"t": "Para", "c": []},
            ]
        }

        result = extractor._extract_metadata(raw_meta)
        assert result["citations"] == ["block_cite1", "block_cite2"]

    def test_extract_metadata_merge_citations(self) -> None:
        """Test metadata extraction merging citations from different sources."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        raw_meta = {
            "citations": [{"citationId": "cite1"}],
            "blocks": [{"t": "Cite", "c": [[{"citationId": "block_cite1"}], []]}],
        }

        result = extractor._extract_metadata(raw_meta)
        assert result["citations"] == ["cite1", "block_cite1"]


class TestPandocInlineTextExtraction:
    """Test inline text extraction functionality."""

    def test_extract_inline_text_str(self) -> None:
        """Test extracting text from Str node."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        node = {"t": "Str", "c": "Hello"}

        result = extractor._extract_inline_text(node)
        assert result == "Hello"

    def test_extract_inline_text_space(self) -> None:
        """Test extracting text from Space node."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        node = {"t": "Space", "c": None}

        result = extractor._extract_inline_text(node)
        assert result == " "

    def test_extract_inline_text_emph(self) -> None:
        """Test extracting text from Emph node."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        node = {"t": "Emph", "c": [{"t": "Str", "c": "emphasized"}]}

        result = extractor._extract_inline_text(node)
        assert result == "emphasized"

    def test_extract_inline_text_strong(self) -> None:
        """Test extracting text from Strong node."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        node = {"t": "Strong", "c": [{"t": "Str", "c": "strong"}]}

        result = extractor._extract_inline_text(node)
        assert result == "strong"

    def test_extract_inline_text_unknown(self) -> None:
        """Test extracting text from unknown node type."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        node = {"t": "Unknown", "c": "content"}

        result = extractor._extract_inline_text(node)
        assert result is None

    def test_extract_inlines_multiple(self) -> None:
        """Test extracting text from multiple inline nodes."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        nodes: list[dict[str, Any]] = [
            {"t": "Str", "c": "Hello"},
            {"t": "Space", "c": None},
            {"t": "Str", "c": "world"},
        ]

        result = extractor._extract_inlines(nodes)
        assert result == "Hello world"

    def test_extract_inlines_empty(self) -> None:
        """Test extracting text from empty nodes list."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        nodes: list[dict[str, Any]] = []

        result = extractor._extract_inlines(nodes)
        assert result is None


class TestPandocMetaValueExtraction:
    """Test meta value extraction functionality."""

    def test_extract_meta_value_meta_string(self) -> None:
        """Test extracting MetaString value."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        node = {"t": "MetaString", "c": "test value"}

        result = extractor._extract_meta_value(node)
        assert result == "test value"

    def test_extract_meta_value_meta_inlines(self) -> None:
        """Test extracting MetaInlines value."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        node = {
            "t": "MetaInlines",
            "c": [{"t": "Str", "c": "inline"}, {"t": "Space", "c": None}, {"t": "Str", "c": "text"}],
        }

        result = extractor._extract_meta_value(node)
        assert result == "inline text"

    def test_extract_meta_value_meta_list(self) -> None:
        """Test extracting MetaList value."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        node = {"t": "MetaList", "c": [{"t": "MetaString", "c": "item1"}, {"t": "MetaString", "c": "item2"}]}

        result = extractor._extract_meta_value(node)
        assert result == ["item1", "item2"]

    def test_extract_meta_value_meta_list_nested(self) -> None:
        """Test extracting MetaList with nested lists."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        node = {
            "t": "MetaList",
            "c": [{"t": "MetaList", "c": [{"t": "MetaString", "c": "nested1"}]}, {"t": "MetaString", "c": "item2"}],
        }

        result = extractor._extract_meta_value(node)
        assert result == ["nested1", "item2"]

    def test_extract_meta_value_meta_blocks(self) -> None:
        """Test extracting MetaBlocks value."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        node = {
            "t": "MetaBlocks",
            "c": [
                {
                    "t": "Para",
                    "c": [{"t": "Str", "c": "First"}, {"t": "Space", "c": None}, {"t": "Str", "c": "paragraph"}],
                },
                {
                    "t": "Para",
                    "c": [{"t": "Str", "c": "Second"}, {"t": "Space", "c": None}, {"t": "Str", "c": "paragraph"}],
                },
            ],
        }

        result = extractor._extract_meta_value(node)
        assert result == "First paragraph Second paragraph"

    def test_extract_meta_value_invalid_node(self) -> None:
        """Test extracting from invalid node types."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())

        # Not a dict
        assert extractor._extract_meta_value("string") is None

        # Missing type field
        assert extractor._extract_meta_value({"c": "content"}) is None

        # Missing content field
        assert extractor._extract_meta_value({"t": "MetaString"}) is None

        # Empty content
        assert extractor._extract_meta_value({"t": "MetaString", "c": ""}) is None


class TestPandocFileExtraction:
    """Test file and metadata extraction."""

    @pytest.mark.anyio
    async def test_handle_extract_metadata_success(self) -> None:
        """Test successful metadata extraction."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        test_file = Path("/test/file.md")

        mock_json_data = {"meta": {"title": {"t": "MetaString", "c": "Test Title"}}, "blocks": []}

        with (
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch("kreuzberg._extractors._pandoc.create_temp_file") as mock_temp_file,
            patch("kreuzberg._extractors._pandoc.run_process") as mock_run_process,
            patch("json.loads", return_value=mock_json_data),
            patch.object(extractor, "_extract_metadata", return_value={"title": "Test Title"}) as mock_extract,
        ):
            # Mock temp file
            mock_unlink = AsyncMock()
            temp_path = "/tmp/metadata.json"
            mock_temp_file.return_value = (temp_path, mock_unlink)

            # Mock pandoc process
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run_process.return_value = mock_result

            # Mock file reading
            mock_path = AsyncMock()
            mock_path.read_text.return_value = json.dumps(mock_json_data)

            with patch("kreuzberg._extractors._pandoc.AsyncPath", return_value=mock_path):
                result = await extractor._handle_extract_metadata(test_file)

                assert result == {"title": "Test Title"}
                mock_run_process.assert_called_once()
                mock_extract.assert_called_once_with(mock_json_data)
                mock_unlink.assert_called_once()

    @pytest.mark.anyio
    async def test_handle_extract_metadata_pandoc_error(self) -> None:
        """Test metadata extraction with Pandoc error."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        test_file = Path("/test/file.md")

        with (
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch("kreuzberg._extractors._pandoc.create_temp_file") as mock_temp_file,
            patch("kreuzberg._extractors._pandoc.run_process") as mock_run_process,
        ):
            # Mock temp file
            mock_unlink = AsyncMock()
            temp_path = "/tmp/metadata.json"
            mock_temp_file.return_value = (temp_path, mock_unlink)

            # Mock pandoc process failure
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = b"Error message"
            mock_run_process.return_value = mock_result

            with pytest.raises(ParsingError, match="Failed to extract file data"):
                await extractor._handle_extract_metadata(test_file)

            mock_unlink.assert_called_once()

    @pytest.mark.anyio
    async def test_handle_extract_file_success(self) -> None:
        """Test successful file content extraction."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        test_file = Path("/test/file.md")

        with (
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch("kreuzberg._extractors._pandoc.create_temp_file") as mock_temp_file,
            patch("kreuzberg._extractors._pandoc.run_process") as mock_run_process,
        ):
            # Mock temp file
            mock_unlink = AsyncMock()
            temp_path = "/tmp/output.md"
            mock_temp_file.return_value = (temp_path, mock_unlink)

            # Mock pandoc process
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run_process.return_value = mock_result

            # Mock file reading
            mock_path = AsyncMock()
            mock_path.read_text.return_value = "# Test Content\n\nThis is test content."

            with patch("kreuzberg._extractors._pandoc.AsyncPath", return_value=mock_path):
                result = await extractor._handle_extract_file(test_file)

                assert "Test Content" in result
                mock_run_process.assert_called_once()
                mock_unlink.assert_called_once()

    def test_extract_metadata_sync_success(self) -> None:
        """Test successful sync metadata extraction."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        test_path = Path("/test/file.md")

        mock_json_data = {"meta": {"title": {"t": "MetaString", "c": "Test Title"}}, "blocks": []}

        with (
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch("tempfile.mkstemp") as mock_mkstemp,
            patch("os.close") as mock_close,
            patch("subprocess.run") as mock_run,
            patch("json.loads", return_value=mock_json_data),
            patch.object(extractor, "_extract_metadata", return_value={"title": "Test Title"}) as mock_extract,
            patch("pathlib.Path.open") as mock_open,
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            # Mock temp file
            mock_fd = 3
            temp_path = "/tmp/metadata.json"
            mock_mkstemp.return_value = (mock_fd, temp_path)

            # Mock subprocess
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Mock file reading
            mock_file = Mock()
            mock_file.read.return_value = json.dumps(mock_json_data)
            mock_open.return_value.__enter__.return_value = mock_file

            result = extractor._extract_metadata_sync(test_path)

            assert result == {"title": "Test Title"}
            mock_close.assert_called_once_with(mock_fd)
            mock_run.assert_called_once()
            mock_extract.assert_called_once_with(mock_json_data)
            mock_unlink.assert_called_once()

    def test_extract_file_sync_success(self) -> None:
        """Test successful sync file extraction."""
        extractor = PandocExtractor("text/x-markdown", ExtractionConfig())
        test_path = Path("/test/file.md")

        with (
            patch.object(extractor, "_get_pandoc_type_from_mime_type", return_value="markdown"),
            patch("tempfile.mkstemp") as mock_mkstemp,
            patch("os.close") as mock_close,
            patch("subprocess.run") as mock_run,
            patch("pathlib.Path.open") as mock_open,
            patch("pathlib.Path.unlink") as mock_unlink,
        ):
            # Mock temp file
            mock_fd = 3
            temp_path = "/tmp/output.md"
            mock_mkstemp.return_value = (mock_fd, temp_path)

            # Mock subprocess
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            # Mock file reading
            mock_file = Mock()
            mock_file.read.return_value = "# Test Content\n\nThis is test content."
            mock_open.return_value.__enter__.return_value = mock_file

            result = extractor._extract_file_sync(test_path)

            assert "Test Content" in result
            mock_close.assert_called_once_with(mock_fd)
            mock_run.assert_called_once()
            mock_unlink.assert_called_once()


class TestPandocExtractorSubclasses:
    """Test PandocExtractor subclasses."""

    def test_markdown_extractor_mime_types(self) -> None:
        """Test MarkdownExtractor supported MIME types."""
        expected_types = {
            "text/x-markdown",
            "text/x-commonmark",
            "text/x-gfm",
            "text/x-markdown-extra",
            "text/x-multimarkdown",
            "text/x-mdoc",
        }
        assert expected_types == MarkdownExtractor.SUPPORTED_MIME_TYPES

    def test_office_document_extractor_mime_types(self) -> None:
        """Test OfficeDocumentExtractor supported MIME types."""
        expected_types = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.oasis.opendocument.text",
        }
        assert expected_types == OfficeDocumentExtractor.SUPPORTED_MIME_TYPES

    def test_ebook_extractor_mime_types(self) -> None:
        """Test EbookExtractor supported MIME types."""
        expected_types = {
            "application/epub+zip",
            "application/x-fictionbook+xml",
        }
        assert expected_types == EbookExtractor.SUPPORTED_MIME_TYPES

    def test_structured_text_extractor_mime_types(self) -> None:
        """Test StructuredTextExtractor supported MIME types."""
        expected_types = {
            "text/x-rst",
            "text/x-org",
            "text/x-dokuwiki",
            "text/x-pod",
        }
        assert expected_types == StructuredTextExtractor.SUPPORTED_MIME_TYPES

    def test_latex_extractor_mime_types(self) -> None:
        """Test LaTeXExtractor supported MIME types."""
        expected_types = {
            "application/x-latex",
            "application/x-typst",
        }
        assert expected_types == LaTeXExtractor.SUPPORTED_MIME_TYPES

    def test_bibliography_extractor_mime_types(self) -> None:
        """Test BibliographyExtractor supported MIME types."""
        expected_types = {
            "application/x-bibtex",
            "application/x-biblatex",
            "application/csl+json",
            "application/x-research-info-systems",
            "application/x-endnote+xml",
        }
        assert expected_types == BibliographyExtractor.SUPPORTED_MIME_TYPES

    def test_xml_based_extractor_mime_types(self) -> None:
        """Test XMLBasedExtractor supported MIME types."""
        expected_types = {
            "application/docbook+xml",
            "application/x-jats+xml",
            "application/x-opml+xml",
        }
        assert expected_types == XMLBasedExtractor.SUPPORTED_MIME_TYPES

    def test_tabular_data_extractor_mime_types(self) -> None:
        """Test TabularDataExtractor supported MIME types."""
        expected_types = {
            "text/csv",
            "text/tab-separated-values",
        }
        assert expected_types == TabularDataExtractor.SUPPORTED_MIME_TYPES

    def test_misc_format_extractor_mime_types(self) -> None:
        """Test MiscFormatExtractor supported MIME types."""
        expected_types = {
            "application/rtf",
            "text/troff",
            "application/x-ipynb+json",
        }
        assert expected_types == MiscFormatExtractor.SUPPORTED_MIME_TYPES

    def test_subclass_inheritance(self) -> None:
        """Test that all subclasses properly inherit from PandocExtractor."""
        subclasses = [
            MarkdownExtractor,
            OfficeDocumentExtractor,
            EbookExtractor,
            StructuredTextExtractor,
            LaTeXExtractor,
            BibliographyExtractor,
            XMLBasedExtractor,
            TabularDataExtractor,
            MiscFormatExtractor,
        ]

        for subclass in subclasses:
            assert issubclass(subclass, PandocExtractor)
            # Test that they can be instantiated
            instance = subclass("text/x-markdown", ExtractionConfig())
            assert isinstance(instance, PandocExtractor)
