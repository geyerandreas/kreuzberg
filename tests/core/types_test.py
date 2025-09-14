from __future__ import annotations

from kreuzberg import ExtractionConfig
from kreuzberg._types import ExtractedImage


def test_extracted_image_hashable() -> None:
    img = ExtractedImage(data=b"abc", format="png", filename="x.png", page_number=1)
    _ = hash(img)
    s = {img}
    assert len(s) == 1


def test_extraction_config_image_ocr_defaults() -> None:
    cfg = ExtractionConfig()
    assert cfg.extract_images is False
    assert cfg.ocr_extracted_images is False
    assert isinstance(cfg.image_ocr_min_dimensions, tuple)
    assert len(cfg.image_ocr_min_dimensions) == 2
    assert isinstance(cfg.image_ocr_max_dimensions, tuple)
    assert len(cfg.image_ocr_max_dimensions) == 2
    assert isinstance(cfg.image_ocr_formats, frozenset)
    assert "png" in cfg.image_ocr_formats
