"""Table extraction from Tesseract TSV output."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import numpy as np

from kreuzberg.exceptions import ParsingError

if TYPE_CHECKING:
    from kreuzberg._types import TSVWord

try:
    from scipy.cluster.hierarchy import fclusterdata

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@runtime_checkable
class TableExtractor(Protocol):
    """Protocol for table extraction algorithms."""

    def extract_words(self, tsv_data: str) -> list[TSVWord]:
        """Parse TSV data into word objects.

        Args:
            tsv_data: Raw TSV output from Tesseract.

        Returns:
            List of word dictionaries with position and text data.
        """
        ...

    def detect_columns(self, words: list[TSVWord]) -> list[int]:
        """Detect column positions using clustering.

        Args:
            words: List of word dictionaries from TSV.

        Returns:
            Sorted list of column X positions.
        """
        ...

    def detect_rows(self, words: list[TSVWord]) -> list[int]:
        """Detect row positions using clustering.

        Args:
            words: List of word dictionaries from TSV.

        Returns:
            Sorted list of row Y positions.
        """
        ...

    def reconstruct_table(self, words: list[TSVWord]) -> list[list[str]]:
        """Reconstruct table as 2D array.

        Args:
            words: List of word dictionaries from TSV.

        Returns:
            2D list representing the table structure.
        """
        ...

    def to_markdown(self, table: list[list[str]]) -> str:
        """Convert table to markdown format.

        Args:
            table: 2D list representing the table.

        Returns:
            Markdown-formatted table string.
        """
        ...


@dataclass
class TesseractTableExtractor:
    """Concrete implementation of table extraction from TSV.

    This class implements algorithms for detecting table structure
    from Tesseract's TSV output and reconstructing it as formatted tables.
    """

    column_threshold: int = 20
    """Pixel threshold for column clustering."""

    row_threshold_ratio: float = 0.5
    """Row threshold as ratio of mean text height."""

    min_confidence: float = 30.0
    """Minimum confidence score to include a word."""

    def extract_words(self, tsv_data: str) -> list[TSVWord]:
        """Parse TSV output into structured word data.

        Args:
            tsv_data: Raw TSV output from Tesseract.

        Returns:
            List of word dictionaries with position and text data.

        Raises:
            ParsingError: If TSV data cannot be parsed.
        """
        try:
            reader = csv.DictReader(StringIO(tsv_data), delimiter="\t")
            words: list[TSVWord] = []

            for row in reader:
                # Only process word-level data (level 5)
                if row.get("level") == "5" and row.get("text", "").strip():
                    try:
                        conf = float(row["conf"])
                        if conf < self.min_confidence:
                            continue

                        words.append(
                            {
                                "level": int(row["level"]),
                                "page_num": int(row["page_num"]),
                                "block_num": int(row["block_num"]),
                                "par_num": int(row["par_num"]),
                                "line_num": int(row["line_num"]),
                                "word_num": int(row["word_num"]),
                                "left": int(row["left"]),
                                "top": int(row["top"]),
                                "width": int(row["width"]),
                                "height": int(row["height"]),
                                "conf": conf,
                                "text": row["text"],
                            }
                        )
                    except (ValueError, KeyError):
                        # Skip malformed rows
                        continue

            return words

        except Exception as e:
            raise ParsingError("Failed to parse TSV data", context={"error": str(e)}) from e

    def detect_columns(self, words: list[TSVWord]) -> list[int]:
        """Detect columns using hierarchical clustering on X positions.

        Args:
            words: List of word dictionaries from TSV.

        Returns:
            Sorted list of column X positions.
        """
        if not words:
            return []

        x_positions = np.array([w["left"] for w in words]).reshape(-1, 1)

        if len(x_positions) == 1:
            return [int(x_positions[0, 0])]

        if not SCIPY_AVAILABLE:
            # Fallback to simple gap-based detection
            return self._detect_columns_simple(words)

        clusters = fclusterdata(x_positions, self.column_threshold, criterion="distance", method="single")

        # Get median position for each cluster
        column_positions = []
        for cluster_id in np.unique(clusters):
            cluster_mask = clusters == cluster_id
            cluster_positions = x_positions[cluster_mask]
            column_positions.append(int(np.median(cluster_positions)))

        return sorted(column_positions)

    def _detect_columns_simple(self, words: list[TSVWord]) -> list[int]:
        """Simple column detection without scipy.

        Args:
            words: List of word dictionaries.

        Returns:
            List of detected column positions.
        """
        if not words:
            return []

        # Sort by X position
        x_positions = sorted({w["left"] for w in words})

        if len(x_positions) == 1:
            return x_positions

        # Group nearby X positions
        columns = []
        current_group = [x_positions[0]]

        for x in x_positions[1:]:
            if x - current_group[-1] <= self.column_threshold:
                current_group.append(x)
            else:
                # New column detected
                columns.append(int(np.median(current_group)))
                current_group = [x]

        # Add last group
        columns.append(int(np.median(current_group)))

        return columns

    def detect_rows(self, words: list[TSVWord]) -> list[int]:
        """Detect rows using clustering on Y positions.

        Args:
            words: List of word dictionaries from TSV.

        Returns:
            Sorted list of row Y positions.
        """
        if not words:
            return []

        # Use Y center for better alignment
        y_centers = np.array([w["top"] + w["height"] / 2 for w in words])
        mean_height = np.mean([w["height"] for w in words])
        threshold = mean_height * self.row_threshold_ratio

        y_positions = y_centers.reshape(-1, 1)

        if len(y_positions) == 1:
            return [int(y_positions[0, 0])]

        if not SCIPY_AVAILABLE:
            # Fallback to simple detection
            return self._detect_rows_simple(words, float(threshold))

        clusters = fclusterdata(y_positions, threshold, criterion="distance", method="single")

        row_positions = []
        for cluster_id in np.unique(clusters):
            cluster_mask = clusters == cluster_id
            cluster_positions = y_positions[cluster_mask]
            row_positions.append(int(np.median(cluster_positions)))

        return sorted(row_positions)

    def _detect_rows_simple(self, words: list[TSVWord], threshold: float) -> list[int]:
        """Simple row detection without scipy.

        Args:
            words: List of word dictionaries.
            threshold: Distance threshold for grouping.

        Returns:
            List of detected row positions.
        """
        if not words:
            return []

        # Sort by Y center position
        y_centers = sorted(w["top"] + w["height"] / 2 for w in words)

        if len(y_centers) == 1:
            return [int(y_centers[0])]

        # Group nearby Y positions
        rows = []
        current_group = [y_centers[0]]

        for y in y_centers[1:]:
            if y - np.mean(current_group) <= threshold:
                current_group.append(y)
            else:
                # New row detected
                rows.append(int(np.median(current_group)))
                current_group = [y]

        # Add last group
        rows.append(int(np.median(current_group)))

        return rows

    def reconstruct_table(self, words: list[TSVWord]) -> list[list[str]]:
        """Reconstruct table from words and detected structure.

        Args:
            words: List of word dictionaries from TSV.

        Returns:
            2D list representing the table structure.
        """
        if not words:
            return []

        col_positions = self.detect_columns(words)
        row_positions = self.detect_rows(words)

        if not col_positions or not row_positions:
            return []

        # Create table grid
        table: list[list[str]] = [[""] * len(col_positions) for _ in range(len(row_positions))]

        # Assign words to cells
        for word in words:
            # Find closest column
            col_idx = self._find_closest_index(word["left"], col_positions)

            # Find closest row (using Y center)
            y_center = word["top"] + word["height"] / 2
            row_idx = self._find_closest_index(y_center, row_positions)

            # Add word to cell (handle multi-word cells)
            if table[row_idx][col_idx]:
                table[row_idx][col_idx] += " " + word["text"]
            else:
                table[row_idx][col_idx] = word["text"]

        # Clean up empty rows/columns
        return self._remove_empty_rows_cols(table)

    def _find_closest_index(self, value: float, positions: list[int]) -> int:
        """Find index of closest position.

        Args:
            value: The value to match.
            positions: List of positions to search.

        Returns:
            Index of the closest position.
        """
        if not positions:
            return 0

        distances = [abs(value - pos) for pos in positions]
        return distances.index(min(distances))

    def _remove_empty_rows_cols(self, table: list[list[str]]) -> list[list[str]]:
        """Remove completely empty rows and columns.

        Args:
            table: 2D table array.

        Returns:
            Cleaned table with empty rows/columns removed.
        """
        if not table:
            return table

        # Remove empty rows
        table = [row for row in table if any(cell.strip() for cell in row)]

        if not table:
            return []

        # Remove empty columns
        non_empty_cols = [
            col_idx
            for col_idx in range(len(table[0]))
            if any(row[col_idx].strip() for row in table if col_idx < len(row))
        ]

        if not non_empty_cols:
            return []

        return [[row[col_idx] if col_idx < len(row) else "" for col_idx in non_empty_cols] for row in table]

    def to_markdown(self, table: list[list[str]]) -> str:
        """Convert table to markdown format.

        Args:
            table: 2D list representing the table.

        Returns:
            Markdown-formatted table string.
        """
        if not table or not table[0]:
            return ""

        lines = []

        # Header row
        lines.append("| " + " | ".join(str(cell) for cell in table[0]) + " |")

        # Separator row
        lines.append("| " + " | ".join(["---"] * len(table[0])) + " |")

        # Data rows
        for row in table[1:]:
            # Ensure row has same number of columns as header
            padded_row = list(row) + [""] * (len(table[0]) - len(row))
            lines.append("| " + " | ".join(str(cell) for cell in padded_row[: len(table[0])]) + " |")

        return "\n".join(lines)


def extract_table_from_tsv(
    tsv_data: str, column_threshold: int = 20, row_threshold_ratio: float = 0.5, min_confidence: float = 30.0
) -> str:
    """Convenience function to extract table from TSV data.

    Args:
        tsv_data: Raw TSV output from Tesseract.
        column_threshold: Pixel threshold for column clustering.
        row_threshold_ratio: Row threshold as ratio of mean text height.
        min_confidence: Minimum confidence score to include a word.

    Returns:
        Markdown-formatted table string, or empty string if no table detected.
    """
    extractor = TesseractTableExtractor(
        column_threshold=column_threshold, row_threshold_ratio=row_threshold_ratio, min_confidence=min_confidence
    )

    words = extractor.extract_words(tsv_data)
    if not words:
        return ""

    table = extractor.reconstruct_table(words)
    if not table:
        return ""

    return extractor.to_markdown(table)
