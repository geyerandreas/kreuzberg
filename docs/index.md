# Kreuzberg

Kreuzberg is an advanced open source document intelligence framework built for production workloads. Designed by engineers for reliability and performance, it transforms PDFs, images, and office documents into structured data with minimal complexity.

Built on proven technologies including PDFium, Tesseract, and Pandoc, Kreuzberg delivers enterprise-grade document processing capabilities while maintaining simplicity and speed.

## Why Kreuzberg?

Kreuzberg addresses real production needs with measurable benefits. While not exclusively a complete solution, it integrates well with existing pipelines and can be deployed alongside other tools based on specific requirements.

### 🚀 Performance

- [benchmarked as the fastest framework](https://goldziher.github.io/python-text-extraction-libs-benchmarks/) - 6-126x
    faster than competitors
- Minimal footprint: 87MB install vs 1GB+ for competitors
- Lowest memory usage (~360MB average) optimized for production workloads
- Edge and serverless ready - deploy anywhere without heavy dependencies

### 🛠️ Engineering Quality

- Built by software engineers with modern Python best practices
- 95%+ test coverage with comprehensive test suite
- Thoroughly benchmarked and profiled for real-world performance
- Only framework offering true async/await support alongside sync APIs
- Robust error handling and detailed logging

### 🎯 Developer Experience

- Works out of the box with sane defaults, scales with your needs
- Native MCP server for AI tool integration (Claude Desktop, Cursor)
- Full type safety with excellent IDE support (completions)
- Comprehensive documentation including full API reference

### 🌍 Deployment Options

- Docker images for all architectures (AMD64, ARM64)
- Cloud native - AWS Lambda, Google Cloud Functions, Azure Functions
- Supports both CPU and GPU processing (PaddleOCR, EasyOCR)
- Local processing - no external API dependencies
- Multiple deployment modes: CLI, REST API, MCP server

### 🎯 Complete Solution

- Comprehensive format support: PDFs, images, Office docs, HTML, spreadsheets, presentations
- Multiple OCR engines: Tesseract, EasyOCR, PaddleOCR with intelligent fallbacks
- Advanced features: Table extraction, metadata extraction, content chunking for RAG
- Production tools: REST API, CLI tools, batch processing, custom extractors
- Fully extensible: Add your own extractors

## Perfect for Modern Applications

Kreuzberg was architected for **RAG (Retrieval Augmented Generation)** applications, **serverless functions**, and \*
*cloud-native deployments*\*. Whether you're building AI applications, processing pipelines, or document management
systems, Kreuzberg delivers unmatched performance with minimal complexity.
