"""Synchronous OCR implementations for all backends."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

from kreuzberg._mime_types import PLAIN_TEXT_MIME_TYPE
from kreuzberg._ocr._easyocr import EasyOCRConfig
from kreuzberg._ocr._paddleocr import PaddleOCRConfig
from kreuzberg._ocr._tesseract import TesseractConfig
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


def process_image_easyocr_sync(
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


def process_image_bytes_easyocr_sync(
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
        return process_image_easyocr_sync(image_path, config)
    finally:
        image_file = Path(image_path)
        if image_file.exists():
            image_file.unlink()


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


def process_image_paddleocr_sync(
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


def process_image_bytes_paddleocr_sync(
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
        return process_image_paddleocr_sync(image_path, config)
    finally:
        image_file = Path(image_path)
        if image_file.exists():
            image_file.unlink()


def process_image_tesseract_sync(
    image_path: str | Path,
    config: TesseractConfig | None = None,
) -> ExtractionResult:
    """Process an image with Tesseract using pure sync implementation.

    This bypasses all async overhead and calls Tesseract directly.

    Args:
        image_path: Path to the image file.
        config: Tesseract configuration.

    Returns:
        Extraction result.
    """
    import os
    import subprocess

    cfg = config or TesseractConfig()

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
        output_base = tmp_file.name.replace(".txt", "")

    try:
        command = [
            "tesseract",
            str(image_path),
            output_base,
            "-l",
            cfg.language,
            "--psm",
            str(cfg.psm.value if hasattr(cfg.psm, "value") else cfg.psm),
            "--oem",
            "1",
            "--loglevel",
            "OFF",
        ]

        boolean_fields = [
            "classify_use_pre_adapted_templates",
            "language_model_ngram_on",
            "tessedit_dont_blkrej_good_wds",
            "tessedit_dont_rowrej_good_wds",
            "tessedit_enable_dict_correction",
            "tessedit_use_primary_params_model",
            "textord_space_size_is_variable",
            "thresholding_method",
        ]

        for field in boolean_fields:
            if hasattr(cfg, field):
                value = 1 if getattr(cfg, field) else 0
                command.extend(["-c", f"{field}={value}"])

        env = os.environ.copy()
        env["OMP_THREAD_LIMIT"] = "1"

        result = subprocess.run(
            command,
            check=False,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise OCRError(f"Tesseract failed with return code {result.returncode}: {result.stderr}")

        output_file = output_base + ".txt"
        with Path(output_file).open(encoding="utf-8") as f:
            text = f.read()

        text = normalize_spaces(text)

        return ExtractionResult(
            content=text,
            mime_type=PLAIN_TEXT_MIME_TYPE,
            metadata={},
            chunks=[],
        )

    finally:
        for ext in [".txt"]:
            temp_file = output_base + ext
            temp_path = Path(temp_file)
            if temp_path.exists():
                temp_path.unlink()


def process_image_bytes_tesseract_sync(
    image_bytes: bytes,
    config: TesseractConfig | None = None,
) -> ExtractionResult:
    """Process image bytes with Tesseract using pure sync implementation.

    Args:
        image_bytes: Image data as bytes.
        config: Tesseract configuration.

    Returns:
        Extraction result.
    """
    import io

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_image:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.save(tmp_image.name, format="PNG")
        image_path = tmp_image.name

    try:
        return process_image_tesseract_sync(image_path, config)
    finally:
        image_file = Path(image_path)
        if image_file.exists():
            image_file.unlink()


def process_batch_images_sync(
    image_paths: list[str | Path],
    config: EasyOCRConfig | PaddleOCRConfig | TesseractConfig | None = None,
    backend: str = "tesseract",
) -> list[ExtractionResult]:
    """Process a batch of images sequentially with pure sync implementation.

    Args:
        image_paths: List of image file paths.
        config: OCR configuration.
        backend: OCR backend to use.

    Returns:
        List of extraction results.
    """
    results = []
    for image_path in image_paths:
        if backend == "easyocr":
            result = process_image_easyocr_sync(image_path, config)  # type: ignore[arg-type]
        elif backend == "paddleocr":
            result = process_image_paddleocr_sync(image_path, config)  # type: ignore[arg-type]
        else:
            result = process_image_tesseract_sync(image_path, config)  # type: ignore[arg-type]
        results.append(result)
    return results


def process_batch_images_threaded(
    image_paths: list[str | Path],
    config: EasyOCRConfig | PaddleOCRConfig | TesseractConfig | None = None,
    backend: str = "tesseract",
    max_workers: int | None = None,
) -> list[ExtractionResult]:
    """Process a batch of images using threading.

    Args:
        image_paths: List of image file paths.
        config: OCR configuration.
        backend: OCR backend to use.
        max_workers: Maximum number of threads.

    Returns:
        List of extraction results in same order as input.
    """
    import multiprocessing as mp
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if max_workers is None:
        max_workers = min(len(image_paths), mp.cpu_count())

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        if backend == "easyocr":
            future_to_index = {
                executor.submit(process_image_easyocr_sync, path, config): i  # type: ignore[arg-type]
                for i, path in enumerate(image_paths)
            }
        elif backend == "paddleocr":
            future_to_index = {
                executor.submit(process_image_paddleocr_sync, path, config): i  # type: ignore[arg-type]
                for i, path in enumerate(image_paths)
            }
        else:
            future_to_index = {
                executor.submit(process_image_tesseract_sync, path, config): i  # type: ignore[arg-type]
                for i, path in enumerate(image_paths)
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


def process_batch_images_process_pool(
    image_paths: list[str | Path],
    config: TesseractConfig | None = None,
    max_workers: int | None = None,
) -> list[ExtractionResult]:
    """Process a batch of images using process pool.

    Args:
        image_paths: List of image file paths.
        config: Tesseract configuration.
        max_workers: Maximum number of processes.

    Returns:
        List of extraction results in same order as input.
    """
    import multiprocessing as mp
    from concurrent.futures import ProcessPoolExecutor, as_completed

    if max_workers is None:
        max_workers = min(len(image_paths), mp.cpu_count())

    cfg = config or TesseractConfig()
    config_dict = {}
    for field_name in cfg.__dataclass_fields__:
        value = getattr(cfg, field_name)
        if hasattr(value, "value"):
            config_dict[field_name] = value.value
        else:
            config_dict[field_name] = value

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        from kreuzberg._ocr._pool import _process_image_with_tesseract

        future_to_index = {
            executor.submit(_process_image_with_tesseract, str(path), config_dict): i
            for i, path in enumerate(image_paths)
        }

        results: list[ExtractionResult] = [None] * len(image_paths)  # type: ignore[list-item]
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result_dict = future.result()
                if result_dict["success"]:
                    results[index] = ExtractionResult(
                        content=result_dict["text"],
                        mime_type=PLAIN_TEXT_MIME_TYPE,
                        metadata={},
                        chunks=[],
                    )
                else:
                    results[index] = ExtractionResult(
                        content=f"Error: {result_dict['error']}",
                        mime_type=PLAIN_TEXT_MIME_TYPE,
                        metadata={"error": result_dict["error"]},  # type: ignore[typeddict-unknown-key]
                        chunks=[],
                    )
            except Exception as e:  # noqa: BLE001
                results[index] = ExtractionResult(
                    content=f"Error: {e}",
                    mime_type=PLAIN_TEXT_MIME_TYPE,
                    metadata={"error": str(e)},  # type: ignore[typeddict-unknown-key]
                    chunks=[],
                )

    return results
