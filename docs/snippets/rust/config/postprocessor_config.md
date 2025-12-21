```rust title="Rust"
use kreuzberg::{extract_file, ExtractionConfig, PostProcessorConfig};

#[tokio::main]
async fn main() -> kreuzberg::Result<()> {
    let config = ExtractionConfig {
        postprocessor: Some(PostProcessorConfig {
            enabled: true,
            enabled_processors: Some(vec![
                "whitespace_normalizer".to_string(),
                "unicode_normalizer".to_string(),
            ]),
            disabled_processors: None,
        }),
        ..Default::default()
    };

    let result = extract_file("document.pdf", None::<&str>, &config).await?;
    println!("Processed content: {}", result.content);
    Ok(())
}
```
