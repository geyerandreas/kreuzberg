"""Pure synchronous EasyOCR without any async overhead."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from kreuzberg._mime_types import PLAIN_TEXT_MIME_TYPE
from kreuzberg._ocr._easyocr import EasyOCRConfig
from kreuzberg._types import ExtractionResult
from kreuzberg._utils._string import normalize_spaces
from kreuzberg.exceptions import MissingDependencyError, OCRError


def _get_easyocr_instance(config: EasyOCRConfig) -> Any:
    """Get an EasyOCR Reader instance with the given configuration."""
    try:
        import easyocr
    except ImportError as e:
        raise MissingDependencyError("EasyOCR is not installed. Install it with: pip install easyocr") from e

    gpu = False
    if hasattr(config, "device"):
        if config.device and config.device.lower() != "cpu":
            gpu = True
    elif hasattr(config, "use_gpu"):
        gpu = config.use_gpu

    language = config.language if hasattr(config, "language") else "en"
    if isinstance(language, str):
        lang_list = [lang.strip().lower() for lang in language.split(",")]
    else:
        lang_list = [lang.lower() for lang in language]

    kwargs = {
        "lang_list": lang_list,
        "gpu": gpu,
        "model_storage_directory": getattr(config, "model_storage_directory", None),
        "user_network_directory": getattr(config, "user_network_directory", None),
        "recog_network": getattr(config, "recog_network", None),
        "detector": getattr(config, "detector", None),
        "recognizer": getattr(config, "recognizer", None),
        "verbose": False,
        "quantize": getattr(config, "quantize", None),
        "cudnn_benchmark": getattr(config, "cudnn_benchmark", None),
    }

    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    return easyocr.Reader(**kwargs)


def process_image_sync_pure(
    image_path: str | Path,
    config: EasyOCRConfig | None = None,
) -> ExtractionResult:
    """Process an image with EasyOCR using pure sync implementation.

    This bypasses all async overhead and calls EasyOCR directly.

    Args:
        image_path: Path to the image file.
        config: EasyOCR configuration.

    Returns:
        Extraction result.
    """
    cfg = config or EasyOCRConfig()

    try:
        reader = _get_easyocr_instance(cfg)

        readtext_kwargs = {
            "decoder": cfg.decoder,
            "beamWidth": cfg.beam_width,
            "batch_size": getattr(cfg, "batch_size", 1),
            "workers": getattr(cfg, "workers", 0),
            "allowlist": getattr(cfg, "allowlist", None),
            "blocklist": getattr(cfg, "blocklist", None),
            "detail": getattr(cfg, "detail", 1),
            "rotation_info": cfg.rotation_info,
            "paragraph": getattr(cfg, "paragraph", False),
            "min_size": cfg.min_size,
            "text_threshold": cfg.text_threshold,
            "low_text": cfg.low_text,
            "link_threshold": cfg.link_threshold,
            "canvas_size": cfg.canvas_size,
            "mag_ratio": cfg.mag_ratio,
            "slope_ths": cfg.slope_ths,
            "ycenter_ths": cfg.ycenter_ths,
            "height_ths": cfg.height_ths,
            "width_ths": cfg.width_ths,
            "add_margin": cfg.add_margin,
            "x_ths": cfg.x_ths,
            "y_ths": cfg.y_ths,
        }

        readtext_kwargs = {k: v for k, v in readtext_kwargs.items() if v is not None}

        results = reader.readtext(str(image_path), **readtext_kwargs)

        if not results:
            return ExtractionResult(
                content="",
                mime_type=PLAIN_TEXT_MIME_TYPE,
                metadata={},
                chunks=[],
            )

        texts = []
        confidences = []

        detail_value = getattr(cfg, "detail", 1)
        if detail_value:
            for result in results:
                min_result_length = 2
                max_confidence_index = 2
                if len(result) >= min_result_length:
                    _bbox, text = result[0], result[1]
                    confidence = result[max_confidence_index] if len(result) > max_confidence_index else 1.0
                    texts.append(text)
                    confidences.append(confidence)
        else:
            texts = results
            confidences = [1.0] * len(texts)

        content = "\n".join(texts)
        content = normalize_spaces(content)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        metadata = {"confidence": avg_confidence} if confidences else {}

        return ExtractionResult(
            content=content,
            mime_type=PLAIN_TEXT_MIME_TYPE,
            metadata=metadata,  # type: ignore[arg-type]
            chunks=[],
        )

    except Exception as e:
        raise OCRError(f"EasyOCR processing failed: {e}") from e


def process_image_bytes_sync_pure(
    image_bytes: bytes,
    config: EasyOCRConfig | None = None,
) -> ExtractionResult:
    """Process image bytes with EasyOCR using pure sync implementation.

    Args:
        image_bytes: Image data as bytes.
        config: EasyOCR configuration.

    Returns:
        Extraction result.
    """
    import io

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_image:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.save(tmp_image.name, format="PNG")
        image_path = tmp_image.name

    try:
        return process_image_sync_pure(image_path, config)
    finally:
        image_file = Path(image_path)
        if image_file.exists():
            image_file.unlink()


def process_batch_images_sync_pure(
    image_paths: list[str | Path],
    config: EasyOCRConfig | None = None,
) -> list[ExtractionResult]:
    """Process a batch of images sequentially with pure sync implementation.

    Args:
        image_paths: List of image file paths.
        config: EasyOCR configuration.

    Returns:
        List of extraction results.
    """
    results = []
    for image_path in image_paths:
        result = process_image_sync_pure(image_path, config)
        results.append(result)
    return results


def process_batch_images_threaded(
    image_paths: list[str | Path],
    config: EasyOCRConfig | None = None,
    max_workers: int | None = None,
) -> list[ExtractionResult]:
    """Process a batch of images using threading.

    Args:
        image_paths: List of image file paths.
        config: EasyOCR configuration.
        max_workers: Maximum number of threads.

    Returns:
        List of extraction results in same order as input.
    """
    import multiprocessing as mp
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if max_workers is None:
        max_workers = min(len(image_paths), mp.cpu_count())

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(process_image_sync_pure, path, config): i for i, path in enumerate(image_paths)
        }

        results: list[ExtractionResult] = [None] * len(image_paths)  # type: ignore[list-item]
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as e:  # noqa: BLE001
                results[index] = ExtractionResult(
                    content=f"Error: {e}",
                    mime_type=PLAIN_TEXT_MIME_TYPE,
                    metadata={"error": str(e)},  # type: ignore[typeddict-unknown-key]
                    chunks=[],
                )

    return results
