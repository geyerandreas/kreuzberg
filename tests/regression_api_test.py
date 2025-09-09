from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from kreuzberg import batch_extract_bytes
from kreuzberg._types import ExtractionConfig

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kreuzberg._types import ExtractionResult


REGRESSION_DATA_DIR = Path(__file__).parent / "regression_data"


@pytest.mark.anyio
async def test_batch_extract_bytes_with_pdfs() -> None:
    google_doc_pdf = REGRESSION_DATA_DIR / "google-doc-document.pdf"
    xerox_pdf = REGRESSION_DATA_DIR / "Xerox_AltaLink_series_mfp_sag_en-US 2.pdf"

    contents = []

    for pdf_path in [google_doc_pdf, xerox_pdf]:
        with pdf_path.open("rb") as f:
            contents.append((f.read(), "application/pdf"))

    config = ExtractionConfig(
        force_ocr=True,
        ocr_backend="tesseract",
    )

    results: Sequence[ExtractionResult] = await batch_extract_bytes(
        contents=contents,
        config=config,
    )

    assert len(results) == 2

    for i, result in enumerate(results):
        assert hasattr(result, "content") or hasattr(result, "error"), f"Result {i} has neither content nor error"

        if hasattr(result, "error"):
            error_str = str(result.error) if hasattr(result, "error") else ""
            assert "ExceptionGroup" not in error_str, f"Found ExceptionGroup error in result {i}: {error_str}"
            assert "unhandled errors in a TaskGroup" not in error_str, (
                f"Found TaskGroup error in result {i}: {error_str}"
            )
        else:
            assert result.content, f"Result {i} has empty content"
            assert result.mime_type == "text/plain", f"Result {i} has unexpected mime_type: {result.mime_type}"


@pytest.mark.anyio
async def test_batch_extract_bytes_with_xls() -> None:
    test_xls = REGRESSION_DATA_DIR / "testXls.xls"

    with test_xls.open("rb") as f:
        xls_content = f.read()

    config = ExtractionConfig()

    results: Sequence[ExtractionResult] = await batch_extract_bytes(
        contents=[(xls_content, "application/vnd.ms-excel")],
        config=config,
    )

    assert len(results) == 1
    result = results[0]

    if hasattr(result, "content"):
        assert "workbook.xml.rels" not in result.content, "Found workbook.xml.rels error in content"
        assert "ParsingError" not in result.content, "Found ParsingError in content"
        assert result.mime_type == "text/markdown"

    if hasattr(result, "error"):
        error_str = str(result.error)
        assert "workbook.xml.rels" not in error_str, f"Found workbook.xml.rels error: {error_str}"
