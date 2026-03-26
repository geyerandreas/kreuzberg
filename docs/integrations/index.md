# Integrations

Kreuzberg integrations connect extracted document content to external databases for storage, indexing, and search.

Each integration is a standalone package that manages schema setup, content deduplication, and index configuration against the target system.

---

## Available integrations

| Integration | Target | Package | Search capabilities | Status |
|---|---|---|---|---|
| [SurrealDB](surrealdb.md) | [SurrealDB](https://surrealdb.com/) | [`kreuzberg-surrealdb`](https://pypi.org/project/kreuzberg-surrealdb/) | BM25, Vector (HNSW), Hybrid (RRF¹) | :white_check_mark: Stable |

¹ RRF = Reciprocal Rank Fusion — combines results from multiple search strategies into a single ranked list.

!!! tip "Building a new integration?"
    Use the [SurrealDB integration](https://github.com/kreuzberg-dev/kreuzberg-surrealdb) as the reference implementation.