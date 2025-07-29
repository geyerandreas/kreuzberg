"""Comprehensive tests for kreuzberg._document_classification module."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from kreuzberg._document_classification import (
    DOCUMENT_CLASSIFIERS,
    _get_translated_text,
    auto_detect_document_type,
    classify_document,
    classify_document_from_layout,
)
from kreuzberg._types import ExtractionConfig, ExtractionResult, Metadata, TableData
from kreuzberg.exceptions import MissingDependencyError


class TestDocumentClassifiers:
    """Test document classifier constants."""

    def test_document_classifiers_structure(self) -> None:
        """Test that document classifiers are properly structured."""
        assert isinstance(DOCUMENT_CLASSIFIERS, dict)
        assert len(DOCUMENT_CLASSIFIERS) > 0

        # Check specific document types exist
        expected_types = {"invoice", "receipt", "contract", "report", "form"}
        assert expected_types.issubset(set(DOCUMENT_CLASSIFIERS.keys()))

        # Check all patterns are strings
        for patterns in DOCUMENT_CLASSIFIERS.values():
            assert isinstance(patterns, list)
            assert len(patterns) > 0
            for pattern in patterns:
                assert isinstance(pattern, str)
                assert len(pattern) > 0

    def test_invoice_patterns(self) -> None:
        """Test invoice document patterns."""
        invoice_patterns = DOCUMENT_CLASSIFIERS["invoice"]
        expected_patterns = {"invoice", "bill to", "invoice number", "total amount", "tax id"}
        assert set(invoice_patterns) == expected_patterns

    def test_receipt_patterns(self) -> None:
        """Test receipt document patterns."""
        receipt_patterns = DOCUMENT_CLASSIFIERS["receipt"]
        expected_patterns = {"receipt", "cash receipt", "payment", "subtotal", "total due"}
        assert set(receipt_patterns) == expected_patterns


class TestGetTranslatedText:
    """Test _get_translated_text function."""

    def test_get_translated_text_success(self) -> None:
        """Test successful text translation."""
        result = ExtractionResult(content="This is a test invoice", mime_type="text/plain", metadata={})

        # Mock the GoogleTranslator class
        mock_translator_class = Mock()
        mock_instance = Mock()
        mock_instance.translate.return_value = "This is a test invoice"
        mock_translator_class.return_value = mock_instance

        with patch.dict("sys.modules", {"deep_translator": Mock(GoogleTranslator=mock_translator_class)}):
            translated = _get_translated_text(result)

            assert translated == "this is a test invoice"
            mock_translator_class.assert_called_once_with(source="auto", target="en")
            mock_instance.translate.assert_called_once_with("This is a test invoice")

    def test_get_translated_text_with_non_english(self) -> None:
        """Test translation of non-English text."""
        result = ExtractionResult(content="Factura número 12345", mime_type="text/plain", metadata={})

        # Mock the GoogleTranslator class
        mock_translator_class = Mock()
        mock_instance = Mock()
        mock_instance.translate.return_value = "Invoice number 12345"
        mock_translator_class.return_value = mock_instance

        with patch.dict("sys.modules", {"deep_translator": Mock(GoogleTranslator=mock_translator_class)}):
            translated = _get_translated_text(result)

            assert translated == "invoice number 12345"

    def test_get_translated_text_missing_dependency(self) -> None:
        """Test handling of missing deep-translator dependency."""
        result = ExtractionResult(content="Test content", mime_type="text/plain", metadata={})

        # Mock the import to fail
        import builtins
        original_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "deep_translator":
                raise ImportError("No module named 'deep_translator'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(MissingDependencyError, match="deep-translator.*library is not installed"):
                _get_translated_text(result)

    def test_get_translated_text_empty_content(self) -> None:
        """Test translation of empty content."""
        result = ExtractionResult(content="", mime_type="text/plain", metadata={})

        # Mock the GoogleTranslator class
        mock_translator_class = Mock()
        mock_instance = Mock()
        mock_instance.translate.return_value = ""
        mock_translator_class.return_value = mock_instance

        with patch.dict("sys.modules", {"deep_translator": Mock(GoogleTranslator=mock_translator_class)}):
            translated = _get_translated_text(result)

            assert translated == ""

    def test_get_translated_text_handles_none_response(self) -> None:
        """Test handling of None response from translator."""
        result = ExtractionResult(content="Test content", mime_type="text/plain", metadata={})

        # Mock the GoogleTranslator class to return None, which should be handled
        mock_translator_class = Mock()
        mock_instance = Mock()
        # Create a Mock that returns None but has a lower() method that returns "none"
        mock_response = Mock()
        mock_response.lower.return_value = "none"
        mock_instance.translate.return_value = mock_response
        mock_translator_class.return_value = mock_instance

        with patch.dict("sys.modules", {"deep_translator": Mock(GoogleTranslator=mock_translator_class)}):
            translated = _get_translated_text(result)

            assert translated == "none"


class TestClassifyDocument:
    """Test classify_document function."""

    def test_classify_invoice_document(self) -> None:
        """Test classification of invoice document."""
        result = ExtractionResult(
            content="Invoice number 12345 total amount $100 tax id 123456", mime_type="text/plain", metadata={}
        )
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = "invoice number 12345 total amount $100 tax id 123456"

            doc_type, confidence = classify_document(result, config)

            assert doc_type == "invoice"
            assert confidence is not None
            assert confidence > 0.3

    def test_classify_receipt_document(self) -> None:
        """Test classification of receipt document."""
        result = ExtractionResult(
            content="Cash receipt payment subtotal $50 total due $55", mime_type="text/plain", metadata={}
        )
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = "cash receipt payment subtotal $50 total due $55"

            doc_type, confidence = classify_document(result, config)

            assert doc_type == "receipt"
            assert confidence is not None
            assert confidence > 0.3

    def test_classify_contract_document(self) -> None:
        """Test classification of contract document."""
        result = ExtractionResult(
            content="Agreement between party a and party b with terms and conditions requiring signature",
            mime_type="text/plain",
            metadata={},
        )
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = (
                "agreement between party a and party b with terms and conditions requiring signature"
            )

            doc_type, confidence = classify_document(result, config)

            assert doc_type == "contract"
            assert confidence is not None
            assert confidence > 0.3

    def test_classify_report_document(self) -> None:
        """Test classification of report document."""
        result = ExtractionResult(
            content="Report summary analysis findings conclusion of the study", mime_type="text/plain", metadata={}
        )
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = "report summary analysis findings conclusion of the study"

            doc_type, confidence = classify_document(result, config)

            assert doc_type == "report"
            assert confidence is not None
            assert confidence > 0.3

    def test_classify_form_document(self) -> None:
        """Test classification of form document."""
        result = ExtractionResult(
            content="Please fill out this form with date and signature then submit", mime_type="text/plain", metadata={}
        )
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = "please fill out this form with date and signature then submit"

            doc_type, confidence = classify_document(result, config)

            assert doc_type == "form"
            assert confidence is not None
            assert confidence > 0.3

    def test_classify_no_matches(self) -> None:
        """Test classification when no patterns match."""
        result = ExtractionResult(
            content="This is just random text with no document keywords", mime_type="text/plain", metadata={}
        )
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = "this is just random text with no document keywords"

            doc_type, confidence = classify_document(result, config)

            assert doc_type is None
            assert confidence is None

    def test_classify_low_confidence(self) -> None:
        """Test classification with confidence below threshold."""
        result = ExtractionResult(
            content="some random text", mime_type="text/plain", metadata={}
        )  # Text with no strong matches
        config = ExtractionConfig(document_type_confidence_threshold=0.8)  # High threshold

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = "some random text"

            doc_type, confidence = classify_document(result, config)

            assert doc_type is None
            assert confidence is None

    def test_classify_multiple_types_highest_wins(self) -> None:
        """Test classification when multiple document types match."""
        # Content that matches both invoice and receipt patterns
        result = ExtractionResult(content="Invoice receipt payment total amount", mime_type="text/plain", metadata={})
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = "invoice receipt payment total amount"

            doc_type, confidence = classify_document(result, config)

            # Should return the type with highest confidence
            assert doc_type is not None
            assert confidence is not None
            assert confidence > 0.3


class TestClassifyDocumentFromLayout:
    """Test classify_document_from_layout function."""

    def test_classify_from_layout_success(self) -> None:
        """Test successful classification from layout data."""
        # Create mock layout DataFrame
        layout_data = pd.DataFrame(
            {
                "text": ["Invoice", "Number", "12345", "Total Amount", "$100"],
                "top": [10, 20, 30, 40, 50],
                "height": [15, 15, 15, 15, 15],
            }
        )

        result = ExtractionResult(
            content="Invoice Number 12345 Total Amount $100", mime_type="text/plain", metadata={}, layout=layout_data
        )
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = "invoice number 12345 total amount $100"

            doc_type, confidence = classify_document_from_layout(result, config)

            assert doc_type == "invoice"
            assert confidence is not None
            assert confidence > 0.3

    def test_classify_from_layout_no_layout(self) -> None:
        """Test classification when layout is None."""
        result = ExtractionResult(content="Test content", mime_type="text/plain", metadata={}, layout=None)
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        doc_type, confidence = classify_document_from_layout(result, config)

        assert doc_type is None
        assert confidence is None

    def test_classify_from_layout_empty_layout(self) -> None:
        """Test classification when layout is empty."""
        empty_layout = pd.DataFrame()
        result = ExtractionResult(content="Test content", mime_type="text/plain", metadata={}, layout=empty_layout)
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        doc_type, confidence = classify_document_from_layout(result, config)

        assert doc_type is None
        assert confidence is None

    def test_classify_from_layout_missing_columns(self) -> None:
        """Test classification when layout missing required columns."""
        # Missing 'height' column
        layout_data = pd.DataFrame({"text": ["Invoice", "Number"], "top": [10, 20]})

        result = ExtractionResult(content="Invoice Number", mime_type="text/plain", metadata={}, layout=layout_data)
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        doc_type, confidence = classify_document_from_layout(result, config)

        assert doc_type is None
        assert confidence is None

    def test_classify_from_layout_header_bonus(self) -> None:
        """Test that matches in document header get bonus scoring."""
        # Create layout where keywords appear at top (header)
        layout_data = pd.DataFrame(
            {
                "text": ["Invoice", "Number", "12345"],
                "top": [5, 15, 200],  # First word very near top
                "height": [10, 10, 10],
            }
        )

        result = ExtractionResult(
            content="Invoice Number 12345", mime_type="text/plain", metadata={}, layout=layout_data
        )
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = "invoice number 12345"

            doc_type, confidence = classify_document_from_layout(result, config)

            assert doc_type == "invoice"
            assert confidence is not None
            # Should have higher confidence due to header bonus
            assert confidence > 0.3

    def test_classify_from_layout_no_matches(self) -> None:
        """Test layout classification with no pattern matches."""
        layout_data = pd.DataFrame({"text": ["Random", "Text", "Here"], "top": [10, 20, 30], "height": [15, 15, 15]})

        result = ExtractionResult(content="Random Text Here", mime_type="text/plain", metadata={}, layout=layout_data)
        config = ExtractionConfig(document_type_confidence_threshold=0.3)

        with patch("kreuzberg._document_classification._get_translated_text") as mock_translate:
            mock_translate.return_value = "random text here"

            doc_type, confidence = classify_document_from_layout(result, config)

            assert doc_type is None
            assert confidence is None


class TestAutoDetectDocumentType:
    """Test auto_detect_document_type function."""

    def test_auto_detect_vision_mode_with_file(self) -> None:
        """Test auto-detection in vision mode with file path."""
        result = ExtractionResult(content="Test content", mime_type="text/plain", metadata={})
        config = ExtractionConfig(document_classification_mode="vision")
        file_path = Path("/test/file.pdf")

        # Mock OCR backend and its response
        mock_layout_result = ExtractionResult(
            content="Test content",
            mime_type="text/plain",
            metadata={},
            layout=pd.DataFrame({"text": ["Invoice", "Number"], "top": [10, 20], "height": [15, 15]}),
        )

        with (
            patch("kreuzberg._document_classification.get_ocr_backend") as mock_get_backend,
            patch("kreuzberg._document_classification.classify_document_from_layout") as mock_classify_layout,
        ):
            mock_backend = Mock()
            mock_backend.process_file_sync.return_value = mock_layout_result
            mock_get_backend.return_value = mock_backend
            mock_classify_layout.return_value = ("invoice", 0.8)

            updated_result = auto_detect_document_type(result, config, file_path)

            assert updated_result.document_type == "invoice"
            assert updated_result.document_type_confidence == 0.8
            mock_get_backend.assert_called_once_with("tesseract")
            mock_backend.process_file_sync.assert_called_once_with(file_path, **config.get_config_dict())
            mock_classify_layout.assert_called_once_with(mock_layout_result, config)

    def test_auto_detect_text_mode(self) -> None:
        """Test auto-detection in text mode."""
        result = ExtractionResult(content="Invoice number 12345", mime_type="text/plain", metadata={})
        config = ExtractionConfig(document_classification_mode="text")

        with patch("kreuzberg._document_classification.classify_document") as mock_classify:
            mock_classify.return_value = ("invoice", 0.7)

            updated_result = auto_detect_document_type(result, config)

            assert updated_result.document_type == "invoice"
            assert updated_result.document_type_confidence == 0.7
            mock_classify.assert_called_once_with(result, config)

    def test_auto_detect_vision_mode_no_file(self) -> None:
        """Test auto-detection in vision mode without file path."""
        result = ExtractionResult(content="Invoice number 12345", mime_type="text/plain", metadata={})
        config = ExtractionConfig(document_classification_mode="vision")
        file_path = None

        with patch("kreuzberg._document_classification.classify_document") as mock_classify:
            mock_classify.return_value = ("invoice", 0.7)

            updated_result = auto_detect_document_type(result, config, file_path)

            assert updated_result.document_type == "invoice"
            assert updated_result.document_type_confidence == 0.7
            mock_classify.assert_called_once_with(result, config)

    def test_auto_detect_no_detection(self) -> None:
        """Test auto-detection when no document type is detected."""
        result = ExtractionResult(content="Random text", mime_type="text/plain", metadata={})
        config = ExtractionConfig(document_classification_mode="text")

        with patch("kreuzberg._document_classification.classify_document") as mock_classify:
            mock_classify.return_value = (None, None)

            updated_result = auto_detect_document_type(result, config)

            assert updated_result.document_type is None
            assert updated_result.document_type_confidence is None

    def test_auto_detect_preserves_other_fields(self) -> None:
        """Test that auto-detection preserves other result fields."""
        original_tables: list[TableData] = []
        original_metadata: Metadata = {"title": "test"}

        result = ExtractionResult(
            content="Invoice number 12345", mime_type="text/plain", tables=original_tables, metadata=original_metadata
        )
        config = ExtractionConfig(document_classification_mode="text")

        with patch("kreuzberg._document_classification.classify_document") as mock_classify:
            mock_classify.return_value = ("invoice", 0.7)

            updated_result = auto_detect_document_type(result, config)

            # Document type should be set
            assert updated_result.document_type == "invoice"
            assert updated_result.document_type_confidence == 0.7

            # Other fields should be preserved
            assert updated_result.content == "Invoice number 12345"
            assert updated_result.tables == []
            assert updated_result.metadata == original_metadata
