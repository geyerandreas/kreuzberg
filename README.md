# Kreuzberg

[![Discord](https://img.shields.io/badge/Discord-Join%20our%20community-7289da)](https://discord.gg/pXxagNK2zN)
[![PyPI version](https://badge.fury.io/py/kreuzberg.svg)](https://badge.fury.io/py/kreuzberg)
[![Documentation](https://img.shields.io/badge/docs-GitHub_Pages-blue)](https://goldziher.github.io/kreuzberg/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-95%25-green)](https://github.com/Goldziher/kreuzberg)

**The fastest Open Source Document Intelligence framework for Python.** Built by engineers for production workloads - extract text from any document with unmatched performance, minimal footprint, and enterprise-grade reliability.

📖 **[Complete Documentation](https://goldziher.github.io/kreuzberg/)**

## Why Kreuzberg Leads the Pack

### 🏆 Unmatched Performance

- **⚡ Fastest in Class**: [35+ files/second](https://goldziher.github.io/python-text-extraction-libs-benchmarks/) - **2-3x faster** than any competitor
- **🪶 Minimal Footprint**: **14x smaller** install (71MB vs 1GB+), **lowest memory usage** (~530MB)
- **🚀 Edge & Serverless Ready**: Deploy anywhere - cloud functions, edge computing, containers
- **⭐ Only Async Framework**: True async/await support for maximum concurrency

### 🛠️ Engineering Excellence

- **👨‍💻 Built by Engineers**: Clean, optimal Python code with **95%+ test coverage**
- **🔍 Battle-Tested**: Thoroughly benchmarked and profiled for production workloads
- **📝 Superior TypeScript-Grade Typing**: Full type safety and IDE support
- **⚙️ Zero Configuration**: Works perfectly out of the box, scales with your needs

### 🌍 Universal Deployment & Sustainability

- **🐳 Docker-First**: Pre-built images for all architectures (AMD64, ARM64)
- **☁️ Cloud Native**: Deploy on AWS Lambda, Google Cloud Functions, Azure Functions
- **🌱 Green Computing**: CPU-only processing, 65% less energy than GPU alternatives
- **🔌 AI-Ready**: Native MCP server for Claude Desktop, Cursor, and other AI tools
- **🏠 100% Local**: No external APIs, cloud dependencies, or data privacy concerns

### 🎯 Complete Solution

- **📄 Universal Format Support**: PDFs, images, Office docs, HTML, spreadsheets, presentations
- **🧠 Multiple OCR Engines**: Tesseract, EasyOCR, PaddleOCR with intelligent fallbacks
- **📊 Advanced Features**: Table extraction, metadata extraction, content chunking for RAG
- **🔧 Enterprise Features**: REST API, CLI tools, batch processing, custom extractors

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

## 📊 Industry-Leading Performance

**[Comprehensive benchmarks](https://goldziher.github.io/python-text-extraction-libs-benchmarks/)** across 94 real-world documents (~210MB) • [View source](https://github.com/Goldziher/python-text-extraction-libs-benchmarks):

| Framework     | Speed           | Memory    | Install Size | Dependencies | Success Rate | Notes                    |
| ------------- | --------------- | --------- | ------------ | ------------ | ------------ | ------------------------ |
| **Kreuzberg** | **35+ files/s** | **530MB** | **71MB**     | **20**       | **High**     | ✅ **Production Ready**  |
| Unstructured  | ~12 files/s     | ~1GB      | 146MB        | 54           | 88%+         | ⚠️ Memory intensive      |
| MarkItDown    | ~15 files/s†    | ~1.5GB    | 251MB        | 25           | 80%†         | ⚠️ Fails on complex docs |
| Docling       | 0.017 files/s‡  | ~5GB      | **1,032MB**  | 88           | **Low**‡     | ❌ Not production viable |

**Key Advantages:**

- 🏃‍♂️ **2-3x faster** than closest competitor
- 🧠 **14x smaller** footprint than alternatives
- ⚡ **Only framework** with true async support
- 🌱 **65% less energy** consumption (CPU-only, no GPU required)
- 🔒 **Highest reliability** when properly configured
- 🏗️ **Built for production** by software engineers, not data scientists

†_Good on simple documents, struggles with large/complex files (>10MB)_
‡_Frequently fails/times out on medium files (>1MB), requires massive resources_

> **Benchmark methodology**: Real-world document corpus including PDFs, Word docs, HTML, images, spreadsheets in 6 languages (English, Hebrew, German, Chinese, Japanese, Korean). Performance measured on standardized hardware with consistent methodology.

## Documentation

### Quick Links

- [Installation Guide](https://goldziher.github.io/kreuzberg/getting-started/installation/) - Setup and dependencies
- [User Guide](https://goldziher.github.io/kreuzberg/user-guide/) - Comprehensive usage guide
- [API Reference](https://goldziher.github.io/kreuzberg/api-reference/) - Complete API documentation
- [Docker Guide](https://goldziher.github.io/kreuzberg/user-guide/docker/) - Container deployment
- [REST API](https://goldziher.github.io/kreuzberg/user-guide/api-server/) - HTTP endpoints
- [CLI Guide](https://goldziher.github.io/kreuzberg/cli/) - Command-line usage
- [OCR Configuration](https://goldziher.github.io/kreuzberg/user-guide/ocr-configuration/) - OCR engine setup

## 🚀 Production Deployment Scenarios

### Deployment Ready

- **📈 High-Volume Processing**: Handle thousands of documents per hour with async batching
- **💰 Cost Optimization**: 14x smaller footprint = significant infrastructure savings
- **🔒 Data Privacy**: 100% local processing, no external API dependencies
- **⚖️ Compliance Ready**: GDPR, HIPAA, SOC2 compatible (no data leaves your infrastructure)

### AI & Machine Learning

- **🧠 RAG Applications**: Perfect for document preprocessing in Retrieval Augmented Generation
- **🤖 AI Workflow Integration**: Native MCP server for seamless Claude Desktop integration
- **📊 Data Pipeline**: Async-first design for ML data preprocessing workflows
- **🔗 Vector Database Prep**: Built-in chunking for embedding generation

### Serverless & Edge Computing

- **☁️ AWS Lambda**: Cold start optimized, minimal memory footprint
- **⚡ Vercel/Netlify Functions**: Edge deployment ready
- **🌍 Global CDN**: Deploy processing closer to your users
- **📱 Mobile Backend**: Lightweight enough for mobile app backends

### DevOps & Platform Engineering

- **🐳 Kubernetes Ready**: Horizontal scaling with minimal resource requirements
- **📊 Observability**: Built-in metrics and health checks
- **🔄 CI/CD Friendly**: Deterministic builds, comprehensive test coverage
- **🛡️ Security First**: No external dependencies, minimal attack surface

## 🎯 Advanced Features

### 🧠 Intelligence & Quality

- **📊 Advanced Table Extraction**: Powered by GMFT for complex table structures
- **🌍 Multi-language OCR**: 100+ languages with intelligent engine selection
- **📋 Rich Metadata**: Extract creation dates, authors, document properties
- **✨ Quality Processing**: Automatic text cleanup and normalization

### 🔧 Developer Experience

- **📝 TypeScript-Grade Types**: Full type safety and excellent IDE support
- **🧩 Modular Architecture**: Use only what you need, extend what you want
- **🎯 Custom Extractors**: Build domain-specific document handlers
- **🪝 Lifecycle Hooks**: Pre/post-processing customization points

### ⚡ Performance & Scale

- **🔄 Intelligent Batching**: Automatic optimization for bulk processing
- **🧵 Thread & Process Pools**: CPU-intensive tasks optimized automatically
- **💾 Memory Management**: Streaming processing for large documents
- **📈 Horizontal Scaling**: Stateless design for cloud-native scaling

## License

MIT License - see [LICENSE](LICENSE) for details.

______________________________________________________________________

<div align="center">

**[Documentation](https://goldziher.github.io/kreuzberg/) • [PyPI](https://pypi.org/project/kreuzberg/) • [Docker Hub](https://hub.docker.com/r/goldziher/kreuzberg) • [Benchmarks](https://github.com/Goldziher/python-text-extraction-libs-benchmarks) • [Discord](https://discord.gg/pXxagNK2zN)**

Made with ❤️ by the [Kreuzberg contributors](https://github.com/Goldziher/kreuzberg/graphs/contributors)

</div>
