"""Comprehensive class attribute documentation for Kreuzberg configuration classes.

This module applies detailed docstrings to configuration classes imported from
_internal_bindings, documenting all attributes with types, defaults, and descriptions.

The docstrings are applied dynamically to classes after import to provide better
IDE support and help() output for users.
"""

from __future__ import annotations

from kreuzberg._internal_bindings import (
    ChunkingConfig,
    EmbeddingConfig,
    EmbeddingModelType,
    EmbeddingPreset,
    ExtractionConfig,
    ImageExtractionConfig,
    ImagePreprocessingConfig,
    LanguageDetectionConfig,
    OcrConfig,
    PdfConfig,
    PostProcessorConfig,
    TesseractConfig,
    TokenReductionConfig,
)


def apply_docstrings() -> None:
    """Apply comprehensive docstrings to all configuration classes.

    This function enriches the configuration classes with detailed documentation
    for all attributes, including types, defaults, and usage guidance.

    Call this after importing configuration classes to enable enhanced IDE support
    and detailed help() output.
    """
    _document_extraction_config()
    _document_ocr_config()
    _document_chunking_config()
    _document_embedding_config()
    _document_embedding_model_type()
    _document_embedding_preset()
    _document_image_extraction_config()
    _document_image_preprocessing_config()
    _document_pdf_config()
    _document_token_reduction_config()
    _document_language_detection_config()
    _document_post_processor_config()
    _document_tesseract_config()


def _document_extraction_config() -> None:
    """Document ExtractionConfig class attributes."""
    ExtractionConfig.__doc__ = """Main extraction configuration for document processing.

    This class contains all configuration options for the extraction process.
    All attributes are optional and use sensible defaults when not specified.

    Attributes:
        use_cache (bool): Enable caching of extraction results to improve performance
            on repeated extractions. Default: True

        enable_quality_processing (bool): Enable quality post-processing to clean
            and normalize extracted text. Default: True

        ocr (OcrConfig | None): OCR configuration for extracting text from images
            and scanned documents. None = OCR disabled. Default: None

        force_ocr (bool): Force OCR processing even for searchable PDFs that contain
            extractable text. Useful for ensuring consistent formatting. Default: False

        chunking (ChunkingConfig | None): Text chunking configuration for dividing
            content into manageable chunks. None = chunking disabled. Default: None

        images (ImageExtractionConfig | None): Image extraction configuration for
            extracting images FROM documents (not for OCR preprocessing).
            None = no image extraction. Default: None

        pdf_options (PdfConfig | None): PDF-specific options like password handling
            and metadata extraction. None = use defaults. Default: None

        token_reduction (TokenReductionConfig | None): Token reduction configuration
            for reducing token count in extracted content (useful for LLM APIs).
            None = no token reduction. Default: None

        language_detection (LanguageDetectionConfig | None): Language detection
            configuration for identifying the language(s) in documents.
            None = no language detection. Default: None

        pages (PageConfig | None): Page extraction configuration for tracking and
            extracting page boundaries. None = no page tracking. Default: None

        keywords (KeywordConfig | None): Keyword extraction configuration for
            identifying important terms and phrases in content.
            None = no keyword extraction. Default: None

        postprocessor (PostProcessorConfig | None): Post-processor configuration
            for custom text processing. None = use defaults. Default: None

        max_concurrent_extractions (int | None): Maximum concurrent extractions
            in batch operations. None = num_cpus * 2. Default: None

        html_options (dict[str, Any] | None): HTML conversion options for
            converting documents to markdown. Default: None

    Example:
        Basic extraction with defaults:
            >>> from kreuzberg import ExtractionConfig, extract_file_sync
            >>> config = ExtractionConfig()
            >>> result = extract_file_sync("document.pdf", config=config)

        Enable chunking with 512-char chunks and 100-char overlap:
            >>> from kreuzberg import ExtractionConfig, ChunkingConfig
            >>> config = ExtractionConfig(
            ...     chunking=ChunkingConfig(max_chars=512, max_overlap=100)
            ... )

        Enable OCR with Tesseract for non-searchable PDFs:
            >>> from kreuzberg import ExtractionConfig, OcrConfig, TesseractConfig
            >>> config = ExtractionConfig(
            ...     ocr=OcrConfig(
            ...         backend="tesseract",
            ...         language="eng",
            ...         tesseract_config=TesseractConfig(psm=6)
            ...     )
            ... )
    """


def _document_ocr_config() -> None:
    """Document OcrConfig class attributes."""
    OcrConfig.__doc__ = """OCR configuration for extracting text from images.

    Attributes:
        backend (str): OCR backend to use. Options: "tesseract", "easyocr", "paddleocr".
            Default: "tesseract"

        language (str): Language code (ISO 639-3 three-letter code or ISO 639-1
            two-letter code). Examples: "eng", "deu", "fra", "en", "de", "fr".
            Default: "eng"

        tesseract_config (TesseractConfig | None): Tesseract-specific configuration
            for fine-tuning OCR behavior. Only used when backend="tesseract".
            Default: None

    Example:
        Using Tesseract with German language:
            >>> from kreuzberg import OcrConfig
            >>> config = OcrConfig(backend="tesseract", language="deu")

        Using EasyOCR for faster recognition:
            >>> config = OcrConfig(backend="easyocr", language="eng")

        Using PaddleOCR for production deployments:
            >>> config = OcrConfig(backend="paddleocr", language="chi_sim")
    """


def _document_chunking_config() -> None:
    """Document ChunkingConfig class attributes."""
    ChunkingConfig.__doc__ = """Text chunking configuration for dividing content into chunks.

    Chunking is useful for preparing content for embedding, indexing, or processing
    with length-limited systems (like LLM context windows).

    Attributes:
        max_chars (int): Maximum number of characters per chunk. Chunks larger than
            this will be split intelligently at sentence/paragraph boundaries.
            Default: 1000

        max_overlap (int): Overlap between consecutive chunks in characters. Creates
            context bridges between chunks for smoother processing.
            Default: 200

        embedding (EmbeddingConfig | None): Configuration for generating embeddings
            for each chunk using ONNX models. None = no embeddings. Default: None

        preset (str | None): Use a preset chunking configuration (overrides individual
            settings if provided). Use list_embedding_presets() to see available presets.
            Default: None

    Example:
        Basic chunking with defaults:
            >>> from kreuzberg import ExtractionConfig, ChunkingConfig
            >>> config = ExtractionConfig(
            ...     chunking=ChunkingConfig()
            ... )

        Custom chunk size with overlap:
            >>> config = ExtractionConfig(
            ...     chunking=ChunkingConfig(max_chars=512, max_overlap=100)
            ... )

        Chunking with embeddings:
            >>> from kreuzberg import EmbeddingConfig, EmbeddingModelType
            >>> config = ExtractionConfig(
            ...     chunking=ChunkingConfig(
            ...         max_chars=512,
            ...         embedding=EmbeddingConfig(
            ...             model=EmbeddingModelType.preset("balanced")
            ...         )
            ...     )
            ... )

        Using preset configuration:
            >>> config = ExtractionConfig(
            ...     chunking=ChunkingConfig(preset="semantic")
            ... )
    """


def _document_embedding_config() -> None:
    """Document EmbeddingConfig class attributes."""
    EmbeddingConfig.__doc__ = """Embedding generation configuration for text chunks.

    Configures embedding generation using ONNX models via fastembed-rs.
    Embeddings are useful for semantic search, clustering, and similarity operations.

    Requires the embeddings feature to be enabled in the Rust core.

    Attributes:
        model (EmbeddingModelType): The embedding model to use. Can be a preset
            (recommended), specific fastembed model, or custom ONNX model.
            Default: Preset "balanced"

        normalize (bool): Whether to normalize embedding vectors to unit length.
            Recommended for cosine similarity calculations. Default: True

        batch_size (int): Number of texts to process simultaneously. Higher values
            use more memory but may be faster. Default: 32

        show_download_progress (bool): Display progress during embedding model
            download. Useful for large models on slow connections. Default: False

        cache_dir (str | None): Custom directory for caching downloaded models.
            Defaults to ~/.cache/kreuzberg/embeddings/ if not specified.
            Default: None

    Example:
        Basic preset embedding (recommended):
            >>> from kreuzberg import EmbeddingConfig, EmbeddingModelType
            >>> config = EmbeddingConfig()

        Specific preset with settings:
            >>> from kreuzberg import EmbeddingConfig, EmbeddingModelType
            >>> config = EmbeddingConfig(
            ...     model=EmbeddingModelType.preset("balanced"),
            ...     normalize=True,
            ...     batch_size=64
            ... )

        Custom ONNX model:
            >>> config = EmbeddingConfig(
            ...     model=EmbeddingModelType.custom(
            ...         model_id="sentence-transformers/all-MiniLM-L6-v2",
            ...         dimensions=384
            ...     )
            ... )

        With custom cache directory:
            >>> config = EmbeddingConfig(
            ...     cache_dir="/path/to/model/cache"
            ... )
    """


def _document_embedding_model_type() -> None:
    """Document EmbeddingModelType class and static methods."""
    EmbeddingModelType.__doc__ = """Embedding model type selector with multiple configurations.

    Choose from preset configurations (recommended), specific fastembed models,
    or custom ONNX models for different embedding tasks.

    Static Methods:
        preset(name: str) -> EmbeddingModelType: Use a preset configuration.
            Recommended for most use cases. Available presets: balanced, compact,
            large. Call list_embedding_presets() to see all available presets.

        fastembed(model: str, dimensions: int) -> EmbeddingModelType: Use a specific
            fastembed model by name. Requires embeddings feature.

        custom(model_id: str, dimensions: int) -> EmbeddingModelType: Use a custom
            ONNX model from HuggingFace (e.g., sentence-transformers/*).

    Example:
        Using the balanced preset (recommended for general use):
            >>> from kreuzberg import EmbeddingModelType
            >>> model = EmbeddingModelType.preset("balanced")

        Using a specific fast embedding model:
            >>> model = EmbeddingModelType.fastembed(
            ...     model="BAAI/bge-small-en-v1.5",
            ...     dimensions=384
            ... )

        Using a custom HuggingFace model:
            >>> model = EmbeddingModelType.custom(
            ...     model_id="sentence-transformers/all-MiniLM-L6-v2",
            ...     dimensions=384
            ... )

        Listing available presets:
            >>> from kreuzberg import list_embedding_presets
            >>> presets = list_embedding_presets()
            >>> print(f"Available presets: {presets}")
    """


def _document_embedding_preset() -> None:
    """Document EmbeddingPreset class attributes."""
    EmbeddingPreset.__doc__ = """Embedding preset configuration metadata.

    Provides information about a predefined embedding configuration, including
    recommended chunking parameters and model details.

    Attributes:
        name (str): Preset name (e.g., "balanced", "compact", "large")

        chunk_size (int): Recommended chunk size in characters for this preset.
            Optimized for the underlying model's strengths.

        overlap (int): Recommended chunk overlap in characters.

        model_name (str): Name of the underlying embedding model used.

        dimensions (int): Vector dimensions produced by the model.

        description (str): Human-readable description of the preset and its use cases.

    Example:
        List all available embedding presets:
            >>> from kreuzberg import list_embedding_presets, get_embedding_preset
            >>> presets = list_embedding_presets()
            >>> for preset_name in presets:
            ...     preset = get_embedding_preset(preset_name)
            ...     print(f"{preset.name}: {preset.description}")
            ...     print(f"  Dimensions: {preset.dimensions}")
            ...     print(f"  Chunk size: {preset.chunk_size}")

        Get a specific preset:
            >>> balanced = get_embedding_preset("balanced")
            >>> print(f"Model: {balanced.model_name}")
            >>> print(f"Dimensions: {balanced.dimensions}")
    """


def _document_image_extraction_config() -> None:
    """Document ImageExtractionConfig class attributes."""
    ImageExtractionConfig.__doc__ = """Configuration for extracting images FROM documents.

    This configuration controls image extraction from documents like PDFs and
    presentations. It is NOT for preprocessing images before OCR.
    (See ImagePreprocessingConfig for OCR preprocessing.)

    Attributes:
        extract_images (bool): Enable image extraction from documents.
            Default: True

        target_dpi (int): Target DPI for image normalization. Images are resampled
            to this DPI for consistency. Default: 300

        max_image_dimension (int): Maximum width or height for extracted images.
            Larger images are downscaled to fit. Default: 4096

        auto_adjust_dpi (bool): Automatically adjust DPI based on image content
            quality. May override target_dpi for better results. Default: True

        min_dpi (int): Minimum DPI threshold. Images with lower DPI are upscaled.
            Default: 72

        max_dpi (int): Maximum DPI threshold. Images with higher DPI are downscaled.
            Default: 600

    Example:
        Basic image extraction:
            >>> from kreuzberg import ExtractionConfig, ImageExtractionConfig
            >>> config = ExtractionConfig(
            ...     images=ImageExtractionConfig()
            ... )

        Extract images with custom DPI settings:
            >>> config = ExtractionConfig(
            ...     images=ImageExtractionConfig(
            ...         target_dpi=150,
            ...         max_image_dimension=2048,
            ...         auto_adjust_dpi=False
            ...     )
            ... )

        Note: For OCR image preprocessing (not image extraction from documents):
            >>> from kreuzberg import TesseractConfig, ImagePreprocessingConfig
            >>> config = TesseractConfig(
            ...     preprocessing=ImagePreprocessingConfig(
            ...         target_dpi=300,
            ...         denoise=True
            ...     )
            ... )
    """


def _document_image_preprocessing_config() -> None:
    """Document ImagePreprocessingConfig class attributes."""
    ImagePreprocessingConfig.__doc__ = """Configuration for preprocessing images before OCR.

    This configuration controls image preprocessing for OCR operations. It is NOT for
    extracting images from documents. (See ImageExtractionConfig for image extraction.)

    Attributes:
        target_dpi (int): Target DPI for image normalization before OCR.
            Default: 300

        auto_rotate (bool): Automatically detect and correct image rotation.
            Default: False

        deskew (bool): Correct skewed images to improve OCR accuracy.
            Default: False

        denoise (bool): Apply denoising filters to reduce noise in images.
            Improves OCR accuracy on low-quality scans. Default: False

        contrast_enhance (bool): Enhance contrast to improve text readability.
            Default: False

        binarization_method (str): Method for converting images to black and white.
            Options depend on the OCR backend. Default: "auto"

        invert_colors (bool): Invert colors (white text on black background).
            Useful for certain document types. Default: False

    Example:
        Basic preprocessing for OCR:
            >>> from kreuzberg import TesseractConfig, ImagePreprocessingConfig
            >>> config = TesseractConfig(
            ...     preprocessing=ImagePreprocessingConfig()
            ... )

        Aggressive preprocessing for low-quality scans:
            >>> config = TesseractConfig(
            ...     preprocessing=ImagePreprocessingConfig(
            ...         target_dpi=300,
            ...         denoise=True,
            ...         contrast_enhance=True,
            ...         auto_rotate=True,
            ...         deskew=True
            ...     )
            ... )
    """


def _document_pdf_config() -> None:
    """Document PdfConfig class attributes."""
    PdfConfig.__doc__ = """PDF-specific extraction configuration.

    Attributes:
        extract_images (bool): Extract images from PDF documents.
            Default: False

        passwords (list[str] | None): List of passwords to try when opening
            encrypted PDFs. Try each password in order until one succeeds.
            Default: None

        extract_metadata (bool): Extract PDF metadata (title, author, creation date,
            etc.). Default: True

    Example:
        Basic PDF configuration:
            >>> from kreuzberg import ExtractionConfig, PdfConfig
            >>> config = ExtractionConfig(
            ...     pdf_options=PdfConfig()
            ... )

        Extract metadata and images from PDF:
            >>> config = ExtractionConfig(
            ...     pdf_options=PdfConfig(
            ...         extract_images=True,
            ...         extract_metadata=True
            ...     )
            ... )

        Handle encrypted PDFs:
            >>> config = ExtractionConfig(
            ...     pdf_options=PdfConfig(
            ...         passwords=["password123", "fallback_password"]
            ...     )
            ... )
    """


def _document_token_reduction_config() -> None:
    """Document TokenReductionConfig class attributes."""
    TokenReductionConfig.__doc__ = """Configuration for reducing token count in extracted content.

    Reduces token count to lower costs when working with LLM APIs. Higher modes
    are more aggressive but may lose more information.

    Attributes:
        mode (str): Token reduction mode. Options: "off", "light", "moderate",
            "aggressive", "maximum". Default: "off"
            - "off": No token reduction
            - "light": Remove extra whitespace and redundant punctuation
            - "moderate": Also remove common filler words and some formatting
            - "aggressive": Also remove longer stopwords and collapse similar phrases
            - "maximum": Maximum reduction while preserving semantic content

        preserve_important_words (bool): Preserve capitalized words, technical terms,
            and proper nouns even in aggressive reduction modes. Default: True

    Example:
        Moderate token reduction:
            >>> from kreuzberg import ExtractionConfig, TokenReductionConfig
            >>> config = ExtractionConfig(
            ...     token_reduction=TokenReductionConfig(
            ...         mode="moderate",
            ...         preserve_important_words=True
            ...     )
            ... )

        Maximum reduction for large batches:
            >>> config = ExtractionConfig(
            ...     token_reduction=TokenReductionConfig(
            ...         mode="maximum",
            ...         preserve_important_words=True
            ...     )
            ... )

        No reduction (default):
            >>> config = ExtractionConfig(
            ...     token_reduction=TokenReductionConfig(mode="off")
            ... )
    """


def _document_language_detection_config() -> None:
    """Document LanguageDetectionConfig class attributes."""
    LanguageDetectionConfig.__doc__ = """Configuration for detecting document language(s).

    Attributes:
        enabled (bool): Enable language detection for extracted content.
            Default: True

        min_confidence (float): Minimum confidence threshold (0.0-1.0) for language
            detection. Results below this threshold are discarded. Default: 0.8

        detect_multiple (bool): Detect multiple languages in the document. When False,
            only the most confident language is returned. Default: False

    Example:
        Basic language detection:
            >>> from kreuzberg import ExtractionConfig, LanguageDetectionConfig
            >>> config = ExtractionConfig(
            ...     language_detection=LanguageDetectionConfig()
            ... )

        Detect multiple languages with lower confidence threshold:
            >>> config = ExtractionConfig(
            ...     language_detection=LanguageDetectionConfig(
            ...         detect_multiple=True,
            ...         min_confidence=0.6
            ...     )
            ... )

        Access detected languages in result:
            >>> from kreuzberg import extract_file_sync
            >>> result = extract_file_sync("multilingual.pdf", config=config)
            >>> print(f"Languages: {result.detected_languages}")
    """


def _document_post_processor_config() -> None:
    """Document PostProcessorConfig class attributes."""
    PostProcessorConfig.__doc__ = """Configuration for post-processors in the extraction pipeline.

    Post-processors allow custom text processing after extraction. They can be used
    to normalize text, fix formatting issues, or apply domain-specific transformations.

    Attributes:
        enabled (bool): Enable post-processors in the extraction pipeline.
            Default: True

        enabled_processors (list[str] | None): Whitelist of processor names to run.
            If specified, only these processors are executed. None = run all enabled.
            Default: None

        disabled_processors (list[str] | None): Blacklist of processor names to skip.
            If specified, these processors are not executed. None = none disabled.
            Default: None

    Example:
        Basic post-processing with defaults:
            >>> from kreuzberg import ExtractionConfig, PostProcessorConfig
            >>> config = ExtractionConfig(
            ...     postprocessor=PostProcessorConfig()
            ... )

        Enable only specific processors:
            >>> config = ExtractionConfig(
            ...     postprocessor=PostProcessorConfig(
            ...         enabled=True,
            ...         enabled_processors=["normalize_whitespace", "fix_encoding"]
            ...     )
            ... )

        Disable specific processors:
            >>> config = ExtractionConfig(
            ...     postprocessor=PostProcessorConfig(
            ...         enabled=True,
            ...         disabled_processors=["experimental_cleanup"]
            ...     )
            ... )

        Disable all post-processing:
            >>> config = ExtractionConfig(
            ...     postprocessor=PostProcessorConfig(enabled=False)
            ... )

        Register custom post-processor:
            >>> from kreuzberg import register_post_processor
            >>> class MyProcessor:
            ...     def name(self) -> str:
            ...         return "my_processor"
            ...     def process(self, result) -> Any:
            ...         return result
            ...     def processing_stage(self) -> str:
            ...         return "middle"
            >>> register_post_processor(MyProcessor())
    """


def _document_tesseract_config() -> None:
    """Document TesseractConfig class attributes."""
    TesseractConfig.__doc__ = """Detailed Tesseract OCR configuration for advanced tuning.

    Fine-tune Tesseract OCR behavior for specific document types and quality levels.
    Most documents work well with defaults; adjust these settings for specialized cases.

    Attributes:
        language (str): OCR language (ISO 639-3 three-letter code).
            Default: "eng"

        psm (int): Page Segmentation Mode - how to analyze page layout.
            Default: 3 (Fully automatic page segmentation)
            - 0: Orientation and script detection only (no OCR)
            - 3: Fully automatic page segmentation (default)
            - 6: Uniform block of text
            - 11: Sparse text - find as much text as possible
            Examples: psm=3 for general documents, psm=6 for simple uniform text.
            See Tesseract documentation for all modes.

        output_format (str): Output format for OCR results.
            Default: "plaintext"

        oem (int): OCR Engine Mode - which OCR engine to use.
            Default: 3 (Auto - tesseract default)
            - 0: Legacy Tesseract only (older, fast)
            - 1: Neural Nets LSTM only (newer, accurate)
            - 2: Both legacy and LSTM (best accuracy)
            - 3: Default - Tesseract chooses based on build

        min_confidence (float): Minimum confidence threshold (0.0-1.0) for accepting
            OCR results. Default: 0.0 (accept all results)

        preprocessing (ImagePreprocessingConfig | None): Image preprocessing configuration
            for cleaning up images before OCR. Default: None

        enable_table_detection (bool): Enable automatic table detection and extraction.
            Default: False

        table_min_confidence (float): Minimum confidence for table detection (0.0-1.0).
            Default: 0.5

        table_column_threshold (int): Minimum pixel width between columns.
            Default: 10

        table_row_threshold_ratio (float): Minimum row height ratio.
            Default: 0.5

        use_cache (bool): Cache OCR results for improved performance.
            Default: True

        classify_use_pre_adapted_templates (bool): Use pre-adapted character templates.
            Default: False

        language_model_ngram_on (bool): Enable language model n-gram processing.
            Default: True

        tessedit_dont_blkrej_good_wds (bool): Don't block-reject good words.
            Default: False

        tessedit_dont_rowrej_good_wds (bool): Don't row-reject good words.
            Default: False

        tessedit_enable_dict_correction (bool): Enable dictionary-based spelling correction.
            Default: False

        tessedit_char_whitelist (str): Whitelist of characters to recognize.
            Only these characters will be recognized. Empty = all characters.
            Default: ""

        tessedit_char_blacklist (str): Blacklist of characters to ignore.
            These characters will be skipped. Default: ""

        tessedit_use_primary_params_model (bool): Use primary parameters model.
            Default: False

        textord_space_size_is_variable (bool): Allow variable space sizes.
            Default: False

        thresholding_method (bool): Thresholding method for binarization.
            Default: False

    Example:
        General document OCR:
            >>> from kreuzberg import TesseractConfig
            >>> config = TesseractConfig(psm=3, oem=3)

        Invoice/form OCR with table detection:
            >>> config = TesseractConfig(
            ...     psm=6,
            ...     oem=2,
            ...     enable_table_detection=True,
            ...     min_confidence=0.6
            ... )

        High-precision technical document OCR:
            >>> from kreuzberg import ImagePreprocessingConfig
            >>> config = TesseractConfig(
            ...     psm=3,
            ...     oem=2,
            ...     preprocessing=ImagePreprocessingConfig(
            ...         denoise=True,
            ...         contrast_enhance=True,
            ...         auto_rotate=True
            ...     ),
            ...     min_confidence=0.7,
            ...     tessedit_enable_dict_correction=True
            ... )

        Numeric-only OCR (for receipts, barcodes):
            >>> config = TesseractConfig(
            ...     psm=6,
            ...     tessedit_char_whitelist="0123456789.-,",
            ...     min_confidence=0.8
            ... )

        Multiple language document:
            >>> config = TesseractConfig(
            ...     language="eng+fra+deu",
            ...     psm=3,
            ...     oem=2
            ... )
    """
