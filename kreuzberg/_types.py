from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, TypedDict

import msgspec

from kreuzberg._constants import DEFAULT_MAX_CHARACTERS, DEFAULT_MAX_OVERLAP
from kreuzberg._utils._table import (
    export_table_to_csv,
    export_table_to_tsv,
    extract_table_structure_info,
)
from kreuzberg.exceptions import ValidationError

if TYPE_CHECKING:
    from kreuzberg._utils._device import DeviceType

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import NotRequired
else:  # pragma: no cover
    from typing import NotRequired

if TYPE_CHECKING:
    from pathlib import Path

    from PIL.Image import Image
    from polars import DataFrame

OcrBackendType = Literal["tesseract", "easyocr", "paddleocr"]
OutputFormatType = Literal["text", "tsv", "hocr", "markdown"]


class ConfigDict:
    def to_dict(self, include_none: bool = False) -> dict[str, Any]:
        result = msgspec.to_builtins(
            self,
            builtin_types=(type(None),),
            order="deterministic",
        )

        if include_none:
            return result  # type: ignore[no-any-return]

        return {k: v for k, v in result.items() if v is not None}


class PSMMode(Enum):
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
class TesseractConfig(ConfigDict):
    classify_use_pre_adapted_templates: bool = True
    """Whether to use pre-adapted templates during classification to improve recognition accuracy."""
    language: str = "eng"
    """Language code to use for OCR.
    Examples:
            -   'eng' for English
            -   'deu' for German
            -    multiple languages combined with '+', e.g. 'eng+deu'
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
    output_format: OutputFormatType = "markdown"
    """Output format: 'markdown' (default), 'text', 'tsv' (for structured data), or 'hocr' (HTML-based)."""
    enable_table_detection: bool = False
    """Enable table structure detection from TSV output."""
    table_column_threshold: int = 20
    """Pixel threshold for column clustering in table detection."""
    table_row_threshold_ratio: float = 0.5
    """Row threshold as ratio of mean text height for table detection."""
    table_min_confidence: float = 30.0
    """Minimum confidence score to include a word in table extraction."""


@dataclass(unsafe_hash=True, frozen=True, slots=True)
class EasyOCRConfig(ConfigDict):
    add_margin: float = 0.1
    """Extend bounding boxes in all directions."""
    adjust_contrast: float = 0.5
    """Target contrast level for low contrast text."""
    beam_width: int = 5
    """Beam width for beam search in recognition."""
    canvas_size: int = 2560
    """Maximum image dimension for detection."""
    contrast_ths: float = 0.1
    """Contrast threshold for preprocessing."""
    decoder: Literal["greedy", "beamsearch", "wordbeamsearch"] = "greedy"
    """Decoder method. Options: 'greedy', 'beamsearch', 'wordbeamsearch'."""
    height_ths: float = 0.5
    """Maximum difference in box height for merging."""
    language: str | list[str] = "en"
    """Language or languages to use for OCR. Can be a single language code (e.g., 'en'),
    a comma-separated string of language codes (e.g., 'en,ch_sim'), or a list of language codes."""
    link_threshold: float = 0.4
    """Link confidence threshold."""
    low_text: float = 0.4
    """Text low-bound score."""
    mag_ratio: float = 1.0
    """Image magnification ratio."""
    min_size: int = 10
    """Minimum text box size in pixels."""
    rotation_info: list[int] | None = None
    """List of angles to try for detection."""
    slope_ths: float = 0.1
    """Maximum slope for merging text boxes."""
    text_threshold: float = 0.7
    """Text confidence threshold."""
    use_gpu: bool = False
    """Whether to use GPU for inference. DEPRECATED: Use 'device' parameter instead."""
    device: DeviceType = "auto"
    """Device to use for inference. Options: 'cpu', 'cuda', 'mps', 'auto'."""
    gpu_memory_limit: float | None = None
    """Maximum GPU memory to use in GB. None for no limit."""
    fallback_to_cpu: bool = True
    """Whether to fallback to CPU if requested device is unavailable."""
    width_ths: float = 0.5
    """Maximum horizontal distance for merging boxes."""
    x_ths: float = 1.0
    """Maximum horizontal distance for paragraph merging."""
    y_ths: float = 0.5
    """Maximum vertical distance for paragraph merging."""
    ycenter_ths: float = 0.5
    """Maximum shift in y direction for merging."""


@dataclass(unsafe_hash=True, frozen=True, slots=True)
class PaddleOCRConfig(ConfigDict):
    cls_image_shape: str = "3,48,192"
    """Image shape for classification algorithm in format 'channels,height,width'."""
    det_algorithm: Literal["DB", "EAST", "SAST", "PSE", "FCE", "PAN", "CT", "DB++", "Layout"] = "DB"
    """Detection algorithm."""
    det_db_box_thresh: float = 0.5
    """DEPRECATED in PaddleOCR 3.2.0+: Use 'text_det_box_thresh' instead. Score threshold for detected boxes."""
    det_db_thresh: float = 0.3
    """DEPRECATED in PaddleOCR 3.2.0+: Use 'text_det_thresh' instead. Binarization threshold for DB output map."""
    det_db_unclip_ratio: float = 2.0
    """DEPRECATED in PaddleOCR 3.2.0+: Use 'text_det_unclip_ratio' instead. Expansion ratio for detected text boxes."""
    det_east_cover_thresh: float = 0.1
    """Score threshold for EAST output boxes."""
    det_east_nms_thresh: float = 0.2
    """NMS threshold for EAST model output boxes."""
    det_east_score_thresh: float = 0.8
    """Binarization threshold for EAST output map."""
    det_max_side_len: int = 960
    """Maximum size of image long side. Images exceeding this will be proportionally resized."""
    det_model_dir: str | None = None
    """Directory for detection model. If None, uses default model location."""
    drop_score: float = 0.5
    """Filter recognition results by confidence score. Results below this are discarded."""
    enable_mkldnn: bool = False
    """Whether to enable MKL-DNN acceleration (Intel CPU only)."""
    gpu_mem: int = 8000
    """DEPRECATED in PaddleOCR 3.2.0+: Parameter no longer supported. GPU memory size (in MB) to use for initialization."""
    language: str = "en"
    """Language to use for OCR."""
    max_text_length: int = 25
    """Maximum text length that the recognition algorithm can recognize."""
    rec: bool = True
    """Enable text recognition when using the ocr() function."""
    rec_algorithm: Literal[
        "CRNN",
        "SRN",
        "NRTR",
        "SAR",
        "SEED",
        "SVTR",
        "SVTR_LCNet",
        "ViTSTR",
        "ABINet",
        "VisionLAN",
        "SPIN",
        "RobustScanner",
        "RFL",
    ] = "CRNN"
    """Recognition algorithm."""
    rec_image_shape: str = "3,32,320"
    """Image shape for recognition algorithm in format 'channels,height,width'."""
    rec_model_dir: str | None = None
    """Directory for recognition model. If None, uses default model location."""
    table: bool = True
    """Whether to enable table recognition."""
    use_angle_cls: bool = True
    """DEPRECATED in PaddleOCR 3.2.0+: Use 'use_textline_orientation' instead. Whether to use text orientation classification model."""
    use_gpu: bool = False
    """DEPRECATED in PaddleOCR 3.2.0+: Parameter no longer supported. Use hardware acceleration flags instead."""
    device: DeviceType = "auto"
    """Device to use for inference. Options: 'cpu', 'cuda', 'auto'. Note: MPS not supported by PaddlePaddle."""
    gpu_memory_limit: float | None = None
    """DEPRECATED in PaddleOCR 3.2.0+: Parameter no longer supported. Maximum GPU memory to use in GB."""
    fallback_to_cpu: bool = True
    """Whether to fallback to CPU if requested device is unavailable."""
    use_space_char: bool = True
    """Whether to recognize spaces."""
    use_zero_copy_run: bool = False
    """Whether to enable zero_copy_run for inference optimization."""

    text_det_thresh: float = 0.3
    """Binarization threshold for text detection output map (replaces det_db_thresh)."""
    text_det_box_thresh: float = 0.5
    """Score threshold for detected text boxes (replaces det_db_box_thresh)."""
    text_det_unclip_ratio: float = 2.0
    """Expansion ratio for detected text boxes (replaces det_db_unclip_ratio)."""
    use_textline_orientation: bool = True
    """Whether to use text line orientation classification model (replaces use_angle_cls)."""


@dataclass(unsafe_hash=True, frozen=True, slots=True)
class GMFTConfig(ConfigDict):
    verbosity: int = 0
    """
    Verbosity level for logging.

    0: errors only
    1: print warnings
    2: print warnings and info
    3: print warnings, info, and debug
    """
    formatter_base_threshold: float = 0.3
    """
    Base threshold for the confidence demanded of a table feature (row/column).

    Note that a low threshold is actually better, because overzealous rows means that generally, numbers are still aligned and there are just many empty rows (having fewer rows than expected merges cells, which is bad).
    """
    cell_required_confidence: dict[Literal[0, 1, 2, 3, 4, 5, 6], float] = field(
        default_factory=lambda: {
            0: 0.3,
            1: 0.3,
            2: 0.3,
            3: 0.3,
            4: 0.5,
            5: 0.5,
            6: 99,
        },
        hash=False,
    )
    """
    Confidences required (>=) for a row/column feature to be considered good. See TATRFormattedTable.id2label

    But low confidences may be better than too high confidence (see formatter_base_threshold)
    """
    detector_base_threshold: float = 0.9
    """Minimum confidence score required for a table"""
    remove_null_rows: bool = True
    """
    Flag to remove rows with no text.
    """
    enable_multi_header: bool = False
    """
    Enable multi-indices in the dataframe.

    If false, then multiple headers will be merged column-wise.
    """
    semantic_spanning_cells: bool = False
    """
    [Experimental] Enable semantic spanning cells, which often encode hierarchical multi-level indices.
    """
    semantic_hierarchical_left_fill: Literal["algorithm", "deep"] | None = "algorithm"
    """
    [Experimental] When semantic spanning cells is enabled, when a left header is detected which might represent a group of rows, that same value is reduplicated for each row.

    Possible values: 'algorithm', 'deep', None.
    """
    large_table_if_n_rows_removed: int = 8
    """
    If >= n rows are removed due to non-maxima suppression (NMS), then this table is classified as a large table.
    """
    large_table_threshold: int = 10
    """
    With large tables, table transformer struggles with placing too many overlapping rows. Luckily, with more rows, we have more info on the usual size of text, which we can use to make a guess on the height such that no rows are merged or overlapping.

    Large table assumption is only applied when (# of rows > large_table_threshold) AND (total overlap > large_table_row_overlap_threshold). Set 9999 to disable; set 0 to force large table assumption to run every time.
    """
    large_table_row_overlap_threshold: float = 0.2
    """
    With large tables, table transformer struggles with placing too many overlapping rows. Luckily, with more rows, we have more info on the usual size of text, which we can use to make a guess on the height such that no rows are merged or overlapping.

    Large table assumption is only applied when (# of rows > large_table_threshold) AND (total overlap > large_table_row_overlap_threshold).
    """
    large_table_maximum_rows: int = 1000
    """
    Maximum number of rows allowed for a large table.
    """
    force_large_table_assumption: bool | None = None
    """
    Force the large table assumption to be applied, regardless of the number of rows and overlap.
    """
    total_overlap_reject_threshold: float = 0.9
    """
    Reject if total overlap is > 90% of table area.
    """
    total_overlap_warn_threshold: float = 0.1
    """
    Warn if total overlap is > 10% of table area.
    """
    nms_warn_threshold: int = 5
    """
    Warn if non maxima suppression removes > 5 rows.
    """
    iob_reject_threshold: float = 0.05
    """
    Reject if iob between textbox and cell is < 5%.
    """
    iob_warn_threshold: float = 0.5
    """
    Warn if iob between textbox and cell is < 50%.
    """


@dataclass(unsafe_hash=True, frozen=True, slots=True)
class LanguageDetectionConfig(ConfigDict):
    low_memory: bool = True
    """If True, uses a smaller model (~200MB). If False, uses a larger, more accurate model.
    Defaults to True for better memory efficiency."""
    top_k: int = 3
    """Maximum number of languages to return for multilingual detection."""
    multilingual: bool = False
    """If True, uses multilingual detection to handle mixed-language text.
    If False, uses single language detection."""
    cache_dir: str | None = None
    """Custom directory for model cache. If None, uses system default."""
    allow_fallback: bool = True
    """If True, falls back to small model if large model fails."""


@dataclass(unsafe_hash=True, frozen=True, slots=True)
class SpacyEntityExtractionConfig(ConfigDict):
    model_cache_dir: str | Path | None = None
    """Directory to cache spaCy models. If None, uses spaCy's default."""
    language_models: dict[str, str] | tuple[tuple[str, str], ...] | None = None
    """Mapping of language codes to spaCy model names.

    If None, uses default mappings:
    - en: en_core_web_sm
    - de: de_core_news_sm
    - fr: fr_core_news_sm
    - es: es_core_news_sm
    - pt: pt_core_news_sm
    - it: it_core_news_sm
    - nl: nl_core_news_sm
    - zh: zh_core_web_sm
    - ja: ja_core_news_sm
    """
    fallback_to_multilingual: bool = True
    """If True and language-specific model fails, try xx_ent_wiki_sm (multilingual)."""
    max_doc_length: int = 1000000
    """Maximum document length for spaCy processing."""
    batch_size: int = 1000
    """Batch size for processing multiple texts."""

    def __post_init__(self) -> None:
        if self.language_models is None:
            object.__setattr__(self, "language_models", self._get_default_language_models())

        if isinstance(self.language_models, dict):
            object.__setattr__(self, "language_models", tuple(sorted(self.language_models.items())))

    @staticmethod
    def _get_default_language_models() -> dict[str, str]:
        return {
            "en": "en_core_web_sm",
            "de": "de_core_news_sm",
            "fr": "fr_core_news_sm",
            "es": "es_core_news_sm",
            "pt": "pt_core_news_sm",
            "it": "it_core_news_sm",
            "nl": "nl_core_news_sm",
            "zh": "zh_core_web_sm",
            "ja": "ja_core_news_sm",
            "ko": "ko_core_news_sm",
            "ru": "ru_core_news_sm",
            "pl": "pl_core_news_sm",
            "ro": "ro_core_news_sm",
            "el": "el_core_news_sm",
            "da": "da_core_news_sm",
            "fi": "fi_core_news_sm",
            "nb": "nb_core_news_sm",
            "sv": "sv_core_news_sm",
            "ca": "ca_core_news_sm",
            "hr": "hr_core_news_sm",
            "lt": "lt_core_news_sm",
            "mk": "mk_core_news_sm",
            "sl": "sl_core_news_sm",
            "uk": "uk_core_news_sm",
            "xx": "xx_ent_wiki_sm",
        }

    def get_model_for_language(self, language_code: str) -> str | None:
        if not self.language_models:
            return None

        models_dict = dict(self.language_models) if isinstance(self.language_models, tuple) else self.language_models

        if language_code in models_dict:
            return models_dict[language_code]

        base_lang = language_code.split("-")[0].lower()
        if base_lang in models_dict:
            return models_dict[base_lang]

        return None

    def get_fallback_model(self) -> str | None:
        return "xx_ent_wiki_sm" if self.fallback_to_multilingual else None


class BoundingBox(TypedDict):
    left: int
    """X coordinate of the left edge."""
    top: int
    """Y coordinate of the top edge."""
    width: int
    """Width of the bounding box."""
    height: int
    """Height of the bounding box."""


class TSVWord(TypedDict):
    level: int
    """Hierarchy level (1=page, 2=block, 3=para, 4=line, 5=word)."""
    page_num: int
    """Page number."""
    block_num: int
    """Block number within the page."""
    par_num: int
    """Paragraph number within the block."""
    line_num: int
    """Line number within the paragraph."""
    word_num: int
    """Word number within the line."""
    left: int
    """X coordinate of the left edge of the word."""
    top: int
    """Y coordinate of the top edge of the word."""
    width: int
    """Width of the word bounding box."""
    height: int
    """Height of the word bounding box."""
    conf: float
    """Confidence score (0-100)."""
    text: str
    """The recognized text content."""


class TableCell(TypedDict):
    row: int
    """Row index (0-based)."""
    col: int
    """Column index (0-based)."""
    text: str
    """Cell text content."""
    bbox: BoundingBox
    """Bounding box of the cell."""
    confidence: float
    """Average confidence of words in the cell."""


class TableData(TypedDict):
    cropped_image: Image
    """The cropped image of the table."""
    df: DataFrame | None
    """The table data as a polars DataFrame."""
    page_number: int
    """The page number of the table."""
    text: str
    """The table text as a markdown string."""


class ImagePreprocessingMetadata(NamedTuple):
    """Metadata about image preprocessing operations for OCR."""

    original_dimensions: tuple[int, int]
    """Original image dimensions (width, height) in pixels."""
    original_dpi: tuple[float, float]
    """Original image DPI (horizontal, vertical)."""
    target_dpi: int
    """Target DPI that was requested."""
    scale_factor: float
    """Scale factor applied to the image."""
    auto_adjusted: bool
    """Whether DPI was automatically adjusted due to size constraints."""
    final_dpi: int | None = None
    """Final DPI used after processing."""
    new_dimensions: tuple[int, int] | None = None
    """New image dimensions after processing (width, height) in pixels."""
    resample_method: str | None = None
    """Resampling method used (LANCZOS, BICUBIC, etc.)."""
    skipped_resize: bool = False
    """Whether resizing was skipped (no change needed)."""
    dimension_clamped: bool = False
    """Whether image was clamped to maximum dimension constraints."""
    calculated_dpi: int | None = None
    """DPI calculated during auto-adjustment."""
    resize_error: str | None = None
    """Error message if resizing failed."""


class Metadata(TypedDict, total=False):
    authors: NotRequired[list[str]]
    """List of document authors."""
    categories: NotRequired[list[str]]
    """Categories or classifications."""
    citations: NotRequired[list[str]]
    """Citation identifiers."""
    comments: NotRequired[str]
    """General comments."""
    copyright: NotRequired[str]
    """Copyright information."""
    created_at: NotRequired[str]
    """Creation timestamp in ISO format."""
    created_by: NotRequired[str]
    """Document creator."""
    description: NotRequired[str]
    """Document description."""
    fonts: NotRequired[list[str]]
    """List of fonts used in the document."""
    height: NotRequired[int]
    """Height of the document page/slide/image, if applicable."""
    identifier: NotRequired[str]
    """Unique document identifier."""
    keywords: NotRequired[list[str]]
    """Keywords or tags."""
    languages: NotRequired[list[str]]
    """Document language code."""
    license: NotRequired[str]
    """License information."""
    modified_at: NotRequired[str]
    """Last modification timestamp in ISO format."""
    modified_by: NotRequired[str]
    """Username of last modifier."""
    organization: NotRequired[str | list[str]]
    """Organizational affiliation."""
    publisher: NotRequired[str]
    """Publisher or organization name."""
    references: NotRequired[list[str]]
    """Reference entries."""
    status: NotRequired[str]
    """Document status (e.g., draft, final)."""
    subject: NotRequired[str]
    """Document subject or topic."""
    subtitle: NotRequired[str]
    """Document subtitle."""
    summary: NotRequired[str]
    """Document Summary"""
    title: NotRequired[str]
    """Document title."""
    version: NotRequired[str]
    """Version identifier or revision number."""
    width: NotRequired[int]
    """Width of the document page/slide/image, if applicable."""
    email_from: NotRequired[str]
    """Email sender (from field)."""
    email_to: NotRequired[str]
    """Email recipient (to field)."""
    email_cc: NotRequired[str]
    """Email carbon copy recipients."""
    email_bcc: NotRequired[str]
    """Email blind carbon copy recipients."""
    date: NotRequired[str]
    """Email date or document date."""
    attachments: NotRequired[list[str]]
    """List of attachment names."""
    content: NotRequired[str]
    """Content metadata field."""
    parse_error: NotRequired[str]
    """Parse error information."""
    warning: NotRequired[str]
    """Warning messages."""
    table_count: NotRequired[int]
    """Number of tables extracted from the document."""
    tables_detected: NotRequired[int]
    """Number of tables detected in the document."""
    tables_summary: NotRequired[str]
    """Summary of table extraction results."""
    quality_score: NotRequired[float]
    """Quality score for extracted content (0.0-1.0)."""
    image_preprocessing: NotRequired[ImagePreprocessingMetadata]
    """Metadata about image preprocessing operations (DPI adjustments, scaling, etc.)."""
    source_format: NotRequired[str]
    """Source format of the extracted content."""
    error: NotRequired[str]
    """Error message if extraction failed."""


_VALID_METADATA_KEYS = {
    "authors",
    "categories",
    "citations",
    "comments",
    "content",
    "copyright",
    "created_at",
    "created_by",
    "description",
    "fonts",
    "height",
    "identifier",
    "keywords",
    "languages",
    "license",
    "modified_at",
    "modified_by",
    "organization",
    "parse_error",
    "publisher",
    "references",
    "status",
    "subject",
    "subtitle",
    "summary",
    "title",
    "version",
    "warning",
    "width",
    "email_from",
    "email_to",
    "email_cc",
    "email_bcc",
    "date",
    "attachments",
    "table_count",
    "tables_summary",
    "quality_score",
    "image_preprocessing",
}


def normalize_metadata(data: dict[str, Any] | None) -> Metadata:
    if not data:
        return {}

    normalized: Metadata = {}
    for key, value in data.items():
        if key in _VALID_METADATA_KEYS and value is not None:
            normalized[key] = value  # type: ignore[literal-required]

    return normalized


@dataclass(frozen=True, slots=True)
class Entity:
    type: str
    """e.g., PERSON, ORGANIZATION, LOCATION, DATE, EMAIL, PHONE, or custom"""
    text: str
    """Extracted text"""
    start: int
    """Start character offset in the content"""
    end: int
    """End character offset in the content"""


@dataclass(slots=True)
class ExtractionResult:
    content: str
    """The extracted content."""
    mime_type: str
    """The mime type of the extracted content. Is either text/plain or text/markdown."""
    metadata: Metadata
    """The metadata of the content."""
    tables: list[TableData] = field(default_factory=list)
    """Extracted tables. Is an empty list if 'extract_tables' is not set to True in the ExtractionConfig."""
    chunks: list[str] = field(default_factory=list)
    """The extracted content chunks. This is an empty list if 'chunk_content' is not set to True in the ExtractionConfig."""
    entities: list[Entity] | None = None
    """Extracted entities, if entity extraction is enabled."""
    keywords: list[tuple[str, float]] | None = None
    """Extracted keywords and their scores, if keyword extraction is enabled."""
    detected_languages: list[str] | None = None
    """Languages detected in the extracted content, if language detection is enabled."""
    document_type: str | None = None
    """Detected document type, if document type detection is enabled."""
    document_type_confidence: float | None = None
    """Confidence of the detected document type."""
    layout: DataFrame | None = field(default=None, repr=False, hash=False)
    """Internal layout data from OCR, not for public use."""

    def to_dict(self, include_none: bool = False) -> dict[str, Any]:
        result = msgspec.to_builtins(
            self,
            builtin_types=(type(None),),
            order="deterministic",
        )

        if include_none:
            return result  # type: ignore[no-any-return]

        return {k: v for k, v in result.items() if v is not None}

    def export_tables_to_csv(self) -> list[str]:
        if not self.tables:  # pragma: no cover
            return []

        return [export_table_to_csv(table) for table in self.tables]

    def export_tables_to_tsv(self) -> list[str]:
        if not self.tables:  # pragma: no cover
            return []

        return [export_table_to_tsv(table) for table in self.tables]

    def get_table_summaries(self) -> list[dict[str, Any]]:
        if not self.tables:  # pragma: no cover
            return []

        return [extract_table_structure_info(table) for table in self.tables]


PostProcessingHook = Callable[[ExtractionResult], ExtractionResult | Awaitable[ExtractionResult]]
ValidationHook = Callable[[ExtractionResult], None | Awaitable[None]]


@dataclass(unsafe_hash=True, frozen=True, slots=True)
class ExtractionConfig(ConfigDict):
    force_ocr: bool = False
    """Whether to force OCR."""
    chunk_content: bool = False
    """Whether to chunk the content into smaller chunks."""
    extract_tables: bool = False
    """Whether to extract tables from the content. This requires the 'gmft' dependency."""
    extract_tables_from_ocr: bool = False
    """Extract tables from OCR output using TSV format (Tesseract only)."""
    max_chars: int = DEFAULT_MAX_CHARACTERS
    """The size of each chunk in characters."""
    max_overlap: int = DEFAULT_MAX_OVERLAP
    """The overlap between chunks in characters."""
    ocr_backend: OcrBackendType | None = "tesseract"
    """The OCR backend to use.

    Notes:
        - If set to 'None', OCR will not be performed.
    """
    ocr_config: TesseractConfig | PaddleOCRConfig | EasyOCRConfig | None = None
    """Configuration to pass to the OCR backend."""
    gmft_config: GMFTConfig | None = None
    """GMFT configuration."""
    post_processing_hooks: list[PostProcessingHook] | None = None
    """Post processing hooks to call after processing is done and before the final result is returned."""
    validators: list[ValidationHook] | None = None
    """Validation hooks to call after processing is done and before post-processing and result return."""
    extract_entities: bool = False
    """Whether to extract named entities from the content."""
    extract_keywords: bool = False
    """Whether to extract keywords from the content."""
    keyword_count: int = 10
    """Number of keywords to extract if extract_keywords is True."""
    custom_entity_patterns: frozenset[tuple[str, str]] | None = None
    """Custom entity patterns as a frozenset of (entity_type, regex_pattern) tuples."""
    auto_detect_language: bool = False
    """Whether to automatically detect language and configure OCR accordingly."""
    language_detection_config: LanguageDetectionConfig | None = None
    """Configuration for language detection. If None, uses default settings."""
    spacy_entity_extraction_config: SpacyEntityExtractionConfig | None = None
    """Configuration for spaCy entity extraction. If None, uses default settings."""
    auto_detect_document_type: bool = False
    """Whether to automatically detect the document type."""
    document_type_confidence_threshold: float = 0.5
    """Confidence threshold for document type detection."""
    document_classification_mode: Literal["text", "vision"] = "text"
    """The mode to use for document classification."""
    enable_quality_processing: bool = True
    """Whether to apply quality post-processing to improve extraction results."""
    pdf_password: str | list[str] = ""
    """Password(s) for encrypted PDF files. Can be a single password or list of passwords to try in sequence. Only used when crypto extra is installed."""
    html_to_markdown_config: HTMLToMarkdownConfig | None = None
    """Configuration for HTML to Markdown conversion. If None, uses default settings."""
    use_cache: bool = True
    """Whether to use caching for extraction results. Set to False to disable all caching."""
    target_dpi: int = 150
    """Target DPI for OCR processing. Images and PDF pages will be scaled to this DPI for optimal OCR results."""
    max_image_dimension: int = 25000
    """Maximum allowed pixel dimension (width or height) for processed images to prevent memory issues."""
    auto_adjust_dpi: bool = True
    """Whether to automatically adjust DPI based on image dimensions to stay within max_image_dimension limits."""
    min_dpi: int = 72
    """Minimum DPI threshold when auto-adjusting DPI."""
    max_dpi: int = 600
    """Maximum DPI threshold when auto-adjusting DPI."""

    def __post_init__(self) -> None:
        if self.custom_entity_patterns is not None and isinstance(self.custom_entity_patterns, dict):
            object.__setattr__(self, "custom_entity_patterns", frozenset(self.custom_entity_patterns.items()))
        if self.post_processing_hooks is not None and isinstance(self.post_processing_hooks, list):
            object.__setattr__(self, "post_processing_hooks", tuple(self.post_processing_hooks))
        if self.validators is not None and isinstance(self.validators, list):
            object.__setattr__(self, "validators", tuple(self.validators))

        if self.ocr_backend is None and self.ocr_config is not None:
            raise ValidationError("'ocr_backend' is None but 'ocr_config' is provided")

        if self.ocr_config is not None and (
            (self.ocr_backend == "tesseract" and not isinstance(self.ocr_config, TesseractConfig))
            or (self.ocr_backend == "easyocr" and not isinstance(self.ocr_config, EasyOCRConfig))
            or (self.ocr_backend == "paddleocr" and not isinstance(self.ocr_config, PaddleOCRConfig))
        ):
            raise ValidationError(
                "incompatible 'ocr_config' value provided for 'ocr_backend'",
                context={"ocr_backend": self.ocr_backend, "ocr_config": type(self.ocr_config).__name__},
            )

        # Validate DPI configuration
        if self.target_dpi <= 0:
            raise ValidationError("target_dpi must be positive", context={"target_dpi": self.target_dpi})
        if self.min_dpi <= 0:
            raise ValidationError("min_dpi must be positive", context={"min_dpi": self.min_dpi})
        if self.max_dpi <= 0:
            raise ValidationError("max_dpi must be positive", context={"max_dpi": self.max_dpi})
        if self.min_dpi >= self.max_dpi:
            raise ValidationError(
                "min_dpi must be less than max_dpi", context={"min_dpi": self.min_dpi, "max_dpi": self.max_dpi}
            )
        if self.max_image_dimension <= 0:
            raise ValidationError(
                "max_image_dimension must be positive", context={"max_image_dimension": self.max_image_dimension}
            )
        if not (self.min_dpi <= self.target_dpi <= self.max_dpi):
            raise ValidationError(
                "target_dpi must be between min_dpi and max_dpi",
                context={"target_dpi": self.target_dpi, "min_dpi": self.min_dpi, "max_dpi": self.max_dpi},
            )

    def get_config_dict(self) -> dict[str, Any]:
        if self.ocr_backend is None:
            return {"use_cache": self.use_cache}

        if self.ocr_config is not None:
            config_dict = asdict(self.ocr_config)
            config_dict["use_cache"] = self.use_cache
            return config_dict

        match self.ocr_backend:
            case "tesseract":
                config_dict = asdict(TesseractConfig())
                config_dict["use_cache"] = self.use_cache
                return config_dict
            case "easyocr":
                config_dict = asdict(EasyOCRConfig())
                config_dict["use_cache"] = self.use_cache
                return config_dict
            case _:
                config_dict = asdict(PaddleOCRConfig())
                config_dict["use_cache"] = self.use_cache
                return config_dict

    def to_dict(self, include_none: bool = False) -> dict[str, Any]:
        result = msgspec.to_builtins(
            self,
            builtin_types=(type(None),),
            order="deterministic",
        )

        for field_name, value in result.items():
            if hasattr(value, "to_dict"):
                result[field_name] = value.to_dict(include_none=include_none)

        if include_none:
            return result  # type: ignore[no-any-return]

        return {k: v for k, v in result.items() if v is not None}


@dataclass(frozen=True)
class HTMLToMarkdownConfig:
    stream_processing: bool = False
    """Enable streaming mode for processing large HTML documents."""
    chunk_size: int = 1024
    """Size of chunks when stream_processing is enabled."""
    chunk_callback: Callable[[str], None] | None = None
    """Callback function invoked for each chunk during stream processing."""
    progress_callback: Callable[[int, int], None] | None = None
    """Callback function for progress updates (current, total)."""
    parser: str | None = "lxml"
    """BeautifulSoup parser to use. Defaults to 'lxml' for ~30% better performance. Falls back to 'html.parser' if lxml not available."""
    autolinks: bool = True
    """Convert URLs to clickable links automatically."""
    bullets: str = "*+-"
    """Characters to use for unordered list bullets."""
    code_language: str = ""
    """Default language for code blocks."""
    code_language_callback: Callable[[Any], str] | None = None
    """Callback to determine code language dynamically."""
    convert: str | Iterable[str] | None = None
    """HTML tags to convert. If None, all supported tags are converted."""
    convert_as_inline: bool = False
    """Convert block elements as inline elements."""
    custom_converters: Mapping[Any, Any] | None = None
    """Custom converters for specific HTML elements."""
    default_title: bool = False
    """Use a default title if none is found."""
    escape_asterisks: bool = True
    """Escape asterisks in text to prevent unintended emphasis."""
    escape_misc: bool = True
    """Escape miscellaneous characters that have special meaning in Markdown."""
    escape_underscores: bool = True
    """Escape underscores in text to prevent unintended emphasis."""
    extract_metadata: bool = True
    """Extract metadata from HTML head section."""
    heading_style: Literal["underlined", "atx", "atx_closed"] = "underlined"
    """Style for markdown headings."""
    highlight_style: Literal["double-equal", "html", "bold"] = "double-equal"
    """Style for highlighting text."""
    keep_inline_images_in: Iterable[str] | None = None
    """HTML tags where inline images should be preserved."""
    newline_style: Literal["spaces", "backslash"] = "spaces"
    """Style for line breaks in markdown."""
    strip: str | Iterable[str] | None = None
    """HTML tags to strip completely from output."""
    strip_newlines: bool = False
    """Strip newlines from the output."""
    strong_em_symbol: Literal["*", "_"] = "*"
    """Symbol to use for strong/emphasis formatting."""
    sub_symbol: str = ""
    """Symbol to use for subscript text."""
    sup_symbol: str = ""
    """Symbol to use for superscript text."""
    wrap: bool = False
    """Enable text wrapping."""
    wrap_width: int = 80
    """Width for text wrapping when wrap is True."""
    preprocess_html: bool = True
    """Enable HTML preprocessing to clean up the input."""
    preprocessing_preset: Literal["minimal", "standard", "aggressive"] = "aggressive"
    """Preprocessing level for cleaning HTML."""
    remove_navigation: bool = True
    """Remove navigation elements from HTML."""
    remove_forms: bool = True
    """Remove form elements from HTML."""

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if value is not None}
