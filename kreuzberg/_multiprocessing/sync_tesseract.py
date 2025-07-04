"""Pure synchronous Tesseract OCR without any async overhead."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from kreuzberg._mime_types import PLAIN_TEXT_MIME_TYPE
from kreuzberg._ocr._tesseract import TesseractConfig
from kreuzberg._types import ExtractionResult
from kreuzberg._utils._string import normalize_spaces
from kreuzberg.exceptions import OCRError


def process_image_sync_pure(
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


def process_image_bytes_sync_pure(
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
        return process_image_sync_pure(image_path, config)
    finally:
        image_file = Path(image_path)
        if image_file.exists():
            image_file.unlink()


def process_batch_images_sync_pure(
    image_paths: list[str | Path],
    config: TesseractConfig | None = None,
) -> list[ExtractionResult]:
    """Process a batch of images sequentially with pure sync implementation.

    Args:
        image_paths: List of image file paths.
        config: Tesseract configuration.

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
    config: TesseractConfig | None = None,
    max_workers: int | None = None,
) -> list[ExtractionResult]:
    """Process a batch of images using threading.

    Args:
        image_paths: List of image file paths.
        config: Tesseract configuration.
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
            except Exception as e:  # noqa: BLE001  # noqa: BLE001
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
        from kreuzberg._multiprocessing.tesseract_pool import _process_image_with_tesseract

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
