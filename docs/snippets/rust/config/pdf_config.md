```rust title="Rust"
use kreuzberg::{extract_file_sync, ExtractionConfig, PdfConfig};

fn main() -> kreuzberg::Result<()> {
    let config = ExtractionConfig {
        pdf_options: Some(PdfConfig {
            extract_images: true,
            passwords: Some(vec!["password123".to_string()]),
            extract_metadata: true,
        }),
        ..Default::default()
    };

    let result = extract_file_sync("encrypted.pdf", None::<&str>, &config)?;
    println!("Title: {:?}", result.metadata.get("title"));
    println!("Author: {:?}", result.metadata.get("author"));
    Ok(())
}
```
