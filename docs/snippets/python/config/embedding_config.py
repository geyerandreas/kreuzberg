from kreuzberg import EmbeddingConfig, EmbeddingModelType, ChunkingConfig, ExtractionConfig

# Example 1: Preset model (recommended)
# Fast, balanced, or quality preset configurations optimized for common use cases.
embedding_config = EmbeddingConfig(
    model=EmbeddingModelType.preset("balanced"),
    batch_size=32,
    normalize=True,
    show_download_progress=True,
    cache_dir="~/.cache/kreuzberg/embeddings",
)

# Available presets:
# - "fast" (384 dims): Quick prototyping, development, resource-constrained
# - "balanced" (768 dims): Production, general-purpose RAG, English documents
# - "quality" (1024 dims): Complex documents, maximum accuracy
# - "multilingual" (768 dims): International documents, 100+ languages


# Example 2: FastEmbed model (requires embeddings feature)
# Direct access to specific fastembed models with custom dimensions.
embedding_config = EmbeddingConfig(
    model=EmbeddingModelType.fastembed(
        model="BAAI/bge-small-en-v1.5",
        dimensions=384,
    ),
    batch_size=32,
    normalize=True,
    show_download_progress=True,
    cache_dir=None,  # Uses default: .kreuzberg/embeddings/
)

# Supported FastEmbed models:
# - "AllMiniLML6V2Q" (384 dims): Quantized, fastest
# - "BGEBaseENV15" (768 dims): Balanced quality/speed
# - "BGELargeENV15" (1024 dims): High quality, slower
# - "MultilingualE5Base" (768 dims): Multilingual support


# Example 3: Custom HuggingFace model
# For advanced users wanting specific HuggingFace embedding models.
embedding_config = EmbeddingConfig(
    model=EmbeddingModelType.custom(
        model_id="sentence-transformers/all-mpnet-base-v2",
        dimensions=768,
    ),
    batch_size=16,  # Larger model requires smaller batch size
    normalize=True,
    show_download_progress=True,
    cache_dir="/var/cache/embeddings",
)


# Integration with ChunkingConfig
# Add embeddings to your chunking configuration:
chunking_with_embeddings = ChunkingConfig(
    max_chars=1024,
    max_overlap=100,
    preset="balanced",
    embedding=EmbeddingConfig(),  # Uses balanced preset
)

extraction_config = ExtractionConfig(
    chunking=chunking_with_embeddings,
)


# Key parameter explanations:
#
# batch_size: Number of texts to embed at once (32-128 typical)
#   - Larger batches are faster but use more memory
#   - Smaller batches for resource-constrained environments
#
# normalize: Whether to normalize vectors (L2 norm)
#   - True (recommended): Enables cosine similarity in vector DBs
#   - False: Raw embedding values
#
# cache_dir: Where to store downloaded models
#   - None: Uses .kreuzberg/embeddings/ in current directory
#   - String path: Custom directory for model storage
#
# show_download_progress: Display download progress bar
#   - Useful for monitoring large model downloads
