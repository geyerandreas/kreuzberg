from __future__ import annotations

from kreuzberg import ExtractionConfig


def test_extract_images_config_default() -> None:
    cfg = ExtractionConfig()
    assert cfg.extract_images is False
    assert cfg.ocr_extracted_images is False


def test_extract_images_config_enabled() -> None:
    cfg = ExtractionConfig(extract_images=True, ocr_extracted_images=True)
    assert cfg.extract_images is True
    assert cfg.ocr_extracted_images is True
