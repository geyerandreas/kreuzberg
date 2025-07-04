"""Pure synchronous PaddleOCR without any async overhead."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from kreuzberg._mime_types import PLAIN_TEXT_MIME_TYPE
from kreuzberg._ocr._paddleocr import PaddleOCRConfig
from kreuzberg._types import ExtractionResult
from kreuzberg._utils._string import normalize_spaces
from kreuzberg.exceptions import MissingDependencyError, OCRError


def _get_paddleocr_instance(config: PaddleOCRConfig) -> Any:
    """Get a PaddleOCR instance with the given configuration."""
    try:
        import paddleocr
    except ImportError as e:
        raise MissingDependencyError("PaddleOCR is not installed. Install it with: pip install paddleocr") from e

    if hasattr(config, "device"):
        if config.device and config.device.lower() != "cpu":
            pass
    elif hasattr(config, "use_gpu"):
        pass

    kwargs = {
        "lang": config.language,
        "use_textline_orientation": config.use_angle_cls,
    }

    if hasattr(config, "det_db_thresh"):
        kwargs["text_det_thresh"] = config.det_db_thresh
    if hasattr(config, "det_db_box_thresh"):
        kwargs["text_det_box_thresh"] = config.det_db_box_thresh
    if hasattr(config, "det_db_unclip_ratio"):
        kwargs["text_det_unclip_ratio"] = config.det_db_unclip_ratio
    if hasattr(config, "det_max_side_len"):
        kwargs["text_det_limit_side_len"] = config.det_max_side_len
    if hasattr(config, "drop_score"):
        kwargs["text_rec_score_thresh"] = config.drop_score

    return paddleocr.PaddleOCR(**kwargs)


def process_image_sync_pure(
    image_path: str | Path,
    config: PaddleOCRConfig | None = None,
) -> ExtractionResult:
    """Process an image with PaddleOCR using pure sync implementation.

    This bypasses all async overhead and calls PaddleOCR directly.

    Args:
        image_path: Path to the image file.
        config: PaddleOCR configuration.

    Returns:
        Extraction result.
    """
    cfg = config or PaddleOCRConfig()

    try:
        ocr_instance = _get_paddleocr_instance(cfg)

        results = ocr_instance.ocr(str(image_path))

        if not results or not results[0]:
            return ExtractionResult(
                content="",
                mime_type=PLAIN_TEXT_MIME_TYPE,
                metadata={},
                chunks=[],
            )

        ocr_result = results[0]
        result_data = ocr_result.json["res"]

        texts = result_data.get("rec_texts", [])
        scores = result_data.get("rec_scores", [])

        if not texts:
            return ExtractionResult(
                content="",
                mime_type=PLAIN_TEXT_MIME_TYPE,
                metadata={},
                chunks=[],
            )

        content = "\n".join(texts)
        content = normalize_spaces(content)

        avg_confidence = sum(scores) / len(scores) if scores else 0.0

        metadata = {"confidence": avg_confidence} if scores else {}

        return ExtractionResult(
            content=content,
            mime_type=PLAIN_TEXT_MIME_TYPE,
            metadata=metadata,  # type: ignore[arg-type]
            chunks=[],
        )

    except Exception as e:
        raise OCRError(f"PaddleOCR processing failed: {e}") from e


def process_image_bytes_sync_pure(
    image_bytes: bytes,
    config: PaddleOCRConfig | None = None,
) -> ExtractionResult:
    """Process image bytes with PaddleOCR using pure sync implementation.

    Args:
        image_bytes: Image data as bytes.
        config: PaddleOCR configuration.

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
    config: PaddleOCRConfig | None = None,
) -> list[ExtractionResult]:
    """Process a batch of images sequentially with pure sync implementation.

    Args:
        image_paths: List of image file paths.
        config: PaddleOCR configuration.

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
    config: PaddleOCRConfig | None = None,
    max_workers: int | None = None,
) -> list[ExtractionResult]:
    """Process a batch of images using threading.

    Args:
        image_paths: List of image file paths.
        config: PaddleOCR configuration.
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
