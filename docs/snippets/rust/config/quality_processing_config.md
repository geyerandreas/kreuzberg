```rust title="Rust"
use kreuzberg::{extract_file_sync, ExtractionConfig};

fn main() -> kreuzberg::Result<()> {
    let config = ExtractionConfig {
        enable_quality_processing: true,
        use_cache: true,
        ..Default::default()
    };

    let result = extract_file_sync("document.pdf", None::<&str>, &config)?;
    println!("Quality score: {}", result.quality_score);
    println!("Processing time: {:?}", result.processing_time);
    Ok(())
}
```
