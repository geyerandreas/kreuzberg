# Kreuzberg

[![Discord](https://img.shields.io/badge/Discord-Join%20our%20community-7289da)](https://discord.gg/pXxagNK2zN)
[![PyPI version](https://badge.fury.io/py/kreuzberg.svg)](https://badge.fury.io/py/kreuzberg)
[![Documentation](https://img.shields.io/badge/docs-GitHub_Pages-blue)](https://goldziher.github.io/kreuzberg/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Kreuzberg is a Python library for text extraction from documents. It provides a unified interface for extracting text from PDFs, images, office documents, and more, with both async and sync APIs.

## Why Kreuzberg?

- **Simple and Hassle-Free**: Clean API that just works, without complex configuration
- **Local Processing**: No external API calls or cloud dependencies required
- **Resource Efficient**: Lightweight processing without GPU requirements
- **Format Support**: Comprehensive support for documents, images, and text formats
- **Multiple OCR Engines**: Support for Tesseract, EasyOCR, and PaddleOCR
- **Command Line Interface**: Powerful CLI for batch processing and automation
- **Metadata Extraction**: Get document metadata alongside text content
- **Table Extraction**: Extract tables from documents using the excellent GMFT library
- **Modern Python**: Built with async/await, type hints, and a functional-first approach
- **Permissive OSS**: MIT licensed with permissively licensed dependencies

## Quick Start

```bash
pip install kreuzberg

# Or install with CLI support
pip install "kreuzberg[cli]"
```

Install pandoc:

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr pandoc

# macOS
brew install tesseract pandoc

# Windows
choco install -y tesseract pandoc
```

The tesseract OCR engine is the default OCR engine. You can decide not to use it - and then either use one of the two alternative OCR engines, or have no OCR at all.

### Alternative OCR engines

```bash
# Install with EasyOCR support
pip install "kreuzberg[easyocr]"

# Install with PaddleOCR support
pip install "kreuzberg[paddleocr]"
```

## Quick Example

```python
import asyncio
from kreuzberg import extract_file

async def main():
    # Extract text from a PDF
    result = await extract_file("document.pdf")
    print(result.content)

    # Extract text from an image
    result = await extract_file("scan.jpg")
    print(result.content)

    # Extract text from a Word document
    result = await extract_file("report.docx")
    print(result.content)

asyncio.run(main())
```

## Command Line Interface

Kreuzberg includes a powerful CLI for processing documents from the command line:

```bash
# Extract text from a file
kreuzberg extract document.pdf

# Extract with JSON output and metadata
kreuzberg extract document.pdf --output-format json --show-metadata

# Extract from stdin
cat document.html | kreuzberg extract

# Use specific OCR backend
kreuzberg extract image.png --ocr-backend easyocr --easyocr-languages en,de

# Extract with configuration file
kreuzberg extract document.pdf --config config.toml
```

### CLI Configuration

Configure via `pyproject.toml`:

```toml
[tool.kreuzberg]
force_ocr = true
chunk_content = false
extract_tables = true
max_chars = 4000
ocr_backend = "tesseract"

[tool.kreuzberg.tesseract]
language = "eng+deu"
psm = 3
```

For full CLI documentation, see the [CLI Guide](https://goldziher.github.io/kreuzberg/cli/).

## Documentation

For comprehensive documentation, visit our [GitHub Pages](https://goldziher.github.io/kreuzberg/):

- [Getting Started](https://goldziher.github.io/kreuzberg/getting-started/) - Installation and basic usage
- [User Guide](https://goldziher.github.io/kreuzberg/user-guide/) - In-depth usage information
- [CLI Guide](https://goldziher.github.io/kreuzberg/cli/) - Command-line interface documentation
- [API Reference](https://goldziher.github.io/kreuzberg/api-reference/) - Detailed API documentation
- [Examples](https://goldziher.github.io/kreuzberg/examples/) - Code examples for common use cases
- [OCR Configuration](https://goldziher.github.io/kreuzberg/user-guide/ocr-configuration/) - Configure OCR engines
- [OCR Backends](https://goldziher.github.io/kreuzberg/user-guide/ocr-backends/) - Choose the right OCR engine

## Supported Formats

Kreuzberg supports a wide range of document formats:

- **Documents**: PDF, DOCX, RTF, TXT, EPUB, etc.
- **Images**: JPG, PNG, TIFF, BMP, GIF, etc.
- **Spreadsheets**: XLSX, XLS, CSV, etc.
- **Presentations**: PPTX, PPT, etc.
- **Web Content**: HTML, XML, etc.

## OCR Engines

Kreuzberg supports multiple OCR engines:

- **Tesseract** (Default): Lightweight, fast startup, requires system installation
- **EasyOCR**: Good for many languages, pure Python, but downloads models on first use
- **PaddleOCR**: Excellent for Asian languages, pure Python, but downloads models on first use

For comparison and selection guidance, see the [OCR Backends](https://goldziher.github.io/kreuzberg/user-guide/ocr-backends/) documentation.

## Performance

Kreuzberg offers both sync and async APIs. Choose the right one based on your use case:

| Operation              | Sync Time | Async Time | Async Advantage    |
| ---------------------- | --------- | ---------- | ------------------ |
| Simple text (Markdown) | 0.4ms     | 17.5ms     | **❌ 41x slower**  |
| HTML documents         | 1.6ms     | 1.1ms      | **✅ 1.5x faster** |
| Complex PDFs           | 39.0s     | 8.5s       | **✅ 4.6x faster** |
| OCR processing         | 0.4s      | 0.7s       | **✅ 1.7x faster** |
| Batch operations       | 38.6s     | 8.5s       | **✅ 4.5x faster** |

**Rule of thumb:**

- Use **sync** for simple documents and CLI applications
- Use **async** for complex PDFs, OCR, and batch processing
- Use **batch operations** for multiple files

For detailed benchmarks and methodology, see our [Performance Documentation](https://goldziher.github.io/kreuzberg/advanced/performance/).

## Contributing

We welcome contributions! Please see our [Contributing Guide](docs/contributing.md) for details on setting up your development environment and submitting pull requests.

## License

This library is released under the MIT license.
