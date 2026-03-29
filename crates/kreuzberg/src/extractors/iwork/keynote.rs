//! Apple Keynote (.key) extractor.

use crate::Result;
use crate::core::config::ExtractionConfig;
use crate::extractors::iwork::{dedup_text, extract_text_from_proto, read_iwa_file};
use crate::plugins::{DocumentExtractor, Plugin};
use crate::types::internal::InternalDocument;
use crate::types::internal_builder::InternalDocumentBuilder;
use async_trait::async_trait;

/// Apple Keynote presentation extractor.
///
/// Supports `.key` files (modern iWork format, 2013+).
///
/// Extracts slide text and speaker notes from the IWA container:
/// ZIP → Snappy → protobuf text fields.
pub struct KeynoteExtractor;

impl KeynoteExtractor {
    pub fn new() -> Self {
        Self
    }
}

impl Default for KeynoteExtractor {
    fn default() -> Self {
        Self::new()
    }
}

impl Plugin for KeynoteExtractor {
    fn name(&self) -> &str {
        "iwork-keynote-extractor"
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
        "Apple Keynote (.key) text extraction via IWA container parser"
    }

    fn author(&self) -> &str {
        "Kreuzberg Team"
    }
}

/// Parse a Keynote ZIP and extract all text from IWA files.
///
/// Keynote stores its content across many IWA files:
/// - `Index/Presentation.iwa` — master slide structure and layout
/// - `Index/Slide_*.iwa` — individual slide content and speaker notes
/// - `Index/MasterSlide_*.iwa` — master slide text
fn parse_keynote(content: &[u8]) -> Result<String> {
    let iwa_paths = super::collect_iwa_paths(content)?;

    let mut all_texts: Vec<String> = Vec::new();

    // Prioritize slide IWA files for more structured output
    let slide_paths: Vec<&String> = iwa_paths
        .iter()
        .filter(|p| p.contains("Slide") || p.contains("Presentation"))
        .collect();

    let other_paths: Vec<&String> = iwa_paths
        .iter()
        .filter(|p| !p.contains("Slide") && !p.contains("Presentation"))
        .collect();

    for path in slide_paths.iter().chain(other_paths.iter()) {
        match read_iwa_file(content, path) {
            Ok(decompressed) => {
                let texts = extract_text_from_proto(&decompressed);
                all_texts.extend(texts);
            }
            Err(_) => {
                tracing::debug!("Skipping IWA file (decompression failed): {path}");
            }
        }
    }

    let deduplicated = dedup_text(all_texts);
    Ok(deduplicated.join("\n"))
}

#[cfg_attr(not(target_arch = "wasm32"), async_trait)]
#[cfg_attr(target_arch = "wasm32", async_trait(?Send))]
impl DocumentExtractor for KeynoteExtractor {
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
                    parse_keynote(&content_owned)
                })
                .await
                .map_err(|e| crate::error::KreuzbergError::parsing(format!("Keynote extraction task failed: {e}")))??
            } else {
                parse_keynote(content)?
            }

            #[cfg(not(feature = "tokio-runtime"))]
            parse_keynote(content)?
        };

        let mut doc = build_keynote_internal_document(&text);
        doc.mime_type = std::borrow::Cow::Owned(mime_type.to_string());
        Ok(doc)
    }

    fn supported_mime_types(&self) -> &[&str] {
        &["application/x-iwork-keynote-sffkey"]
    }

    fn priority(&self) -> i32 {
        50
    }
}

/// Build an `InternalDocument` from extracted Keynote text.
///
/// Maps text lines to slides with paragraphs, mirroring `build_keynote_document_structure`.
fn build_keynote_internal_document(text: &str) -> InternalDocument {
    let mut builder = InternalDocumentBuilder::new("keynote");
    let mut slide_number: u32 = 0;

    let lines: Vec<&str> = text.lines().collect();
    let mut i = 0;
    while i < lines.len() {
        if lines[i].trim().is_empty() {
            i += 1;
            continue;
        }

        slide_number += 1;
        let first_line = lines[i].trim();
        builder.push_slide(slide_number, Some(first_line), None);
        i += 1;

        while i < lines.len() && !lines[i].trim().is_empty() {
            builder.push_paragraph(lines[i].trim(), vec![], None, None);
            i += 1;
        }
    }

    if slide_number == 0 && !text.trim().is_empty() {
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
    fn test_keynote_extractor_plugin_interface() {
        let extractor = KeynoteExtractor::new();
        assert_eq!(extractor.name(), "iwork-keynote-extractor");
        assert!(extractor.initialize().is_ok());
        assert!(extractor.shutdown().is_ok());
    }

    #[test]
    fn test_keynote_extractor_supported_mime_types() {
        let extractor = KeynoteExtractor::new();
        let types = extractor.supported_mime_types();
        assert!(types.contains(&"application/x-iwork-keynote-sffkey"));
    }
}
