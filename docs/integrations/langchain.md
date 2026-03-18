# Langchain Integration

**langchain-kreuzberg** is a LangChain document loader that wraps [Kreuzberg](https://kreuzberg.dev)'s extraction API. It supports 75+ file formats out of the box, provides true async extraction powered by Rust's tokio runtime, and produces LangChain `Document` objects enriched with rich metadata including detected languages, quality scores, and extracted keywords.

For more details, see the [GitHub repository](https://github.com/kreuzberg-dev/langchain-kreuzberg).

## Installation

```bash
pip install langchain-kreuzberg
```

Requires Python 3.10+.

## Quick Start

```python
from langchain_kreuzberg import KreuzbergLoader

loader = KreuzbergLoader(file_path="report.pdf")
docs = loader.load()

print(docs[0].page_content[:200])
print(docs[0].metadata["source"])
```

## Features

- **75+ file formats** -- PDF, DOCX, PPTX, XLSX, images, HTML, Markdown, plain text, and many more
- **True async** -- native async extraction backed by Rust's tokio runtime; no thread-pool workarounds
- **Rich metadata** -- title, author, page count, detected languages, quality score, extracted keywords, and more
- **OCR with 3 backends** -- Tesseract, EasyOCR, and PaddleOCR with configurable language support
- **Per-page splitting** -- yield one `Document` per page for fine-grained RAG pipelines
- **Bytes input** -- load documents directly from raw bytes (e.g., API responses, S3 objects)
- **Output format selection** -- choose between plain text, Markdown, Djot, HTML, or structured output

## Usage Examples

### Load a PDF with defaults

```python
from langchain_kreuzberg import KreuzbergLoader

loader = KreuzbergLoader(file_path="contract.pdf")
docs = loader.load()
```

### Load multiple files

```python
loader = KreuzbergLoader(
    file_path=["report.pdf", "notes.docx", "data.xlsx"],
)
docs = loader.load()
```

### OCR a scanned document with Tesseract

```python
from kreuzberg import ExtractionConfig, OcrConfig

config = ExtractionConfig(
    force_ocr=True,
    ocr=OcrConfig(backend="tesseract", language="eng"),
)

loader = KreuzbergLoader(
    file_path="scanned.pdf",
    config=config,
)
docs = loader.load()
```

### Load all files from a directory

```python
loader = KreuzbergLoader(
    file_path="./documents/",
    glob="**/*.pdf",
)
docs = loader.load()
```

### Per-page splitting for RAG

```python
from kreuzberg import ExtractionConfig, PageConfig

config = ExtractionConfig(pages=PageConfig(extract_pages=True))

loader = KreuzbergLoader(
    file_path="handbook.pdf",
    config=config,
)
docs = loader.load()
# docs[0].metadata["page"] == 0  (zero-indexed)
```

### Async loading

```python
import asyncio
from langchain_kreuzberg import KreuzbergLoader

async def main():
    loader = KreuzbergLoader(file_path="report.pdf")
    docs = await loader.aload()
    print(f"Loaded {len(docs)} documents")

asyncio.run(main())
```
