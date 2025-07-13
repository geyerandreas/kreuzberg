# Kreuzberg

[![Discord](https://img.shields.io/badge/Discord-Join%20our%20community-7289da)](https://discord.gg/pXxagNK2zN)
[![PyPI version](https://badge.fury.io/py/kreuzberg.svg)](https://badge.fury.io/py/kreuzberg)
[![Documentation](https://img.shields.io/badge/docs-GitHub_Pages-blue)](https://goldziher.github.io/kreuzberg/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-95%25-green)](https://github.com/Goldziher/kreuzberg)

**Advanced Document Intelligence for Modern Python Applications.** Transform PDFs, images, and office documents into structured data with production-grade performance. Built by engineers who understand that speed, reliability, and developer experience matter.

📖 **[Complete Documentation](https://goldziher.github.io/kreuzberg/)**

## Why Choose Kreuzberg?

### ⚡ Proven Performance

[Benchmarked](https://goldziher.github.io/python-text-extraction-libs-benchmarks/) 6-126x faster than alternatives while using minimal resources. Process up to 14 files per second with 87MB install size and ~360MB memory usage. Optimized for production workloads and resource-constrained environments.

### 🏗️ Production Engineering

Comprehensive test coverage (95%+), robust error handling, and true async/await support. Built with modern Python practices for reliability in production environments.

### 🔧 Developer Experience

Works immediately with smart defaults, scales as you grow. Native MCP integration for AI tools, full type safety, and clear documentation.

### 🚀 Flexible Deployment

Deploy on serverless platforms, containers, or traditional servers. Supports both CPU and GPU processing (via PaddleOCR and EasyOCR). No external API dependencies. Multiple deployment modes: CLI, REST API, MCP server.

### 📄 Comprehensive Format Support

Extract from PDFs, images, Office documents, HTML, spreadsheets, and presentations. Multiple OCR engines with intelligent fallbacks, table extraction, and content preparation for RAG workflows.

## Quick Start

### Installation

```bash
# Basic installation
pip install kreuzberg

# With optional features
pip install "kreuzberg[cli,api]"        # CLI + REST API
pip install "kreuzberg[easyocr,gmft]"   # EasyOCR + table extraction
pip install "kreuzberg[auto-classify-document-type]"   # Automatic document type classification
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
    # Extract content from files
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

Available variants: `latest`, `v3.8.0`, `v3.8.0-easyocr`, `v3.8.0-paddle`, `v3.8.0-gmft`, `v3.8.0-all`

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

## 📊 Performance Comparison

[Comprehensive benchmarks](https://goldziher.github.io/python-text-extraction-libs-benchmarks/) across ~100 real-world documents • [View source](https://github.com/Goldziher/python-text-extraction-libs-benchmarks) • [**Detailed Analysis**](https://goldziher.github.io/kreuzberg/performance-analysis/):

| Framework     | Speed        | Memory | Install Size | Dependencies | Success Rate |
| ------------- | ------------ | ------ | ------------ | ------------ | ------------ |
| **Kreuzberg** | 14.4 files/s | 360MB  | 87MB         | 43           | 100%         |
| Unstructured  | ~12 files/s  | ~1GB   | 146MB        | 54           | 88%+         |
| MarkItDown    | ~15 files/s  | ~1.5GB | 251MB        | 25           | 80%\*        |
| Docling       | ~1 file/min  | ~5GB   | 1,032MB      | 88           | 45%\*        |

\*_Performance varies significantly with document complexity and size_

**Key strengths:**

- 6-126x faster processing than comparable frameworks
- Smallest installation footprint and memory usage
- Only framework with built-in async/await support
- Supports both CPU and GPU processing
- Built by software engineers for production reliability

> **Benchmark details**: Tests include PDFs, Word docs, HTML, images, and spreadsheets in multiple languages (English, Hebrew, German, Chinese, Japanese, Korean) on standardized hardware.

## Documentation

### Quick Links

- [Installation Guide](https://goldziher.github.io/kreuzberg/getting-started/installation/) - Setup and dependencies
- [User Guide](https://goldziher.github.io/kreuzberg/user-guide/) - Comprehensive usage guide
- [Performance Analysis](https://goldziher.github.io/kreuzberg/performance-analysis/) - Detailed benchmark results
- [API Reference](https://goldziher.github.io/kreuzberg/api-reference/) - Complete API documentation
- [Docker Guide](https://goldziher.github.io/kreuzberg/user-guide/docker/) - Container deployment
- [REST API](https://goldziher.github.io/kreuzberg/user-guide/api-server/) - HTTP endpoints
- [CLI Guide](https://goldziher.github.io/kreuzberg/cli/) - Command-line usage
- [OCR Configuration](https://goldziher.github.io/kreuzberg/user-guide/ocr-configuration/) - OCR engine setup

## License

MIT License - see [LICENSE](LICENSE) for details.
