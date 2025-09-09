from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from kreuzberg import batch_extract_file, extract_bytes, extract_file, extract_file_sync
from kreuzberg._types import ExtractionConfig, ExtractionResult

if TYPE_CHECKING:
    from collections.abc import Sequence


REGRESSION_DATA_DIR = Path(__file__).parent / "regression_data"


@pytest.fixture
def google_doc_pdf() -> Path:
    return REGRESSION_DATA_DIR / "google-doc-document.pdf"


@pytest.fixture
def xerox_pdf() -> Path:
    return REGRESSION_DATA_DIR / "Xerox_AltaLink_series_mfp_sag_en-US 2.pdf"


@pytest.fixture
def test_xls() -> Path:
    return REGRESSION_DATA_DIR / "testXls.xls"


@pytest.mark.anyio
async def test_google_doc_pdf_extraction_with_tesseract(google_doc_pdf: Path) -> None:
    config = ExtractionConfig(
        force_ocr=True,
        ocr_backend="tesseract",
    )
    result: ExtractionResult = await extract_file(
        file_path=str(google_doc_pdf),
        config=config,
    )

    assert result is not None
    assert result.content
    assert "Error: ExceptionGroup" not in result.content
    assert result.mime_type == "text/plain"


@pytest.mark.anyio
async def test_xerox_pdf_extraction_with_tesseract(xerox_pdf: Path) -> None:
    config = ExtractionConfig(
        force_ocr=True,
        ocr_backend="tesseract",
    )
    result: ExtractionResult = await extract_file(
        file_path=str(xerox_pdf),
        config=config,
    )

    assert result is not None
    assert result.content
    assert "Error: ExceptionGroup" not in result.content
    assert result.mime_type == "text/plain"


def test_google_doc_pdf_extraction_sync(google_doc_pdf: Path) -> None:
    config = ExtractionConfig(
        force_ocr=True,
        ocr_backend="tesseract",
    )
    result: ExtractionResult = extract_file_sync(
        file_path=str(google_doc_pdf),
        config=config,
    )

    assert result is not None
    assert result.content
    assert "Error: ExceptionGroup" not in result.content
    assert result.mime_type == "text/plain"


def test_xerox_pdf_extraction_sync(xerox_pdf: Path) -> None:
    config = ExtractionConfig(
        force_ocr=True,
        ocr_backend="tesseract",
    )
    result: ExtractionResult = extract_file_sync(
        file_path=str(xerox_pdf),
        config=config,
    )

    assert result is not None
    assert result.content
    assert "Error: ExceptionGroup" not in result.content
    assert result.mime_type == "text/plain"


@pytest.mark.anyio
async def test_xls_extraction(test_xls: Path) -> None:
    result: ExtractionResult = await extract_file(
        file_path=str(test_xls),
    )

    assert result is not None
    assert result.content
    assert "workbook.xml.rels" not in result.content
    assert "ParsingError" not in result.content
    assert result.mime_type == "text/markdown"


def test_xls_extraction_sync(test_xls: Path) -> None:
    result: ExtractionResult = extract_file_sync(
        file_path=str(test_xls),
    )

    assert result is not None
    assert result.content
    assert "workbook.xml.rels" not in result.content
    assert "ParsingError" not in result.content
    assert result.mime_type == "text/markdown"


@pytest.mark.anyio
async def test_xls_extraction_with_bytes(test_xls: Path) -> None:
    with test_xls.open("rb") as f:
        content: bytes = f.read()

    result: ExtractionResult = await extract_bytes(
        content=content,
        mime_type="application/vnd.ms-excel",
    )

    assert result is not None
    assert result.content
    assert "workbook.xml.rels" not in result.content
    assert "ParsingError" not in result.content
    assert result.mime_type == "text/markdown"


@pytest.mark.anyio
async def test_batch_pdf_extraction(google_doc_pdf: Path, xerox_pdf: Path) -> None:
    config = ExtractionConfig(
        force_ocr=True,
        ocr_backend="tesseract",
    )
    results: Sequence[ExtractionResult] = await batch_extract_file(
        file_paths=[str(google_doc_pdf), str(xerox_pdf)],
        config=config,
    )

    assert len(results) == 2
    for result in results:
        assert result is not None
        if hasattr(result, "error"):
            assert "ExceptionGroup" not in str(result.error)
        else:
            assert result.content
            assert result.mime_type == "text/plain"
