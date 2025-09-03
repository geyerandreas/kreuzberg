"""Integration tests for Tesseract TSV output and table extraction."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kreuzberg._ocr._table_extractor import TesseractTableExtractor, extract_table_from_tsv
from kreuzberg._ocr._tesseract import TesseractBackend, TesseractConfig


@pytest.fixture
def table_image_path() -> Path:
    """Path to table test image."""
    path = Path("tests/test_source_files/tables/simple.png")
    if not path.exists():
        pytest.skip(f"Test image not found: {path}")
    return path


@pytest.fixture
def science_table_image() -> Path:
    """Path to science table test image."""
    path = Path("tests/test_source_files/tables/science_table.png")
    if not path.exists():
        pytest.skip(f"Test image not found: {path}")
    return path


@pytest.mark.anyio
async def test_tesseract_tsv_output_integration(table_image_path: Path) -> None:
    """Test end-to-end TSV output with real image."""
    backend = TesseractBackend()

    # Mock version check to avoid system dependency
    with patch.object(TesseractBackend, "_version_checked", True):
        # Configure for TSV output
        config = TesseractConfig(
            output_format="tsv",
            enable_table_detection=False,  # Just TSV, no table detection
        )

        # This would fail without real Tesseract, so we mock the run_process
        with patch("kreuzberg._ocr._tesseract.run_process") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            # Simulate TSV output
            mock_result.stdout = b""
            mock_run.return_value = mock_result

            with patch("kreuzberg._ocr._tesseract.AsyncPath") as mock_path:
                # Mock reading TSV file
                mock_path.return_value.read_text.return_value = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
5\t1\t1\t1\t1\t1\t56\t24\t57\t43\t95.0\tCell
5\t1\t1\t1\t1\t2\t208\t24\t116\t43\t95.0\tFormat
5\t1\t1\t1\t1\t3\t500\t28\t132\t28\t95.0\tFormula
5\t1\t2\t1\t1\t1\t50\t80\t37\t26\t92.0\tB4
5\t1\t2\t1\t1\t2\t167\t80\t177\t33\t93.0\tPercentage
5\t1\t2\t1\t1\t3\t373\t76\t42\t42\t91.0\tNone"""

                result = await backend.process_file(table_image_path, **config.__dict__)

                assert result is not None
                assert isinstance(result.content, str)
                # Should extract text from TSV
                assert "Cell" in result.content
                assert "Format" in result.content


@pytest.mark.anyio
async def test_table_detection_enabled(table_image_path: Path) -> None:
    """Test table detection from TSV output."""
    backend = TesseractBackend()

    with patch.object(TesseractBackend, "_version_checked", True):
        config = TesseractConfig(
            output_format="text",  # Will be overridden to TSV
            enable_table_detection=True,
            table_column_threshold=20,
            table_row_threshold_ratio=0.5,
        )

        with patch("kreuzberg._ocr._tesseract.run_process") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = b""
            mock_run.return_value = mock_result

            with patch("kreuzberg._ocr._tesseract.AsyncPath") as mock_path:
                # Mock TSV with table-like data
                mock_path.return_value.read_text.return_value = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
5\t1\t1\t1\t1\t1\t50\t50\t50\t30\t95.0\tName
5\t1\t1\t1\t1\t2\t200\t50\t50\t30\t95.0\tAge
5\t1\t1\t1\t1\t3\t350\t50\t60\t30\t95.0\tDepartment
5\t1\t2\t1\t1\t1\t50\t100\t50\t30\t92.0\tJohn
5\t1\t2\t1\t1\t2\t200\t100\t30\t30\t93.0\t25
5\t1\t2\t1\t1\t3\t350\t100\t100\t30\t91.0\tEngineering
5\t1\t3\t1\t1\t1\t50\t150\t50\t30\t94.0\tJane
5\t1\t3\t1\t1\t2\t200\t150\t30\t30\t92.0\t30
5\t1\t3\t1\t1\t3\t350\t150\t80\t30\t93.0\tMarketing"""

                result = await backend.process_file(table_image_path, **config.__dict__)

                assert result is not None
                assert len(result.tables) > 0

                table = result.tables[0]
                assert "text" in table
                assert "|" in table["text"]  # Markdown table format
                assert "Name" in table["text"]
                assert "Age" in table["text"]


def test_table_extractor_with_real_tsv() -> None:
    """Test table extractor with realistic TSV data."""
    tsv_data = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
1\t1\t0\t0\t0\t0\t0\t0\t800\t600\t-1\t
5\t1\t1\t1\t1\t1\t100\t100\t80\t30\t95.0\tProduct
5\t1\t1\t1\t1\t2\t250\t100\t60\t30\t94.0\tPrice
5\t1\t1\t1\t1\t3\t400\t100\t80\t30\t96.0\tQuantity
5\t1\t2\t1\t1\t1\t100\t150\t80\t30\t92.0\tApples
5\t1\t2\t1\t1\t2\t250\t150\t60\t30\t93.0\t$2.50
5\t1\t2\t1\t1\t3\t400\t150\t40\t30\t91.0\t10
5\t1\t3\t1\t1\t1\t100\t200\t80\t30\t94.0\tBananas
5\t1\t3\t1\t1\t2\t250\t200\t60\t30\t92.0\t$1.20
5\t1\t3\t1\t1\t3\t400\t200\t40\t30\t93.0\t15"""

    extractor = TesseractTableExtractor()
    words = extractor.extract_words(tsv_data)

    assert len(words) == 9
    assert words[0]["text"] == "Product"

    # Test column detection
    cols = extractor.detect_columns(words)
    assert len(cols) == 3
    assert 90 < cols[0] < 110  # Around 100
    assert 240 < cols[1] < 260  # Around 250
    assert 390 < cols[2] < 410  # Around 400

    # Test row detection
    rows = extractor.detect_rows(words)
    assert len(rows) == 3

    # Test table reconstruction
    table = extractor.reconstruct_table(words)
    assert len(table) == 3
    assert table[0] == ["Product", "Price", "Quantity"]
    assert table[1] == ["Apples", "$2.50", "10"]
    assert table[2] == ["Bananas", "$1.20", "15"]

    # Test markdown conversion
    markdown = extractor.to_markdown(table)
    assert "| Product | Price | Quantity |" in markdown
    assert "| --- | --- | --- |" in markdown
    assert "| Apples | $2.50 | 10 |" in markdown


def test_extract_table_from_tsv_convenience() -> None:
    """Test convenience function for table extraction."""
    tsv_data = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
5\t1\t1\t1\t1\t1\t50\t50\t40\t20\t95.0\tA
5\t1\t1\t1\t1\t2\t150\t50\t40\t20\t94.0\tB
5\t1\t2\t1\t1\t1\t50\t100\t40\t20\t93.0\t1
5\t1\t2\t1\t1\t2\t150\t100\t40\t20\t92.0\t2"""

    markdown = extract_table_from_tsv(tsv_data)

    assert markdown != ""
    assert "| A | B |" in markdown
    assert "| 1 | 2 |" in markdown


def test_table_extraction_with_empty_cells() -> None:
    """Test handling of tables with missing cells."""
    tsv_data = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
5\t1\t1\t1\t1\t1\t50\t50\t60\t30\t95.0\tHeader1
5\t1\t1\t1\t1\t2\t200\t50\t60\t30\t94.0\tHeader2
5\t1\t1\t1\t1\t3\t350\t50\t60\t30\t96.0\tHeader3
5\t1\t2\t1\t1\t1\t50\t100\t60\t30\t92.0\tData1
5\t1\t2\t1\t1\t2\t350\t100\t60\t30\t91.0\tData3"""

    extractor = TesseractTableExtractor()
    words = extractor.extract_words(tsv_data)
    table = extractor.reconstruct_table(words)

    assert len(table) == 2
    assert table[0] == ["Header1", "Header2", "Header3"]
    assert table[1][0] == "Data1"
    assert table[1][1] == ""  # Empty cell
    assert table[1][2] == "Data3"


def test_table_extraction_confidence_threshold() -> None:
    """Test that low confidence words are filtered."""
    tsv_data = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
5\t1\t1\t1\t1\t1\t50\t50\t60\t30\t95.0\tGood
5\t1\t1\t1\t1\t2\t150\t50\t60\t30\t20.0\tBad
5\t1\t1\t1\t1\t3\t250\t50\t60\t30\t85.0\tAlsoGood"""

    extractor = TesseractTableExtractor(min_confidence=30.0)
    words = extractor.extract_words(tsv_data)

    assert len(words) == 2  # "Bad" should be filtered out
    assert words[0]["text"] == "Good"
    assert words[1]["text"] == "AlsoGood"


@pytest.mark.parametrize(
    "column_threshold,expected_cols",
    [
        (10, 3),  # Tight threshold - more columns
        (50, 2),  # Loose threshold - columns merge
        (200, 1),  # Very loose - all merge to one
    ],
)
def test_column_clustering_thresholds(column_threshold: int, expected_cols: int) -> None:
    """Test different column clustering thresholds."""
    tsv_data = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
5\t1\t1\t1\t1\t1\t50\t50\t40\t30\t95.0\tA
5\t1\t1\t1\t1\t2\t80\t50\t40\t30\t94.0\tB
5\t1\t1\t1\t1\t3\t200\t50\t40\t30\t93.0\tC"""

    extractor = TesseractTableExtractor(column_threshold=column_threshold)
    words = extractor.extract_words(tsv_data)
    cols = extractor.detect_columns(words)

    assert len(cols) == expected_cols
