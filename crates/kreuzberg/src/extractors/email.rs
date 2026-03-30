//! Email message extractor.

use crate::Result;
use crate::core::config::ExtractionConfig;
use crate::extractors::SyncExtractor;
use crate::plugins::{DocumentExtractor, Plugin};
use crate::types::EmailMetadata;
use crate::types::internal::InternalDocument;
use crate::types::internal_builder::InternalDocumentBuilder;
use crate::types::metadata::Metadata;
use ahash::AHashMap;
use async_trait::async_trait;
use std::borrow::Cow;
#[cfg(feature = "tokio-runtime")]
use std::path::Path;

/// Email message extractor.
///
/// Supports: .eml, .msg
pub struct EmailExtractor;

impl Default for EmailExtractor {
    fn default() -> Self {
        Self::new()
    }
}

impl EmailExtractor {
    pub fn new() -> Self {
        Self
    }
}

impl EmailExtractor {
    /// Build an `InternalDocument` from extracted email content.
    ///
    /// Pushes email headers as a metadata block, then body content as paragraphs.
    fn build_internal_document(email_result: &crate::types::EmailExtractionResult) -> InternalDocument {
        let mut builder = InternalDocumentBuilder::new("email");

        // Push email headers as a metadata block
        let mut header_entries = Vec::new();
        if let Some(ref subject) = email_result.subject {
            header_entries.push(("Subject".to_string(), subject.clone()));
        }
        if let Some(ref from) = email_result.from_email {
            header_entries.push(("From".to_string(), from.clone()));
        }
        if !email_result.to_emails.is_empty() {
            header_entries.push(("To".to_string(), email_result.to_emails.join(", ")));
        }
        if !email_result.cc_emails.is_empty() {
            header_entries.push(("CC".to_string(), email_result.cc_emails.join(", ")));
        }
        if let Some(ref date) = email_result.date {
            header_entries.push(("Date".to_string(), date.clone()));
        }
        if !header_entries.is_empty() {
            builder.push_metadata_block(&header_entries, None);
        }

        // Push body content: if HTML body is available, walk the HTML
        // document structure for richer extraction; otherwise fall back to
        // plain text paragraph splitting.
        if let Some(ref html) = email_result.html_content {
            let html_doc = crate::extraction::html::structure::build_document_structure(html);
            for node in &html_doc.nodes {
                if node.parent.is_none() {
                    match &node.content {
                        crate::types::NodeContent::Paragraph { text } => {
                            let trimmed = text.trim();
                            if !trimmed.is_empty() {
                                builder.push_paragraph(trimmed, node.annotations.clone(), None, None);
                            }
                        }
                        crate::types::NodeContent::Heading { level, text } => {
                            builder.push_heading(*level, text.as_str(), None, None);
                        }
                        crate::types::NodeContent::List { ordered } => {
                            builder.push_list(*ordered);
                            for &child_idx in &node.children {
                                if let Some(child) = html_doc.nodes.get(child_idx.0 as usize)
                                    && let crate::types::NodeContent::ListItem { text } = &child.content
                                {
                                    builder.push_list_item(text.as_str(), *ordered, vec![], None, None);
                                }
                            }
                            builder.end_list();
                        }
                        crate::types::NodeContent::Code { text, language } => {
                            builder.push_code(text.as_str(), language.as_deref(), None, None);
                        }
                        _ => {
                            if let Some(text) = node.content.text() {
                                let trimmed = text.trim();
                                if !trimmed.is_empty() {
                                    builder.push_paragraph(trimmed, node.annotations.clone(), None, None);
                                }
                            }
                        }
                    }
                }
            }
        } else {
            for paragraph in email_result.cleaned_text.split("\n\n") {
                let trimmed = paragraph.trim();
                if !trimmed.is_empty() {
                    builder.push_paragraph(trimmed, vec![], None, None);
                }
            }
        }

        builder.build()
    }
}

impl Plugin for EmailExtractor {
    fn name(&self) -> &str {
        "email-extractor"
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
}

impl SyncExtractor for EmailExtractor {
    fn extract_sync(&self, content: &[u8], mime_type: &str, config: &ExtractionConfig) -> Result<InternalDocument> {
        let fallback_codepage = config.email.as_ref().and_then(|e| e.msg_fallback_codepage);
        let email_result = crate::extraction::email::extract_email_content(content, mime_type, fallback_codepage)?;

        let attachment_names: Vec<String> = email_result
            .attachments
            .iter()
            .filter_map(|att| att.filename.clone().or_else(|| att.name.clone()))
            .collect();

        // Filter out keys already represented in EmailMetadata to avoid
        // flattened field conflicts (e.g. "attachments" as string vs Vec).
        const EMAIL_STRUCT_KEYS: &[&str] = &[
            "from_email",
            "from_name",
            "to_emails",
            "cc_emails",
            "bcc_emails",
            "message_id",
            "attachments",
            "subject",
            "date",
            "email_from",
            "email_to",
            "email_cc",
            "email_bcc",
        ];
        let mut additional = AHashMap::new();
        for (key, value) in &email_result.metadata {
            if !EMAIL_STRUCT_KEYS.contains(&key.as_str()) {
                additional.insert(Cow::Owned(key.clone()), serde_json::json!(value));
            }
        }

        // Build internal document from email content
        let mut doc = Self::build_internal_document(&email_result);
        doc.mime_type = Cow::Owned(mime_type.to_string());

        // Move fields out of email_result now that all borrows above are complete.
        let subject = email_result.subject;
        let created_at = email_result.date;
        let email_metadata = EmailMetadata {
            from_email: email_result.from_email,
            from_name: None,
            to_emails: email_result.to_emails,
            cc_emails: email_result.cc_emails,
            bcc_emails: email_result.bcc_emails,
            message_id: email_result.message_id,
            attachments: attachment_names,
        };

        doc.metadata = Metadata {
            format: Some(crate::types::FormatMetadata::Email(email_metadata)),
            subject,
            created_at,
            additional,
            ..Default::default()
        };

        Ok(doc)
    }
}

#[cfg_attr(not(target_arch = "wasm32"), async_trait)]
#[cfg_attr(target_arch = "wasm32", async_trait(?Send))]
impl DocumentExtractor for EmailExtractor {
    async fn extract_bytes(
        &self,
        content: &[u8],
        mime_type: &str,
        config: &ExtractionConfig,
    ) -> Result<InternalDocument> {
        self.extract_sync(content, mime_type, config)
    }

    #[cfg(feature = "tokio-runtime")]
    #[cfg_attr(feature = "otel", tracing::instrument(
        skip(self, path, config),
        fields(
            extractor.name = self.name(),
        )
    ))]
    async fn extract_file(&self, path: &Path, mime_type: &str, config: &ExtractionConfig) -> Result<InternalDocument> {
        let bytes = tokio::fs::read(path).await?;
        self.extract_bytes(&bytes, mime_type, config).await
    }

    fn supported_mime_types(&self) -> &[&str] {
        &["message/rfc822", "application/vnd.ms-outlook"]
    }

    fn priority(&self) -> i32 {
        50
    }

    fn as_sync_extractor(&self) -> Option<&dyn crate::extractors::SyncExtractor> {
        Some(self)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_email_extractor_plugin_interface() {
        let extractor = EmailExtractor::new();
        assert_eq!(extractor.name(), "email-extractor");
        assert!(extractor.initialize().is_ok());
        assert!(extractor.shutdown().is_ok());
    }

    #[test]
    fn test_email_extractor_supported_mime_types() {
        let extractor = EmailExtractor::new();
        let mime_types = extractor.supported_mime_types();
        assert_eq!(mime_types.len(), 2);
        assert!(mime_types.contains(&"message/rfc822"));
        assert!(mime_types.contains(&"application/vnd.ms-outlook"));
    }

    #[test]
    fn test_email_extractor_uses_config() {
        use crate::core::config::EmailConfig;

        // Extractor with email config set should not panic or error on invalid data
        let config = ExtractionConfig {
            email: Some(EmailConfig {
                msg_fallback_codepage: Some(1251),
            }),
            ..Default::default()
        };
        let extractor = EmailExtractor::new();
        // Empty data returns a validation error — config is still used without panic
        let result = extractor.extract_sync(b"", "application/vnd.ms-outlook", &config);
        assert!(result.is_err());
    }
}
