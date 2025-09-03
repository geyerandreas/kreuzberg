"""Tests for Tesseract TSV output and table extraction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from kreuzberg._ocr._tesseract import PSMMode, TesseractBackend, TesseractConfig

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def tesseract_backend() -> TesseractBackend:
    """Create a TesseractBackend instance for testing."""
    return TesseractBackend()


@pytest.fixture
def mock_tsv_output() -> str:
    """Mock TSV output from Tesseract."""
    return """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
1\t1\t0\t0\t0\t0\t0\t0\t770\t342\t-1\t
5\t1\t1\t1\t1\t1\t56\t24\t57\t43\t95.0\tCell
5\t1\t1\t1\t1\t2\t208\t24\t116\t43\t95.0\tFormat
5\t1\t1\t1\t1\t3\t500\t28\t132\t28\t95.0\tFormula
5\t1\t2\t1\t1\t1\t50\t80\t37\t26\t92.0\tB4
5\t1\t2\t1\t1\t2\t167\t80\t177\t33\t93.0\tPercentage
5\t1\t2\t1\t1\t3\t373\t76\t42\t42\t91.0\tNone
5\t1\t3\t1\t1\t1\t48\t130\t39\t27\t92.0\tC4
5\t1\t3\t1\t1\t2\t165\t125\t123\t43\t94.0\tGeneral
5\t1\t3\t1\t1\t3\t373\t126\t42\t42\t91.0\tNone"""


@pytest.fixture
def simple_table_image(tmp_path: Path) -> Path:
    """Create a simple test image with table-like content."""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (800, 400), color="white")
    draw = ImageDraw.Draw(img)

    # Draw simple table structure
    for i in range(4):
        for j in range(3):
            x = 50 + j * 250
            y = 50 + i * 80
            draw.rectangle([x, y, x + 240, y + 70], outline="black")

    img_path = tmp_path / "test_table.png"
    img.save(img_path)
    return img_path


@pytest.mark.anyio
async def test_tsv_output_format(tesseract_backend: TesseractBackend, simple_table_image: Path) -> None:
    """Test that we can get TSV output from Tesseract."""
    with patch("kreuzberg._ocr._tesseract.TesseractBackend._version_checked", True):
        with patch("kreuzberg._ocr._tesseract.run_process") as mock_run:
            # Mock TSV output
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = b"""level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
5\t1\t1\t1\t1\t1\t50\t50\t100\t30\t95.0\tTest"""
            mock_result.stderr = b""
            mock_run.return_value = mock_result

            # We'll need to implement TSV support in process_file
            # For now, test that the backend can be called
            result = await tesseract_backend.process_file(simple_table_image)
            assert result is not None


def test_parse_tsv_output(mock_tsv_output: str) -> None:
    """Test parsing TSV output into structured data."""
    lines = mock_tsv_output.strip().split("\n")
    headers = lines[0].split("\t")

    assert "level" in headers
    assert "text" in headers
    assert "left" in headers
    assert "top" in headers

    # Parse data rows
    data_rows = []
    for line in lines[1:]:
        if line.strip():
            values = line.split("\t")
            if len(values) == len(headers):
                row = dict(zip(headers, values, strict=False))
                if row["text"] and row["text"].strip():
                    data_rows.append(row)

    assert len(data_rows) == 9  # Should have 9 words
    assert data_rows[0]["text"] == "Cell"
    assert data_rows[1]["text"] == "Format"


def test_extract_word_positions(mock_tsv_output: str) -> None:
    """Test extracting word positions from TSV."""
    lines = mock_tsv_output.strip().split("\n")
    headers = lines[0].split("\t")

    words = []
    for line in lines[1:]:
        values = line.split("\t")
        if len(values) == len(headers):
            row = dict(zip(headers, values, strict=False))
            if row.get("level") == "5" and row.get("text", "").strip():
                words.append(
                    {
                        "text": row["text"],
                        "left": int(row["left"]),
                        "top": int(row["top"]),
                        "width": int(row["width"]),
                        "height": int(row["height"]),
                        "conf": float(row["conf"]),
                    }
                )

    assert len(words) == 9

    # Check first row words are roughly aligned
    first_row = [w for w in words if w["top"] < 50]  # type: ignore[operator]
    assert len(first_row) == 3
    assert all(20 <= w["top"] <= 30 for w in first_row)  # type: ignore[operator]


def test_group_words_by_row(mock_tsv_output: str) -> None:
    """Test grouping words into rows based on Y position."""
    lines = mock_tsv_output.strip().split("\n")
    headers = lines[0].split("\t")

    words = []
    for line in lines[1:]:
        values = line.split("\t")
        if len(values) == len(headers):
            row = dict(zip(headers, values, strict=False))
            if row.get("level") == "5" and row.get("text", "").strip():
                words.append({"text": row["text"], "top": int(row["top"]), "left": int(row["left"])})

    # Group by approximate Y position (with threshold)
    rows: dict[Any, Any] = {}
    threshold = 20  # pixels

    for word in words:
        y = word["top"]
        # Find existing row or create new one
        row_key = None
        for key in rows:
            if abs(key - y) <= threshold:
                row_key = key
                break

        if row_key is None:
            row_key = y
            rows[row_key] = []

        rows[row_key].append(word)

    # Sort rows by Y position
    sorted_rows = sorted(rows.items(), key=lambda x: x[0])

    assert len(sorted_rows) == 3  # Should have 3 rows

    # Each row should have 3 words
    for _, row_words in sorted_rows:
        assert len(row_words) == 3


def test_group_words_by_column(mock_tsv_output: str) -> None:
    """Test grouping words into columns based on X position."""
    lines = mock_tsv_output.strip().split("\n")
    headers = lines[0].split("\t")

    words = []
    for line in lines[1:]:
        values = line.split("\t")
        if len(values) == len(headers):
            row = dict(zip(headers, values, strict=False))
            if row.get("level") == "5" and row.get("text", "").strip():
                words.append({"text": row["text"], "left": int(row["left"])})

    # Group by X position
    columns: dict[Any, Any] = {}
    threshold = 50  # pixels

    for word in words:
        x = word["left"]
        # Find existing column or create new one
        col_key = None
        for key in columns:
            if abs(key - x) <= threshold:
                col_key = key
                break

        if col_key is None:
            col_key = x
            columns[col_key] = []

        columns[col_key].append(word)

    # Sort columns by X position
    sorted_cols = sorted(columns.items(), key=lambda x: x[0])

    # Should have 3 or 4 columns (Formula might be far enough to be its own column)
    assert 3 <= len(sorted_cols) <= 4

    # Check that we have the expected words
    all_words = []
    for _, col_words in sorted_cols:
        all_words.extend(col_words)

    assert len(all_words) == 9  # Should have 9 total words


def test_simple_table_reconstruction(mock_tsv_output: str) -> None:
    """Test reconstructing a simple table from TSV data."""
    # Parse TSV
    lines = mock_tsv_output.strip().split("\n")
    headers = lines[0].split("\t")

    words = []
    for line in lines[1:]:
        values = line.split("\t")
        if len(values) == len(headers):
            row = dict(zip(headers, values, strict=False))
            if row.get("level") == "5" and row.get("text", "").strip():
                words.append({"text": row["text"], "left": int(row["left"]), "top": int(row["top"])})

    # Group into rows and columns
    row_threshold = 20

    # Group by rows
    row_groups: dict[Any, Any] = {}
    for word in words:
        y = word["top"]
        row_key = None
        for key in row_groups:
            if abs(key - y) <= row_threshold:
                row_key = key
                break
        if row_key is None:
            row_key = y
            row_groups[row_key] = []
        row_groups[row_key].append(word)

    # Sort rows
    sorted_rows = sorted(row_groups.items(), key=lambda x: x[0])

    # Build table
    table = []
    for _, row_words in sorted_rows:
        # Sort words in row by X position
        row_words.sort(key=lambda w: w["left"])
        row_text = [w["text"] for w in row_words]
        table.append(row_text)

    assert len(table) == 3
    assert table[0] == ["Cell", "Format", "Formula"]
    assert table[1] == ["B4", "Percentage", "None"]
    assert table[2] == ["C4", "General", "None"]


def test_markdown_table_generation() -> None:
    """Test generating markdown table from reconstructed data."""
    table = [["Cell", "Format", "Formula"], ["B4", "Percentage", "None"], ["C4", "General", "None"]]

    # Generate markdown
    lines = []

    # Header
    lines.append("| " + " | ".join(table[0]) + " |")

    # Separator
    lines.append("| " + " | ".join(["---"] * len(table[0])) + " |")

    # Data rows
    lines.extend("| " + " | ".join(row) + " |" for row in table[1:])

    markdown = "\n".join(lines)

    expected = """| Cell | Format | Formula |
| --- | --- | --- |
| B4 | Percentage | None |
| C4 | General | None |"""

    assert markdown == expected


@pytest.mark.anyio
async def test_config_with_tsv_output() -> None:
    """Test that TesseractConfig can be extended for TSV output."""
    config = TesseractConfig(language="eng", psm=PSMMode.AUTO)

    # We'll need to add output_format to TesseractConfig
    # For now, just test the existing config
    assert config.language == "eng"
    assert config.psm == PSMMode.AUTO


@pytest.mark.anyio
async def test_psm_mode_for_tables() -> None:
    """Test using appropriate PSM mode for table extraction."""
    # PSM 6 - Uniform block of text
    config_block = TesseractConfig(psm=PSMMode.SINGLE_BLOCK)
    assert config_block.psm.value == 6

    # PSM 3 - Fully automatic
    config_auto = TesseractConfig(psm=PSMMode.AUTO)
    assert config_auto.psm.value == 3

    # PSM 4 - Single column (good for tables)
    config_column = TesseractConfig(psm=PSMMode.SINGLE_COLUMN)
    assert config_column.psm.value == 4


def test_handle_empty_cells_in_table() -> None:
    """Test handling tables with empty cells."""
    # Mock TSV with missing cells
    tsv_data = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
5\t1\t1\t1\t1\t1\t50\t50\t100\t30\t95.0\tName
5\t1\t1\t1\t1\t2\t200\t50\t100\t30\t95.0\tAge
5\t1\t2\t1\t1\t1\t50\t100\t100\t30\t92.0\tJohn
5\t1\t3\t1\t1\t1\t50\t150\t100\t30\t93.0\tJane
5\t1\t3\t1\t1\t2\t200\t150\t100\t30\t94.0\t25"""

    lines = tsv_data.strip().split("\n")
    headers = lines[0].split("\t")

    # Extract words
    words = []
    for line in lines[1:]:
        values = line.split("\t")
        if len(values) == len(headers):
            row_dict = dict(zip(headers, values, strict=False))
            if row_dict.get("level") == "5":
                words.append({"text": row_dict["text"], "left": int(row_dict["left"]), "top": int(row_dict["top"])})

    # Group by rows with larger threshold
    row_groups: dict[Any, Any] = {}
    threshold = 30
    for word in words:
        y = word["top"]
        row_key = None
        for key in row_groups:
            if abs(key - y) <= threshold:
                row_key = key
                break
        if row_key is None:
            row_key = y
            row_groups[row_key] = []
        row_groups[row_key].append(word)

    sorted_rows = sorted(row_groups.items(), key=lambda x: x[0])

    # Detect columns
    all_x_positions = sorted({w["left"] for w in words})  # type: ignore[type-var]

    # Build table with empty cell handling
    table: list[list[str]] = []
    for _, row_words in sorted_rows:
        row_dict = {w["left"]: w["text"] for w in row_words}
        row_data = [row_dict.get(x, "") for x in all_x_positions]  # type: ignore[call-overload]
        table.append(row_data)

    assert len(table) == 3
    assert table[0] == ["Name", "Age"]
    assert table[1] == ["John", ""]  # Missing age for John
    assert table[2] == ["Jane", "25"]


def test_handle_multi_word_cells() -> None:
    """Test handling cells with multiple words."""
    tsv_data = """level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext
5\t1\t1\t1\t1\t1\t50\t50\t50\t30\t95.0\tFirst
5\t1\t1\t1\t1\t2\t105\t50\t50\t30\t95.0\tName
5\t1\t1\t1\t1\t3\t300\t50\t100\t30\t95.0\tDepartment
5\t1\t2\t1\t1\t1\t50\t100\t50\t30\t92.0\tJohn
5\t1\t2\t1\t1\t2\t105\t100\t50\t30\t92.0\tDoe
5\t1\t2\t1\t1\t3\t300\t100\t100\t30\t93.0\tEngineering"""

    lines = tsv_data.strip().split("\n")
    headers = lines[0].split("\t")

    words = []
    for line in lines[1:]:
        values = line.split("\t")
        if len(values) == len(headers):
            row_dict = dict(zip(headers, values, strict=False))
            if row_dict.get("level") == "5":
                words.append({"text": row_dict["text"], "left": int(row_dict["left"]), "top": int(row_dict["top"])})

    # Group by rows
    row_groups: dict[Any, Any] = {}
    for word in words:
        y = word["top"]
        row_key = None
        for key in row_groups:
            if abs(key - y) <= 20:
                row_key = key
                break
        if row_key is None:
            row_key = y
            row_groups[row_key] = []
        row_groups[row_key].append(word)

    # Detect column boundaries (larger gap between columns)
    sorted_rows = sorted(row_groups.items(), key=lambda x: x[0])

    # Simple column detection based on gaps
    table = []
    for _, row_words in sorted_rows:
        row_words.sort(key=lambda w: w["left"])

        # Group words into cells based on proximity
        cells = []
        current_cell = [row_words[0]["text"]]
        last_x = row_words[0]["left"]

        for word in row_words[1:]:
            # If gap is large, start new cell
            if word["left"] - last_x > 150:  # Large gap indicates new column
                cells.append(" ".join(current_cell))
                current_cell = [word["text"]]
            else:
                current_cell.append(word["text"])
            last_x = word["left"]

        cells.append(" ".join(current_cell))
        table.append(cells)

    assert len(table) == 2
    assert table[0] == ["First Name", "Department"]
    assert table[1] == ["John Doe", "Engineering"]
