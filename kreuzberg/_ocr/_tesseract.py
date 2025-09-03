from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Final

import anyio
import html_to_markdown
import pandas as pd
from anyio import Path as AsyncPath
from anyio import run_process
from bs4 import BeautifulSoup
from bs4.element import Tag
from PIL import Image
from PIL.Image import Image as PILImage
from typing_extensions import Self

from kreuzberg._mime_types import HTML_MIME_TYPE, MARKDOWN_MIME_TYPE, PLAIN_TEXT_MIME_TYPE
from kreuzberg._ocr._base import OCRBackend
from kreuzberg._ocr._table_extractor import extract_words, reconstruct_table, to_markdown
from kreuzberg._types import ExtractionResult, HTMLToMarkdownConfig, TableData
from kreuzberg._utils._cache import get_ocr_cache
from kreuzberg._utils._string import normalize_spaces
from kreuzberg._utils._sync import run_sync
from kreuzberg._utils._tmp import create_temp_file
from kreuzberg.exceptions import MissingDependencyError, OCRError, ValidationError

if TYPE_CHECKING:
    from bs4.element import Tag
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
    output_format: str = "markdown"
    """Output format: 'markdown' (default), 'text', 'tsv' (for structured data), or 'hocr' (HTML-based)."""
    enable_table_detection: bool = False
    """Enable table structure detection from TSV output."""
    table_column_threshold: int = 20
    """Pixel threshold for column clustering in table detection."""
    table_row_threshold_ratio: float = 0.5
    """Row threshold as ratio of mean text height for table detection."""
    table_min_confidence: float = 30.0
    """Minimum confidence score to include a word in table extraction."""

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for passing as kwargs."""
        return asdict(self)


class TesseractBackend(OCRBackend[TesseractConfig]):
    _version_checked: ClassVar[bool] = False

    async def process_image(
        self,
        image: PILImage,
        **kwargs: Unpack[TesseractConfig],
    ) -> ExtractionResult:
        use_cache = kwargs.pop("use_cache", True)

        save_image = image
        if image.mode not in ("RGB", "RGBA", "L", "LA", "P", "1"):
            save_image = image.convert("RGB")

        image_buffer = io.BytesIO()
        await run_sync(save_image.save, image_buffer, format="PNG")
        image_content = image_buffer.getvalue()

        cache_kwargs = {
            "image_hash": hashlib.sha256(image_content).hexdigest()[:16],
            "ocr_backend": "tesseract",
            "ocr_config": str(sorted(kwargs.items())),
        }

        if use_cache:
            cached_result = await self._handle_cache_lookup(cache_kwargs)
            if cached_result:
                return cached_result

        ocr_cache = get_ocr_cache()
        try:
            await self._validate_tesseract_version()
            image_path, unlink = await create_temp_file(".png")

            try:
                await run_sync(save_image.save, str(image_path), format="PNG")
            except OSError as e:
                if "cannot write mode" not in str(e):
                    raise
                save_image = image.convert("RGB")
                await run_sync(save_image.save, str(image_path), format="PNG")
            try:
                result = await self.process_file(image_path, **kwargs)

                if use_cache:
                    await ocr_cache.aset(result, **cache_kwargs)

                return result
            finally:
                await unlink()
        finally:
            if use_cache:
                ocr_cache.mark_complete(**cache_kwargs)

    async def _handle_cache_lookup(self, cache_kwargs: dict[str, Any]) -> ExtractionResult | None:
        """Handle cache lookup before processing."""
        ocr_cache = get_ocr_cache()

        cached_result = await ocr_cache.aget(**cache_kwargs)
        if cached_result is not None:
            return cached_result

        if ocr_cache.is_processing(**cache_kwargs):
            event = ocr_cache.mark_processing(**cache_kwargs)
            await anyio.to_thread.run_sync(event.wait)
            cached_result = await ocr_cache.aget(**cache_kwargs)
            if cached_result is not None:
                return cached_result

        ocr_cache.mark_processing(**cache_kwargs)
        return None

    def _prepare_tesseract_run_config(self, **kwargs: Any) -> dict[str, Any]:
        """Prepare configuration for a Tesseract run."""
        language = self._validate_language_code(kwargs.pop("language", "eng"))
        psm = kwargs.pop("psm", PSMMode.AUTO)
        output_format = kwargs.pop("output_format", "markdown")
        enable_table_detection = kwargs.pop("enable_table_detection", False)

        if enable_table_detection and output_format == "text":
            output_format = "tsv"

        if output_format == "markdown":
            tesseract_format = "hocr"
            ext = ".hocr"
        elif output_format == "tsv":
            tesseract_format = "tsv"
            ext = ".tsv"
        elif output_format == "hocr":
            tesseract_format = "hocr"
            ext = ".hocr"
        else:
            tesseract_format = "text"
            ext = ".txt"

        return {
            "language": language,
            "psm": psm,
            "output_format": output_format,
            "enable_table_detection": enable_table_detection,
            "tesseract_format": tesseract_format,
            "ext": ext,
            "remaining_kwargs": kwargs,
        }

    async def _execute_tesseract(self, path: Path, output_base: str, run_config: dict[str, Any]) -> None:
        """Build and execute the Tesseract command."""
        command = [
            "tesseract",
            str(path),
            output_base,
            "-l",
            run_config["language"],
            "--psm",
            str(run_config["psm"].value),
            "--oem",
            "1",
            "--loglevel",
            "OFF",
        ]

        if run_config["tesseract_format"] != "text":
            command.append(run_config["tesseract_format"])

        for kwarg, value in run_config["remaining_kwargs"].items():
            if kwarg.startswith("table_"):
                continue
            if isinstance(value, bool):
                command.extend(["-c", f"{kwarg}={1 if value else 0}"])
            else:
                command.extend(["-c", f"{kwarg}={value}"])

        env: dict[str, Any] | None = None
        if sys.platform.startswith("linux"):
            env = {"OMP_THREAD_LIMIT": "1"}

        try:
            result = await run_process(command, env=env)
            if not result.returncode == 0:
                raise OCRError(
                    "OCR failed with a non-0 return code.",
                    context={"error": result.stderr.decode() if isinstance(result.stderr, bytes) else result.stderr},
                )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            raise OCRError(
                f"Failed to OCR using tesseract: {error_msg}",
                context={"command": command, "returncode": e.returncode, "error": error_msg},
            ) from e

    async def _process_tesseract_output(self, output: str, run_config: dict[str, Any]) -> ExtractionResult:
        """Process the raw output from Tesseract based on the requested format."""
        output_format = run_config["output_format"]
        enable_table_detection = run_config["enable_table_detection"]
        kwargs = run_config["remaining_kwargs"]

        if output_format == "markdown":
            return await self._process_hocr_to_markdown(output, enable_table_detection=enable_table_detection, **kwargs)
        if output_format == "tsv" and enable_table_detection:
            return await self._process_tsv_output(
                output,
                table_column_threshold=kwargs.get("table_column_threshold", 20),
                table_row_threshold_ratio=kwargs.get("table_row_threshold_ratio", 0.5),
                table_min_confidence=kwargs.get("table_min_confidence", 30.0),
            )
        if output_format == "tsv":
            return self._extract_text_from_tsv(output)
        if output_format == "hocr":
            return ExtractionResult(content=output, mime_type=HTML_MIME_TYPE, metadata={}, chunks=[])

        return ExtractionResult(
            content=normalize_spaces(output), mime_type=PLAIN_TEXT_MIME_TYPE, metadata={}, chunks=[]
        )

    async def process_file(self, path: Path, **kwargs: Unpack[TesseractConfig]) -> ExtractionResult:
        use_cache = kwargs.pop("use_cache", True)

        try:
            stat = path.stat()
            file_info = {"path": str(path.resolve()), "size": stat.st_size, "mtime": stat.st_mtime}
        except OSError:
            file_info = {"path": str(path), "size": 0, "mtime": 0}

        cache_kwargs = {
            "file_info": str(sorted(file_info.items())),
            "ocr_backend": "tesseract",
            "ocr_config": str(sorted(kwargs.items())),
        }

        if use_cache:
            cached_result = await self._handle_cache_lookup(cache_kwargs)
            if cached_result:
                return cached_result

        ocr_cache = get_ocr_cache()
        try:
            await self._validate_tesseract_version()

            run_config = self._prepare_tesseract_run_config(**kwargs)
            output_path, unlink = await create_temp_file(run_config["ext"])

            try:
                output_base = str(output_path).replace(run_config["ext"], "")
                await self._execute_tesseract(path, output_base, run_config)

                output = await AsyncPath(output_path).read_text("utf-8")
                extraction_result = await self._process_tesseract_output(output, run_config)

                if use_cache:
                    final_cache_kwargs = cache_kwargs.copy()
                    final_cache_kwargs["ocr_config"] = str(
                        sorted(
                            {
                                **run_config["remaining_kwargs"],
                                "language": run_config["language"],
                                "psm": run_config["psm"],
                            }.items()
                        )
                    )
                    await ocr_cache.aset(extraction_result, **final_cache_kwargs)

                return extraction_result
            except (RuntimeError, OSError) as e:
                raise OCRError(f"Failed to OCR using tesseract: {e}") from e
            finally:
                await unlink()
        finally:
            if use_cache:
                ocr_cache.mark_complete(**cache_kwargs)

    async def _process_tsv_output(
        self,
        tsv_content: str,
        table_column_threshold: int = 20,
        table_row_threshold_ratio: float = 0.5,
        table_min_confidence: float = 30.0,
    ) -> ExtractionResult:
        """Process TSV output and extract tables if detected.

        Args:
            tsv_content: Raw TSV output from Tesseract.
            table_column_threshold: Pixel threshold for column clustering.
            table_row_threshold_ratio: Row threshold as ratio of mean text height.
            table_min_confidence: Minimum confidence score to include a word.

        Returns:
            ExtractionResult with extracted content and tables.
        """
        text_result = self._extract_text_from_tsv(tsv_content)

        try:
            if (
                (words := extract_words(tsv_content, min_confidence=table_min_confidence))
                and (
                    table_data := reconstruct_table(
                        words,
                        column_threshold=table_column_threshold,
                        row_threshold_ratio=table_row_threshold_ratio,
                    )
                )
                and len(table_data) > 1
            ):
                markdown = to_markdown(table_data)

                try:
                    df = await run_sync(pd.DataFrame, table_data[1:], columns=table_data[0])
                except (ImportError, IndexError):
                    df = None

                table: TableData = {"text": markdown, "df": df, "page_number": 1, "cropped_image": None}  # type: ignore[typeddict-item]

                return ExtractionResult(
                    content=text_result.content,
                    mime_type=text_result.mime_type,
                    metadata=text_result.metadata,
                    tables=[table],
                    chunks=text_result.chunks,
                )
        except (ValueError, KeyError, ImportError):
            pass

        return text_result

    def _extract_text_from_tsv(self, tsv_content: str) -> ExtractionResult:
        """Extract plain text from TSV output.

        Args:
            tsv_content: Raw TSV output from Tesseract.

        Returns:
            ExtractionResult with extracted text.
        """
        try:
            reader = csv.DictReader(StringIO(tsv_content), delimiter="\t")

            lines: dict[tuple[int, int, int, int], list[tuple[int, str]]] = {}

            for row in reader:
                if row.get("level") == "5" and row.get("text", "").strip():
                    line_key = (int(row["page_num"]), int(row["block_num"]), int(row["par_num"]), int(row["line_num"]))

                    if line_key not in lines:
                        lines[line_key] = []

                    lines[line_key].append((int(row["left"]), row["text"]))

            text_parts: list[str] = []
            last_block = -1
            last_para = -1

            for line_key in sorted(lines.keys()):
                page_num, block_num, par_num, line_num = line_key

                if block_num != last_block:
                    if text_parts:  # ~keep
                        text_parts.append("\n\n")
                    last_block = block_num
                    last_para = par_num
                elif par_num != last_para:
                    text_parts.append("\n\n")
                    last_para = par_num

                words = sorted(lines[line_key], key=lambda x: x[0])
                line_text = " ".join(word[1] for word in words)
                text_parts.append(line_text)
                text_parts.append("\n")

            content = "".join(text_parts).strip()

        except (ValueError, KeyError):
            content = ""
            for line in tsv_content.split("\n")[1:]:  # ~keep skip header
                parts = line.split("\t")
                if len(parts) > 11 and parts[11].strip():  # ~keep text is in column 11
                    content += parts[11] + " "
            content = content.strip()

        return ExtractionResult(
            content=normalize_spaces(content), mime_type=PLAIN_TEXT_MIME_TYPE, metadata={}, chunks=[]
        )

    async def _process_hocr_to_markdown(
        self,
        hocr_content: str,
        enable_table_detection: bool = False,
        html_to_markdown_config: HTMLToMarkdownConfig | None = None,
        table_column_threshold: int = 20,
        table_row_threshold_ratio: float = 0.5,
        table_min_confidence: float = 30.0,
        **_kwargs: Any,
    ) -> ExtractionResult:
        """Convert hOCR content to Markdown with table detection.

        Args:
            hocr_content: Raw hOCR HTML/XML content from Tesseract.
            enable_table_detection: Whether to detect and format tables.
            html_to_markdown_config: Configuration for HTML to Markdown conversion.
            table_column_threshold: Pixel threshold for column clustering.
            table_row_threshold_ratio: Row threshold as ratio of mean text height.
            table_min_confidence: Minimum confidence score to include a word.
            **kwargs: Additional configuration options.

        Returns:
            ExtractionResult with Markdown content and detected tables.
        """
        config = html_to_markdown_config or HTMLToMarkdownConfig(
            escape_asterisks=False,
            escape_underscores=False,
            extract_metadata=False,
            strip="meta title",
        )

        tables: list[TableData] = []
        if enable_table_detection:
            soup = BeautifulSoup(hocr_content, "lxml")
            tables = await self._extract_tables_from_hocr(
                soup,
                table_column_threshold,
                table_row_threshold_ratio,
                table_min_confidence,
            )

        hocr_converters = self._create_hocr_converters(tables)

        all_converters = dict(hocr_converters)
        if config.custom_converters:
            all_converters.update(config.custom_converters)

        config_dict = config.to_dict()
        config_dict["custom_converters"] = all_converters

        try:
            markdown_content = html_to_markdown.convert_to_markdown(hocr_content, **config_dict)
            markdown_content = normalize_spaces(markdown_content)
        except (ValueError, TypeError, AttributeError):
            try:
                soup = BeautifulSoup(hocr_content, "lxml")
                words = soup.find_all("span", class_="ocrx_word")
                text_parts = []
                for word in words:
                    text = word.get_text().strip()
                    if text:
                        text_parts.append(text)

                if text_parts:
                    markdown_content = " ".join(text_parts)
                else:
                    markdown_content = soup.get_text().strip() or "[No text detected]"

                markdown_content = normalize_spaces(markdown_content)
            except (ValueError, TypeError, AttributeError):
                markdown_content = "[OCR processing failed]"

        if tables:
            table_sections = []
            for i, table in enumerate(tables):
                table_sections.append(f"\n## Table {i + 1}\n\n{table['text']}\n")

            if markdown_content.strip():
                final_content = f"{markdown_content}\n{''.join(table_sections)}"
            else:
                final_content = "".join(table_sections).strip()
        else:
            final_content = markdown_content

        return ExtractionResult(
            content=final_content,
            mime_type=MARKDOWN_MIME_TYPE,
            metadata={"source_format": "hocr", "tables_detected": len(tables)},
            chunks=[],
            tables=tables,
        )

    def _create_basic_converters(self) -> dict[str, Any]:
        """Create basic converters for individual hOCR elements."""

        def ocrx_word_converter(*, tag: Tag, text: str, **_conv_kwargs: Any) -> str:
            """Custom converter for hOCR word elements - adds spaces between words."""
            del tag
            return f"{text.strip()} "

        def ocr_line_converter(*, tag: Tag, text: str, **_conv_kwargs: Any) -> str:
            """Custom converter for hOCR line elements - handles line breaks."""
            del tag
            return f"{text.strip()}\n"

        def ocr_par_converter(*, tag: Tag, text: str, **_conv_kwargs: Any) -> str:
            """Custom converter for hOCR paragraph elements - handles paragraph breaks."""
            del tag
            content = text.strip()
            if not content:
                return ""
            return f"{content}\n\n"

        def ocr_carea_converter(*, tag: Tag, text: str, **_conv_kwargs: Any) -> str:
            """Custom converter for hOCR content area elements."""
            del tag
            content = text.strip()
            if not content:
                return ""
            return f"{content}\n\n"

        def ocr_page_converter(*, tag: Tag, text: str, **_conv_kwargs: Any) -> str:
            """Custom converter for hOCR page elements."""
            del tag
            return text.strip()

        def ocr_separator_converter(*, tag: Tag, text: str, **_conv_kwargs: Any) -> str:
            """Custom converter for hOCR separator elements - convert to horizontal rules."""
            del tag, text
            return "---\n"

        def ocr_photo_converter(*, tag: Tag, text: str, **_conv_kwargs: Any) -> str:
            """Custom converter for hOCR photo/image elements - indicate image presence."""
            del text
            title = tag.get("title", "")
            if isinstance(title, str):
                bbox_match = re.search(r"bbox (\d+) (\d+) (\d+) (\d+)", title)
                if bbox_match:
                    x0, y0, x1, y1 = bbox_match.groups()
                    width = int(x1) - int(x0)
                    height = int(y1) - int(y0)
                    return f"*[Image region: {width}x{height} pixels]*\n\n"
            return "*[Image detected]*\n\n"

        return {
            "ocrx_word": ocrx_word_converter,
            "ocr_line": ocr_line_converter,
            "ocr_par": ocr_par_converter,
            "ocr_carea": ocr_carea_converter,
            "ocr_page": ocr_page_converter,
            "ocr_separator": ocr_separator_converter,
            "ocr_photo": ocr_photo_converter,
        }

    def _create_hocr_converters(self, _tables: list[TableData]) -> dict[str, Any]:
        """Create custom converters for hOCR elements that preserve spacing.

        Args:
            tables: List of detected tables (not used for filtering, tables added separately).

        Returns:
            Dictionary mapping HTML tags to converter functions.
        """
        basic_converters = self._create_basic_converters()

        def generic_div_converter(*, tag: Tag, text: str, **_conv_kwargs: Any) -> str:
            """Generic converter for div elements based on class."""
            class_attr = tag.get("class", "")
            if isinstance(class_attr, list):
                class_attr = " ".join(class_attr)
            elif not isinstance(class_attr, str):
                class_attr = ""

            for class_name in ["ocr_separator", "ocr_photo", "ocr_page", "ocr_carea"]:
                if class_name in class_attr:
                    converter_result = basic_converters[class_name](tag=tag, text=text, **_conv_kwargs)
                    return str(converter_result)
            return text

        def generic_span_converter(*, tag: Tag, text: str, **_conv_kwargs: Any) -> str:
            """Generic converter for span elements based on class."""
            class_attr = tag.get("class", "")
            if isinstance(class_attr, list):
                class_attr = " ".join(class_attr)
            elif not isinstance(class_attr, str):
                class_attr = ""

            for class_name in ["ocrx_word", "ocr_line"]:
                if class_name in class_attr:
                    converter_result = basic_converters[class_name](tag=tag, text=text, **_conv_kwargs)
                    return str(converter_result)
            return f"{text.strip()} "

        return {
            "span": generic_span_converter,
            "div": generic_div_converter,
            "p": basic_converters["ocr_par"],
        }

    def _process_hocr_to_markdown_sync(self, hocr_content: str, config: TesseractConfig) -> ExtractionResult:
        """Synchronously process hOCR content to markdown format.

        Args:
            hocr_content: Raw hOCR content as string
            config: Tesseract configuration object

        Returns:
            ExtractionResult with markdown content
        """
        tables: list[TableData] = []

        if config.enable_table_detection:
            pass

        try:
            converters = self._create_hocr_converters(tables)

            html_config = HTMLToMarkdownConfig(
                custom_converters=converters,
                escape_asterisks=False,
                escape_underscores=False,
                extract_metadata=False,
                strip="meta title",
            )

            markdown_content = html_to_markdown.convert_to_markdown(
                hocr_content,
                **html_config.to_dict(),
            )

            markdown_content = normalize_spaces(markdown_content)

        except (ValueError, TypeError, AttributeError):
            try:
                soup = BeautifulSoup(hocr_content, "lxml")
                words = soup.find_all("span", class_="ocrx_word")
                text_parts = []
                for word in words:
                    text = word.get_text().strip()
                    if text:
                        text_parts.append(text)

                if text_parts:
                    markdown_content = " ".join(text_parts)
                else:
                    markdown_content = soup.get_text().strip() or "[No text detected]"

                markdown_content = normalize_spaces(markdown_content)
            except (ValueError, TypeError, AttributeError):
                markdown_content = "[OCR processing failed]"

        if tables:
            table_sections = []
            for i, table in enumerate(tables):
                table_sections.append(f"\n## Table {i + 1}\n\n{table['text']}\n")

            if markdown_content.strip():
                final_content = f"{markdown_content}\n{''.join(table_sections)}"
            else:
                final_content = "".join(table_sections).strip()
        else:
            final_content = markdown_content

        return ExtractionResult(
            content=final_content,
            mime_type=MARKDOWN_MIME_TYPE,
            metadata={"source_format": "hocr", "tables_detected": len(tables)},
            chunks=[],
            tables=tables,
        )

    def _process_tsv_output_sync(
        self,
        tsv_content: str,
        table_column_threshold: int = 20,
        table_row_threshold_ratio: float = 0.5,
        table_min_confidence: float = 30.0,
    ) -> ExtractionResult:
        """Synchronously process TSV output and extract tables if detected.

        Args:
            tsv_content: Raw TSV output from Tesseract.
            table_column_threshold: Pixel threshold for column clustering.
            table_row_threshold_ratio: Row threshold as ratio of mean text height.
            table_min_confidence: Minimum confidence score to include a word.

        Returns:
            ExtractionResult with extracted content and tables.
        """
        text_result = self._extract_text_from_tsv(tsv_content)

        try:
            if (
                (words := extract_words(tsv_content, min_confidence=table_min_confidence))
                and (
                    table_data := reconstruct_table(
                        words,
                        column_threshold=table_column_threshold,
                        row_threshold_ratio=table_row_threshold_ratio,
                    )
                )
                and len(table_data) > 1
            ):
                markdown = to_markdown(table_data)

                try:
                    df = pd.DataFrame(table_data[1:], columns=table_data[0])
                except (ImportError, IndexError):
                    df = None

                table: TableData = {"text": markdown, "df": df, "page_number": 1, "cropped_image": None}  # type: ignore[typeddict-item]

                return ExtractionResult(
                    content=text_result.content,
                    mime_type=text_result.mime_type,
                    metadata=text_result.metadata,
                    tables=[table],
                    chunks=text_result.chunks,
                )
        except (ValueError, KeyError, ImportError):
            pass

        return text_result

    async def _extract_tables_from_hocr(
        self,
        soup: Any,
        column_threshold: int = 20,
        row_threshold_ratio: float = 0.5,
        min_confidence: float = 30.0,
    ) -> list[TableData]:
        """Extract tables from hOCR structure using coordinate analysis.

        Args:
            soup: Parsed hOCR BeautifulSoup object.
            column_threshold: Pixel threshold for column clustering.
            row_threshold_ratio: Row threshold as ratio of mean text height.
            min_confidence: Minimum confidence score to include a word.

        Returns:
            List of detected tables as TableData objects.
        """
        tsv_data = await self._hocr_to_tsv_data(soup, min_confidence)

        if not tsv_data:
            return []

        if not (words := extract_words(tsv_data, min_confidence=min_confidence)):
            return []

        tables: list[TableData] = []
        try:
            table_data = reconstruct_table(
                words,
                column_threshold=column_threshold,
                row_threshold_ratio=row_threshold_ratio,
            )
            if table_data and len(table_data) > 1:  # ~keep At least header + one data row
                markdown = to_markdown(table_data)

                min_x = min(w["left"] for w in words)
                max_x = max(w["left"] + w["width"] for w in words)
                min_y = min(w["top"] for w in words)
                max_y = max(w["top"] + w["height"] for w in words)

                try:
                    df = await run_sync(pd.DataFrame, table_data[1:], columns=table_data[0])
                except (ImportError, IndexError):
                    df = None

                dummy_image = Image.new("RGB", (1, 1), "white")

                table: TableData = {
                    "text": markdown,
                    "df": df,
                    "page_number": 1,
                    "cropped_image": dummy_image,
                    "metadata": {"bbox": (min_x, min_y, max_x, max_y)},
                }  # type: ignore[typeddict-unknown-key]
                tables.append(table)
        except (ValueError, KeyError, ImportError):
            pass

        return tables

    async def _hocr_to_tsv_data(self, soup: Any, min_confidence: float) -> str:
        """Convert hOCR structure to TSV format for table extraction.

        Args:
            soup: Parsed hOCR BeautifulSoup object.
            min_confidence: Minimum confidence score to include.

        Returns:
            TSV formatted string compatible with table extractor.
        """
        tsv_lines = ["level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"]

        words = soup.find_all("span", class_="ocrx_word")
        word_num = 1

        for word in words:
            title = word.get("title", "")
            text = word.get_text().strip()

            if not text:
                continue

            bbox_match = re.search(r"bbox (\d+) (\d+) (\d+) (\d+)", title)
            if not bbox_match:
                continue

            x0, y0, x1, y1 = map(int, bbox_match.groups())

            conf_match = re.search(r"x_wconf (\d+)", title)
            confidence = float(conf_match.group(1)) if conf_match else 100.0

            if confidence < min_confidence:
                continue

            line = word.find_parent(class_="ocr_line")
            par = word.find_parent(class_="ocr_par")
            block = word.find_parent(class_="ocr_carea")

            tsv_line = f"5\t1\t{block.get('id', '1').split('_')[-1] if block else 1}\t{par.get('id', '1').split('_')[-1] if par else 1}\t{line.get('id', '1').split('_')[-1] if line else 1}\t{word_num}\t{x0}\t{y0}\t{x1 - x0}\t{y1 - y0}\t{confidence}\t{text}"
            tsv_lines.append(tsv_line)
            word_num += 1

        return "\n".join(tsv_lines)

    def _identify_table_regions(self, words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """Identify potential table regions from word coordinates.

        Args:
            words: List of word dictionaries with coordinates.

        Returns:
            List of word groups representing potential tables.
        """
        if not words:
            return []

        return [words]

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
            env = {"OMP_THREAD_LIMIT": "1"} if sys.platform.startswith("linux") else None
            try:
                result = await run_process(command, env=env)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                raise MissingDependencyError(
                    "Tesseract version 5 is a required system dependency. Please install it on your system and make sure its available in $PATH."
                ) from e
            version_match = re.search(r"tesseract\s+v?(\d+)\.\d+\.\d+", result.stdout.decode("utf-8"))
            if not version_match or int(version_match.group(1)) < MINIMAL_SUPPORTED_TESSERACT_VERSION:
                raise MissingDependencyError(
                    "Tesseract version 5 is a required system dependency. Please install it on your system and make sure its available in $PATH."
                )

            cls._version_checked = True
        except FileNotFoundError as e:
            raise MissingDependencyError(
                "Tesseract version 5 is a required system dependency. Please install it on your system and make sure its available in $PATH."
            ) from e

    def _handle_cache_lookup_sync(self, cache_kwargs: dict[str, Any]) -> ExtractionResult | None:
        """Handle cache lookup before processing (sync)."""
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
        return None

    def _execute_tesseract_sync(self, command: list[str]) -> None:
        """Run tesseract command synchronously."""
        env = os.environ.copy()
        if sys.platform.startswith("linux"):
            env["OMP_THREAD_LIMIT"] = "1"

        try:
            subprocess.run(
                command,
                check=True,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise OCRError(
                f"Failed to OCR using tesseract: {error_msg}",
                context={"command": command, "returncode": e.returncode, "error": error_msg},
            ) from e
        except subprocess.TimeoutExpired as e:
            raise OCRError(
                "Tesseract timed out during processing.",
                context={"command": command, "timeout": 30},
            ) from e

    def _process_tesseract_output_sync(self, output: str, run_config: dict[str, Any]) -> ExtractionResult:
        """Process the raw output from Tesseract based on the requested format (sync)."""
        output_format = run_config["output_format"]
        enable_table_detection = run_config["enable_table_detection"]
        kwargs = run_config["remaining_kwargs"]
        config = TesseractConfig(**kwargs)

        if output_format == "markdown":
            return self._process_hocr_to_markdown_sync(output, config)
        if output_format == "tsv" and enable_table_detection:
            return self._process_tsv_output_sync(
                output,
                table_column_threshold=config.table_column_threshold,
                table_row_threshold_ratio=config.table_row_threshold_ratio,
                table_min_confidence=config.table_min_confidence,
            )
        if output_format == "tsv":
            return self._extract_text_from_tsv(output)
        if output_format == "hocr":
            return ExtractionResult(content=output, mime_type=HTML_MIME_TYPE, metadata={}, chunks=[])

        return ExtractionResult(
            content=normalize_spaces(output), mime_type=PLAIN_TEXT_MIME_TYPE, metadata={}, chunks=[]
        )

    def process_image_sync(self, image: PILImage, **kwargs: Unpack[TesseractConfig]) -> ExtractionResult:
        """Synchronously process an image and extract its text and metadata."""
        use_cache = kwargs.pop("use_cache", True)

        save_image = image
        if image.mode not in ("RGB", "RGBA", "L", "LA", "P", "1"):
            save_image = image.convert("RGB")

        image_buffer = io.BytesIO()
        save_image.save(image_buffer, format="PNG")
        image_content = image_buffer.getvalue()

        cache_kwargs = {
            "image_hash": hashlib.sha256(image_content).hexdigest()[:16],
            "ocr_backend": "tesseract",
            "ocr_config": str(sorted(kwargs.items())),
        }

        if use_cache:
            cached_result = self._handle_cache_lookup_sync(cache_kwargs)
            if cached_result:
                return cached_result

        ocr_cache = get_ocr_cache()
        try:
            self._validate_tesseract_version_sync()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                image_path = Path(tmp_file.name)
                save_image.save(str(image_path), format="PNG")
            try:
                kwargs_with_cache = {**kwargs, "use_cache": use_cache}
                result = self.process_file_sync(image_path, **kwargs_with_cache)

                if use_cache:
                    ocr_cache.set(result, **cache_kwargs)

                return result
            finally:
                if image_path.exists():
                    image_path.unlink()
        finally:
            if use_cache:
                ocr_cache.mark_complete(**cache_kwargs)

    def process_file_sync(self, path: Path, **kwargs: Unpack[TesseractConfig]) -> ExtractionResult:
        """Synchronously process a file and extract its text and metadata."""
        use_cache = kwargs.pop("use_cache", True)

        file_info = self._get_file_info(path)

        cache_kwargs = {
            "file_info": str(sorted(file_info.items())),
            "ocr_backend": "tesseract",
            "ocr_config": str(sorted(kwargs.items())),
        }

        if use_cache:
            cached_result = self._handle_cache_lookup_sync(cache_kwargs)
            if cached_result:
                return cached_result

        ocr_cache = get_ocr_cache()
        try:
            self._validate_tesseract_version_sync()

            run_config = self._prepare_tesseract_run_config(**kwargs)

            temp_fd, temp_path = tempfile.mkstemp(suffix=run_config["ext"])
            os.close(temp_fd)
            Path(temp_path).unlink()
            output_base = temp_path.replace(run_config["ext"], "")

            try:
                command = self._build_tesseract_command(
                    path,
                    output_base,
                    run_config["language"],
                    run_config["psm"],
                    run_config["tesseract_format"],
                    **run_config["remaining_kwargs"],
                )
                self._execute_tesseract_sync(command)

                output_path = Path(f"{output_base}{run_config['ext']}")
                if not output_path.exists():
                    return ExtractionResult(
                        content="[OCR processing failed]",
                        mime_type=PLAIN_TEXT_MIME_TYPE,
                        metadata={
                            "source_format": run_config["tesseract_format"],
                            "error": f"{run_config['ext']} file not generated",
                        },
                        chunks=[],
                        tables=[],
                    )

                with output_path.open(encoding="utf-8") as f:
                    output = f.read()

                extraction_result = self._process_tesseract_output_sync(output, run_config)

                if use_cache:
                    final_cache_kwargs = cache_kwargs.copy()
                    final_cache_kwargs["ocr_config"] = str(
                        sorted(
                            {
                                **run_config["remaining_kwargs"],
                                "language": run_config["language"],
                                "psm": run_config["psm"],
                            }.items()
                        )
                    )
                    ocr_cache.set(extraction_result, **final_cache_kwargs)

                return extraction_result
            finally:
                for cleanup_ext in [".txt", ".hocr", ".tsv"]:
                    cleanup_path = Path(f"{output_base}{cleanup_ext}")
                    cleanup_path.unlink(missing_ok=True)
        except Exception as e:
            raise OCRError(f"Failed to OCR using tesseract: {e}") from e
        finally:
            if use_cache:
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
        self, path: Path, output_base: str, language: str, psm: PSMMode, output_format: str = "text", **kwargs: Any
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

        if output_format != "text":
            command.append(output_format)

        for kwarg, value in kwargs.items():
            if kwarg.startswith("table_"):
                continue
            if isinstance(value, bool):
                command.extend(["-c", f"{kwarg}={1 if value else 0}"])
            else:
                command.extend(["-c", f"{kwarg}={value}"])
        return command

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
            try:
                result = subprocess.run(command, capture_output=True, text=True, check=True, encoding="utf-8")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                raise MissingDependencyError(
                    "Tesseract version 5 is a required system dependency. Please install it on your system and make sure its available in $PATH."
                ) from e
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
                encoding="utf-8",
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
        with (
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_image,
            Image.open(io.BytesIO(image_bytes)) as image,
        ):
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
