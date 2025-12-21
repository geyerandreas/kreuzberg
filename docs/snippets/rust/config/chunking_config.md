```rust title="Rust"
use kreuzberg::{extract_file, ExtractionConfig, ChunkingConfig};

#[tokio::main]
async fn main() -> kreuzberg::Result<()> {
    let config = ExtractionConfig {
        chunking: Some(ChunkingConfig {
            max_chars: 1000,
            max_overlap: 200,
            ..Default::default()
        }),
        ..Default::default()
    };

    let result = extract_file("document.pdf", None::<&str>, &config).await?;
    println!("Chunks: {}", result.chunks.len());
    for chunk in &result.chunks {
        println!("Length: {}", chunk.content.len());
    }
    Ok(())
}
```
