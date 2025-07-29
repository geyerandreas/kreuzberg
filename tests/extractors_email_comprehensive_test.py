"""Comprehensive tests for kreuzberg._extractors._email module."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest

from kreuzberg._extractors._email import _HTML_TAG_PATTERN, EmailExtractor
from kreuzberg._mime_types import EML_MIME_TYPE, PLAIN_TEXT_MIME_TYPE
from kreuzberg._types import ExtractionConfig, ExtractionResult
from kreuzberg.exceptions import MissingDependencyError


class TestEmailExtractor:
    """Test EmailExtractor class."""

    def test_supported_mime_types(self) -> None:
        """Test that email extractor supports correct MIME types."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        assert EML_MIME_TYPE in extractor.SUPPORTED_MIME_TYPES
        assert len(extractor.SUPPORTED_MIME_TYPES) == 1

    @pytest.mark.anyio
    async def test_extract_bytes_async_calls_sync(self) -> None:
        """Test that async extraction calls sync method."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        with patch.object(extractor, "extract_bytes_sync") as mock_sync:
            mock_result = ExtractionResult(
                content="test content", mime_type=PLAIN_TEXT_MIME_TYPE, metadata={}, chunks=[]
            )
            mock_sync.return_value = mock_result

            result = await extractor.extract_bytes_async(content)

            assert result == mock_result
            mock_sync.assert_called_once_with(content)

    @pytest.mark.anyio
    async def test_extract_path_async(self) -> None:
        """Test async path extraction."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test email content")
            temp_path = Path(f.name)

        try:
            with patch.object(extractor, "extract_bytes_async") as mock_bytes:
                mock_result = ExtractionResult(
                    content="test content", mime_type=PLAIN_TEXT_MIME_TYPE, metadata={}, chunks=[]
                )
                mock_bytes.return_value = mock_result

                result = await extractor.extract_path_async(temp_path)

                assert result == mock_result
                mock_bytes.assert_called_once_with(b"test email content")
        finally:
            temp_path.unlink()

    def test_extract_path_sync(self) -> None:
        """Test sync path extraction."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())

        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test email content")
            temp_path = Path(f.name)

        try:
            with patch.object(extractor, "extract_bytes_sync") as mock_bytes:
                mock_result = ExtractionResult(
                    content="test content", mime_type=PLAIN_TEXT_MIME_TYPE, metadata={}, chunks=[]
                )
                mock_bytes.return_value = mock_result

                result = extractor.extract_path_sync(temp_path)

                assert result == mock_result
                mock_bytes.assert_called_once_with(b"test email content")
        finally:
            temp_path.unlink()


class TestEmailExtractionSync:
    """Test email extraction synchronous methods."""

    def test_extract_bytes_sync_missing_dependency(self) -> None:
        """Test extraction when mailparse is not available."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())

        with patch("kreuzberg._extractors._email.mailparse", None):
            with pytest.raises(MissingDependencyError, match="mailparse is required for email extraction"):
                extractor.extract_bytes_sync(b"test content")

    def test_extract_bytes_sync_basic_email(self) -> None:
        """Test extraction of basic email content."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        mock_parsed_email: dict[str, Any] = {
            "subject": "Test Subject",
            "from": {"email": "sender@example.com"},
            "to": [{"email": "recipient@example.com"}],
            "date": "2023-01-01T12:00:00Z",
            "text": "This is the email body content.",
        }

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse:
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            assert isinstance(result, ExtractionResult)
            assert result.mime_type == PLAIN_TEXT_MIME_TYPE
            assert "Subject: Test Subject" in result.content
            assert "From: sender@example.com" in result.content
            assert "To: recipient@example.com" in result.content
            assert "Date: 2023-01-01T12:00:00Z" in result.content
            assert "This is the email body content." in result.content

            assert result.metadata["subject"] == "Test Subject"
            assert result.metadata["email_from"] == "sender@example.com"
            assert result.metadata["email_to"] == "recipient@example.com"
            assert result.metadata["date"] == "2023-01-01T12:00:00Z"

    def test_extract_bytes_sync_with_cc_bcc(self) -> None:
        """Test extraction with CC and BCC fields."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        mock_parsed_email: dict[str, Any] = {
            "subject": "Test Subject",
            "from": {"email": "sender@example.com"},
            "to": [{"email": "recipient@example.com"}],
            "cc": "cc@example.com",
            "bcc": "bcc@example.com",
            "text": "Email body",
        }

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse:
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            assert "CC: cc@example.com" in result.content
            assert "BCC: bcc@example.com" in result.content
            assert result.metadata["email_cc"] == "cc@example.com"
            assert result.metadata["email_bcc"] == "bcc@example.com"

    def test_extract_bytes_sync_with_attachments(self) -> None:
        """Test extraction with attachments."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        mock_parsed_email: dict[str, Any] = {
            "subject": "Test with Attachments",
            "from": {"email": "sender@example.com"},
            "text": "Email with attachments",
            "attachments": [
                {"name": "document.pdf"},
                {"name": "image.jpg"},
                {},  # Test unknown attachment (no name key)
            ],
        }

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse:
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            assert "Attachments: document.pdf, image.jpg, unknown" in result.content
            assert result.metadata["attachments"] == ["document.pdf", "image.jpg", "unknown"]

    def test_extract_bytes_sync_html_content_with_html2text(self) -> None:
        """Test extraction of HTML content when html2text is available."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        mock_parsed_email: dict[str, Any] = {
            "subject": "HTML Email",
            "from": {"email": "sender@example.com"},
            "html": "<p>This is <b>HTML</b> content with <a href='#'>links</a></p>",
        }

        mock_html2text = Mock()
        mock_h = Mock()
        mock_h.handle.return_value = "This is HTML content with links"
        mock_html2text.HTML2Text.return_value = mock_h

        with (
            patch("kreuzberg._extractors._email.mailparse") as mock_mailparse,
            patch("kreuzberg._extractors._email.html2text", mock_html2text),
        ):
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            assert "This is HTML content with links" in result.content
            mock_h.handle.assert_called_once_with("<p>This is <b>HTML</b> content with <a href='#'>links</a></p>")
            assert mock_h.ignore_links is True
            assert mock_h.ignore_images is True

    def test_extract_bytes_sync_html_content_fallback(self) -> None:
        """Test extraction of HTML content when html2text is not available."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        mock_parsed_email: dict[str, Any] = {
            "subject": "HTML Email",
            "from": {"email": "sender@example.com"},
            "html": "<p>This is <b>HTML</b> content with &lt;entities&gt;</p>",
        }

        with (
            patch("kreuzberg._extractors._email.mailparse") as mock_mailparse,
            patch("kreuzberg._extractors._email.html2text", None),
        ):
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            # Should strip HTML tags and unescape entities
            assert "This is HTML content with <entities>" in result.content
            assert "<p>" not in result.content
            assert "<b>" not in result.content

    def test_extract_bytes_sync_text_preferred_over_html(self) -> None:
        """Test that text content is preferred over HTML when both are present."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        mock_parsed_email: dict[str, Any] = {
            "subject": "Mixed Content",
            "from": {"email": "sender@example.com"},
            "text": "This is plain text content.",
            "html": "<p>This is HTML content</p>",
        }

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse:
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            assert "This is plain text content." in result.content
            assert "This is HTML content" not in result.content

    def test_extract_bytes_sync_various_from_formats(self) -> None:
        """Test extraction with different 'from' field formats."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        # Test with string format
        mock_parsed_email: dict[str, Any] = {
            "from": "sender@example.com",
            "text": "Test content",
        }

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse:
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            assert result.metadata["email_from"] == "sender@example.com"
            assert "From: sender@example.com" in result.content

    def test_extract_bytes_sync_various_to_formats(self) -> None:
        """Test extraction with different 'to' field formats."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        # Test with dict format
        mock_parsed_email: dict[str, Any] = {
            "to": {"email": "recipient@example.com"},
            "text": "Test content",
        }

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse:
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            assert result.metadata["email_to"] == "recipient@example.com"

        # Test with string format - create new extractor to avoid state issues
        extractor2 = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        mock_parsed_email2: dict[str, Any] = {
            "to": "recipient@example.com",
            "text": "Test content",
        }

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse2:
            mock_mailparse2.EmailDecode.load.return_value = mock_parsed_email2
            result = extractor2.extract_bytes_sync(content)

            assert result.metadata["email_to"] == "recipient@example.com"

    def test_extract_bytes_sync_empty_fields(self) -> None:
        """Test extraction when email fields are empty or missing."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        mock_parsed_email: dict[str, Any] = {
            "text": "Just body content",
            # Missing subject, from, to, etc.
        }

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse:
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            assert result.content == "Just body content"
            assert "subject" not in result.metadata
            assert "email_from" not in result.metadata
            assert "email_to" not in result.metadata

    def test_extract_bytes_sync_no_content(self) -> None:
        """Test extraction when email has no text or HTML content."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        mock_parsed_email: dict[str, Any] = {
            "subject": "Empty Email",
            "from": {"email": "sender@example.com"},
            # No text or html content
        }

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse:
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            assert "Subject: Empty Email" in result.content
            assert "From: sender@example.com" in result.content
            # Should not contain any body content

    def test_extract_bytes_sync_parsing_error(self) -> None:
        """Test handling of email parsing errors."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"invalid email content"

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse:
            mock_mailparse.EmailDecode.load.side_effect = Exception("Parsing failed")

            with pytest.raises(RuntimeError, match="Failed to parse email content: Parsing failed"):
                extractor.extract_bytes_sync(content)

    def test_extract_email_headers_method(self) -> None:
        """Test the _extract_email_headers method directly."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())

        parsed_email: dict[str, Any] = {
            "subject": "Test Subject",
            "from": {"email": "sender@example.com"},
            "to": [{"email": "recipient@example.com"}],
            "date": "2023-01-01",
            "cc": "cc@example.com",
            "bcc": "bcc@example.com",
        }

        text_parts: list[str] = []
        metadata: dict[str, Any] = {}

        extractor._extract_email_headers(parsed_email, text_parts, metadata)

        assert len(text_parts) == 6  # subject, from, to, date, cc, bcc
        assert "Subject: Test Subject" in text_parts
        assert "From: sender@example.com" in text_parts
        assert "To: recipient@example.com" in text_parts
        assert "Date: 2023-01-01" in text_parts
        assert "CC: cc@example.com" in text_parts
        assert "BCC: bcc@example.com" in text_parts

        assert metadata["subject"] == "Test Subject"
        assert metadata["email_from"] == "sender@example.com"
        assert metadata["email_to"] == "recipient@example.com"
        assert metadata["date"] == "2023-01-01"
        assert metadata["email_cc"] == "cc@example.com"
        assert metadata["email_bcc"] == "bcc@example.com"

    def test_extract_email_body_method(self) -> None:
        """Test the _extract_email_body method directly."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())

        # Test with text content
        parsed_email: dict[str, Any] = {"text": "Plain text content"}
        text_parts: list[str] = []

        extractor._extract_email_body(parsed_email, text_parts)

        assert len(text_parts) == 1
        assert "Plain text content" in text_parts[0]

    def test_extract_email_attachments_method(self) -> None:
        """Test the _extract_email_attachments method directly."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())

        parsed_email: dict[str, Any] = {
            "attachments": [
                {"name": "file1.pdf"},
                {"name": "file2.jpg"},
            ]
        }

        text_parts: list[str] = []
        metadata: dict[str, Any] = {}

        extractor._extract_email_attachments(parsed_email, text_parts, metadata)

        assert len(text_parts) == 1
        assert "Attachments: file1.pdf, file2.jpg" in text_parts[0]
        assert metadata["attachments"] == ["file1.pdf", "file2.jpg"]

    def test_extract_email_attachments_method_empty(self) -> None:
        """Test _extract_email_attachments with no attachments."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())

        parsed_email: dict[str, Any] = {}  # No attachments
        text_parts: list[str] = []
        metadata: dict[str, Any] = {}

        extractor._extract_email_attachments(parsed_email, text_parts, metadata)

        assert len(text_parts) == 0
        assert "attachments" not in metadata


class TestHTMLTagPattern:
    """Test the HTML tag removal regex pattern."""

    def test_html_tag_pattern_removes_tags(self) -> None:
        """Test that HTML tag pattern correctly removes HTML tags."""
        html_content = "<p>Hello <b>world</b>!</p>"
        result = _HTML_TAG_PATTERN.sub("", html_content)
        assert result == "Hello world!"

    def test_html_tag_pattern_complex_tags(self) -> None:
        """Test pattern with complex HTML tags."""
        html_content = '<div class="test" id="main"><span style="color: red">Text</span></div>'
        result = _HTML_TAG_PATTERN.sub("", html_content)
        assert result == "Text"

    def test_html_tag_pattern_self_closing_tags(self) -> None:
        """Test pattern with self-closing tags."""
        html_content = "Line 1<br/>Line 2<hr/>"
        result = _HTML_TAG_PATTERN.sub("", html_content)
        assert result == "Line 1Line 2"

    def test_html_tag_pattern_no_tags(self) -> None:
        """Test pattern with content that has no HTML tags."""
        content = "Plain text with no tags"
        result = _HTML_TAG_PATTERN.sub("", content)
        assert result == "Plain text with no tags"


class TestEmailExtractorIntegration:
    """Integration tests for EmailExtractor."""

    def test_full_email_extraction_workflow(self) -> None:
        """Test complete email extraction workflow."""
        extractor = EmailExtractor(EML_MIME_TYPE, ExtractionConfig())
        content = b"test email content"

        mock_parsed_email: dict[str, Any] = {
            "subject": "Integration Test Email",
            "from": {"email": "sender@test.com"},
            "to": [{"email": "recipient@test.com"}],
            "date": "2023-01-15T10:30:00Z",
            "cc": "cc@test.com",
            "text": "This is the main email content.\n\nSecond paragraph.",
            "attachments": [
                {"name": "report.pdf"},
                {"name": "data.csv"},
            ],
        }

        with patch("kreuzberg._extractors._email.mailparse") as mock_mailparse:
            mock_mailparse.EmailDecode.load.return_value = mock_parsed_email

            result = extractor.extract_bytes_sync(content)

            # Verify all components are present in content
            assert "Subject: Integration Test Email" in result.content
            assert "From: sender@test.com" in result.content
            assert "To: recipient@test.com" in result.content
            assert "Date: 2023-01-15T10:30:00Z" in result.content
            assert "CC: cc@test.com" in result.content
            assert "This is the main email content." in result.content
            assert "Second paragraph." in result.content
            assert "Attachments: report.pdf, data.csv" in result.content

            # Verify metadata
            assert result.metadata["subject"] == "Integration Test Email"
            assert result.metadata["email_from"] == "sender@test.com"
            assert result.metadata["email_to"] == "recipient@test.com"
            assert result.metadata["date"] == "2023-01-15T10:30:00Z"
            assert result.metadata["email_cc"] == "cc@test.com"
            assert result.metadata["attachments"] == ["report.pdf", "data.csv"]

            # Verify result structure
            assert result.mime_type == PLAIN_TEXT_MIME_TYPE
            assert isinstance(result.chunks, list)
            assert len(result.chunks) == 0  # No chunking by default
