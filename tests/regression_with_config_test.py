from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from kreuzberg import batch_extract_file, extract_file, extract_file_sync
from kreuzberg._types import ExtractionConfig, PSMMode, TesseractConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kreuzberg._types import ExtractionResult


TEST_DATA_DIR = Path(__file__).parent / "test_source_files"


@pytest.fixture
def user_config() -> ExtractionConfig:
    tesseract_config = TesseractConfig(
        language="eng",
        psm=PSMMode.SINGLE_COLUMN,
    )

    return ExtractionConfig(
        force_ocr=True,
        chunk_content=False,
        extract_tables=False,
        extract_entities=False,
        extract_keywords=False,
        ocr_backend="tesseract",
        auto_detect_language=False,
        auto_detect_document_type=False,
        ocr_config=tesseract_config,
    )


@pytest.fixture
def google_doc_pdf() -> Path:
    return TEST_DATA_DIR / "google-doc-document.pdf"


@pytest.fixture
def xerox_pdf() -> Path:
    return TEST_DATA_DIR / "Xerox_AltaLink_series_mfp_sag_en-US 2.pdf"


@pytest.fixture
def test_xls() -> Path:
    return TEST_DATA_DIR / "testXls.xls"


@pytest.mark.anyio
async def test_pdf_with_user_config_async(google_doc_pdf: Path, user_config: ExtractionConfig) -> None:
    result: ExtractionResult = await extract_file(
        file_path=str(google_doc_pdf),
        config=user_config,
    )

    assert result is not None
    assert result.content
    assert "Error: ExceptionGroup" not in result.content
    assert "unhandled errors in a TaskGroup" not in result.content
    assert result.mime_type == "text/plain"


def test_pdf_with_user_config_sync(xerox_pdf: Path, user_config: ExtractionConfig) -> None:
    result: ExtractionResult = extract_file_sync(
        file_path=str(xerox_pdf),
        config=user_config,
    )

    assert result is not None
    assert result.content
    assert "Error: ExceptionGroup" not in result.content
    assert "unhandled errors in a TaskGroup" not in result.content
    assert result.mime_type == "text/plain"

    assert len(result.content) > 1000, f"Content too short: {len(result.content)} chars"


@pytest.mark.anyio
async def test_batch_pdfs_with_user_config(
    google_doc_pdf: Path, xerox_pdf: Path, user_config: ExtractionConfig
) -> None:
    results: Sequence[ExtractionResult] = await batch_extract_file(
        file_paths=[str(google_doc_pdf), str(xerox_pdf)],
        config=user_config,
    )

    assert len(results) == 2

    for i, result in enumerate(results):
        assert result is not None
        assert hasattr(result, "content"), f"Result {i} has no content attribute"

        if hasattr(result, "error"):
            error_str = str(result.error)
            assert "ExceptionGroup" not in error_str, f"Found ExceptionGroup in result {i}: {error_str}"
            assert "unhandled errors in a TaskGroup" not in error_str, (
                f"Found TaskGroup error in result {i}: {error_str}"
            )
        else:
            assert result.content, f"Result {i} has empty content"
            assert result.mime_type == "text/plain"


@pytest.mark.anyio
async def test_xls_with_user_config(test_xls: Path, user_config: ExtractionConfig) -> None:
    result: ExtractionResult = await extract_file(
        file_path=str(test_xls),
        config=user_config,
    )

    assert result is not None
    assert result.content
    assert "workbook.xml.rels" not in result.content
    assert "ParsingError" not in result.content
    assert result.mime_type == "text/markdown"


@pytest.mark.anyio
async def test_psm_mode_4_specifically(google_doc_pdf: Path) -> None:
    tesseract_config = TesseractConfig(
        language="eng",
        psm=PSMMode.SINGLE_COLUMN,
    )

    config = ExtractionConfig(
        force_ocr=True,
        ocr_backend="tesseract",
        ocr_config=tesseract_config,
    )

    result: ExtractionResult = await extract_file(
        file_path=str(google_doc_pdf),
        config=config,
    )

    assert result is not None
    assert result.content
    assert "Error" not in result.content or "Error" not in result.content[:100]
    assert result.mime_type == "text/plain"
