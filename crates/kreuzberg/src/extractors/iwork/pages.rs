//! Apple Pages (.pages) extractor.

use crate::Result;
use crate::core::config::ExtractionConfig;
use crate::extractors::iwork::{dedup_text, extract_text_from_proto, read_iwa_file};
use crate::plugins::{DocumentExtractor, Plugin};
use crate::types::internal::InternalDocument;
use crate::types::internal_builder::InternalDocumentBuilder;
use async_trait::async_trait;

/// Apple Pages document extractor.
///
/// Supports `.pages` files (modern iWork format, 2013+).
///
/// Extracts all text content from the document by parsing the IWA
/// (iWork Archive) container: ZIP → Snappy → protobuf text fields.
pub struct PagesExtractor;

impl PagesExtractor {
    pub fn new() -> Self {
        Self
    }
}

impl Default for PagesExtractor {
    fn default() -> Self {
        Self::new()
    }
}

impl Plugin for PagesExtractor {
    fn name(&self) -> &str {
        "iwork-pages-extractor"
    }

    fn version(&self) -> String {
        env!("CARGO_PKG_VERSION").to_string()
    }

    fn initialize(&self) -> Result<()> {
        Ok(())
    }

    fn shutdown(&self) -> Result<()> {
        Ok(())
    }

    fn description(&self) -> &str {
        "Apple Pages (.pages) text extraction via IWA container parser"
    }

    fn author(&self) -> &str {
        "Kreuzberg Team"
    }
}

/// Parse a Pages ZIP and extract all text from IWA files.
///
/// Pages stores its content in:
/// - `Index/Document.iwa` — main document text
/// - `Index/AnnotationAuthorStorage.iwa` — comments/annotations
/// - Any `DataRecords/*.iwa` — embedded data blocks
fn parse_pages(content: &[u8]) -> Result<String> {
    // Collect all IWA paths inside the archive
    let iwa_paths = super::collect_iwa_paths(content)?;

    let mut all_texts: Vec<String> = Vec::new();

    // Attempt to read each IWA file and extract its text
    for path in &iwa_paths {
        match read_iwa_file(content, path) {
            Ok(decompressed) => {
                let texts = extract_text_from_proto(&decompressed);
                all_texts.extend(texts);
            }
            Err(_) => {
                // Some IWA files may fail decompression (e.g., newer Snappy variants)
                // Skip gracefully to produce partial results rather than hard failure
                tracing::debug!("Skipping IWA file (decompression failed): {path}");
            }
        }
    }

    let deduplicated = dedup_text(all_texts);
    Ok(deduplicated.join("\n"))
}

#[cfg_attr(not(target_arch = "wasm32"), async_trait)]
#[cfg_attr(target_arch = "wasm32", async_trait(?Send))]
impl DocumentExtractor for PagesExtractor {
    async fn extract_bytes(
        &self,
        content: &[u8],
        mime_type: &str,
        _config: &ExtractionConfig,
    ) -> Result<InternalDocument> {
        let text = {
            #[cfg(feature = "tokio-runtime")]
            if crate::core::batch_mode::is_batch_mode() {
                let content_owned = content.to_vec();
                let span = tracing::Span::current();
                tokio::task::spawn_blocking(move || {
                    let _guard = span.entered();
                    parse_pages(&content_owned)
                })
                .await
                .map_err(|e| crate::error::KreuzbergError::parsing(format!("Pages extraction task failed: {e}")))??
            } else {
                parse_pages(content)?
            }

            #[cfg(not(feature = "tokio-runtime"))]
            parse_pages(content)?
        };

        let mut doc = build_pages_internal_document(&text);
        doc.mime_type = std::borrow::Cow::Owned(mime_type.to_string());
        Ok(doc)
    }

    fn supported_mime_types(&self) -> &[&str] {
        &["application/x-iwork-pages-sffpages"]
    }

    fn priority(&self) -> i32 {
        50
    }
}

/// Build an `InternalDocument` from extracted Pages text.
///
/// Maps text content to paragraphs, mirroring `build_pages_document_structure`.
fn build_pages_internal_document(text: &str) -> InternalDocument {
    let mut builder = InternalDocumentBuilder::new("pages");

    if text.contains("\n\n") {
        for paragraph in text.split("\n\n") {
            let trimmed = paragraph.trim();
            if !trimmed.is_empty() {
                builder.push_paragraph(trimmed, vec![], None, None);
            }
        }
    } else {
        for line in text.lines() {
            let trimmed = line.trim();
            if !trimmed.is_empty() {
                builder.push_paragraph(trimmed, vec![], None, None);
            }
        }
    }

    builder.build()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pages_extractor_plugin_interface() {
        let extractor = PagesExtractor::new();
        assert_eq!(extractor.name(), "iwork-pages-extractor");
        assert!(extractor.initialize().is_ok());
        assert!(extractor.shutdown().is_ok());
    }

    #[test]
    fn test_pages_extractor_supported_mime_types() {
        let extractor = PagesExtractor::new();
        let types = extractor.supported_mime_types();
        assert!(types.contains(&"application/x-iwork-pages-sffpages"));
    }
}
