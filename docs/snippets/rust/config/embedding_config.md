```rust title="Rust"
use kreuzberg::{extract_file, ExtractionConfig, ChunkingConfig, EmbeddingConfig, EmbeddingModelType};

#[tokio::main]
async fn main() -> kreuzberg::Result<()> {
    let config = ExtractionConfig {
        chunking: Some(ChunkingConfig {
            max_chars: 1000,
            max_overlap: 200,
            embedding: Some(EmbeddingConfig {
                model: EmbeddingModelType::Preset {
                    name: "balanced".to_string(),
                },
                batch_size: 16,
                normalize: true,
                show_download_progress: true,
                cache_dir: None,
            }),
            ..Default::default()
        }),
        ..Default::default()
    };

    let result = extract_file("document.pdf", None::<&str>, &config).await?;
    println!("Chunks with embeddings: {}", result.chunks.len());
    Ok(())
}
```
