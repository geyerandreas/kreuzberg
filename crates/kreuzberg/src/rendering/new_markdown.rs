//! Render an `InternalDocument` to CommonMark-compliant Markdown.

use crate::types::document_structure::AnnotationKind;
use crate::types::internal::{ElementKind, InternalDocument};

use super::common::{
    FootnoteCollector, NestingKind, RenderState, ensure_trailing_newline, finalize_output, get_admonition_kind,
    get_admonition_title, get_language, handle_container_end, is_body_element, is_container_end,
    parse_metadata_entries, push_with_bq, render_annotated_text, render_table_markdown,
};

/// Render an `InternalDocument` to CommonMark Markdown.
pub fn render_markdown(doc: &InternalDocument) -> String {
    let footnotes = FootnoteCollector::new(doc);
    let mut state = RenderState::default();
    let mut out = String::with_capacity(doc.elements.len() * 80);

    for (i, elem) in doc.elements.iter().enumerate() {
        // Skip non-body elements (footnotes collected separately)
        if !is_body_element(elem) {
            continue;
        }

        // Skip container end markers
        if is_container_end(elem) {
            handle_container_end(&elem.kind, &mut state);
            continue;
        }

        // Depth-based fallback: pop containers that are deeper than current element
        state.pop_to_depth(elem.depth);

        let bq_depth = state.blockquote_depth();

        match elem.kind {
            ElementKind::Title => {
                let text = render_md_annotated(&elem.text, &elem.annotations);
                let block = format!("# {}\n\n", text);
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::Heading { level } => {
                let hashes = "#".repeat(level as usize);
                let text = render_md_annotated(&elem.text, &elem.annotations);
                let block = format!("{} {}\n\n", hashes, text);
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::Paragraph => {
                let text = render_md_annotated(&elem.text, &elem.annotations);
                let block = format!("{}\n\n", text);
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::ListItem { ordered } => {
                let list_depth = state.list_depth();
                let indent = "  ".repeat(list_depth.saturating_sub(1));
                let text = render_md_annotated(&elem.text, &elem.annotations);
                let mut block = String::with_capacity(indent.len() + text.len() + 8);
                block.push_str(&indent);
                if ordered {
                    let n = state.next_list_number();
                    block.push_str(&n.to_string());
                    block.push_str(". ");
                } else {
                    block.push_str("- ");
                };
                block.push_str(&text);
                block.push('\n');
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::Code => {
                let lang = get_language(elem).unwrap_or("");
                let mut block = format!("```{}\n{}", lang, elem.text);
                if !elem.text.ends_with('\n') {
                    block.push('\n');
                }
                block.push_str("```\n\n");
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::Formula => {
                let mut block = format!("$$\n{}", elem.text);
                if !elem.text.ends_with('\n') {
                    block.push('\n');
                }
                block.push_str("$$\n\n");
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::Table { table_index } => {
                if let Some(table) = doc.tables.get(table_index as usize) {
                    // Prefer cells grid; fall back to pre-rendered markdown
                    // (TATR produces markdown directly without populating cells).
                    let table_str = if !table.cells.is_empty() {
                        render_table_markdown(&table.cells)
                    } else {
                        table.markdown.clone()
                    };
                    if !table_str.trim().is_empty() {
                        let block = format!("{}\n", table_str);
                        push_with_bq(&mut out, &block, bq_depth);
                    }
                }
            }
            ElementKind::Image { image_index } => {
                let image = doc.images.get(image_index as usize);
                let desc = image.and_then(|img| img.description.as_deref()).unwrap_or("");
                // Reference by named file: image_0.png, image_1.jpeg, etc.
                // The actual binary data is in ExtractionResult.images.
                // Fall back to source_path (e.g., "media/image1.png" from DOCX) when
                // binary data is not available, or element text as last resort.
                let url = image
                    .and_then(|img| {
                        if !img.data.is_empty() {
                            Some(format!("image_{}.{}", image_index, img.format))
                        } else {
                            img.source_path.clone()
                        }
                    })
                    .unwrap_or_default();
                let block = format!("![{}]({})\n\n", desc, url);
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::FootnoteRef => {
                if let Some(n) = footnotes.ref_number(i as u32) {
                    out.push_str("[^");
                    out.push_str(&n.to_string());
                    out.push(']');
                }
            }
            ElementKind::FootnoteDefinition => {
                // Skip in body pass; rendered at the end.
            }
            ElementKind::Citation => {
                // Rendered at end of document.
            }
            ElementKind::PageBreak => {
                let block = "\n<!-- page break -->\n\n";
                push_with_bq(&mut out, block, bq_depth);
            }
            ElementKind::Slide { number: _ } => {
                if elem.text.is_empty() {
                    push_with_bq(&mut out, "\n---\n\n", bq_depth);
                } else {
                    let text = render_md_annotated(&elem.text, &elem.annotations);
                    let mut block = String::with_capacity(12 + text.len());
                    block.push_str("\n---\n\n## ");
                    block.push_str(&text);
                    block.push_str("\n\n");
                    push_with_bq(&mut out, &block, bq_depth);
                }
            }
            ElementKind::DefinitionTerm => {
                let text = render_md_annotated(&elem.text, &elem.annotations);
                let block = format!("{}\n", text);
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::DefinitionDescription => {
                let text = render_md_annotated(&elem.text, &elem.annotations);
                let block = format!(": {}\n\n", text);
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::Admonition => {
                let kind = get_admonition_kind(elem);
                let title = get_admonition_title(elem).unwrap_or({
                    // Capitalize kind
                    kind
                });
                let title_display = if get_admonition_title(elem).is_some() {
                    title.to_string()
                } else {
                    let mut chars = kind.chars();
                    match chars.next() {
                        Some(c) => {
                            let mut s = c.to_uppercase().to_string();
                            s.extend(chars);
                            s
                        }
                        None => String::new(),
                    }
                };
                let text = render_md_annotated(&elem.text, &elem.annotations);
                let mut block = format!("> **{}**\n", title_display);
                if !text.is_empty() {
                    for line in text.lines() {
                        block.push_str("> ");
                        block.push_str(line);
                        block.push('\n');
                    }
                }
                block.push('\n');
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::RawBlock => {
                let mut block = elem.text.clone();
                ensure_trailing_newline(&mut block);
                block.push('\n');
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::MetadataBlock => {
                let entries = parse_metadata_entries(&elem.text);
                let mut block = String::new();
                for (key, value) in &entries {
                    block.push_str("**");
                    block.push_str(key);
                    block.push_str("**: ");
                    block.push_str(value);
                    block.push('\n');
                }
                if entries.is_empty() && !elem.text.is_empty() {
                    // Fallback: just output the text
                    block.push_str(&elem.text);
                    ensure_trailing_newline(&mut block);
                }
                block.push('\n');
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::OcrText { .. } => {
                // Treat as paragraph
                let text = render_md_annotated(&elem.text, &elem.annotations);
                let block = format!("{}\n\n", text);
                push_with_bq(&mut out, &block, bq_depth);
            }
            ElementKind::ListStart { ordered } => {
                state.push_container(NestingKind::List { ordered, item_count: 0 }, elem.depth);
            }
            ElementKind::ListEnd => {
                // Handled above in container end section
            }
            ElementKind::QuoteStart => {
                state.push_container(NestingKind::BlockQuote, elem.depth);
            }
            ElementKind::QuoteEnd => {
                // Handled above
            }
            ElementKind::GroupStart => {
                state.push_container(NestingKind::Group, elem.depth);
            }
            ElementKind::GroupEnd => {
                // Handled above
            }
        }
    }

    // Render footnote definitions at end
    let defs = footnotes.definitions();
    if !defs.is_empty() {
        out.push_str("\n---\n\n");
        for entry in defs {
            out.push_str("[^");
            out.push_str(&entry.number.to_string());
            out.push_str("]: ");
            out.push_str(&entry.text);
            out.push_str("\n\n");
        }
    }

    // Render citations at end
    for elem in &doc.elements {
        if elem.kind == ElementKind::Citation {
            let key = elem.anchor.as_deref().unwrap_or("?");
            out.push_str("[^");
            out.push_str(key);
            out.push_str("]: ");
            out.push_str(&elem.text);
            out.push_str("\n\n");
        }
    }

    finalize_output(out)
}

/// Render text with markdown inline annotations.
fn render_md_annotated(text: &str, annotations: &[crate::types::document_structure::TextAnnotation]) -> String {
    render_annotated_text(text, annotations, |span, kind| match kind {
        AnnotationKind::Bold => format!("**{}**", span),
        AnnotationKind::Italic => format!("*{}*", span),
        AnnotationKind::Code => format!("`{}`", span),
        AnnotationKind::Strikethrough => format!("~~{}~~", span),
        AnnotationKind::Underline => format!("<u>{}</u>", span),
        AnnotationKind::Subscript => format!("<sub>{}</sub>", span),
        AnnotationKind::Superscript => format!("<sup>{}</sup>", span),
        AnnotationKind::Highlight => format!("<mark>{}</mark>", span),
        AnnotationKind::Link { url, title } => {
            if let Some(t) = title {
                format!("[{}]({} \"{}\")", span, url, t)
            } else {
                format!("[{}]({})", span, url)
            }
        }
        AnnotationKind::Color { .. } | AnnotationKind::FontSize { .. } | AnnotationKind::Custom { .. } => {
            span.to_string()
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::document_structure::{AnnotationKind, ContentLayer, TextAnnotation};
    use crate::types::internal_builder::InternalDocumentBuilder;

    // ========================================================================
    // 1. Element rendering tests
    // ========================================================================

    #[test]
    fn test_render_markdown_title() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_title("My Document", None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert_eq!(out, "# My Document\n");
    }

    #[test]
    fn test_render_markdown_heading_levels() {
        for level in 1u8..=6 {
            let mut b = InternalDocumentBuilder::new("test");
            b.push_heading(level, "Heading", None, None);
            let doc = b.build();
            let out = render_markdown(&doc);
            let hashes = "#".repeat(level as usize);
            assert!(
                out.starts_with(&format!("{} Heading", hashes)),
                "level {}: got {}",
                level,
                out
            );
        }
    }

    #[test]
    fn test_render_markdown_paragraph() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_paragraph("Hello world.", vec![], None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert_eq!(out, "Hello world.\n");
    }

    #[test]
    fn test_render_markdown_unordered_list_items() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_list(false);
        b.push_list_item("Alpha", false, vec![], None, None);
        b.push_list_item("Beta", false, vec![], None, None);
        b.push_list_item("Gamma", false, vec![], None, None);
        b.end_list();
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("- Alpha\n"), "got: {}", out);
        assert!(out.contains("- Beta\n"), "got: {}", out);
        assert!(out.contains("- Gamma\n"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_ordered_list_items() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_list(true);
        b.push_list_item("First", true, vec![], None, None);
        b.push_list_item("Second", true, vec![], None, None);
        b.push_list_item("Third", true, vec![], None, None);
        b.end_list();
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("1. First\n"), "got: {}", out);
        assert!(out.contains("2. Second\n"), "got: {}", out);
        assert!(out.contains("3. Third\n"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_nested_list() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_list(false);
        b.push_list_item("Outer", false, vec![], None, None);
        b.push_list(false);
        b.push_list_item("Inner", false, vec![], None, None);
        b.end_list();
        b.end_list();
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("- Outer\n"), "got: {}", out);
        assert!(out.contains("  - Inner\n"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_code_block_with_language() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_code("fn main() {}", Some("rust"), None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("```rust\n"), "got: {}", out);
        assert!(out.contains("fn main() {}"), "got: {}", out);
        assert!(out.contains("```\n"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_formula() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_formula("E = mc^2", None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("$$\n"), "got: {}", out);
        assert!(out.contains("E = mc^2"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_table() {
        let mut b = InternalDocumentBuilder::new("test");
        let cells = vec![
            vec!["Name".to_string(), "Age".to_string()],
            vec!["Alice".to_string(), "30".to_string()],
        ];
        b.push_table_from_cells(&cells, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("| Name | Age |"), "got: {}", out);
        assert!(out.contains("| --- | --- |"), "got: {}", out);
        assert!(out.contains("| Alice | 30 |"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_image() {
        let mut b = InternalDocumentBuilder::new("test");
        let image = crate::types::ExtractedImage {
            data: bytes::Bytes::new(),
            format: std::borrow::Cow::Borrowed("png"),
            image_index: 0,
            page_number: None,
            width: None,
            height: None,
            colorspace: None,
            bits_per_component: None,
            is_mask: false,
            description: Some("A nice photo".to_string()),
            ocr_result: None,
            bounding_box: None,
            source_path: None,
        };
        b.push_image(Some("A nice photo"), image, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("![A nice photo]()"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_page_break() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_paragraph("Before", vec![], None, None);
        b.push_page_break();
        b.push_paragraph("After", vec![], None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("<!-- page break -->"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_slide() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_slide(1, Some("Intro Slide"), None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("---"), "got: {}", out);
        assert!(out.contains("## Intro Slide"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_definition_term_and_description() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_definition_term("Rust", None);
        b.push_definition_description("A systems programming language", None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("Rust\n"), "got: {}", out);
        assert!(out.contains(": A systems programming language"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_admonition_with_title() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_admonition("warning", Some("Be careful"), None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("> **Be careful**"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_admonition_without_title() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_admonition("note", None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("> **Note**"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_raw_block() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_raw_block("tex", "\\begin{equation}x^2\\end{equation}", None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("\\begin{equation}x^2\\end{equation}"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_metadata_block() {
        let mut b = InternalDocumentBuilder::new("test");
        let entries = vec![
            ("Author".to_string(), "Alice".to_string()),
            ("Date".to_string(), "2024-01-01".to_string()),
        ];
        b.push_metadata_block(&entries, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("**Author**: Alice"), "got: {}", out);
        assert!(out.contains("**Date**: 2024-01-01"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_empty_document() {
        let b = InternalDocumentBuilder::new("test");
        let doc = b.build();
        let out = render_markdown(&doc);
        assert_eq!(out, "");
    }

    // ========================================================================
    // 2. Annotation tests
    // ========================================================================

    #[test]
    fn test_render_markdown_bold_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        // "Hello world" - bold on "Hello"
        let ann = vec![TextAnnotation {
            start: 0,
            end: 5,
            kind: AnnotationKind::Bold,
        }];
        b.push_paragraph("Hello world", ann, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("**Hello** world"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_italic_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 5,
            kind: AnnotationKind::Italic,
        }];
        b.push_paragraph("Hello world", ann, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("*Hello* world"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_code_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 4,
            end: 9,
            kind: AnnotationKind::Code,
        }];
        b.push_paragraph("Use print here", ann, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("`print`"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_link_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 5,
            kind: AnnotationKind::Link {
                url: "https://example.com".to_string(),
                title: None,
            },
        }];
        b.push_paragraph("Click here", ann, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("[Click](https://example.com)"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_link_with_title() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 5,
            kind: AnnotationKind::Link {
                url: "https://example.com".to_string(),
                title: Some("Example".to_string()),
            },
        }];
        b.push_paragraph("Click here", ann, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("[Click](https://example.com \"Example\")"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_strikethrough_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 3,
            kind: AnnotationKind::Strikethrough,
        }];
        b.push_paragraph("old new", ann, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("~~old~~"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_underline_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 4,
            kind: AnnotationKind::Underline,
        }];
        b.push_paragraph("text rest", ann, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("<u>text</u>"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_multiple_non_overlapping_annotations() {
        let mut b = InternalDocumentBuilder::new("test");
        // "Hello brave world" - bold "Hello", italic "world"
        let ann = vec![
            TextAnnotation {
                start: 0,
                end: 5,
                kind: AnnotationKind::Bold,
            },
            TextAnnotation {
                start: 12,
                end: 17,
                kind: AnnotationKind::Italic,
            },
        ];
        b.push_paragraph("Hello brave world", ann, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("**Hello**"), "got: {}", out);
        assert!(out.contains("*world*"), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_overlapping_annotations_inner_skipped() {
        let mut b = InternalDocumentBuilder::new("test");
        // "Hello world" - bold 0..11, italic 6..11 (overlaps, inner should be skipped)
        let ann = vec![
            TextAnnotation {
                start: 0,
                end: 11,
                kind: AnnotationKind::Bold,
            },
            TextAnnotation {
                start: 6,
                end: 11,
                kind: AnnotationKind::Italic,
            },
        ];
        b.push_paragraph("Hello world", ann, None, None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("**Hello world**"), "got: {}", out);
        // The italic should NOT appear since it overlaps
        assert!(
            !out.contains("*world*"),
            "overlapping italic should be skipped, got: {}",
            out
        );
    }

    // ========================================================================
    // 3. Nested structure tests
    // ========================================================================

    #[test]
    fn test_render_markdown_blockquote() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_quote_start();
        b.push_paragraph("Quoted text.", vec![], None, None);
        b.push_quote_end();
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("> Quoted text."), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_nested_blockquote() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_quote_start();
        b.push_quote_start();
        b.push_paragraph("Deeply quoted.", vec![], None, None);
        b.push_quote_end();
        b.push_quote_end();
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("> > Deeply quoted."), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_list_inside_blockquote() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_quote_start();
        b.push_list(false);
        b.push_list_item("Quoted item", false, vec![], None, None);
        b.end_list();
        b.push_quote_end();
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("> - Quoted item"), "got: {}", out);
    }

    // ========================================================================
    // 4. Footnote tests
    // ========================================================================

    #[test]
    fn test_render_markdown_footnote() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_paragraph("See note", vec![], None, None);
        let _ref_idx = b.push_footnote_ref("1", "fn1", None);
        let def_idx = b.push_footnote_definition("This is the footnote text.", "fn1", None);
        b.set_layer(def_idx, ContentLayer::Footnote);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("[^1]"), "should contain footnote ref, got: {}", out);
        assert!(
            out.contains("[^1]: This is the footnote text."),
            "should contain footnote def, got: {}",
            out
        );
    }

    #[test]
    fn test_render_markdown_multiple_footnotes() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_paragraph("Text", vec![], None, None);
        b.push_footnote_ref("a", "fn1", None);
        b.push_footnote_ref("b", "fn2", None);
        let d1 = b.push_footnote_definition("First note.", "fn1", None);
        let d2 = b.push_footnote_definition("Second note.", "fn2", None);
        b.set_layer(d1, ContentLayer::Footnote);
        b.set_layer(d2, ContentLayer::Footnote);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("[^1]"), "got: {}", out);
        assert!(out.contains("[^2]"), "got: {}", out);
        assert!(out.contains("[^1]: First note."), "got: {}", out);
        assert!(out.contains("[^2]: Second note."), "got: {}", out);
    }

    #[test]
    fn test_render_markdown_citation() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_citation("Smith et al. 2024", "smith2024", None);
        let doc = b.build();
        let out = render_markdown(&doc);
        assert!(out.contains("[^smith2024]: Smith et al. 2024"), "got: {}", out);
    }
}
