//! HTML document extractor.

use super::annotation_utils::adjust_annotations_for_trim;
use crate::Result;
use crate::core::config::{ExtractionConfig, OutputFormat};
use crate::extractors::SyncExtractor;
use crate::plugins::{DocumentExtractor, Plugin};
use crate::text::utf8_validation;
use crate::types::document_structure::TextAnnotation;
use crate::types::extraction::ExtractedImage;
use crate::types::internal::InternalDocument;
use crate::types::internal::RelationshipKind;
use crate::types::internal::RelationshipTarget;
use crate::types::internal_builder::InternalDocumentBuilder;
use crate::types::{HtmlMetadata, Metadata, Table};
use async_trait::async_trait;
use bytes::Bytes;
use html_to_markdown_rs::InlineImageFormat;
use std::borrow::Cow;
#[cfg(feature = "tokio-runtime")]
use std::path::Path;

/// HTML document extractor using html-to-markdown.
pub struct HtmlExtractor;

impl Default for HtmlExtractor {
    fn default() -> Self {
        Self::new()
    }
}

impl HtmlExtractor {
    pub fn new() -> Self {
        Self
    }
}

impl HtmlExtractor {
    /// Build an `InternalDocument` from raw HTML source.
    ///
    /// Captures structural elements, anchor IDs, internal links (`href="#..."`),
    /// figcaption-to-figure relationships, and label-for relationships.
    pub fn build_internal_document(html: &str) -> InternalDocument {
        let mut b = InternalDocumentBuilder::new("html");

        // Tracking state for the tag-level parser
        let mut text_buf = String::new();
        let mut text_annotations: Vec<TextAnnotation> = Vec::new();
        // Annotation tracking: stack of (kind_tag: u8, start_offset: u32, optional_url: Option<String>)
        // kind_tag: 0=bold, 1=italic, 2=code, 3=link
        let mut annotation_starts: Vec<(u8, u32, Option<String>)> = Vec::new();
        let mut pending_id: Option<String> = None;
        let mut pending_tag: Option<String> = None; // current block-level tag
        let mut in_pre = false;
        let mut pre_lang: Option<String> = None;
        let mut pre_text = String::new();
        let mut list_stack: Vec<bool> = Vec::new();
        let mut table_rows: Vec<Vec<String>> = Vec::new();
        let mut in_table = false;
        let mut in_cell = false;
        let mut cell_text = String::new();
        let mut current_row: Vec<String> = Vec::new();
        let mut in_figure = false;
        let mut figure_element_idx: Option<u32> = None;
        let mut in_figcaption = false;
        let mut figcaption_text = String::new();
        // Deferred: (source_element_idx, target_key, kind) — source=u32::MAX means "next element"
        let mut deferred_rels: Vec<(u32, String, RelationshipKind)> = Vec::new();

        let bytes = html.as_bytes();
        let mut pos = 0;

        while pos < html.len() {
            // Skip HTML comments
            if html[pos..].starts_with("<!--") {
                if let Some(end) = html[pos..].find("-->") {
                    pos += end + 3;
                } else {
                    break;
                }
                continue;
            }

            if bytes[pos] == b'<' {
                let Some(end) = html[pos..].find('>') else { break };
                let tag_content = &html[pos + 1..pos + end];
                pos += end + 1;

                let is_closing = tag_content.starts_with('/');
                let raw_tag = if is_closing { &tag_content[1..] } else { tag_content };
                let name_end = raw_tag
                    .find(|c: char| c.is_whitespace() || c == '/' || c == '>')
                    .unwrap_or(raw_tag.len());
                let tag_name = raw_tag[..name_end].to_ascii_lowercase();
                let attrs_str = raw_tag[name_end..].trim_end_matches('/');

                if is_closing {
                    match tag_name.as_str() {
                        "h1" | "h2" | "h3" | "h4" | "h5" | "h6" => {
                            let level: u8 = tag_name[1..].parse().unwrap_or(1);
                            let text = std::mem::take(&mut text_buf);
                            let trimmed = text.trim();
                            if !trimmed.is_empty() {
                                let annotations =
                                    adjust_annotations_for_trim(std::mem::take(&mut text_annotations), &text, trimmed);
                                let idx = b.push_heading(level, trimmed, None, None);
                                if !annotations.is_empty() {
                                    b.set_annotations(idx, annotations);
                                }
                                if let Some(id) = pending_id.take() {
                                    b.set_anchor(idx, &id);
                                }
                                Self::resolve_deferred(&mut deferred_rels, &mut b, idx);
                            } else {
                                text_annotations.clear();
                            }
                            annotation_starts.clear();
                            pending_tag = None;
                        }
                        "p" => {
                            let text = std::mem::take(&mut text_buf);
                            let trimmed = text.trim();
                            if !trimmed.is_empty() {
                                let annotations =
                                    adjust_annotations_for_trim(std::mem::take(&mut text_annotations), &text, trimmed);
                                let idx = b.push_paragraph(trimmed, annotations, None, None);
                                if let Some(id) = pending_id.take() {
                                    b.set_anchor(idx, &id);
                                }
                                Self::resolve_deferred(&mut deferred_rels, &mut b, idx);
                            } else {
                                text_annotations.clear();
                            }
                            annotation_starts.clear();
                            pending_tag = None;
                        }
                        "li" => {
                            let text = std::mem::take(&mut text_buf);
                            let trimmed = text.trim();
                            let ordered = list_stack.last().copied().unwrap_or(false);
                            if !trimmed.is_empty() {
                                let annotations =
                                    adjust_annotations_for_trim(std::mem::take(&mut text_annotations), &text, trimmed);
                                let idx = b.push_list_item(trimmed, ordered, annotations, None, None);
                                if let Some(id) = pending_id.take() {
                                    b.set_anchor(idx, &id);
                                }
                            } else {
                                text_annotations.clear();
                            }
                            annotation_starts.clear();
                        }
                        "ul" | "ol" => {
                            list_stack.pop();
                            b.end_list();
                        }
                        "pre" => {
                            if in_pre {
                                let code = std::mem::take(&mut pre_text);
                                let lang = pre_lang.take();
                                b.push_code(&code, lang.as_deref(), None, None);
                                in_pre = false;
                            }
                        }
                        "code" if !in_pre => {
                            // Inline code annotation
                            if let Some(i) = annotation_starts.iter().rposition(|(k, _, _)| *k == 2) {
                                let (_, start, _) = annotation_starts.remove(i);
                                let end = text_buf.len() as u32;
                                if start < end {
                                    text_annotations.push(crate::types::builder::code(start, end));
                                }
                            }
                        }
                        "code" => {} // handled by </pre>
                        "strong" | "b" => {
                            if let Some(i) = annotation_starts.iter().rposition(|(k, _, _)| *k == 0) {
                                let (_, start, _) = annotation_starts.remove(i);
                                let end = text_buf.len() as u32;
                                if start < end {
                                    text_annotations.push(crate::types::builder::bold(start, end));
                                }
                            }
                        }
                        "em" | "i" => {
                            if let Some(i) = annotation_starts.iter().rposition(|(k, _, _)| *k == 1) {
                                let (_, start, _) = annotation_starts.remove(i);
                                let end = text_buf.len() as u32;
                                if start < end {
                                    text_annotations.push(crate::types::builder::italic(start, end));
                                }
                            }
                        }
                        "a" => {
                            if let Some(i) = annotation_starts.iter().rposition(|(k, _, _)| *k == 3) {
                                let (_, start, url_opt) = annotation_starts.remove(i);
                                let end = text_buf.len() as u32;
                                if start < end
                                    && let Some(url) = url_opt
                                {
                                    text_annotations.push(crate::types::builder::link(start, end, &url, None));
                                }
                            }
                        }
                        "td" | "th" => {
                            if in_cell {
                                current_row.push(std::mem::take(&mut cell_text).trim().to_string());
                                in_cell = false;
                            }
                        }
                        "tr" => {
                            if !current_row.is_empty() {
                                table_rows.push(std::mem::take(&mut current_row));
                            }
                        }
                        "table" => {
                            if in_table && !table_rows.is_empty() {
                                let cells = std::mem::take(&mut table_rows);
                                b.push_table_from_cells(&cells, None, None);
                            }
                            in_table = false;
                        }
                        "figure" => {
                            in_figure = false;
                            figure_element_idx = None;
                        }
                        "figcaption" => {
                            if in_figcaption {
                                let cap = std::mem::take(&mut figcaption_text);
                                let cap = cap.trim();
                                if !cap.is_empty() {
                                    let cap_idx = b.push_paragraph(cap, vec![], None, None);
                                    if let Some(fig_idx) = figure_element_idx {
                                        b.push_relationship(
                                            cap_idx,
                                            RelationshipTarget::Index(fig_idx),
                                            RelationshipKind::Caption,
                                        );
                                    }
                                }
                                in_figcaption = false;
                            }
                        }
                        _ => {}
                    }
                } else {
                    // Opening tag
                    let id_attr = extract_attr(attrs_str, "id");

                    match tag_name.as_str() {
                        "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "p" => {
                            // Flush stale text
                            let prev = std::mem::take(&mut text_buf);
                            let prev = prev.trim().to_string();
                            if !prev.is_empty() {
                                b.push_paragraph(&prev, vec![], None, None);
                            }
                            pending_id = id_attr;
                            pending_tag = Some(tag_name.clone());
                        }
                        "ul" => {
                            list_stack.push(false);
                            b.push_list(false);
                        }
                        "ol" => {
                            list_stack.push(true);
                            b.push_list(true);
                        }
                        "li" => {
                            text_buf.clear();
                            pending_id = id_attr;
                        }
                        "pre" => {
                            in_pre = true;
                            pre_text.clear();
                            pre_lang = None;
                        }
                        "code" if in_pre => {
                            if let Some(cls) = extract_attr(attrs_str, "class") {
                                for part in cls.split_whitespace() {
                                    if let Some(lang) = part.strip_prefix("language-") {
                                        pre_lang = Some(lang.to_string());
                                        break;
                                    }
                                }
                            }
                        }
                        "code" => {
                            // Inline code — track annotation start
                            annotation_starts.push((2, text_buf.len() as u32, None));
                        }
                        "strong" | "b" => {
                            annotation_starts.push((0, text_buf.len() as u32, None));
                        }
                        "em" | "i" => {
                            annotation_starts.push((1, text_buf.len() as u32, None));
                        }
                        "table" => {
                            in_table = true;
                            table_rows.clear();
                        }
                        "td" | "th" => {
                            in_cell = true;
                            cell_text.clear();
                        }
                        "tr" => {
                            current_row = Vec::new();
                        }
                        "img" => {
                            let alt = extract_attr(attrs_str, "alt").unwrap_or_default();
                            let idx = b.push_paragraph(&format!("[image: {}]", alt), vec![], None, None);
                            if let Some(ref id) = id_attr {
                                b.set_anchor(idx, id.as_str());
                            }
                            if in_figure {
                                figure_element_idx = Some(idx);
                            }
                        }
                        "figure" => {
                            in_figure = true;
                            figure_element_idx = None;
                        }
                        "figcaption" => {
                            in_figcaption = true;
                            figcaption_text.clear();
                        }
                        "a" => {
                            if let Some(href) = extract_attr(attrs_str, "href") {
                                if let Some(target_id) = href.strip_prefix('#') {
                                    // Mark u32::MAX to mean "associate with next pushed element"
                                    deferred_rels.push((
                                        u32::MAX,
                                        target_id.to_string(),
                                        RelationshipKind::InternalLink,
                                    ));
                                }
                                // Track link annotation for inline text
                                annotation_starts.push((3, text_buf.len() as u32, Some(href)));
                            }
                        }
                        "label" => {
                            if let Some(for_id) = extract_attr(attrs_str, "for") {
                                deferred_rels.push((u32::MAX, for_id, RelationshipKind::Label));
                            }
                        }
                        _ => {
                            // Any element with an id: push a placeholder so anchors are available
                            if let Some(id) = id_attr {
                                // If we're inside a block element, set pending_id
                                if pending_tag.is_some() {
                                    // nested element inside a block: store for later
                                } else {
                                    // standalone element with id — create a group marker
                                    let idx = b.push_paragraph("", vec![], None, None);
                                    b.set_anchor(idx, &id);
                                }
                                let _ = id;
                            }
                        }
                    }
                }
            } else {
                // Text content
                let start = pos;
                while pos < html.len() && bytes[pos] != b'<' {
                    pos += 1;
                }
                let raw = &html[start..pos];
                let decoded = decode_html_entities(raw);

                if in_pre {
                    pre_text.push_str(&decoded);
                } else if in_cell {
                    cell_text.push_str(&decoded);
                } else if in_figcaption {
                    figcaption_text.push_str(&decoded);
                } else {
                    text_buf.push_str(&decoded);
                }
            }
        }

        // Flush remaining text
        let remaining = text_buf.trim().to_string();
        if !remaining.is_empty() {
            let annotations = adjust_annotations_for_trim(std::mem::take(&mut text_annotations), &text_buf, &remaining);
            b.push_paragraph(&remaining, annotations, None, None);
        }

        // Emit any remaining deferred relationships as Key-based
        let mut doc = b.build();
        for (source, target_key, kind) in deferred_rels {
            if source != u32::MAX {
                doc.push_relationship(crate::types::internal::Relationship {
                    source,
                    target: RelationshipTarget::Key(target_key),
                    kind,
                });
            }
            // u32::MAX entries that weren't resolved are dropped — they belonged to
            // anchor links in non-structural positions.
        }

        doc
    }

    /// Resolve deferred relationships whose source is `u32::MAX` (meaning "next element").
    fn resolve_deferred(
        deferred: &mut Vec<(u32, String, RelationshipKind)>,
        b: &mut InternalDocumentBuilder,
        current_idx: u32,
    ) {
        let mut i = 0;
        while i < deferred.len() {
            if deferred[i].0 == u32::MAX {
                let (_, target_key, kind) = deferred.remove(i);
                b.push_relationship(current_idx, RelationshipTarget::Key(target_key), kind);
            } else {
                i += 1;
            }
        }
    }
}

/// Extract an attribute value from an HTML tag's attribute string.
fn extract_attr(attrs: &str, name: &str) -> Option<String> {
    // Case-insensitive search for name=
    let lower_attrs = attrs.to_ascii_lowercase();
    let search = format!("{}=", name.to_ascii_lowercase());
    let pos = lower_attrs.find(&search)?;
    let after = &attrs[pos + search.len()..];
    let after = after.trim_start();
    if let Some(inner) = after.strip_prefix('"') {
        let end = inner.find('"')?;
        Some(inner[..end].to_string())
    } else if let Some(inner) = after.strip_prefix('\'') {
        let end = inner.find('\'')?;
        Some(inner[..end].to_string())
    } else {
        let end = after
            .find(|c: char| c.is_whitespace() || c == '>' || c == '/')
            .unwrap_or(after.len());
        Some(after[..end].to_string())
    }
}

/// Decode common HTML entities.
fn decode_html_entities(s: &str) -> String {
    s.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
        .replace("&#39;", "'")
        .replace("&apos;", "'")
        .replace("&nbsp;", " ")
}

impl Plugin for HtmlExtractor {
    fn name(&self) -> &str {
        "html-extractor"
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

impl SyncExtractor for HtmlExtractor {
    fn extract_sync(&self, content: &[u8], mime_type: &str, config: &ExtractionConfig) -> Result<InternalDocument> {
        let html = utf8_validation::from_utf8(content)
            .map(|s| s.to_string())
            .unwrap_or_else(|_| String::from_utf8_lossy(content).into_owned());

        let (_content_text, html_metadata, table_data) = crate::extraction::html::convert_html_to_markdown_with_tables(
            &html,
            config.html_options.clone(),
            Some(config.output_format),
        )?;

        let tables: Vec<Table> = table_data
            .into_iter()
            .enumerate()
            .map(|(i, t)| {
                let grid = &t.grid;
                let mut cells = vec![vec![String::new(); grid.cols as usize]; grid.rows as usize];
                for cell in &grid.cells {
                    if (cell.row as usize) < cells.len() && (cell.col as usize) < cells[0].len() {
                        cells[cell.row as usize][cell.col as usize] = cell.content.clone();
                    }
                }
                Table {
                    cells,
                    markdown: t.markdown,
                    page_number: i + 1,
                    bounding_box: None,
                }
            })
            .collect();

        let format_metadata = html_metadata.map(|m: HtmlMetadata| crate::types::FormatMetadata::Html(Box::new(m)));

        // Signal that the extractor already formatted the output so the pipeline
        // does not double-convert.
        let pre_formatted = match config.output_format {
            OutputFormat::Markdown => Some("markdown".to_string()),
            OutputFormat::Djot => Some("djot".to_string()),
            _ => None,
        };

        // Build InternalDocument from the original HTML.
        let mut doc = Self::build_internal_document(&html);
        doc.metadata = Metadata {
            output_format: pre_formatted,
            format: format_metadata,
            ..Default::default()
        };
        doc.mime_type = std::borrow::Cow::Owned(mime_type.to_string());

        // Add tables to InternalDocument
        for table in tables {
            doc.push_table(table);
        }

        // Extract inline images when image extraction is configured
        let should_extract_images = config.images.as_ref().map(|i| i.extract_images).unwrap_or(false);

        if should_extract_images {
            let inline_images =
                crate::extraction::html::extract_html_inline_images(&html, config.html_options.clone())?;

            for (i, img) in inline_images.into_iter().enumerate() {
                let (width, height) = img.dimensions.map_or((None, None), |(w, h)| (Some(w), Some(h)));
                let format: Cow<'static, str> = match img.format {
                    InlineImageFormat::Png => Cow::Borrowed("png"),
                    InlineImageFormat::Jpeg => Cow::Borrowed("jpeg"),
                    InlineImageFormat::Gif => Cow::Borrowed("gif"),
                    InlineImageFormat::Bmp => Cow::Borrowed("bmp"),
                    InlineImageFormat::Webp => Cow::Borrowed("webp"),
                    InlineImageFormat::Svg => Cow::Borrowed("svg"),
                    InlineImageFormat::Other(ref s) => Cow::Owned(s.clone()),
                };

                let extracted = ExtractedImage {
                    data: Bytes::from(img.data),
                    format,
                    image_index: i,
                    page_number: None,
                    width,
                    height,
                    colorspace: None,
                    bits_per_component: None,
                    is_mask: false,
                    description: img.description,
                    ocr_result: None,
                    bounding_box: None,
                    source_path: None,
                };
                doc.push_image(extracted);
            }
        }

        Ok(doc)
    }
}

#[cfg_attr(not(target_arch = "wasm32"), async_trait)]
#[cfg_attr(target_arch = "wasm32", async_trait(?Send))]
impl DocumentExtractor for HtmlExtractor {
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
        &["text/html", "application/xhtml+xml"]
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

    /// Helper to extract tables from HTML using the unified converter.
    fn extract_tables(html: &str) -> Vec<Table> {
        let (_, _, table_data): (String, _, Vec<html_to_markdown_rs::types::TableData>) =
            crate::extraction::html::convert_html_to_markdown_with_tables(html, None, None).unwrap();
        table_data
            .into_iter()
            .enumerate()
            .map(|(i, t)| {
                let grid = &t.grid;
                let mut cells = vec![vec![String::new(); grid.cols as usize]; grid.rows as usize];
                for cell in &grid.cells {
                    if (cell.row as usize) < cells.len() && (cell.col as usize) < cells[0].len() {
                        cells[cell.row as usize][cell.col as usize] = cell.content.clone();
                    }
                }
                Table {
                    cells,
                    markdown: t.markdown,
                    page_number: i + 1,
                    bounding_box: None,
                }
            })
            .collect()
    }

    #[test]
    fn test_html_extractor_plugin_interface() {
        let extractor = HtmlExtractor::new();
        assert_eq!(extractor.name(), "html-extractor");
        assert!(extractor.initialize().is_ok());
        assert!(extractor.shutdown().is_ok());
    }

    #[test]
    fn test_html_extractor_supported_mime_types() {
        let extractor = HtmlExtractor::new();
        let mime_types = extractor.supported_mime_types();
        assert_eq!(mime_types.len(), 2);
        assert!(mime_types.contains(&"text/html"));
        assert!(mime_types.contains(&"application/xhtml+xml"));
    }

    #[test]
    fn test_extract_html_tables_basic() {
        let html = r#"
            <table>
                <tr><th>Header1</th><th>Header2</th></tr>
                <tr><td>Row1Col1</td><td>Row1Col2</td></tr>
                <tr><td>Row2Col1</td><td>Row2Col2</td></tr>
            </table>
        "#;

        let tables = extract_tables(html);
        assert_eq!(tables.len(), 1);

        let table = &tables[0];
        assert_eq!(table.cells.len(), 3);
        assert_eq!(table.cells[0], vec!["Header1", "Header2"]);
        assert_eq!(table.cells[1], vec!["Row1Col1", "Row1Col2"]);
        assert_eq!(table.cells[2], vec!["Row2Col1", "Row2Col2"]);
        assert_eq!(table.page_number, 1);
        assert!(table.markdown.contains("Header1"));
        assert!(table.markdown.contains("Row1Col1"));
    }

    #[test]
    fn test_extract_html_tables_multiple() {
        let html = r#"
            <table>
                <tr><th>Table1</th></tr>
                <tr><td>Data1</td></tr>
            </table>
            <p>Some text</p>
            <table>
                <tr><th>Table2</th></tr>
                <tr><td>Data2</td></tr>
            </table>
        "#;

        let tables = extract_tables(html);
        assert_eq!(tables.len(), 2);
        assert_eq!(tables[0].page_number, 1);
        assert_eq!(tables[1].page_number, 2);
    }

    #[test]
    fn test_extract_html_tables_no_thead() {
        let html = r#"
            <table>
                <tr><td>Cell1</td><td>Cell2</td></tr>
                <tr><td>Cell3</td><td>Cell4</td></tr>
            </table>
        "#;

        let tables = extract_tables(html);
        assert_eq!(tables.len(), 1);

        let table = &tables[0];
        assert_eq!(table.cells.len(), 2);
        assert_eq!(table.cells[0], vec!["Cell1", "Cell2"]);
        assert_eq!(table.cells[1], vec!["Cell3", "Cell4"]);
    }

    #[test]
    fn test_extract_html_tables_empty() {
        let html = "<p>No tables here</p>";
        let tables = extract_tables(html);
        assert_eq!(tables.len(), 0);
    }

    #[test]
    fn test_extract_html_tables_with_nested_elements() {
        let html = r#"
            <table>
                <tr><th>Header <strong>Bold</strong></th></tr>
                <tr><td>Data with <em>emphasis</em></td></tr>
            </table>
        "#;

        let tables = extract_tables(html);
        assert_eq!(tables.len(), 1);

        let table = &tables[0];
        assert!(table.cells[0][0].contains("Header"));
        assert!(table.cells[0][0].contains("Bold"));
        assert!(table.cells[1][0].contains("Data with"));
        assert!(table.cells[1][0].contains("emphasis"));
    }

    #[test]
    fn test_extract_nested_html_tables() {
        let html = r#"
            <table>
                <tr>
                    <th>Category</th>
                    <th>Details &amp; Nested Data</th>
                </tr>
                <tr>
                    <td><strong>Project Alpha</strong></td>
                    <td>
                    <table>
                        <tr><th>Task ID</th><th>Status</th><th>Priority</th></tr>
                        <tr><td>001</td><td>Completed</td><td>High</td></tr>
                        <tr><td>002</td><td>In Progress</td><td>Medium</td></tr>
                    </table>
                    </td>
                </tr>
                <tr>
                    <td><strong>Project Beta</strong></td>
                    <td>No sub-tasks assigned yet.</td>
                </tr>
            </table>
        "#;

        let tables = extract_tables(html);

        // Should find at least 2 tables: outer + nested
        assert!(
            tables.len() >= 2,
            "Expected at least 2 tables (outer + nested), found {}",
            tables.len()
        );

        // Find the nested table (has Task ID header)
        let nested = tables
            .iter()
            .find(|t| {
                t.cells
                    .first()
                    .is_some_and(|row| row.iter().any(|c| c.contains("Task ID")))
            })
            .expect("Should find nested table with Task ID header");

        assert_eq!(nested.cells[0].len(), 3, "Nested table header should have 3 columns");
        assert!(nested.cells[0][0].contains("Task ID"));
        assert!(nested.cells[0][1].contains("Status"));
        assert!(nested.cells[0][2].contains("Priority"));
        assert_eq!(
            nested.cells.len(),
            3,
            "Nested table should have 3 rows (header + 2 data)"
        );
        assert!(nested.cells[1][0].contains("001"));
        assert!(nested.cells[1][1].contains("Completed"));
        assert!(nested.cells[2][0].contains("002"));
        assert!(nested.cells[2][1].contains("In Progress"));
    }

    #[tokio::test]
    async fn test_html_extractor_with_table() {
        let html = r#"
            <html>
                <body>
                    <h1>Test Page</h1>
                    <table>
                        <tr><th>Name</th><th>Age</th></tr>
                        <tr><td>Alice</td><td>30</td></tr>
                        <tr><td>Bob</td><td>25</td></tr>
                    </table>
                </body>
            </html>
        "#;

        let extractor = HtmlExtractor::new();
        let config = ExtractionConfig::default();
        let result = extractor
            .extract_bytes(html.as_bytes(), "text/html", &config)
            .await
            .unwrap();
        let result =
            crate::extraction::derive::derive_extraction_result(result, true, crate::core::config::OutputFormat::Plain);

        // The HTML extractor produces 2 table entries: one from build_internal_document
        // and one from convert_html_to_markdown_with_tables. Both contain the same data.
        assert_eq!(result.tables.len(), 2);
        // Verify table content (both tables contain the same data)
        let table = &result.tables[0];
        assert_eq!(table.cells.len(), 3);
        assert_eq!(table.cells[0], vec!["Name", "Age"]);
        assert_eq!(table.cells[1], vec!["Alice", "30"]);
        assert_eq!(table.cells[2], vec!["Bob", "25"]);
    }

    #[tokio::test]
    async fn test_html_extractor_with_djot_output() {
        let html = r#"
        <html>
            <body>
                <h1>Test Page</h1>
                <p>Content with <strong>emphasis</strong>.</p>
            </body>
        </html>
    "#;

        let extractor = HtmlExtractor::new();
        let config = ExtractionConfig {
            output_format: OutputFormat::Djot,
            ..Default::default()
        };

        let result = extractor
            .extract_bytes(html.as_bytes(), "text/html", &config)
            .await
            .unwrap();
        let result =
            crate::extraction::derive::derive_extraction_result(result, true, crate::core::config::OutputFormat::Plain);

        assert_eq!(result.mime_type, "text/html");
        // The derive pipeline produces plain text content; heading/emphasis markers are in DocumentStructure
        assert!(
            result.content.contains("Test Page"),
            "Should contain heading text: {}",
            result.content
        );
        assert!(
            result.content.contains("emphasis"),
            "Should contain emphasis text: {}",
            result.content
        );
    }

    #[tokio::test]
    async fn test_html_extractor_djot_double_conversion_prevention() {
        let html = r#"
        <html>
            <body>
                <h1>Test</h1>
                <p>Content with <strong>bold</strong> text.</p>
            </body>
        </html>
    "#;

        let extractor = HtmlExtractor::new();
        let config = ExtractionConfig {
            output_format: OutputFormat::Djot,
            ..Default::default()
        };

        let result = extractor
            .extract_bytes(html.as_bytes(), "text/html", &config)
            .await
            .unwrap();
        let result =
            crate::extraction::derive::derive_extraction_result(result, true, crate::core::config::OutputFormat::Plain);

        // Content should already be in djot format
        assert_eq!(result.mime_type, "text/html");
        let original_content = result.content.clone();

        // Simulate pipeline format application
        let mut pipeline_result = result.clone();
        crate::core::pipeline::apply_output_format(&mut pipeline_result, OutputFormat::Djot);

        // Content should be identical - no re-conversion should occur
        assert_eq!(pipeline_result.content, original_content);
        assert_eq!(pipeline_result.mime_type, "text/html");
    }
}
