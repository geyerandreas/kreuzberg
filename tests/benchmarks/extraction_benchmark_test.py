from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import pytest

from kreuzberg import extract_file_sync
from kreuzberg._types import ExtractionConfig, TesseractConfig
from kreuzberg._utils._cache import clear_all_caches
from tests.benchmarks.files_test import get_benchmark_files

# Skip all benchmark tests unless RUN_BENCHMARKS environment variable is set
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_BENCHMARKS"), reason="Benchmark tests are slow and only run when RUN_BENCHMARKS=1 is set"
)

if TYPE_CHECKING:
    from pathlib import Path

# Always run all files
ALL_TEST_FILES = get_benchmark_files()

# Reduced set of meaningful configurations
BENCHMARK_CONFIGS = {
    "default": ExtractionConfig(use_cache=False),
    "with_ocr": ExtractionConfig(ocr_backend="tesseract", ocr_config=TesseractConfig(), use_cache=False),
    "with_features": ExtractionConfig(
        chunk_content=True,
        auto_detect_language=True,
        extract_keywords=True,
        use_cache=False,
    ),
}


@pytest.fixture(autouse=True)
def setup_benchmark() -> None:
    """Clear caches before each benchmark test."""
    clear_all_caches()


@pytest.mark.benchmark(group="extract_file")
@pytest.mark.parametrize("test_id,file_path", ALL_TEST_FILES, ids=lambda x: x if isinstance(x, str) else None)
def test_extract_file_sync_benchmark(
    test_id: str,
    file_path: Path,
    benchmark: Any,
) -> None:
    """Benchmark file extraction with default configuration."""
    config = ExtractionConfig(use_cache=False)

    # Use pytest-benchmark to measure performance
    result = benchmark(extract_file_sync, str(file_path), config=config)

    # Basic validation
    assert result is not None
    assert result.content is not None
    assert len(result.content) > 0


@pytest.mark.benchmark(group="extract_configs")
@pytest.mark.parametrize(
    "config_name,config", BENCHMARK_CONFIGS.items(), ids=lambda x: x if isinstance(x, str) else None
)
@pytest.mark.parametrize(
    "test_id,file_path", ALL_TEST_FILES[:5], ids=lambda x: x if isinstance(x, str) else None
)  # Sample 5 files for config testing
def test_extract_with_configs_benchmark(
    test_id: str,
    file_path: Path,
    config_name: str,
    config: ExtractionConfig,
    benchmark: Any,
) -> None:
    """Benchmark extraction with different configurations."""
    # Skip OCR test for non-image files
    if config_name == "with_ocr" and file_path.suffix.lower() not in [".png", ".jpg", ".jpeg", ".pdf"]:
        pytest.skip("OCR test only for image/PDF files")

    # Skip feature extraction for very small files
    if config_name == "with_features" and file_path.stat().st_size < 1024:
        pytest.skip("Feature extraction needs sufficient text")

    result = benchmark(extract_file_sync, str(file_path), config=config)

    assert result is not None
    assert result.content is not None
