"""Comprehensive tests for email extractor covering all code paths."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from kreuzberg import ExtractionConfig
from kreuzberg._extractors._email import EmailExtractor
from kreuzberg._mime_types import EML_MIME_TYPE, PLAIN_TEXT_MIME_TYPE
from kreuzberg.exceptions import MissingDependencyError


@pytest.fixture
def email_extractor() -> EmailExtractor:
    """Create email extractor instance."""
    config = ExtractionConfig()
    return EmailExtractor(EML_MIME_TYPE, config)


@pytest.fixture
def sample_email_path(tmp_path: Path) -> Path:
    """Create a sample email file."""
    email_content = b"""From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 1 Jan 2024 12:00:00 +0000
Content-Type: text/plain; charset=utf-8

This is a test email body.
"""
    email_file = tmp_path / "test.eml"
    email_file.write_bytes(email_content)
    return email_file


class TestEmailExtractorAsync:
    """Test async methods of email extractor."""

    @pytest.mark.anyio
    async def test_extract_bytes_async(self, email_extractor: EmailExtractor) -> None:
        """Test async byte extraction."""
        email_content = b"""From: test@example.com
To: user@example.com
Subject: Async Test
Content-Type: text/plain

Async email body content.
"""
        result = await email_extractor.extract_bytes_async(email_content)

        assert result.content
        assert "Async Test" in result.content
        assert "Async email body content" in result.content
        assert result.mime_type == PLAIN_TEXT_MIME_TYPE

    @pytest.mark.anyio
    async def test_extract_path_async(self, email_extractor: EmailExtractor, sample_email_path: Path) -> None:
        """Test async path extraction."""
        result = await email_extractor.extract_path_async(sample_email_path)

        assert result.content
        assert "Test Email" in result.content
        assert "sender@example.com" in result.content
        assert result.metadata["subject"] == "Test Email"


class TestEmailExtractorHeaders:
    """Test email header extraction edge cases."""

    def test_email_with_cc_bcc(self, email_extractor: EmailExtractor) -> None:
        """Test email with CC and BCC headers."""
        email_content = b"""From: sender@example.com
To: recipient@example.com
CC: cc1@example.com, cc2@example.com
BCC: bcc@example.com
Subject: Test with CC/BCC
Content-Type: text/plain

Body content.
"""
        result = email_extractor.extract_bytes_sync(email_content)

        # CC and BCC are included in the content (their string representation)
        assert "CC:" in result.content
        assert "BCC:" in result.content
        # Metadata contains the parsed values (could be list or string)
        assert "email_cc" in result.metadata
        assert "email_bcc" in result.metadata

    def test_email_without_optional_headers(self, email_extractor: EmailExtractor) -> None:
        """Test email without optional headers (no subject, date)."""
        email_content = b"""From: sender@example.com
To: recipient@example.com
Content-Type: text/plain

Simple email without subject or date.
"""
        result = email_extractor.extract_bytes_sync(email_content)

        assert result.content
        assert "sender@example.com" in result.content
        assert "subject" not in result.metadata
        assert "date" not in result.metadata

    def test_email_with_complex_to_field(self, email_extractor: EmailExtractor) -> None:
        """Test email with complex To field structures."""
        # Test with list of dict
        with patch("mailparse.EmailDecode.load") as mock_load:
            mock_load.return_value = {
                "from": {"email": "sender@example.com", "name": "Sender"},
                "to": [{"email": "recipient1@example.com", "name": "Recipient 1"}],
                "subject": "Test",
                "text": "Body",
            }

            result = email_extractor.extract_bytes_sync(b"dummy")
            assert result.metadata["email_to"] == "recipient1@example.com"

        # Test with dict
        with patch("mailparse.EmailDecode.load") as mock_load:
            mock_load.return_value = {
                "from": "sender@example.com",
                "to": {"email": "recipient@example.com", "name": "Recipient"},
                "subject": "Test",
                "text": "Body",
            }

            result = email_extractor.extract_bytes_sync(b"dummy")
            assert result.metadata["email_to"] == "recipient@example.com"

        # Test with string
        with patch("mailparse.EmailDecode.load") as mock_load:
            mock_load.return_value = {
                "from": "sender@example.com",
                "to": "simple@example.com",
                "subject": "Test",
                "text": "Body",
            }

            result = email_extractor.extract_bytes_sync(b"dummy")
            assert result.metadata["email_to"] == "simple@example.com"

        # Test with empty list
        with patch("mailparse.EmailDecode.load") as mock_load:
            mock_load.return_value = {"from": "sender@example.com", "to": [], "subject": "Test", "text": "Body"}

            result = email_extractor.extract_bytes_sync(b"dummy")
            assert "email_to" not in result.metadata


class TestEmailExtractorBody:
    """Test email body extraction including HTML handling."""

    def test_email_with_html_body_with_html2text(self, email_extractor: EmailExtractor) -> None:
        """Test HTML email body extraction with html2text available."""
        with patch("kreuzberg._extractors._email.html2text") as mock_html2text:
            mock_h2t = MagicMock()
            mock_h2t.handle.return_value = "Converted text from HTML"
            mock_html2text.HTML2Text.return_value = mock_h2t

            with patch("mailparse.EmailDecode.load") as mock_load:
                mock_load.return_value = {
                    "from": "sender@example.com",
                    "to": "recipient@example.com",
                    "subject": "HTML Email",
                    "html": "<html><body><p>Hello <b>World</b></p></body></html>",
                }

                result = email_extractor.extract_bytes_sync(b"dummy")

                assert "Converted text from HTML" in result.content
                mock_h2t.handle.assert_called_once()
                assert mock_h2t.ignore_links is True
                assert mock_h2t.ignore_images is True

    def test_email_with_html_body_without_html2text(self, email_extractor: EmailExtractor) -> None:
        """Test HTML email body extraction without html2text (fallback)."""
        with patch("kreuzberg._extractors._email.html2text", None):
            with patch("mailparse.EmailDecode.load") as mock_load:
                mock_load.return_value = {
                    "from": "sender@example.com",
                    "to": "recipient@example.com",
                    "subject": "HTML Email",
                    "html": "<html><body><p>Hello <b>World</b> &amp; Friends</p></body></html>",
                }

                result = email_extractor.extract_bytes_sync(b"dummy")

                # Should strip HTML tags and unescape entities
                assert "Hello World & Friends" in result.content
                assert "<p>" not in result.content
                assert "&amp;" not in result.content

    def test_email_text_preferred_over_html(self, email_extractor: EmailExtractor) -> None:
        """Test that text content is preferred over HTML when both exist."""
        with patch("mailparse.EmailDecode.load") as mock_load:
            mock_load.return_value = {
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "subject": "Multipart Email",
                "text": "Plain text version",
                "html": "<html><body>HTML version</body></html>",
            }

            result = email_extractor.extract_bytes_sync(b"dummy")

            assert "Plain text version" in result.content
            assert "HTML version" not in result.content


class TestEmailExtractorAttachments:
    """Test email attachment handling."""

    def test_email_with_attachments(self, email_extractor: EmailExtractor) -> None:
        """Test email with attachments."""
        with patch("mailparse.EmailDecode.load") as mock_load:
            mock_load.return_value = {
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "subject": "Email with attachments",
                "text": "See attached files",
                "attachments": [
                    {"name": "document.pdf", "content": b"fake pdf"},
                    {"name": "image.jpg", "content": b"fake image"},
                    {},  # Attachment without name
                ],
            }

            result = email_extractor.extract_bytes_sync(b"dummy")

            assert "Attachments: document.pdf, image.jpg, unknown" in result.content
            assert result.metadata["attachments"] == ["document.pdf", "image.jpg", "unknown"]

    def test_email_without_attachments(self, email_extractor: EmailExtractor) -> None:
        """Test email without attachments."""
        with patch("mailparse.EmailDecode.load") as mock_load:
            mock_load.return_value = {
                "from": "sender@example.com",
                "to": "recipient@example.com",
                "subject": "No attachments",
                "text": "Email body",
            }

            result = email_extractor.extract_bytes_sync(b"dummy")

            assert "Attachments:" not in result.content
            assert "attachments" not in result.metadata


class TestEmailExtractorErrors:
    """Test error handling in email extractor."""

    def test_missing_mailparse_dependency(self, email_extractor: EmailExtractor) -> None:
        """Test error when mailparse is not installed."""
        with patch("kreuzberg._extractors._email.mailparse", None):
            with pytest.raises(MissingDependencyError, match="mailparse is required"):
                email_extractor.extract_bytes_sync(b"dummy")

    def test_mailparse_exception(self, email_extractor: EmailExtractor) -> None:
        """Test handling of exceptions from mailparse."""
        with patch("mailparse.EmailDecode.load", side_effect=Exception("Parse error")):
            with pytest.raises(RuntimeError, match="Failed to parse email content"):
                email_extractor.extract_bytes_sync(b"invalid email content")

    def test_extract_path_sync(self, email_extractor: EmailExtractor, sample_email_path: Path) -> None:
        """Test sync path extraction."""
        result = email_extractor.extract_path_sync(sample_email_path)

        assert result.content
        assert "Test Email" in result.content
        assert result.metadata["subject"] == "Test Email"


class TestEmailExtractorEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_email(self, email_extractor: EmailExtractor) -> None:
        """Test extraction of empty/minimal email."""
        with patch("mailparse.EmailDecode.load") as mock_load:
            mock_load.return_value = {}

            result = email_extractor.extract_bytes_sync(b"dummy")

            assert result.content == ""
            assert result.metadata == {}

    def test_email_with_all_fields(self, email_extractor: EmailExtractor) -> None:
        """Test email with all possible fields populated."""
        with patch("mailparse.EmailDecode.load") as mock_load:
            mock_load.return_value = {
                "from": {"email": "sender@example.com", "name": "Sender Name"},
                "to": [{"email": "recipient@example.com", "name": "Recipient"}],
                "cc": "cc@example.com",
                "bcc": "bcc@example.com",
                "subject": "Complete Email",
                "date": "Mon, 1 Jan 2024 12:00:00 +0000",
                "text": "Email body text",
                "attachments": [{"name": "file.txt"}],
            }

            result = email_extractor.extract_bytes_sync(b"dummy")

            # Check all components are present
            assert "Subject: Complete Email" in result.content
            assert "From: sender@example.com" in result.content
            assert "To: recipient@example.com" in result.content
            assert "CC: cc@example.com" in result.content
            assert "BCC: bcc@example.com" in result.content
            assert "Date: Mon, 1 Jan 2024 12:00:00 +0000" in result.content
            assert "Email body text" in result.content
            assert "Attachments: file.txt" in result.content

            # Check metadata
            assert result.metadata["subject"] == "Complete Email"
            assert result.metadata["email_from"] == "sender@example.com"
            assert result.metadata["email_to"] == "recipient@example.com"
            assert result.metadata["email_cc"] == "cc@example.com"
            assert result.metadata["email_bcc"] == "bcc@example.com"
            assert result.metadata["date"] == "Mon, 1 Jan 2024 12:00:00 +0000"
            assert result.metadata["attachments"] == ["file.txt"]
