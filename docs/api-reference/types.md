# Types

Core data structures for extraction results, configuration, and metadata.

## ExtractionResult

The result of a file extraction, containing the extracted text, MIME type, metadata, and table data:

::: kreuzberg.ExtractionResult

## ExtractionConfig

Configuration options for extraction functions:

::: kreuzberg.ExtractionConfig

## TableData

A TypedDict that contains data extracted from tables in documents:

::: kreuzberg.TableData

## OCR Configuration

### TesseractConfig

::: kreuzberg.TesseractConfig

### EasyOCRConfig

::: kreuzberg.EasyOCRConfig

### PaddleOCRConfig

::: kreuzberg.PaddleOCRConfig

## GMFT Configuration

Configuration options for the GMFT table extraction engine:

::: kreuzberg.GMFTConfig

## Entity Extraction Configuration

Configuration options for spaCy-based entity extraction:

::: kreuzberg.SpacyEntityExtractionConfig

## Language Detection Configuration

Configuration options for automatic language detection:

::: kreuzberg.LanguageDetectionConfig

## PSMMode (Page Segmentation Mode)

::: kreuzberg.PSMMode

## Entity

Represents an extracted named entity:

::: kreuzberg.Entity

## Metadata

A TypedDict that contains optional metadata fields extracted from documents:

::: kreuzberg.Metadata
