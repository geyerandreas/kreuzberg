from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PIL import Image

from kreuzberg import extract_file
from kreuzberg._types import ExtractionConfig

if TYPE_CHECKING:
    from pathlib import Path


class TestDPIIntegration:
    """Integration tests for DPI configuration across the full extraction pipeline."""

    @pytest.fixture
    def large_test_image(self, tmp_path: Path) -> Path:
        """Create a large test image that would trigger DPI adjustments."""
        # Create a large image (simulating a high-resolution scan)
        image = Image.new("RGB", (5000, 7000), "white")

        # Add some simple text-like patterns
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(image)

        # Try to use a default font, fall back to basic drawing if not available
        try:
            # This might not work in all environments
            font = ImageFont.load_default()
        except OSError:
            font = None

        # Add some text patterns that OCR can recognize
        if font:
            for i in range(20):
                y_pos = 100 + (i * 300)
                draw.text((100, y_pos), f"Test text line {i + 1} with some content", fill="black", font=font)
        else:
            # Fallback: draw simple rectangles as text placeholders
            for i in range(20):
                y_pos = 100 + (i * 300)
                draw.rectangle([100, y_pos, 2000, y_pos + 50], fill="black")
                draw.rectangle([110, y_pos + 10, 1990, y_pos + 40], fill="white")

        # Set high DPI to make it a large image
        image.info["dpi"] = (300, 300)

        image_path = tmp_path / "large_test_image.png"
        image.save(str(image_path), format="PNG", dpi=(300, 300))
        return image_path

    @pytest.fixture
    def small_test_image(self, tmp_path: Path) -> Path:
        """Create a small test image that shouldn't trigger DPI adjustments."""
        image = Image.new("RGB", (400, 600), "white")

        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.load_default()
        except OSError:
            font = None

        if font:
            draw.text((50, 50), "Small test image", fill="black", font=font)
            draw.text((50, 100), "With some text", fill="black", font=font)
        else:
            draw.rectangle([50, 50, 350, 80], fill="black")
            draw.rectangle([60, 60, 340, 70], fill="white")

        image.info["dpi"] = (72, 72)

        image_path = tmp_path / "small_test_image.png"
        image.save(str(image_path), format="PNG", dpi=(72, 72))
        return image_path

    @pytest.mark.anyio
    async def test_large_image_dpi_adjustment(self, large_test_image: Path) -> None:
        """Test that large images get automatically adjusted to prevent OCR errors."""
        # Configure with restrictive max_image_dimension
        config = ExtractionConfig(
            ocr_backend="tesseract",
            target_dpi=300,  # High DPI that would normally create huge images
            max_image_dimension=10000,  # Restrictive limit
            auto_adjust_dpi=True,
            min_dpi=72,
            max_dpi=600,
        )

        # This should succeed without "Image too large" errors
        result = await extract_file(str(large_test_image), config=config)

        assert result is not None
        assert result.content is not None
        assert len(result.content.strip()) > 0

        # Check that preprocessing metadata was added
        assert "image_preprocessing" in result.metadata
        preprocessing = result.metadata["image_preprocessing"]

        # Should have been auto-adjusted due to size constraints
        assert preprocessing.auto_adjusted or preprocessing.scale_factor != 1.0

    @pytest.mark.anyio
    async def test_small_image_no_adjustment(self, small_test_image: Path) -> None:
        """Test that small images don't get unnecessarily adjusted."""
        config = ExtractionConfig(
            ocr_backend="tesseract",
            target_dpi=150,
            max_image_dimension=25000,
            auto_adjust_dpi=True,
        )

        result = await extract_file(str(small_test_image), config=config)

        assert result is not None
        assert result.content is not None

        # Check preprocessing metadata
        if "image_preprocessing" in result.metadata:
            preprocessing = result.metadata["image_preprocessing"]
            # Should not have been significantly adjusted
            scale_factor = preprocessing.scale_factor
            assert 0.3 <= scale_factor <= 3.0  # More lenient range for test images

    @pytest.mark.anyio
    async def test_dpi_disabled_auto_adjust(self, large_test_image: Path) -> None:
        """Test behavior when auto_adjust_dpi is disabled."""
        config = ExtractionConfig(
            ocr_backend="tesseract",
            target_dpi=72,  # Low DPI
            max_image_dimension=25000,
            auto_adjust_dpi=False,  # Disabled
        )

        result = await extract_file(str(large_test_image), config=config)

        assert result is not None
        assert result.content is not None

        # Should still work but might have different preprocessing behavior
        if "image_preprocessing" in result.metadata:
            preprocessing = result.metadata["image_preprocessing"]
            assert not preprocessing.auto_adjusted

    @pytest.mark.anyio
    async def test_different_dpi_targets(self, small_test_image: Path) -> None:
        """Test different DPI target values can be configured."""
        low_dpi_config = ExtractionConfig(
            ocr_backend="tesseract",
            target_dpi=72,
            auto_adjust_dpi=False,
        )

        high_dpi_config = ExtractionConfig(
            ocr_backend="tesseract",
            target_dpi=300,
            auto_adjust_dpi=False,
        )

        # Both should complete successfully without errors
        low_result = await extract_file(str(small_test_image), config=low_dpi_config)
        high_result = await extract_file(str(small_test_image), config=high_dpi_config)

        assert low_result is not None
        assert high_result is not None
        assert low_result.content is not None
        assert high_result.content is not None

        # This mainly tests that different DPI configs don't crash
        # The exact metadata depends on the image's original DPI

    @pytest.mark.anyio
    async def test_pdf_dpi_integration(self, google_doc_pdf: Path) -> None:
        """Test DPI configuration works with PDF extraction."""
        # This PDF previously caused "Image too large" errors
        config = ExtractionConfig(
            ocr_backend="tesseract",
            target_dpi=100,  # Moderate DPI
            max_image_dimension=20000,
            auto_adjust_dpi=True,
            force_ocr=True,  # Force OCR to test image processing
        )

        # Should complete without errors
        result = await extract_file(str(google_doc_pdf), config=config)

        assert result is not None
        assert result.content is not None
        assert len(result.content) > 100  # Should have extracted substantial content

        # Should contain typical PDF content
        content_lower = result.content.lower()
        assert any(word in content_lower for word in ["page", "web", "guide", "the", "and"])

    @pytest.mark.anyio
    async def test_extreme_dpi_values(self, small_test_image: Path) -> None:
        """Test extreme DPI values are handled gracefully."""
        # Very low DPI
        very_low_config = ExtractionConfig(
            ocr_backend="tesseract",
            target_dpi=72,
            min_dpi=72,
            max_dpi=100,
            max_image_dimension=5000,  # Small limit
            auto_adjust_dpi=True,
        )

        result = await extract_file(str(small_test_image), config=very_low_config)
        assert result is not None
        assert result.content is not None

    @pytest.mark.anyio
    async def test_metadata_preservation(self, small_test_image: Path) -> None:
        """Test that DPI processing preserves and adds appropriate metadata."""
        config = ExtractionConfig(
            ocr_backend="tesseract",
            target_dpi=144,
            auto_adjust_dpi=True,
        )

        result = await extract_file(str(small_test_image), config=config)

        assert result is not None
        assert result.metadata is not None

        if "image_preprocessing" in result.metadata:
            preprocessing = result.metadata["image_preprocessing"]

            # Should have essential preprocessing info
            assert hasattr(preprocessing, "original_dimensions")
            assert hasattr(preprocessing, "scale_factor")
            assert hasattr(preprocessing, "target_dpi")

            # Dimensions should be tuples
            orig_dims = preprocessing.original_dimensions
            assert isinstance(orig_dims, (list, tuple))
            assert len(orig_dims) == 2
            assert all(isinstance(d, int) and d > 0 for d in orig_dims)
