"""Tesseract process pool for parallel OCR processing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image
from typing_extensions import Self

from kreuzberg._ocr._tesseract import TesseractConfig
from kreuzberg._types import ExtractionResult

from .process_manager import ProcessPoolManager


def _process_image_with_tesseract(
    image_path: str,
    config_dict: dict[str, Any],
) -> dict[str, Any]:
    """Process a single image with Tesseract in a separate process.

    This function is designed to be pickled and executed in a subprocess.
    It uses direct tesseract command execution to avoid async complications.

    Args:
        image_path: Path to the image file.
        config_dict: Tesseract configuration as dictionary.

    Returns:
        OCR result as dictionary.
    """
    try:
        import os
        import subprocess
        import tempfile

        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            output_base = tmp_file.name.replace(".txt", "")

        try:
            # Build tesseract command
            language = config_dict.get("language", "eng")
            psm = config_dict.get("psm", 3)  # Default to AUTO

            command = [
                "tesseract",
                image_path,
                output_base,
                "-l",
                language,
                "--psm",
                str(psm),
                "--oem",
                "1",
                "--loglevel",
                "OFF",
            ]

            # Add boolean config options
            boolean_options = [
                "classify_use_pre_adapted_templates",
                "language_model_ngram_on",
                "tessedit_dont_blkrej_good_wds",
                "tessedit_dont_rowrej_good_wds",
                "tessedit_enable_dict_correction",
                "tessedit_use_primary_params_model",
                "textord_space_size_is_variable",
                "thresholding_method",
            ]

            for option in boolean_options:
                if option in config_dict:
                    value = 1 if config_dict[option] else 0
                    command.extend(["-c", f"{option}={value}"])

            # Set environment to prevent multithreading deadlocks
            env = os.environ.copy()
            env["OMP_THREAD_LIMIT"] = "1"

            # Run tesseract
            result = subprocess.run(
                command,
                check=False,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
            )

            if result.returncode != 0:
                raise Exception(f"Tesseract failed with return code {result.returncode}: {result.stderr}")

            # Read output
            output_file = output_base + ".txt"
            with open(output_file, encoding="utf-8") as f:
                text = f.read()

            # Normalize text
            from kreuzberg._utils._string import normalize_spaces

            text = normalize_spaces(text)

            return {
                "success": True,
                "text": text,
                "confidence": None,
                "error": None,
            }

        finally:
            # Clean up temporary files
            for ext in [".txt"]:
                temp_file = output_base + ext
                if os.path.exists(temp_file):
                    Path(temp_file).unlink()

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "confidence": None,
            "error": str(e),
        }


def _process_image_bytes_with_tesseract(
    image_bytes: bytes,
    config_dict: dict[str, Any],
) -> dict[str, Any]:
    """Process image bytes with Tesseract in a separate process.

    Args:
        image_bytes: Image data as bytes.
        config_dict: Tesseract configuration as dictionary.

    Returns:
        OCR result as dictionary.
    """
    try:
        import io
        import os
        import tempfile

        # Save image bytes to temporary file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_image:
            # Load image and save as PNG
            with Image.open(io.BytesIO(image_bytes)) as image:
                image.save(tmp_image.name, format="PNG")
            image_path = tmp_image.name

        try:
            # Use the file processing function
            return _process_image_with_tesseract(image_path, config_dict)
        finally:
            # Clean up temporary image file
            if os.path.exists(image_path):
                Path(image_path).unlink()

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "confidence": None,
            "error": str(e),
        }


class TesseractProcessPool:
    """Process pool for parallel Tesseract OCR processing."""

    def __init__(
        self,
        config: TesseractConfig | None = None,
        max_processes: int | None = None,
        memory_limit_gb: float | None = None,
    ) -> None:
        """Initialize the Tesseract process pool.

        Args:
            config: Default Tesseract configuration.
            max_processes: Maximum number of processes.
            memory_limit_gb: Memory limit in GB.
        """
        self.config = config or TesseractConfig()
        self.process_manager = ProcessPoolManager(
            max_processes=max_processes,
            memory_limit_gb=memory_limit_gb,
        )

    def _config_to_dict(self, config: TesseractConfig | None = None) -> dict[str, Any]:
        """Convert TesseractConfig to dictionary for pickling."""
        cfg = config or self.config

        # Convert all TesseractConfig fields to a dictionary
        config_dict = {}
        for field_name in cfg.__dataclass_fields__:
            value = getattr(cfg, field_name)
            # Handle enum values
            if hasattr(value, "value"):
                config_dict[field_name] = value.value
            else:
                config_dict[field_name] = value

        return config_dict

    def _result_from_dict(self, result_dict: dict[str, Any]) -> ExtractionResult:
        """Convert result dictionary back to OCRResult."""
        if not result_dict["success"]:
            from kreuzberg.exceptions import OCRError

            raise OCRError(f"Tesseract processing failed: {result_dict['error']}")

        from kreuzberg._mime_types import PLAIN_TEXT_MIME_TYPE

        return ExtractionResult(
            content=result_dict["text"],
            mime_type=PLAIN_TEXT_MIME_TYPE,
            metadata={"confidence": result_dict["confidence"]} if result_dict["confidence"] else {},
            chunks=[],
        )

    async def process_image(
        self,
        image_path: str | Path,
        config: TesseractConfig | None = None,
    ) -> ExtractionResult:
        """Process a single image file with Tesseract.

        Args:
            image_path: Path to the image file.
            config: Tesseract configuration (uses default if None).

        Returns:
            OCR result.
        """
        config_dict = self._config_to_dict(config)

        # Estimate memory usage (typical Tesseract process uses ~50-100MB)
        task_memory_mb = 80

        result_dict = await self.process_manager.submit_task(
            _process_image_with_tesseract,
            str(image_path),
            config_dict,
            task_memory_mb=task_memory_mb,
        )

        return self._result_from_dict(result_dict)

    async def process_image_bytes(
        self,
        image_bytes: bytes,
        config: TesseractConfig | None = None,
    ) -> ExtractionResult:
        """Process image bytes with Tesseract.

        Args:
            image_bytes: Image data as bytes.
            config: Tesseract configuration (uses default if None).

        Returns:
            OCR result.
        """
        config_dict = self._config_to_dict(config)

        # Estimate memory usage based on image size
        image_size_mb = len(image_bytes) / 1024 / 1024
        task_memory_mb = max(80, image_size_mb * 2 + 50)  # Tesseract + image processing

        result_dict = await self.process_manager.submit_task(
            _process_image_bytes_with_tesseract,
            image_bytes,
            config_dict,
            task_memory_mb=task_memory_mb,
        )

        return self._result_from_dict(result_dict)

    async def process_batch_images(
        self,
        image_paths: list[str | Path],
        config: TesseractConfig | None = None,
        max_concurrent: int | None = None,
    ) -> list[ExtractionResult]:
        """Process a batch of images in parallel.

        Args:
            image_paths: List of image file paths.
            config: Tesseract configuration (uses default if None).
            max_concurrent: Maximum concurrent processes.

        Returns:
            List of OCR results in the same order as input.
        """
        if not image_paths:
            return []

        config_dict = self._config_to_dict(config)

        # Prepare arguments for batch processing
        arg_batches = [(str(path), config_dict) for path in image_paths]

        # Estimate memory usage
        task_memory_mb = 80

        result_dicts = await self.process_manager.submit_batch(
            _process_image_with_tesseract,
            arg_batches,
            task_memory_mb=task_memory_mb,
            max_concurrent=max_concurrent,
        )

        return [self._result_from_dict(result_dict) for result_dict in result_dicts]

    async def process_batch_bytes(
        self,
        image_bytes_list: list[bytes],
        config: TesseractConfig | None = None,
        max_concurrent: int | None = None,
    ) -> list[ExtractionResult]:
        """Process a batch of image bytes in parallel.

        Args:
            image_bytes_list: List of image data as bytes.
            config: Tesseract configuration (uses default if None).
            max_concurrent: Maximum concurrent processes.

        Returns:
            List of OCR results in the same order as input.
        """
        if not image_bytes_list:
            return []

        config_dict = self._config_to_dict(config)

        # Prepare arguments for batch processing
        arg_batches = [(image_bytes, config_dict) for image_bytes in image_bytes_list]

        # Estimate memory usage based on average image size
        avg_image_size_mb = sum(len(img) for img in image_bytes_list) / len(image_bytes_list) / 1024 / 1024
        task_memory_mb = max(80, avg_image_size_mb * 2 + 50)

        result_dicts = await self.process_manager.submit_batch(
            _process_image_bytes_with_tesseract,
            arg_batches,
            task_memory_mb=task_memory_mb,
            max_concurrent=max_concurrent,
        )

        return [self._result_from_dict(result_dict) for result_dict in result_dicts]

    def get_system_info(self) -> dict[str, Any]:
        """Get system information from the process manager."""
        return self.process_manager.get_system_info()

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the process pool."""
        self.process_manager.shutdown(wait=wait)

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        self.shutdown()
