# Kreuzberg

[![Discord](https://img.shields.io/badge/Discord-Join%20our%20community-7289da)](https://discord.gg/pXxagNK2zN)
[![PyPI version](https://badge.fury.io/py/kreuzberg.svg)](https://badge.fury.io/py/kreuzberg)
[![Documentation](https://img.shields.io/badge/docs-GitHub_Pages-blue)](https://goldziher.github.io/kreuzberg/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**High-performance Python library for text extraction from documents.** Extract text from PDFs, images, office documents, and more with both async and sync APIs.

📖 **[Complete Documentation](https://goldziher.github.io/kreuzberg/)**

## Why Kreuzberg?

- **🚀 Fastest Performance**: [35+ files/second](https://goldziher.github.io/python-text-extraction-libs-benchmarks/) - the fastest text extraction library
- **💾 Memory Efficient**: 14x smaller than alternatives (71MB vs 1GB+) with lowest memory usage (~530MB)
- **⚡ Dual APIs**: Only library with both sync and async support
- **🔧 Zero Configuration**: Works out of the box with sane defaults
- **🏠 Local Processing**: No cloud dependencies or external API calls
- **📦 Rich Format Support**: PDFs, images, Office docs, HTML, and more
- **🔍 Multiple OCR Engines**: Tesseract, EasyOCR, and PaddleOCR support
- **🤖 AI Integration**: Native MCP server for Claude and other AI tools
- **🐳 Production Ready**: CLI, REST API, MCP server, and Docker images included

## Quick Start

### Installation

```bash
# Basic installation
pip install kreuzberg

# With optional features
pip install "kreuzberg[cli,api]"        # CLI + REST API
pip install "kreuzberg[easyocr,gmft]"   # EasyOCR + table extraction
pip install "kreuzberg[all]"            # Everything
```

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr pandoc

# macOS
brew install tesseract pandoc

# Windows
choco install tesseract pandoc
```

### Basic Usage

```python
import asyncio
from kreuzberg import extract_file

async def main():
    # Extract from any document type
    result = await extract_file("document.pdf")
    print(result.content)
    print(result.metadata)

asyncio.run(main())
```

## Deployment Options

### 🤖 MCP Server (AI Integration)

**Connect directly to Claude Desktop, Cursor, and other AI tools with the Model Context Protocol:**

```bash
# Install and run MCP server with all features (recommended)
pip install "kreuzberg[all]"
kreuzberg-mcp

# Or with uvx (recommended for Claude Desktop)
uvx --with "kreuzberg[all]" kreuzberg-mcp

# Basic installation (core features only)
pip install kreuzberg
kreuzberg-mcp
```

**Configure in Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "kreuzberg": {
      "command": "uvx",
      "args": ["--with", "kreuzberg[all]", "kreuzberg-mcp"]
    }
  }
}
```

**Basic configuration (core features only):**

```json
{
  "mcpServers": {
    "kreuzberg": {
      "command": "uvx",
      "args": ["kreuzberg-mcp"]
    }
  }
}
```

**Available MCP capabilities:**

- **Tools**: `extract_document`, `extract_bytes`, `extract_simple`
- **Resources**: Configuration, supported formats, OCR backends
- **Prompts**: Extract-and-summarize, structured analysis workflows

### 🐳 Docker (Recommended)

```bash
# Run API server
docker run -p 8000:8000 goldziher/kreuzberg:latest

# Extract files
curl -X POST http://localhost:8000/extract -F "data=@document.pdf"
```

Available variants: `latest`, `3.6.1`, `3.6.1-easyocr`, `3.6.1-paddle`, `3.6.1-gmft`, `3.6.1-all`

### 🌐 REST API

```bash
# Install and run
pip install "kreuzberg[api]"
litestar --app kreuzberg._api.main:app run

# Health check
curl http://localhost:8000/health

# Extract files
curl -X POST http://localhost:8000/extract -F "data=@file.pdf"
```

### 💻 Command Line

```bash
# Install CLI
pip install "kreuzberg[cli]"

# Extract to stdout
kreuzberg extract document.pdf

# JSON output with metadata
kreuzberg extract document.pdf --output-format json --show-metadata

# Batch processing
kreuzberg extract *.pdf --output-dir ./extracted/
```

## Supported Formats

| Category          | Formats                        |
| ----------------- | ------------------------------ |
| **Documents**     | PDF, DOCX, DOC, RTF, TXT, EPUB |
| **Images**        | JPG, PNG, TIFF, BMP, GIF, WEBP |
| **Spreadsheets**  | XLSX, XLS, CSV, ODS            |
| **Presentations** | PPTX, PPT, ODP                 |
| **Web**           | HTML, XML, MHTML               |
| **Archives**      | Support via extraction         |

## Performance

**[Comprehensive benchmarks](https://goldziher.github.io/python-text-extraction-libs-benchmarks/)** across 94 real-world documents (~210MB) • [View source](https://github.com/Goldziher/python-text-extraction-libs-benchmarks):

| Library       | Speed           | Memory    | Install Size | Dependencies | Success Rate |
| ------------- | --------------- | --------- | ------------ | ------------ | ------------ |
| **Kreuzberg** | **35+ files/s** | **530MB** | **71MB**     | **20**       | High\*       |
| Unstructured  | Moderate        | ~1GB      | 146MB        | 54           | 88%+         |
| MarkItDown    | Good†           | ~1.5GB    | 251MB        | 25           | 80%†         |
| Docling       | 60+ min/file‡   | ~5GB      | 1,032MB      | 88           | Low‡         |

\*_Can achieve 75% reliability with 15% performance trade-off when configured_
†_Good on simple documents, struggles with large/complex files (>10MB)_
‡_Frequently fails/times out on medium files (>1MB)_

> **Benchmark details**: Tested across PDFs, Word docs, HTML, images, spreadsheets in 6 languages (English, Hebrew, German, Chinese, Japanese, Korean)
> **Rule of thumb**: Use async API for complex documents and batch processing (up to 4.5x faster)

## Documentation

### Quick Links

- [Installation Guide](https://goldziher.github.io/kreuzberg/getting-started/installation/) - Setup and dependencies
- [User Guide](https://goldziher.github.io/kreuzberg/user-guide/) - Comprehensive usage guide
- [API Reference](https://goldziher.github.io/kreuzberg/api-reference/) - Complete API documentation
- [Docker Guide](https://goldziher.github.io/kreuzberg/user-guide/docker/) - Container deployment
- [REST API](https://goldziher.github.io/kreuzberg/user-guide/api-server/) - HTTP endpoints
- [CLI Guide](https://goldziher.github.io/kreuzberg/cli/) - Command-line usage
- [OCR Configuration](https://goldziher.github.io/kreuzberg/user-guide/ocr-configuration/) - OCR engine setup

## Advanced Features

- **🤖 MCP Server**: Native integration with Claude Desktop and AI tools
- **📊 Table Extraction**: Extract tables from PDFs with GMFT
- **🧩 Content Chunking**: Split documents for RAG applications
- **🎯 Custom Extractors**: Extend with your own document handlers
- **🔧 Configuration**: Flexible TOML-based configuration
- **🪝 Hooks**: Pre/post-processing customization
- **🌍 Multi-language OCR**: 100+ languages supported
- **⚙️ Metadata Extraction**: Rich document metadata
- **🔄 Batch Processing**: Efficient bulk document processing

## License

MIT License - see [LICENSE](LICENSE) for details.

______________________________________________________________________

<div align="center">

**[Documentation](https://goldziher.github.io/kreuzberg/) • [PyPI](https://pypi.org/project/kreuzberg/) • [Docker Hub](https://hub.docker.com/r/goldziher/kreuzberg) • [Benchmarks](https://github.com/Goldziher/python-text-extraction-libs-benchmarks) • [Discord](https://discord.gg/pXxagNK2zN)**

Made with ❤️ by the [Kreuzberg contributors](https://github.com/Goldziher/kreuzberg/graphs/contributors)

</div>
