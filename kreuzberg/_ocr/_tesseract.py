from __future__ import annotations

import hashlib
import io
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final

import anyio
from anyio import Path as AsyncPath
from anyio import run_process
from PIL import Image
from typing_extensions import Self

from kreuzberg._mime_types import PLAIN_TEXT_MIME_TYPE
from kreuzberg._ocr._base import OCRBackend
from kreuzberg._types import ExtractionResult
from kreuzberg._utils._string import normalize_spaces
from kreuzberg._utils._sync import run_sync
from kreuzberg._utils._tmp import create_temp_file
from kreuzberg.exceptions import MissingDependencyError, OCRError, ValidationError

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

try:  # pragma: no cover
    from typing import Unpack  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    from typing_extensions import Unpack


TESSERACT_SUPPORTED_LANGUAGE_CODES: Final[set[str]] = {
    "afr",
    "amh",
    "ara",
    "asm",
    "aze",
    "aze_cyrl",
    "bel",
    "ben",
    "bod",
    "bos",
    "bre",
    "bul",
    "cat",
    "ceb",
    "ces",
    "chi_sim",
    "chi_tra",
    "chr",
    "cos",
    "cym",
    "dan",
    "dan_frak",
    "deu",
    "deu_frak",
    "deu_latf",
    "dzo",
    "ell",
    "eng",
    "enm",
    "epo",
    "equ",
    "est",
    "eus",
    "fao",
    "fas",
    "fil",
    "fin",
    "fra",
    "frk",
    "frm",
    "fry",
    "gla",
    "gle",
    "glg",
    "grc",
    "guj",
    "hat",
    "heb",
    "hin",
    "hrv",
    "hun",
    "hye",
    "iku",
    "ind",
    "isl",
    "ita",
    "ita_old",
    "jav",
    "jpn",
    "kan",
    "kat",
    "kat_old",
    "kaz",
    "khm",
    "kir",
    "kmr",
    "kor",
    "kor_vert",
    "kur",
    "lao",
    "lat",
    "lav",
    "lit",
    "ltz",
    "mal",
    "mar",
    "mkd",
    "mlt",
    "mon",
    "mri",
    "msa",
    "mya",
    "nep",
    "nld",
    "nor",
    "oci",
    "ori",
    "osd",
    "pan",
    "pol",
    "por",
    "pus",
    "que",
    "ron",
    "rus",
    "san",
    "sin",
    "slk",
    "slk_frak",
    "slv",
    "snd",
    "spa",
    "spa_old",
    "sqi",
    "srp",
    "srp_latn",
    "sun",
    "swa",
    "swe",
    "syr",
    "tam",
    "tat",
    "tel",
    "tgk",
    "tgl",
    "tha",
    "tir",
    "ton",
    "tur",
    "uig",
    "ukr",
    "urd",
    "uzb",
    "uzb_cyrl",
    "vie",
    "yid",
    "yor",
}

MINIMAL_SUPPORTED_TESSERACT_VERSION: Final[int] = 5


class PSMMode(Enum):
    """Enum for Tesseract Page Segmentation Modes (PSM) with human-readable values."""

    OSD_ONLY = 0
    """Orientation and script detection only."""
    AUTO_OSD = 1
    """Automatic page segmentation with orientation and script detection."""
    AUTO_ONLY = 2
    """Automatic page segmentation without OSD."""
    AUTO = 3
    """Fully automatic page segmentation (default)."""
    SINGLE_COLUMN = 4
    """Assume a single column of text."""
    SINGLE_BLOCK_VERTICAL = 5
    """Assume a single uniform block of vertically aligned text."""
    SINGLE_BLOCK = 6
    """Assume a single uniform block of text."""
    SINGLE_LINE = 7
    """Treat the image as a single text line."""
    SINGLE_WORD = 8
    """Treat the image as a single word."""
    CIRCLE_WORD = 9
    """Treat the image as a single word in a circle."""
    SINGLE_CHAR = 10
    """Treat the image as a single character."""


@dataclass(unsafe_hash=True, frozen=True, slots=True)
class TesseractConfig:
    """Configuration options for Tesseract OCR engine."""

    classify_use_pre_adapted_templates: bool = True
    """Whether to use pre-adapted templates during classification to improve recognition accuracy."""
    language: str = "eng"
    """Language code to use for OCR.
    Examples:
            -   'eng' for English
            -   'deu' for German
            -    multiple languages combined with '+', e.g. 'eng+deu')
    """
    language_model_ngram_on: bool = False
    """Enable or disable the use of n-gram-based language models for improved text recognition.

    Default is False for optimal performance on modern documents. Enable for degraded or historical text."""
    psm: PSMMode = PSMMode.AUTO
    """Page segmentation mode (PSM) to guide Tesseract on how to segment the image (e.g., single block, single line)."""
    tessedit_dont_blkrej_good_wds: bool = True
    """If True, prevents block rejection of words identified as good, improving text output quality."""
    tessedit_dont_rowrej_good_wds: bool = True
    """If True, prevents row rejection of words identified as good, avoiding unnecessary omissions."""
    tessedit_enable_dict_correction: bool = True
    """Enable or disable dictionary-based correction for recognized text to improve word accuracy."""
    tessedit_char_whitelist: str = ""
    """Whitelist of characters that Tesseract is allowed to recognize. Empty string means no restriction."""
    tessedit_use_primary_params_model: bool = True
    """If True, forces the use of the primary parameters model for text recognition."""
    textord_space_size_is_variable: bool = True
    """Allow variable spacing between words, useful for text with irregular spacing."""
    thresholding_method: bool = False
    """Enable or disable specific thresholding methods during image preprocessing for better OCR accuracy."""


class TesseractBackend(OCRBackend[TesseractConfig]):
    _version_checked: ClassVar[bool] = False

    async def process_image(
        self,
        image: PILImage,
        **kwargs: Unpack[TesseractConfig],
    ) -> ExtractionResult:
        from kreuzberg._utils._cache import get_ocr_cache  # noqa: PLC0415

        image_buffer = io.BytesIO()
        await run_sync(image.save, image_buffer, format="PNG")
        image_content = image_buffer.getvalue()

        cache_kwargs = {
            "image_hash": hashlib.sha256(image_content).hexdigest()[:16],
            "ocr_backend": "tesseract",
            "ocr_config": str(sorted(kwargs.items())),
        }

        ocr_cache = get_ocr_cache()
        cached_result = await ocr_cache.aget(**cache_kwargs)
        if cached_result is not None:
            return cached_result

        if ocr_cache.is_processing(**cache_kwargs):
            event = ocr_cache.mark_processing(**cache_kwargs)
            await anyio.to_thread.run_sync(event.wait)

            # Try cache again after waiting for other process to complete  # ~keep
            cached_result = await ocr_cache.aget(**cache_kwargs)
            if cached_result is not None:
                return cached_result

        ocr_cache.mark_processing(**cache_kwargs)

        try:
            await self._validate_tesseract_version()
            image_path, unlink = await create_temp_file(".png")
            await run_sync(image.save, str(image_path), format="PNG")
            try:
                result = await self.process_file(image_path, **kwargs)

                await ocr_cache.aset(result, **cache_kwargs)

                return result
            finally:
                await unlink()
        finally:
            ocr_cache.mark_complete(**cache_kwargs)

    async def process_file(
        self,
        path: Path,
        **kwargs: Unpack[TesseractConfig],
    ) -> ExtractionResult:
        from kreuzberg._utils._cache import get_ocr_cache  # noqa: PLC0415

        try:
            stat = path.stat()
            file_info = {
                "path": str(path.resolve()),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            }
        except OSError:
            file_info = {
                "path": str(path),
                "size": 0,
                "mtime": 0,
            }

        cache_kwargs = {
            "file_info": str(sorted(file_info.items())),
            "ocr_backend": "tesseract",
            "ocr_config": str(sorted(kwargs.items())),
        }

        ocr_cache = get_ocr_cache()
        cached_result = await ocr_cache.aget(**cache_kwargs)
        if cached_result is not None:
            return cached_result

        if ocr_cache.is_processing(**cache_kwargs):
            event = ocr_cache.mark_processing(**cache_kwargs)
            await anyio.to_thread.run_sync(event.wait)

            # Try cache again after waiting for other process to complete  # ~keep
            cached_result = await ocr_cache.aget(**cache_kwargs)
            if cached_result is not None:
                return cached_result

        ocr_cache.mark_processing(**cache_kwargs)

        try:
            await self._validate_tesseract_version()
            output_path, unlink = await create_temp_file(".txt")
            language = self._validate_language_code(kwargs.pop("language", "eng"))
            psm = kwargs.pop("psm", PSMMode.AUTO)
            try:
                output_base = str(output_path).replace(".txt", "")
                command = [
                    "tesseract",
                    str(path),
                    output_base,
                    "-l",
                    language,
                    "--psm",
                    str(psm.value),
                    "--oem",
                    "1",
                    "--loglevel",
                    "OFF",
                ]
                for kwarg, value in kwargs.items():
                    if isinstance(value, bool):
                        command.extend(["-c", f"{kwarg}={1 if value else 0}"])
                    else:
                        command.extend(["-c", f"{kwarg}={value}"])

                env: dict[str, Any] | None = None
                if sys.platform.startswith("linux"):
                    env = {"OMP_THREAD_LIMIT": "1"}

                result = await run_process(command, env=env)

                if not result.returncode == 0:
                    raise OCRError(
                        "OCR failed with a non-0 return code.",
                        context={
                            "error": result.stderr.decode() if isinstance(result.stderr, bytes) else result.stderr
                        },
                    )

                output = await AsyncPath(output_path).read_text("utf-8")
                extraction_result = ExtractionResult(
                    content=normalize_spaces(output), mime_type=PLAIN_TEXT_MIME_TYPE, metadata={}, chunks=[]
                )

                final_cache_kwargs = cache_kwargs.copy()
                final_cache_kwargs["ocr_config"] = str(sorted({**kwargs, "language": language, "psm": psm}.items()))
                await ocr_cache.aset(extraction_result, **final_cache_kwargs)

                return extraction_result
            except (RuntimeError, OSError) as e:
                raise OCRError(f"Failed to OCR using tesseract: {e}") from e
            finally:
                await unlink()
        finally:
            ocr_cache.mark_complete(**cache_kwargs)

    @classmethod
    async def _validate_tesseract_version(cls) -> None:
        """Validate that Tesseract is installed and is version 5 or above.

        Raises:
            MissingDependencyError: If Tesseract is not installed or is below version 5.
        """
        try:
            if cls._version_checked:
                return

            command = ["tesseract", "--version"]
            result = await run_process(command)
            version_match = re.search(r"tesseract\s+v?(\d+)\.\d+\.\d+", result.stdout.decode())
            if not version_match or int(version_match.group(1)) < MINIMAL_SUPPORTED_TESSERACT_VERSION:
                raise MissingDependencyError(
                    "Tesseract version 5 is a required system dependency. Please install it on your system and make sure its available in $PATH."
                )

            cls._version_checked = True
        except FileNotFoundError as e:
            raise MissingDependencyError(
                "Tesseract version 5 is a required system dependency. Please install it on your system and make sure its available in $PATH."
            ) from e

    def process_image_sync(
        self,
        image: PILImage,
        **kwargs: Unpack[TesseractConfig],
    ) -> ExtractionResult:
        """Synchronously process an image and extract its text and metadata.

        Args:
            image: An instance of PIL.Image representing the input image.
            **kwargs: Any kwargs related to the given backend

        Returns:
            The extraction result object
        """
        from kreuzberg._utils._cache import get_ocr_cache  # noqa: PLC0415

        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")
        image_content = image_buffer.getvalue()

        cache_kwargs = {
            "image_hash": hashlib.sha256(image_content).hexdigest()[:16],
            "ocr_backend": "tesseract",
            "ocr_config": str(sorted(kwargs.items())),
        }

        ocr_cache = get_ocr_cache()
        cached_result = ocr_cache.get(**cache_kwargs)
        if cached_result is not None:
            return cached_result

        if ocr_cache.is_processing(**cache_kwargs):
            event = ocr_cache.mark_processing(**cache_kwargs)
            event.wait()

            cached_result = ocr_cache.get(**cache_kwargs)
            if cached_result is not None:
                return cached_result

        ocr_cache.mark_processing(**cache_kwargs)

        try:
            self._validate_tesseract_version_sync()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                image_path = Path(tmp_file.name)
                image.save(str(image_path), format="PNG")
            try:
                result = self.process_file_sync(image_path, **kwargs)

                ocr_cache.set(result, **cache_kwargs)

                return result
            finally:
                if image_path.exists():
                    image_path.unlink()
        finally:
            ocr_cache.mark_complete(**cache_kwargs)

    def process_file_sync(
        self,
        path: Path,
        **kwargs: Unpack[TesseractConfig],
    ) -> ExtractionResult:
        """Synchronously process a file and extract its text and metadata.

        Args:
            path: A Path object representing the file to be processed.
            **kwargs: Any kwargs related to the given backend

        Returns:
            The extraction result object
        """
        from kreuzberg._utils._cache import get_ocr_cache  # noqa: PLC0415

        file_info = self._get_file_info(path)

        cache_kwargs = {
            "file_info": str(sorted(file_info.items())),
            "ocr_backend": "tesseract",
            "ocr_config": str(sorted(kwargs.items())),
        }

        ocr_cache = get_ocr_cache()
        cached_result = ocr_cache.get(**cache_kwargs)
        if cached_result is not None:
            return cached_result

        if ocr_cache.is_processing(**cache_kwargs):
            event = ocr_cache.mark_processing(**cache_kwargs)
            event.wait()

            cached_result = ocr_cache.get(**cache_kwargs)
            if cached_result is not None:
                return cached_result

        ocr_cache.mark_processing(**cache_kwargs)

        try:
            self._validate_tesseract_version_sync()
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
                output_base = tmp_file.name.replace(".txt", "")
            language = self._validate_language_code(kwargs.pop("language", "eng"))
            psm = kwargs.pop("psm", PSMMode.AUTO)
            try:
                command = self._build_tesseract_command(path, output_base, language, psm, **kwargs)
                self._run_tesseract_sync(command)

                output_path = Path(output_base + ".txt")
                with output_path.open(encoding="utf-8") as f:
                    output = f.read()
                extraction_result = ExtractionResult(
                    content=normalize_spaces(output), mime_type=PLAIN_TEXT_MIME_TYPE, metadata={}, chunks=[]
                )

                final_cache_kwargs = cache_kwargs.copy()
                final_cache_kwargs["ocr_config"] = str(sorted({**kwargs, "language": language, "psm": psm}.items()))
                ocr_cache.set(extraction_result, **final_cache_kwargs)

                return extraction_result
            except (RuntimeError, OSError) as e:
                raise OCRError(f"Failed to OCR using tesseract: {e}") from e
            finally:
                for ext in [".txt"]:
                    temp_file = Path(output_base + ext)
                    if temp_file.exists():
                        temp_file.unlink()
        finally:
            ocr_cache.mark_complete(**cache_kwargs)

    def _get_file_info(self, path: Path) -> dict[str, Any]:
        """Get file information for caching."""
        try:
            stat = path.stat()
            return {
                "path": str(path.resolve()),
                "size": stat.st_size,
                "mtime": stat.st_mtime,
            }
        except OSError:
            return {
                "path": str(path),
                "size": 0,
                "mtime": 0,
            }

    def _build_tesseract_command(
        self, path: Path, output_base: str, language: str, psm: PSMMode, **kwargs: Any
    ) -> list[str]:
        """Build tesseract command with all parameters."""
        command = [
            "tesseract",
            str(path),
            output_base,
            "-l",
            language,
            "--psm",
            str(psm.value),
            "--oem",
            "1",
            "--loglevel",
            "OFF",
        ]
        for kwarg, value in kwargs.items():
            if isinstance(value, bool):
                command.extend(["-c", f"{kwarg}={1 if value else 0}"])
            else:
                command.extend(["-c", f"{kwarg}={value}"])
        return command

    def _run_tesseract_sync(self, command: list[str]) -> None:
        """Run tesseract command synchronously."""
        env = os.environ.copy()
        if sys.platform.startswith("linux"):
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
            raise OCRError(
                "OCR failed with a non-0 return code.",
                context={"error": result.stderr},
            )

    @classmethod
    def _validate_tesseract_version_sync(cls) -> None:
        """Synchronously validate that Tesseract is installed and is version 5 or above.

        Raises:
            MissingDependencyError: If Tesseract is not installed or is below version 5.
        """
        try:
            if cls._version_checked:
                return

            command = ["tesseract", "--version"]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            version_match = re.search(r"tesseract\s+v?(\d+)\.\d+\.\d+", result.stdout)
            if not version_match or int(version_match.group(1)) < MINIMAL_SUPPORTED_TESSERACT_VERSION:
                raise MissingDependencyError(
                    "Tesseract version 5 is a required system dependency. Please install it on your system and make sure its available in $PATH."
                )

            cls._version_checked = True
        except FileNotFoundError as e:
            raise MissingDependencyError(
                "Tesseract version 5 is a required system dependency. Please install it on your system and make sure its available in $PATH."
            ) from e

    @staticmethod
    def _validate_language_code(language_code: str) -> str:
        """Convert a language code to Tesseract format.

        Args:
            language_code: Tesseract supported language code or multiple language codes connected with '+'

        Raises:
            ValidationError: If the language is not supported by Tesseract

        Returns:
            Language code compatible with Tesseract
        """
        normalized = language_code.lower()
        if normalized in TESSERACT_SUPPORTED_LANGUAGE_CODES:
            return normalized

        if "+" in normalized and all(lang in TESSERACT_SUPPORTED_LANGUAGE_CODES for lang in normalized.split("+")):
            return normalized

        raise ValidationError(
            "The provided language code is not supported by Tesseract",
            context={
                "language_code": normalized
                if "+" not in normalized
                else ",".join(
                    [lang for lang in normalized.split("+") if lang not in TESSERACT_SUPPORTED_LANGUAGE_CODES]
                ),
                "supported_languages": ",".join(sorted(TESSERACT_SUPPORTED_LANGUAGE_CODES)),
            },
        )


def _process_image_with_tesseract(
    image_path: str,
    config_dict: dict[str, Any],
) -> dict[str, Any]:
    """Process a single image with Tesseract in a separate process.

    This function is designed to be executed in a subprocess.
    It uses direct tesseract command execution to avoid async complications.

    Args:
        image_path: Path to the image file.
        config_dict: Tesseract configuration as dictionary.

    Returns:
        OCR result as dictionary.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp_file:
            output_base = tmp_file.name.replace(".txt", "")

        try:
            language = config_dict.get("language", "eng")
            psm = config_dict.get("psm", 3)

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
                raise Exception(f"Tesseract failed with return code {result.returncode}: {result.stderr}")

            output_file = output_base + ".txt"
            with Path(output_file).open(encoding="utf-8") as f:
                text = f.read()

            text = normalize_spaces(text)

            return {
                "success": True,
                "text": text,
                "confidence": None,
                "error": None,
            }

        finally:
            for ext in [".txt"]:
                temp_file = output_base + ext
                temp_path = Path(temp_file)
                if temp_path.exists():
                    temp_path.unlink()

    except Exception as e:  # noqa: BLE001
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
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_image:
            with Image.open(io.BytesIO(image_bytes)) as image:
                image.save(tmp_image.name, format="PNG")
            image_path = tmp_image.name

        try:
            return _process_image_with_tesseract(image_path, config_dict)
        finally:
            image_file = Path(image_path)
            if image_file.exists():
                image_file.unlink()

    except Exception as e:  # noqa: BLE001
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
        from kreuzberg._utils._process_pool import ProcessPoolManager  # noqa: PLC0415

        self.config = config or TesseractConfig()
        self.process_manager = ProcessPoolManager(
            max_processes=max_processes,
            memory_limit_gb=memory_limit_gb,
        )

    def _config_to_dict(self, config: TesseractConfig | None = None) -> dict[str, Any]:
        """Convert TesseractConfig to dictionary for pickling."""
        cfg = config or self.config

        config_dict = {}
        for field_name in cfg.__dataclass_fields__:
            value = getattr(cfg, field_name)

            if hasattr(value, "value"):
                config_dict[field_name] = value.value
            else:
                config_dict[field_name] = value

        return config_dict

    def _result_from_dict(self, result_dict: dict[str, Any]) -> ExtractionResult:
        """Convert result dictionary back to OCRResult."""
        if not result_dict["success"]:
            raise OCRError(f"Tesseract processing failed: {result_dict['error']}")

        return ExtractionResult(
            content=result_dict["text"],
            mime_type=PLAIN_TEXT_MIME_TYPE,
            metadata={"confidence": result_dict["confidence"]} if result_dict["confidence"] else {},  # type: ignore[typeddict-unknown-key]
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

        image_size_mb = len(image_bytes) / 1024 / 1024
        task_memory_mb = max(80, image_size_mb * 2 + 50)

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

        arg_batches = [(str(path), config_dict) for path in image_paths]

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

        arg_batches = [(image_bytes, config_dict) for image_bytes in image_bytes_list]

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

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        self.shutdown()
