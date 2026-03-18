# SurrealDB Integration

The `kreuzberg-surrealdb` package provides seamless integration between Kreuzberg's text extraction capabilities and SurrealDB, allowing you to ingest documents directly into SurrealDB with automated schema management, chunking, and embedding support.

For more details, see the [GitHub repository](https://github.com/kreuzberg-dev/kreuzberg-surrealdb).

## Features

- **Automated schema management** — generates SurrealDB tables, BM25/HNSW indexes, and analyzers via `setup_schema()`
- **Content deduplication** — SHA-256 content hashing with deterministic record IDs prevents duplicates across ingestion runs
- **Two-tier architecture** — `DocumentConnector` for full documents, `DocumentPipeline` for chunked + embedded documents
- **Flexible embedding control** — use preset models, custom ONNX models via kreuzberg's `EmbeddingModelType`, or disable embeddings entirely with `embed=False`
- **Record-linked chunks** — chunks reference their parent document via SurrealDB record links, enabling join-like traversal in SurQL
- **Configurable indexing** — tune BM25 (k1, b, analyzer language) and HNSW (distance metric, EFC, M) parameters per schema
- **Batch ingestion** — ingest single files, multiple files, directories (with glob), or raw bytes, with configurable `insert_batch_size`

## Installation

```bash
pip install kreuzberg-surrealdb
```

Requires Python 3.10+.

## Quickstart

### Document-level search with `DocumentConnector`

Extract full documents and search with BM25. No chunking, no embeddings — fast and simple.

```python
import asyncio
from surrealdb import AsyncSurreal
from kreuzberg_surrealdb import DocumentConnector

async def main():
    db = AsyncSurreal("ws://localhost:8000")
    await db.connect()
    await db.signin({"username": "root", "password": "root"})
    await db.use("default", "default")

    connector = DocumentConnector(db=db)
    await connector.setup_schema()
    await connector.ingest_file("report.pdf")

    # BM25 full-text search via the SurrealDB client
    t = connector.table
    results = await connector.client.query(
        f"SELECT *, search::score(1) AS score FROM {t} "
        f"WHERE content @1@ $query ORDER BY score DESC LIMIT $limit",
        {"query": "quarterly revenue", "limit": 5},
    )
    for r in results:
        print(r["source"], r["score"])

    await db.close()

asyncio.run(main())
```

### Hybrid search with `DocumentPipeline`

Chunk documents, generate embeddings, and search with vector + BM25 fused via Reciprocal Rank Fusion.

```python
import asyncio
from surrealdb import AsyncSurreal
from kreuzberg_surrealdb import DocumentPipeline

async def main():
    async with AsyncSurreal("ws://localhost:8000") as db:
        await db.signin({"username": "root", "password": "root"})
        await db.use("myapp", "knowledge_base")

        pipeline = DocumentPipeline(db=db, embed=True, embedding_model="balanced")
        await pipeline.setup_schema()
        await pipeline.ingest_directory("./papers", glob="**/*.pdf")

        ct = pipeline.chunk_table

        # Hybrid search (vector + BM25 with RRF)
        embedding = await pipeline.embed_query("attention mechanisms in transformers")
        results = await pipeline.client.query(
            f"SELECT * FROM search::rrf(["
            f"(SELECT id, content FROM {ct} WHERE embedding <|10,COSINE|> $embedding),"
            f"(SELECT id, content, search::score(1) AS score FROM {ct} "
            f"WHERE content @1@ $query ORDER BY score DESC LIMIT 10)"
            f"], 10, 60);",
            {"embedding": embedding, "query": "attention mechanisms in transformers"},
        )

asyncio.run(main())
```
