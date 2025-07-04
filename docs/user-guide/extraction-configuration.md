# Extraction Configuration

Kreuzberg provides extensive configuration options for the extraction process through the `ExtractionConfig` class. This guide covers common configuration scenarios and examples.

## Basic Configuration

All extraction functions accept an optional `config` parameter of type `ExtractionConfig`. This object allows you to:

- Control OCR behavior with `force_ocr` and `ocr_backend`
- Provide engine-specific OCR configuration via `ocr_config`
- Enable table extraction with `extract_tables` and configure it via `gmft_config`
- Enable automatic language detection with `auto_detect_language`
- Add validation and post-processing hooks
- Configure custom extractors

## Examples

### Basic Usage

```python
from kreuzberg import extract_file, ExtractionConfig

# Simple extraction with default configuration
result = await extract_file("document.pdf")

# Extraction with custom configuration
result = await extract_file("document.pdf", config=ExtractionConfig(force_ocr=True))
```

### OCR Configuration

```python
from kreuzberg import extract_file, ExtractionConfig, TesseractConfig, PSMMode

# Configure Tesseract OCR with specific language and page segmentation mode
result = await extract_file(
    "document.pdf",
    config=ExtractionConfig(force_ocr=True, ocr_config=TesseractConfig(language="eng+deu", psm=PSMMode.SINGLE_BLOCK)),
)
```

The `language` parameter specifies which language model Tesseract should use. You can specify multiple languages by joining them with a plus sign (e.g., "eng+deu" for English and German).

The `psm` (Page Segmentation Mode) parameter controls how Tesseract analyzes page layout. Different modes are suitable for different types of documents:

- `PSMMode.AUTO`: Automatic page segmentation (default)
- `PSMMode.SINGLE_BLOCK`: Treat the image as a single text block
- `PSMMode.SINGLE_LINE`: Treat the image as a single text line
- `PSMMode.SINGLE_WORD`: Treat the image as a single word
- `PSMMode.SINGLE_CHAR`: Treat the image as a single character

### Alternative OCR Engines

```python
from kreuzberg import extract_file, ExtractionConfig, EasyOCRConfig, PaddleOCRConfig

# Use EasyOCR backend
result = await extract_file(
    "document.jpg", config=ExtractionConfig(ocr_backend="easyocr", ocr_config=EasyOCRConfig(language_list=["en", "de"]))
)

# Use PaddleOCR backend
result = await extract_file(
    "chinese_document.jpg", config=ExtractionConfig(ocr_backend="paddleocr", ocr_config=PaddleOCRConfig(language="ch"))
)
```

### Table Extraction

Kreuzberg can extract tables from PDF documents using the [GMFT](https://github.com/conjuncts/gmft) package:

```python
from kreuzberg import extract_file, ExtractionConfig, GMFTConfig

# Extract tables with default configuration
result = await extract_file("document_with_tables.pdf", config=ExtractionConfig(extract_tables=True))

# Extract tables with custom configuration
config = ExtractionConfig(
    extract_tables=True,
    gmft_config=GMFTConfig(
        detector_base_threshold=0.85,  # Minimum confidence score required for a table
        remove_null_rows=True,  # Remove rows with no text
        enable_multi_header=True,  # Enable multi-indices in the dataframe
    ),
)
result = await extract_file("document_with_tables.pdf", config=config)

# Access extracted tables
for i, table in enumerate(result.tables):
    print(f"Table {i+1} on page {table.page_number}:")
    print(table.text)  # Markdown formatted table text
    # You can also access the pandas DataFrame directly
    df = table.df
    print(df.shape)  # (rows, columns)
```

Note that table extraction requires the `gmft` dependency. You can install it with:

```shell
pip install "kreuzberg[gmft]"
```

### Language Detection

Kreuzberg can automatically detect the language of extracted text using fast-langdetect:

```python
from kreuzberg import extract_file, ExtractionConfig, LanguageDetectionConfig

# Simple automatic language detection
result = await extract_file("multilingual_document.pdf", config=ExtractionConfig(auto_detect_language=True))

# Access detected languages (lowercase ISO 639-1 codes)
if result.detected_languages:
    print(f"Detected languages: {', '.join(result.detected_languages)}")
    # Example output: "Detected languages: en, de, fr"

# Advanced configuration with multilingual detection
lang_config = LanguageDetectionConfig(
    multilingual=True,  # Enable mixed-language detection
    top_k=5,  # Return top 5 languages
    low_memory=False,  # Use high accuracy mode
    cache_dir="/tmp/lang_models",  # Custom model cache directory
)

result = await extract_file(
    "multilingual_document.pdf", config=ExtractionConfig(auto_detect_language=True, language_detection_config=lang_config)
)

# Use detected languages for OCR
if result.detected_languages:
    # Re-extract with OCR using the primary detected language
    from kreuzberg import TesseractConfig

    result_with_ocr = await extract_file(
        "multilingual_document.pdf",
        config=ExtractionConfig(force_ocr=True, ocr_config=TesseractConfig(language=result.detected_languages[0])),
    )
```

#### Language Detection Configuration Options

- `low_memory` (default: `True`): Use smaller model (~200MB) vs larger, more accurate model
- `multilingual` (default: `False`): Enable detection of multiple languages in mixed text
- `top_k` (default: `3`): Maximum number of languages to return
- `cache_dir`: Custom directory for language model storage
- `allow_fallback` (default: `True`): Fall back to small model if large model fails

The feature requires the `langdetect` dependency:

```shell
pip install "kreuzberg[langdetect]"
```

### Entity and Keyword Extraction

Kreuzberg can extract named entities and keywords from documents using spaCy for entity recognition and KeyBERT for keyword extraction:

```python
from kreuzberg import extract_file, ExtractionConfig, SpacyEntityExtractionConfig

# Basic entity and keyword extraction
result = await extract_file(
    "document.pdf",
    config=ExtractionConfig(
        extract_entities=True,
        extract_keywords=True,
        keyword_count=10,  # Number of keywords to extract (default: 10)
    ),
)

# Access extracted entities and keywords
if result.entities:
    for entity in result.entities:
        print(f"{entity.type}: {entity.text} (position {entity.start}-{entity.end})")
        # Example: "PERSON: John Doe (position 0-8)"

if result.keywords:
    for keyword, score in result.keywords:
        print(f"{keyword}: {score:.3f}")
        # Example: "artificial intelligence: 0.845"
```

#### Entity Extraction with Language Support

spaCy supports entity extraction in multiple languages. You can configure language-specific models:

```python
from kreuzberg import extract_file, ExtractionConfig, SpacyEntityExtractionConfig

# Configure spaCy for specific languages
spacy_config = SpacyEntityExtractionConfig(
    language_models={
        "en": "en_core_web_sm",  # English
        "de": "de_core_news_sm",  # German
        "fr": "fr_core_news_sm",  # French
        "es": "es_core_news_sm",  # Spanish
    },
    model_cache_dir="/tmp/spacy_models",  # Custom model cache directory
    fallback_to_multilingual=True,  # Use multilingual model if language-specific model fails
)

# Extract with language detection to automatically choose the right model
result = await extract_file(
    "multilingual_document.pdf",
    config=ExtractionConfig(
        auto_detect_language=True,  # Enable language detection
        extract_entities=True,
        spacy_entity_extraction_config=spacy_config,
    ),
)

# The system will automatically use the appropriate spaCy model based on detected languages
if result.detected_languages and result.entities:
    print(f"Detected languages: {result.detected_languages}")
    print(f"Extracted {len(result.entities)} entities")
```

#### Custom Entity Patterns

You can define custom entity patterns using regular expressions:

```python
result = await extract_file(
    "invoice.pdf",
    config=ExtractionConfig(
        extract_entities=True,
        custom_entity_patterns={
            "INVOICE_ID": r"INV-\d{4,}",  # Invoice numbers
            "PHONE": r"\+?\d{1,3}[-.\s]?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}",  # Phone numbers
            "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",  # Email addresses
        },
    ),
)

# Custom patterns are combined with spaCy's standard entity types
for entity in result.entities:
    if entity.type in ["INVOICE_ID", "PHONE", "EMAIL"]:
        print(f"Custom entity - {entity.type}: {entity.text}")
    else:
        print(f"Standard entity - {entity.type}: {entity.text}")
```

#### Supported Entity Types

spaCy automatically detects these standard entity types:

- **PERSON**: People's names
- **ORG**: Organizations, companies, agencies
- **GPE**: Countries, cities, states (Geopolitical entities)
- **MONEY**: Monetary values
- **DATE**: Date expressions
- **TIME**: Time expressions
- **PERCENT**: Percentage values
- **CARDINAL**: Numerals that do not fall under another type

Language-specific models may support additional entity types relevant to that language.

#### spaCy Configuration Options

- `language_models`: Dict mapping language codes to spaCy model names
- `model_cache_dir`: Custom directory for caching spaCy models
- `fallback_to_multilingual`: Whether to use multilingual model (`xx_ent_wiki_sm`) as fallback
- `max_doc_length`: Maximum document length for spaCy processing (default: 1,000,000 characters)
- `batch_size`: Batch size for processing multiple texts (default: 1,000)

#### Installation Requirements

Entity and keyword extraction require additional dependencies:

```shell
# For entity extraction with spaCy
pip install "kreuzberg[entity-extraction]"

# Install specific spaCy language models as needed
python -m spacy download en_core_web_sm    # English
python -m spacy download de_core_news_sm   # German
python -m spacy download fr_core_news_sm   # French
```

Available spaCy models include: `en_core_web_sm`, `de_core_news_sm`, `fr_core_news_sm`, `es_core_news_sm`, `pt_core_news_sm`, `it_core_news_sm`, `nl_core_news_sm`, `zh_core_web_sm`, `ja_core_news_sm`, `ko_core_news_sm`, `ru_core_news_sm`, and many others.

### Batch Processing

```python
from kreuzberg import batch_extract_file, ExtractionConfig

# Process multiple files with the same configuration
file_paths = ["document1.pdf", "document2.docx", "image.jpg"]
config = ExtractionConfig(force_ocr=True)
results = await batch_extract_file(file_paths, config=config)
```

### Synchronous API

```python
from kreuzberg import extract_file_sync, ExtractionConfig, TesseractConfig

# Synchronous extraction with configuration
result = extract_file_sync("document.pdf", config=ExtractionConfig(ocr_config=TesseractConfig(language="eng")))
```

## Using Custom Extractors

You can register custom extractors to handle specific file formats:

```python
from kreuzberg import ExtractorRegistry, extract_file, ExtractionConfig
from my_module import CustomExtractor

# Register a custom extractor
ExtractorRegistry.add_extractor(CustomExtractor)

# Now extraction functions will use your custom extractor for supported MIME types
result = await extract_file("custom_document.xyz")

# Later, remove the extractor if needed
ExtractorRegistry.remove_extractor(CustomExtractor)
```

See the [Custom Extractors](../advanced/custom-extractors.md) guide for more details on creating and registering custom extractors.

## OCR Best Practices

When configuring OCR for your documents, consider these best practices:

1. **Language Selection**: Choose the appropriate language model for your documents. Using the wrong language model can significantly reduce OCR accuracy.

1. **Page Segmentation Mode**: Select the appropriate PSM based on your document layout:

    - Use `PSMMode.AUTO` for general documents with mixed content
    - Use `PSMMode.SINGLE_BLOCK` for documents with a single column of text
    - Use `PSMMode.SINGLE_LINE` for receipts or single-line text
    - Use `PSMMode.SINGLE_WORD` or `PSMMode.SINGLE_CHAR` for specialized cases

1. **OCR Engine Selection**: Choose the appropriate OCR engine based on your needs:

    - Tesseract: Good general-purpose OCR with support for many languages
    - EasyOCR: Better for some non-Latin scripts and natural scene text
    - PaddleOCR: Excellent for Chinese and other Asian languages

1. **Preprocessing**: For better OCR results, consider using validation and post-processing hooks to clean up the extracted text.
