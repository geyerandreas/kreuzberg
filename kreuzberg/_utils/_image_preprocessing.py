from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PIL import Image

from kreuzberg._types import ExtractionConfig, ImagePreprocessingMetadata

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


def calculate_optimal_dpi(
    page_width: float,
    page_height: float,
    target_dpi: int,
    max_dimension: int,
    min_dpi: int = 72,
    max_dpi: int = 600,
) -> int:
    """Calculate optimal DPI based on page dimensions and constraints.

    Args:
        page_width: Page width in points (1/72 inch)
        page_height: Page height in points (1/72 inch)
        target_dpi: Desired target DPI
        max_dimension: Maximum allowed pixel dimension
        min_dpi: Minimum DPI threshold
        max_dpi: Maximum DPI threshold

    Returns:
        Optimal DPI value that keeps image within max_dimension
    """
    # Convert points to inches (72 points = 1 inch)
    width_inches = page_width / 72.0
    height_inches = page_height / 72.0

    # Calculate pixel dimensions at target DPI
    target_width_pixels = int(width_inches * target_dpi)
    target_height_pixels = int(height_inches * target_dpi)

    # Check if target DPI results in oversized image
    max_pixel_dimension = max(target_width_pixels, target_height_pixels)

    if max_pixel_dimension <= max_dimension:
        # Target DPI is fine, clamp to min/max bounds
        return max(min_dpi, min(target_dpi, max_dpi))

    # Calculate maximum DPI that keeps within dimension constraints
    max_dpi_for_width = max_dimension / width_inches if width_inches > 0 else max_dpi
    max_dpi_for_height = max_dimension / height_inches if height_inches > 0 else max_dpi
    constrained_dpi = int(min(max_dpi_for_width, max_dpi_for_height))

    # Clamp to min/max bounds
    return max(min_dpi, min(constrained_dpi, max_dpi))


def _extract_image_dpi(image: PILImage) -> tuple[tuple[float, float], float]:
    """Extract DPI information from image."""
    current_dpi_info = image.info.get("dpi", (72.0, 72.0))
    if isinstance(current_dpi_info, (list, tuple)):
        original_dpi = (float(current_dpi_info[0]), float(current_dpi_info[1]))
        current_dpi = float(current_dpi_info[0])  # Use horizontal DPI
    else:
        current_dpi = float(current_dpi_info)
        original_dpi = (current_dpi, current_dpi)
    return original_dpi, current_dpi


def _should_skip_processing(
    original_width: int,
    original_height: int,
    current_dpi: float,
    config: ExtractionConfig,
) -> bool:
    """Check if processing should be skipped."""
    max_current_dimension = max(original_width, original_height)
    current_matches_target = abs(current_dpi - config.target_dpi) < 1.0
    return not config.auto_adjust_dpi and current_matches_target and max_current_dimension <= config.max_image_dimension


def _calculate_target_dpi(
    original_width: int,
    original_height: int,
    current_dpi: float,
    config: ExtractionConfig,
) -> tuple[int, bool, int | None]:
    """Calculate target DPI and whether it was auto-adjusted."""
    calculated_dpi = None
    if config.auto_adjust_dpi:
        # Convert pixel dimensions to approximate point dimensions
        # This is an approximation since we don't know the actual physical size
        approx_width_points = original_width * 72.0 / current_dpi
        approx_height_points = original_height * 72.0 / current_dpi

        optimal_dpi = calculate_optimal_dpi(
            approx_width_points,
            approx_height_points,
            config.target_dpi,
            config.max_image_dimension,
            config.min_dpi,
            config.max_dpi,
        )
        calculated_dpi = optimal_dpi
        auto_adjusted = optimal_dpi != config.target_dpi
        target_dpi = optimal_dpi
    else:
        auto_adjusted = False
        target_dpi = config.target_dpi

    return target_dpi, auto_adjusted, calculated_dpi


def normalize_image_dpi(
    image: PILImage,
    config: ExtractionConfig,
) -> tuple[PILImage, ImagePreprocessingMetadata]:
    """Normalize image DPI and dimensions for optimal OCR processing.

    Args:
        image: PIL Image to normalize
        config: ExtractionConfig containing DPI settings

    Returns:
        Tuple of (normalized_image, ImagePreprocessingMetadata)

    Note:
        If auto_adjust_dpi is False, uses target_dpi directly.
        If True, calculates optimal DPI based on image dimensions and constraints.
    """
    original_width, original_height = image.size
    original_dpi, current_dpi = _extract_image_dpi(image)

    # If no auto-adjustment and current DPI matches target and within limits, skip processing
    if _should_skip_processing(original_width, original_height, current_dpi, config):
        return image, ImagePreprocessingMetadata(
            original_dimensions=(original_width, original_height),
            original_dpi=original_dpi,
            target_dpi=config.target_dpi,
            scale_factor=1.0,
            auto_adjusted=False,
            final_dpi=config.target_dpi,
            skipped_resize=True,
        )

    # Calculate target DPI
    target_dpi, auto_adjusted, calculated_dpi = _calculate_target_dpi(
        original_width, original_height, current_dpi, config
    )

    # Calculate scale factor based on DPI ratio
    scale_factor = target_dpi / current_dpi

    # If scale factor is very close to 1.0, skip resizing
    if abs(scale_factor - 1.0) < 0.05:
        return image, ImagePreprocessingMetadata(
            original_dimensions=(original_width, original_height),
            original_dpi=original_dpi,
            target_dpi=config.target_dpi,
            scale_factor=scale_factor,
            auto_adjusted=auto_adjusted,
            final_dpi=target_dpi,
            calculated_dpi=calculated_dpi,
            skipped_resize=True,
        )

    # Calculate new dimensions
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)

    # Ensure we don't exceed max_dimension (safety check)
    dimension_clamped = False
    max_new_dimension = max(new_width, new_height)
    if max_new_dimension > config.max_image_dimension:
        dimension_scale = config.max_image_dimension / max_new_dimension
        new_width = int(new_width * dimension_scale)
        new_height = int(new_height * dimension_scale)
        scale_factor *= dimension_scale
        dimension_clamped = True

    # Resize image
    try:
        # Use LANCZOS for high-quality downscaling, BICUBIC for upscaling
        # Handle different PIL versions
        try:
            # Modern PIL version
            if scale_factor < 1.0:
                resample_method = Image.Resampling.LANCZOS
                resample_name = "LANCZOS"
            else:
                resample_method = Image.Resampling.BICUBIC
                resample_name = "BICUBIC"
        except AttributeError:
            # Older PIL version
            if scale_factor < 1.0:
                resample_method = getattr(Image, "LANCZOS", 1)  # type: ignore[arg-type]
                resample_name = "LANCZOS"
            else:
                resample_method = getattr(Image, "BICUBIC", 3)  # type: ignore[arg-type]
                resample_name = "BICUBIC"

        normalized_image = image.resize((new_width, new_height), resample_method)

        # Update DPI info in the new image
        normalized_image.info["dpi"] = (target_dpi, target_dpi)

        return normalized_image, ImagePreprocessingMetadata(
            original_dimensions=(original_width, original_height),
            original_dpi=original_dpi,
            target_dpi=config.target_dpi,
            scale_factor=scale_factor,
            auto_adjusted=auto_adjusted,
            final_dpi=target_dpi,
            new_dimensions=(new_width, new_height),
            resample_method=resample_name,
            dimension_clamped=dimension_clamped,
            calculated_dpi=calculated_dpi,
        )

    except OSError as e:
        # If resizing fails, return original image with error info
        return image, ImagePreprocessingMetadata(
            original_dimensions=(original_width, original_height),
            original_dpi=original_dpi,
            target_dpi=config.target_dpi,
            scale_factor=scale_factor,
            auto_adjusted=auto_adjusted,
            final_dpi=target_dpi,
            calculated_dpi=calculated_dpi,
            resize_error=str(e),
        )


def get_dpi_adjustment_heuristics(
    width: float,
    height: float,
    current_dpi: int,
    target_dpi: int,
    max_dimension: int,
    content_type: str = "document",
) -> dict[str, Any]:
    """Get smart DPI adjustment recommendations based on content analysis.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        current_dpi: Current DPI setting
        target_dpi: Desired target DPI
        max_dimension: Maximum allowed dimension
        content_type: Type of content ("document", "photo", "mixed")

    Returns:
        Dictionary with adjustment recommendations and rationale
    """
    recommendations: list[str] = []
    heuristics = {
        "recommended_dpi": target_dpi,
        "content_analysis": {},
        "performance_impact": "medium",
        "quality_impact": "medium",
        "recommendations": recommendations,
    }

    # Calculate aspect ratio and size analysis
    aspect_ratio = width / height if height > 0 else 1.0
    total_pixels = width * height
    megapixels = total_pixels / 1_000_000

    heuristics["content_analysis"] = {
        "aspect_ratio": aspect_ratio,
        "megapixels": megapixels,
        "is_portrait": aspect_ratio < 0.8,
        "is_landscape": aspect_ratio > 1.2,
        "is_large": max(width, height) > max_dimension * 0.8,
    }

    # Document-specific heuristics
    if content_type == "document":
        if aspect_ratio > 2.0 or aspect_ratio < 0.5:
            # Very wide or very tall documents (like forms, receipts)
            recommendations.append("Consider higher DPI for narrow documents")
            if target_dpi < 200:
                heuristics["recommended_dpi"] = min(200, target_dpi * 1.3)

        if megapixels > 50:  # Very large document
            recommendations.append("Large document detected - consider DPI reduction")
            heuristics["performance_impact"] = "high"
            if target_dpi > 150:
                heuristics["recommended_dpi"] = max(120, target_dpi * 0.8)

    # Memory usage estimation
    estimated_memory_mb = (width * height * 3) / (1024 * 1024)  # RGB bytes
    if estimated_memory_mb > 200:
        heuristics["performance_impact"] = "high"
        recommendations.append(f"High memory usage expected (~{estimated_memory_mb:.0f}MB)")

    # Quality vs performance tradeoffs
    scale_factor = target_dpi / current_dpi if current_dpi > 0 else 1.0
    if scale_factor < 0.7:
        heuristics["quality_impact"] = "high"
        recommendations.append("Significant downscaling may reduce OCR accuracy")
    elif scale_factor > 1.5:
        heuristics["performance_impact"] = "high"
        recommendations.append("Upscaling will increase processing time")

    return heuristics


def estimate_processing_time(
    width: int,
    height: int,
    ocr_backend: str = "tesseract",
) -> dict[str, float | str]:
    """Estimate processing time based on image dimensions and OCR backend.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        ocr_backend: OCR backend name

    Returns:
        Dictionary with time estimates in seconds
    """
    total_pixels = width * height
    megapixels = total_pixels / 1_000_000

    # Base processing times per megapixel (rough estimates)
    base_times = {
        "tesseract": 2.5,  # seconds per megapixel
        "easyocr": 4.0,  # slower due to deep learning
        "paddleocr": 3.5,  # moderate speed
    }

    base_time = base_times.get(ocr_backend, 3.0)

    # Non-linear scaling for very large images
    scaling_factor = 1.0 + (megapixels - 10) * 0.1 if megapixels > 10 else 1.0

    estimated_time = base_time * megapixels * scaling_factor

    return {
        "estimated_seconds": estimated_time,
        "megapixels": megapixels,
        "backend": ocr_backend,
        "scaling_factor": scaling_factor,
    }
