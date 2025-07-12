# Kreuzberg

[![Discord](https://img.shields.io/badge/Discord-Join%20our%20community-7289da)](https://discord.gg/pXxagNK2zN)
[![PyPI version](https://badge.fury.io/py/kreuzberg.svg)](https://badge.fury.io/py/kreuzberg)
[![Documentation](https://img.shields.io/badge/docs-GitHub_Pages-blue)](https://goldziher.github.io/kreuzberg/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-95%25-green)](https://github.com/Goldziher/kreuzberg)

**High-performance Open Source Document Intelligence framework for Python.** Built by engineers for production workloads - extract text from any document with excellent performance and minimal complexity.

📖 **[Complete Documentation](https://goldziher.github.io/kreuzberg/)**

## Why Choose Kreuzberg?

### 🚀 Performance

- [35+ files/second](https://goldziher.github.io/python-text-extraction-libs-benchmarks/) processing speed - 2-3x faster than alternatives
- Minimal footprint: 71MB install vs 1GB+ for competitors
- Low memory usage (~530MB average) optimized for production workloads
- Edge and serverless ready - deploy anywhere without heavy dependencies

### 🛠️ Engineering Quality

- Built by software engineers with modern Python best practices
- 95%+ test coverage with comprehensive test suite
- Thoroughly benchmarked and profiled for real-world performance
- Full type safety with excellent IDE support
- Robust error handling and detailed logging

### 🎯 Developer Experience

- Works out of the box with sane defaults, scales with your needs
- Only framework offering true async/await support alongside sync APIs
- Native MCP server for AI tool integration (Claude Desktop, Cursor)
- Extensible architecture for custom document handlers
- Comprehensive documentation and examples

### 🌍 Deployment Options

- Docker images for all architectures (AMD64, ARM64)
- Cloud native - AWS Lambda, Google Cloud Functions, Azure Functions
- CPU-only processing - no GPU requirements, lower energy consumption
- 100% local processing - no external API dependencies
- Multiple deployment modes: CLI, REST API, MCP server

### 🎯 Complete Solution

- Universal format support: PDFs, images, Office docs, HTML, spreadsheets, presentations
- Multiple OCR engines: Tesseract, EasyOCR, PaddleOCR with intelligent fallbacks
- Advanced features: Table extraction, metadata extraction, content chunking for RAG
- Production tools: REST API, CLI tools, batch processing, custom extractors

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

[Comprehensive benchmarks](https://goldziher.github.io/python-text-extraction-libs-benchmarks/) across 94 real-world documents • [View source](https://github.com/Goldziher/python-text-extraction-libs-benchmarks):

| Framework     | Speed       | Memory | Install Size | Dependencies | Success Rate |
| ------------- | ----------- | ------ | ------------ | ------------ | ------------ |
| **Kreuzberg** | 35+ files/s | 530MB  | 71MB         | 20           | High         |
| Unstructured  | ~12 files/s | ~1GB   | 146MB        | 54           | 88%+         |
| MarkItDown    | ~15 files/s | ~1.5GB | 251MB        | 25           | 80%\*        |
| Docling       | ~1 file/min | ~5GB   | 1,032MB      | 88           | 45%\*        |

\*_Performance varies significantly with document complexity and size_

**Key strengths:**

- 2-3x faster processing than comparable frameworks
- Smallest installation footprint and memory usage
- Only framework with built-in async/await support
- CPU-only processing - no GPU dependencies
- Built by software engineers for production reliability

> **Benchmark details**: Tests include PDFs, Word docs, HTML, images, and spreadsheets in multiple languages (English, Hebrew, German, Chinese, Japanese, Korean) on standardized hardware.

## Documentation

### Quick Links

- [Installation Guide](https://goldziher.github.io/kreuzberg/getting-started/installation/) - Setup and dependencies
- [User Guide](https://goldziher.github.io/kreuzberg/user-guide/) - Comprehensive usage guide
- [API Reference](https://goldziher.github.io/kreuzberg/api-reference/) - Complete API documentation
- [Docker Guide](https://goldziher.github.io/kreuzberg/user-guide/docker/) - Container deployment
- [REST API](https://goldziher.github.io/kreuzberg/user-guide/api-server/) - HTTP endpoints
- [CLI Guide](https://goldziher.github.io/kreuzberg/cli/) - Command-line usage
- [OCR Configuration](https://goldziher.github.io/kreuzberg/user-guide/ocr-configuration/) - OCR engine setup

## License

MIT License - see [LICENSE](LICENSE) for details.
