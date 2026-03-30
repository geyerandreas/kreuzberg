//! Render an `InternalDocument` directly to HTML.

use crate::types::document_structure::AnnotationKind;
use crate::types::internal::{ElementKind, InternalDocument};

use super::common::{
    FootnoteCollector, NestingKind, RenderState, finalize_output, get_admonition_kind, get_admonition_title,
    get_language, get_raw_format, html_escape, is_body_element, is_container_end, parse_metadata_entries,
    render_annotated_text_escaped, render_table_html,
};

/// Render an `InternalDocument` to HTML.
pub fn render_html(doc: &InternalDocument) -> String {
    let footnotes = FootnoteCollector::new(doc);
    let mut state = RenderState::default();
    let mut out = String::with_capacity(doc.elements.len() * 80);
    let mut slide_open = false;

    for (i, elem) in doc.elements.iter().enumerate() {
        if !is_body_element(elem) {
            continue;
        }

        if is_container_end(elem) {
            match elem.kind {
                ElementKind::ListEnd => {
                    // Close the list tag
                    let was_ordered = close_list(&mut state);
                    if was_ordered {
                        out.push_str("</ol>\n");
                    } else {
                        out.push_str("</ul>\n");
                    }
                }
                ElementKind::QuoteEnd => {
                    state.pop_container(&NestingKind::BlockQuote);
                    out.push_str("</blockquote>\n");
                }
                ElementKind::GroupEnd => {
                    if slide_open {
                        out.push_str("</section>\n");
                        slide_open = false;
                    }
                    state.pop_container(&NestingKind::Group);
                    out.push_str("</section>\n");
                }
                _ => {}
            }
            continue;
        }

        state.pop_to_depth(elem.depth);

        match elem.kind {
            ElementKind::Title => {
                let text = render_html_annotated(&elem.text, &elem.annotations);
                out.push_str("<h1>");
                out.push_str(&text);
                out.push_str("</h1>\n");
            }
            ElementKind::Heading { level } => {
                let lvl = level.min(6);
                let text = render_html_annotated(&elem.text, &elem.annotations);
                out.push_str("<h");
                out.push_str(&lvl.to_string());
                out.push('>');
                out.push_str(&text);
                out.push_str("</h");
                out.push_str(&lvl.to_string());
                out.push_str(">\n");
            }
            ElementKind::Paragraph => {
                let text = render_html_annotated(&elem.text, &elem.annotations);
                out.push_str("<p>");
                out.push_str(&text);
                out.push_str("</p>\n");
            }
            ElementKind::ListItem { .. } => {
                let text = render_html_annotated(&elem.text, &elem.annotations);
                out.push_str("<li>");
                out.push_str(&text);
                out.push_str("</li>\n");
            }
            ElementKind::Code => {
                let lang = get_language(elem).unwrap_or("");
                let escaped = html_escape(&elem.text);
                if lang.is_empty() {
                    out.push_str("<pre><code>");
                    out.push_str(&escaped);
                    out.push_str("</code></pre>\n");
                } else {
                    out.push_str("<pre><code class=\"language-");
                    out.push_str(&html_escape(lang));
                    out.push_str("\">");
                    out.push_str(&escaped);
                    out.push_str("</code></pre>\n");
                }
            }
            ElementKind::Formula => {
                let escaped = html_escape(&elem.text);
                out.push_str("<div class=\"math\">$$");
                out.push_str(&escaped);
                out.push_str("$$</div>\n");
            }
            ElementKind::Table { table_index } => {
                if let Some(table) = doc.tables.get(table_index as usize) {
                    let table_str = if !table.cells.is_empty() {
                        render_table_html(&table.cells)
                    } else {
                        table.markdown.clone()
                    };
                    if !table_str.trim().is_empty() {
                        out.push_str(&table_str);
                        out.push('\n');
                    }
                }
            }
            ElementKind::Image { image_index } => {
                let image = doc.images.get(image_index as usize);
                let desc = image.and_then(|img| img.description.as_deref()).unwrap_or("");
                let url = image
                    .and_then(|img| {
                        if !img.data.is_empty() {
                            Some(format!("image_{}.{}", image_index, img.format))
                        } else {
                            img.source_path.clone()
                        }
                    })
                    .unwrap_or_default();
                out.push_str("<figure>");
                out.push_str("<img src=\"");
                out.push_str(&html_escape(&url));
                out.push_str("\" alt=\"");
                out.push_str(&html_escape(desc));
                out.push_str("\">");
                if !desc.is_empty() {
                    out.push_str("<figcaption>");
                    out.push_str(&html_escape(desc));
                    out.push_str("</figcaption>");
                }
                out.push_str("</figure>\n");
            }
            ElementKind::FootnoteRef => {
                if let Some(n) = footnotes.ref_number(i as u32) {
                    let ns = n.to_string();
                    out.push_str("<sup><a href=\"#fn-");
                    out.push_str(&ns);
                    out.push_str("\" id=\"fnref-");
                    out.push_str(&ns);
                    out.push_str("\">");
                    out.push_str(&ns);
                    out.push_str("</a></sup>");
                }
            }
            ElementKind::FootnoteDefinition => {
                // Skip in body pass
            }
            ElementKind::Citation => {
                // Rendered at end
            }
            ElementKind::PageBreak => {
                out.push_str("<hr class=\"page-break\">\n");
            }
            ElementKind::Slide { number } => {
                if slide_open {
                    out.push_str("</section>\n");
                }
                out.push_str("<section class=\"slide\" data-slide=\"");
                out.push_str(&number.to_string());
                out.push_str("\">\n");
                if !elem.text.is_empty() {
                    let text = render_html_annotated(&elem.text, &elem.annotations);
                    out.push_str("<h2>");
                    out.push_str(&text);
                    out.push_str("</h2>\n");
                }
                slide_open = true;
            }
            ElementKind::DefinitionTerm => {
                let text = render_html_annotated(&elem.text, &elem.annotations);
                out.push_str("<dt>");
                out.push_str(&text);
                out.push_str("</dt>\n");
            }
            ElementKind::DefinitionDescription => {
                let text = render_html_annotated(&elem.text, &elem.annotations);
                out.push_str("<dd>");
                out.push_str(&text);
                out.push_str("</dd>\n");
            }
            ElementKind::Admonition => {
                let kind = get_admonition_kind(elem);
                let title = get_admonition_title(elem);
                let text = render_html_annotated(&elem.text, &elem.annotations);

                out.push_str("<div class=\"admonition ");
                out.push_str(&html_escape(kind));
                out.push_str("\">\n");
                if let Some(t) = title {
                    out.push_str("<p class=\"admonition-title\">");
                    out.push_str(&html_escape(t));
                    out.push_str("</p>\n");
                } else {
                    let mut chars = kind.chars();
                    let title_display = match chars.next() {
                        Some(c) => {
                            let mut s = c.to_uppercase().to_string();
                            s.extend(chars);
                            s
                        }
                        None => String::new(),
                    };
                    out.push_str("<p class=\"admonition-title\">");
                    out.push_str(&html_escape(&title_display));
                    out.push_str("</p>\n");
                }
                if !text.is_empty() {
                    out.push_str("<p>");
                    out.push_str(&text);
                    out.push_str("</p>\n");
                }
                out.push_str("</div>\n");
            }
            ElementKind::RawBlock => {
                let format = get_raw_format(elem);
                if format == "html" {
                    // Raw HTML: emit verbatim
                    out.push_str(&elem.text);
                    if !elem.text.ends_with('\n') {
                        out.push('\n');
                    }
                } else {
                    // Non-HTML raw block: wrap in pre
                    out.push_str("<pre>");
                    out.push_str(&html_escape(&elem.text));
                    out.push_str("</pre>\n");
                }
            }
            ElementKind::MetadataBlock => {
                let entries = parse_metadata_entries(&elem.text);
                if !entries.is_empty() {
                    out.push_str("<dl class=\"metadata\">\n");
                    for (key, value) in &entries {
                        out.push_str("<dt>");
                        out.push_str(&html_escape(key));
                        out.push_str("</dt><dd>");
                        out.push_str(&html_escape(value));
                        out.push_str("</dd>\n");
                    }
                    out.push_str("</dl>\n");
                } else if !elem.text.is_empty() {
                    out.push_str("<pre class=\"metadata\">");
                    out.push_str(&html_escape(&elem.text));
                    out.push_str("</pre>\n");
                }
            }
            ElementKind::OcrText { .. } => {
                let text = render_html_annotated(&elem.text, &elem.annotations);
                out.push_str("<p>");
                out.push_str(&text);
                out.push_str("</p>\n");
            }
            ElementKind::ListStart { ordered } => {
                state.push_container(NestingKind::List { ordered, item_count: 0 }, elem.depth);
                if ordered {
                    out.push_str("<ol>\n");
                } else {
                    out.push_str("<ul>\n");
                }
            }
            ElementKind::ListEnd => {
                // Handled above
            }
            ElementKind::QuoteStart => {
                state.push_container(NestingKind::BlockQuote, elem.depth);
                out.push_str("<blockquote>\n");
            }
            ElementKind::QuoteEnd => {
                // Handled above
            }
            ElementKind::GroupStart => {
                state.push_container(NestingKind::Group, elem.depth);
                out.push_str("<section>\n");
            }
            ElementKind::GroupEnd => {
                // Handled above
            }
        }
    }

    // Close any open slide section at end of document
    if slide_open {
        out.push_str("</section>\n");
    }

    // Footnotes section
    let defs = footnotes.definitions();
    if !defs.is_empty() {
        out.push_str("<section class=\"footnotes\">\n<hr>\n<ol>\n");
        for entry in defs {
            let ns = entry.number.to_string();
            out.push_str("<li id=\"fn-");
            out.push_str(&ns);
            out.push_str("\"><p>");
            out.push_str(&html_escape(&entry.text));
            out.push_str(" <a href=\"#fnref-");
            out.push_str(&ns);
            out.push_str("\">&#x21a9;</a></p></li>\n");
        }
        out.push_str("</ol>\n</section>\n");
    }

    // Citations
    let has_citations = doc.elements.iter().any(|e| e.kind == ElementKind::Citation);
    if has_citations {
        out.push_str("<section class=\"citations\">\n");
        for elem in &doc.elements {
            if elem.kind == ElementKind::Citation {
                let key = elem.anchor.as_deref().unwrap_or("?");
                out.push_str("<p id=\"cite-");
                out.push_str(&html_escape(key));
                out.push_str("\">");
                out.push_str(&html_escape(&elem.text));
                out.push_str("</p>\n");
            }
        }
        out.push_str("</section>\n");
    }

    finalize_output(out)
}

/// Close the innermost list and return whether it was ordered.
fn close_list(state: &mut RenderState) -> bool {
    let was_ordered = state.innermost_list_ordered();
    state.pop_container(&NestingKind::List {
        ordered: false,
        item_count: 0,
    });
    was_ordered
}

/// Render text with HTML inline annotations.
fn render_html_annotated(text: &str, annotations: &[crate::types::document_structure::TextAnnotation]) -> String {
    render_annotated_text_escaped(
        text,
        annotations,
        |span, kind| {
            let escaped = html_escape(span);
            match kind {
                AnnotationKind::Bold => format!("<strong>{}</strong>", escaped),
                AnnotationKind::Italic => format!("<em>{}</em>", escaped),
                AnnotationKind::Code => format!("<code>{}</code>", escaped),
                AnnotationKind::Strikethrough => format!("<del>{}</del>", escaped),
                AnnotationKind::Underline => format!("<u>{}</u>", escaped),
                AnnotationKind::Subscript => format!("<sub>{}</sub>", escaped),
                AnnotationKind::Superscript => format!("<sup>{}</sup>", escaped),
                AnnotationKind::Highlight => format!("<mark>{}</mark>", escaped),
                AnnotationKind::Link { url, title } => {
                    if is_dangerous_url(url) {
                        escaped.into_owned()
                    } else {
                        let escaped_url = html_escape(url);
                        if let Some(t) = title {
                            format!(
                                "<a href=\"{}\" title=\"{}\">{}</a>",
                                escaped_url,
                                html_escape(t),
                                escaped
                            )
                        } else {
                            format!("<a href=\"{}\">{}</a>", escaped_url, escaped)
                        }
                    }
                }
                AnnotationKind::Color { value } => {
                    format!("<span style=\"color: {}\">{}</span>", html_escape(value), escaped)
                }
                AnnotationKind::FontSize { value } => {
                    format!("<span style=\"font-size: {}\">{}</span>", html_escape(value), escaped)
                }
                AnnotationKind::Custom { name, value } => {
                    if let Some(v) = value {
                        format!(
                            "<span data-{}=\"{}\">{}</span>",
                            html_escape(name),
                            html_escape(v),
                            escaped
                        )
                    } else {
                        format!("<span data-{}>{}</span>", html_escape(name), escaped)
                    }
                }
            }
        },
        |s| html_escape(s).into_owned(),
    )
}

/// Check if a URL uses a dangerous scheme that should not be rendered as a link.
fn is_dangerous_url(url: &str) -> bool {
    let normalized = url.trim().to_ascii_lowercase();
    normalized.starts_with("javascript:")
        || normalized.starts_with("vbscript:")
        || normalized.starts_with("data:text/html")
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
    fn test_render_html_title() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_title("My Document", None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<h1>My Document</h1>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_heading_levels() {
        for level in 1u8..=6 {
            let mut b = InternalDocumentBuilder::new("test");
            b.push_heading(level, "Heading", None, None);
            let doc = b.build();
            let out = render_html(&doc);
            let expected = format!("<h{}>Heading</h{}>", level, level);
            assert!(out.contains(&expected), "level {}: got {}", level, out);
        }
    }

    #[test]
    fn test_render_html_paragraph() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_paragraph("Hello world.", vec![], None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<p>Hello world.</p>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_unordered_list() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_list(false);
        b.push_list_item("Alpha", false, vec![], None, None);
        b.push_list_item("Beta", false, vec![], None, None);
        b.end_list();
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<ul>"), "got: {}", out);
        assert!(out.contains("<li>Alpha</li>"), "got: {}", out);
        assert!(out.contains("<li>Beta</li>"), "got: {}", out);
        assert!(out.contains("</ul>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_ordered_list() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_list(true);
        b.push_list_item("First", true, vec![], None, None);
        b.push_list_item("Second", true, vec![], None, None);
        b.end_list();
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<ol>"), "got: {}", out);
        assert!(out.contains("<li>First</li>"), "got: {}", out);
        assert!(out.contains("<li>Second</li>"), "got: {}", out);
        assert!(out.contains("</ol>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_nested_list() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_list(false);
        b.push_list_item("Outer", false, vec![], None, None);
        b.push_list(false);
        b.push_list_item("Inner", false, vec![], None, None);
        b.end_list();
        b.end_list();
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<ul>"), "got: {}", out);
        assert!(out.contains("<li>Outer</li>"), "got: {}", out);
        assert!(out.contains("<li>Inner</li>"), "got: {}", out);
        // Should have two <ul> opens and two </ul> closes
        assert_eq!(out.matches("<ul>").count(), 2, "got: {}", out);
        assert_eq!(out.matches("</ul>").count(), 2, "got: {}", out);
    }

    #[test]
    fn test_render_html_code_block_with_language() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_code("let x = 1;", Some("rust"), None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<pre><code class=\"language-rust\">"), "got: {}", out);
        assert!(out.contains("let x = 1;"), "got: {}", out);
        assert!(out.contains("</code></pre>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_code_block_no_language() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_code("echo hello", None, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<pre><code>echo hello</code></pre>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_formula() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_formula("E = mc^2", None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<div class=\"math\">$$E = mc^2$$</div>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_table() {
        let mut b = InternalDocumentBuilder::new("test");
        let cells = vec![
            vec!["Name".to_string(), "Age".to_string()],
            vec!["Alice".to_string(), "30".to_string()],
        ];
        b.push_table_from_cells(&cells, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<table>"), "got: {}", out);
        assert!(out.contains("<th>Name</th>"), "got: {}", out);
        assert!(out.contains("<th>Age</th>"), "got: {}", out);
        assert!(out.contains("<td>Alice</td>"), "got: {}", out);
        assert!(out.contains("<td>30</td>"), "got: {}", out);
        assert!(out.contains("</table>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_image() {
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
            description: Some("A photo".to_string()),
            ocr_result: None,
            bounding_box: None,
            source_path: None,
        };
        b.push_image(Some("A photo"), image, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<figure>"), "got: {}", out);
        assert!(out.contains("alt=\"A photo\""), "got: {}", out);
        assert!(out.contains("<figcaption>A photo</figcaption>"), "got: {}", out);
        assert!(out.contains("</figure>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_page_break() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_page_break();
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<hr class=\"page-break\">"), "got: {}", out);
    }

    #[test]
    fn test_render_html_slide() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_slide(1, Some("Intro"), None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(
            out.contains("<section class=\"slide\" data-slide=\"1\">"),
            "got: {}",
            out
        );
        assert!(out.contains("<h2>Intro</h2>"), "got: {}", out);
        // Slide should be closed at end of document
        assert!(out.contains("</section>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_definition_term_and_description() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_definition_term("Rust", None);
        b.push_definition_description("A systems language", None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<dt>Rust</dt>"), "got: {}", out);
        assert!(out.contains("<dd>A systems language</dd>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_admonition_with_title() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_admonition("warning", Some("Watch out"), None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<div class=\"admonition warning\">"), "got: {}", out);
        assert!(
            out.contains("<p class=\"admonition-title\">Watch out</p>"),
            "got: {}",
            out
        );
        assert!(out.contains("</div>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_admonition_without_title() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_admonition("note", None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<div class=\"admonition note\">"), "got: {}", out);
        assert!(out.contains("<p class=\"admonition-title\">Note</p>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_raw_block_html_format() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_raw_block("html", "<div>raw content</div>", None);
        let doc = b.build();
        let out = render_html(&doc);
        // Raw HTML should be emitted verbatim
        assert!(out.contains("<div>raw content</div>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_raw_block_non_html_format() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_raw_block("tex", "\\textbf{hello}", None);
        let doc = b.build();
        let out = render_html(&doc);
        // Non-HTML raw block should be wrapped in <pre> and escaped
        assert!(out.contains("<pre>"), "got: {}", out);
        assert!(out.contains("\\textbf{hello}"), "got: {}", out);
        assert!(out.contains("</pre>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_metadata_block() {
        let mut b = InternalDocumentBuilder::new("test");
        let entries = vec![("Author".to_string(), "Alice".to_string())];
        b.push_metadata_block(&entries, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<dl class=\"metadata\">"), "got: {}", out);
        assert!(out.contains("<dt>Author</dt>"), "got: {}", out);
        assert!(out.contains("<dd>Alice</dd>"), "got: {}", out);
        assert!(out.contains("</dl>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_empty_document() {
        let b = InternalDocumentBuilder::new("test");
        let doc = b.build();
        let out = render_html(&doc);
        assert_eq!(out, "");
    }

    // ========================================================================
    // 2. Annotation tests
    // ========================================================================

    #[test]
    fn test_render_html_bold_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 5,
            kind: AnnotationKind::Bold,
        }];
        b.push_paragraph("Hello world", ann, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<strong>Hello</strong>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_italic_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 5,
            kind: AnnotationKind::Italic,
        }];
        b.push_paragraph("Hello world", ann, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<em>Hello</em>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_code_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 4,
            kind: AnnotationKind::Code,
        }];
        b.push_paragraph("code rest", ann, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<code>code</code>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_link_annotation() {
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
        let out = render_html(&doc);
        assert!(
            out.contains("<a href=\"https://example.com\">Click</a>"),
            "got: {}",
            out
        );
    }

    #[test]
    fn test_render_html_link_with_title() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 5,
            kind: AnnotationKind::Link {
                url: "https://example.com".to_string(),
                title: Some("My Title".to_string()),
            },
        }];
        b.push_paragraph("Click here", ann, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(
            out.contains("<a href=\"https://example.com\" title=\"My Title\">Click</a>"),
            "got: {}",
            out
        );
    }

    #[test]
    fn test_render_html_strikethrough_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 3,
            kind: AnnotationKind::Strikethrough,
        }];
        b.push_paragraph("old new", ann, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<del>old</del>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_underline_annotation() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 4,
            kind: AnnotationKind::Underline,
        }];
        b.push_paragraph("text rest", ann, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<u>text</u>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_multiple_non_overlapping_annotations() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![
            TextAnnotation {
                start: 0,
                end: 5,
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
        let out = render_html(&doc);
        assert!(out.contains("<strong>Hello</strong>"), "got: {}", out);
        assert!(out.contains("<em>world</em>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_overlapping_annotations_inner_skipped() {
        let mut b = InternalDocumentBuilder::new("test");
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
        let out = render_html(&doc);
        assert!(out.contains("<strong>Hello world</strong>"), "got: {}", out);
        assert!(!out.contains("<em>"), "overlapping should be skipped, got: {}", out);
    }

    // ========================================================================
    // 3. Nested structure tests
    // ========================================================================

    #[test]
    fn test_render_html_blockquote() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_quote_start();
        b.push_paragraph("Quoted text.", vec![], None, None);
        b.push_quote_end();
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<blockquote>"), "got: {}", out);
        assert!(out.contains("<p>Quoted text.</p>"), "got: {}", out);
        assert!(out.contains("</blockquote>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_nested_blockquote() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_quote_start();
        b.push_quote_start();
        b.push_paragraph("Deep quote.", vec![], None, None);
        b.push_quote_end();
        b.push_quote_end();
        let doc = b.build();
        let out = render_html(&doc);
        assert_eq!(out.matches("<blockquote>").count(), 2, "got: {}", out);
        assert_eq!(out.matches("</blockquote>").count(), 2, "got: {}", out);
        assert!(out.contains("<p>Deep quote.</p>"), "got: {}", out);
    }

    #[test]
    fn test_render_html_list_inside_blockquote() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_quote_start();
        b.push_list(false);
        b.push_list_item("Quoted item", false, vec![], None, None);
        b.end_list();
        b.push_quote_end();
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<blockquote>"), "got: {}", out);
        assert!(out.contains("<ul>"), "got: {}", out);
        assert!(out.contains("<li>Quoted item</li>"), "got: {}", out);
        assert!(out.contains("</ul>"), "got: {}", out);
        assert!(out.contains("</blockquote>"), "got: {}", out);
    }

    // ========================================================================
    // 4. Footnote tests
    // ========================================================================

    #[test]
    fn test_render_html_footnote() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_paragraph("See note", vec![], None, None);
        b.push_footnote_ref("1", "fn1", None);
        let def = b.push_footnote_definition("Footnote content.", "fn1", None);
        b.set_layer(def, ContentLayer::Footnote);
        let doc = b.build();
        let out = render_html(&doc);
        // Ref in body
        assert!(
            out.contains("<sup><a href=\"#fn-1\" id=\"fnref-1\">1</a></sup>"),
            "got: {}",
            out
        );
        // Def in footnotes section
        assert!(out.contains("<section class=\"footnotes\">"), "got: {}", out);
        assert!(out.contains("<li id=\"fn-1\">"), "got: {}", out);
        assert!(out.contains("Footnote content."), "got: {}", out);
        assert!(out.contains("<a href=\"#fnref-1\">"), "got: {}", out);
    }

    #[test]
    fn test_render_html_multiple_footnotes() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_footnote_ref("a", "fn1", None);
        b.push_footnote_ref("b", "fn2", None);
        let d1 = b.push_footnote_definition("First.", "fn1", None);
        let d2 = b.push_footnote_definition("Second.", "fn2", None);
        b.set_layer(d1, ContentLayer::Footnote);
        b.set_layer(d2, ContentLayer::Footnote);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("id=\"fnref-1\""), "got: {}", out);
        assert!(out.contains("id=\"fnref-2\""), "got: {}", out);
        assert!(out.contains("<li id=\"fn-1\">"), "got: {}", out);
        assert!(out.contains("<li id=\"fn-2\">"), "got: {}", out);
    }

    #[test]
    fn test_render_html_citation() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_citation("Smith 2024", "smith2024", None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("<section class=\"citations\">"), "got: {}", out);
        assert!(out.contains("id=\"cite-smith2024\""), "got: {}", out);
        assert!(out.contains("Smith 2024"), "got: {}", out);
    }

    // ========================================================================
    // 5. HTML-specific tests
    // ========================================================================

    #[test]
    fn test_render_html_escapes_script_tags() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_paragraph("<script>alert('xss')</script>", vec![], None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(!out.contains("<script>"), "script tag should be escaped, got: {}", out);
        assert!(out.contains("&lt;script&gt;"), "got: {}", out);
    }

    #[test]
    fn test_render_html_escapes_angle_brackets_in_text() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_paragraph("a < b > c & d", vec![], None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(out.contains("a &lt; b &gt; c &amp; d"), "got: {}", out);
    }

    #[test]
    fn test_render_html_dangerous_url_javascript() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 5,
            kind: AnnotationKind::Link {
                url: "javascript:alert(1)".to_string(),
                title: None,
            },
        }];
        b.push_paragraph("Click here", ann, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        // Dangerous URL should NOT produce an <a> tag
        assert!(
            !out.contains("href=\"javascript:"),
            "dangerous URL should be blocked, got: {}",
            out
        );
        // The text should still appear
        assert!(out.contains("Click"), "got: {}", out);
    }

    #[test]
    fn test_render_html_dangerous_url_vbscript() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 4,
            kind: AnnotationKind::Link {
                url: "vbscript:msgbox".to_string(),
                title: None,
            },
        }];
        b.push_paragraph("text here", ann, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(!out.contains("href=\"vbscript:"), "got: {}", out);
    }

    #[test]
    fn test_render_html_dangerous_url_data() {
        let mut b = InternalDocumentBuilder::new("test");
        let ann = vec![TextAnnotation {
            start: 0,
            end: 4,
            kind: AnnotationKind::Link {
                url: "data:text/html,<script>alert(1)</script>".to_string(),
                title: None,
            },
        }];
        b.push_paragraph("text here", ann, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(!out.contains("href=\"data:text/html"), "got: {}", out);
    }

    #[test]
    fn test_render_html_proper_tag_nesting() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_list(false);
        b.push_list_item("Item", false, vec![], None, None);
        b.end_list();
        let doc = b.build();
        let out = render_html(&doc);
        // Verify <ul> comes before <li> and </li> comes before </ul>
        let ul_open = out.find("<ul>").unwrap();
        let li_open = out.find("<li>").unwrap();
        let li_close = out.find("</li>").unwrap();
        let ul_close = out.find("</ul>").unwrap();
        assert!(ul_open < li_open, "ul should open before li");
        assert!(li_open < li_close, "li should open before close");
        assert!(li_close < ul_close, "li should close before ul");
    }

    #[test]
    fn test_render_html_escapes_in_code_block() {
        let mut b = InternalDocumentBuilder::new("test");
        b.push_code("<div>not html</div>", Some("html"), None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(
            out.contains("&lt;div&gt;not html&lt;/div&gt;"),
            "code should be escaped, got: {}",
            out
        );
    }

    #[test]
    fn test_render_html_escapes_in_table_cells() {
        let mut b = InternalDocumentBuilder::new("test");
        let cells = vec![vec!["<b>Header</b>".to_string()], vec!["<i>Cell</i>".to_string()]];
        b.push_table_from_cells(&cells, None, None);
        let doc = b.build();
        let out = render_html(&doc);
        assert!(
            out.contains("&lt;b&gt;Header&lt;/b&gt;"),
            "table header should be escaped, got: {}",
            out
        );
        assert!(
            out.contains("&lt;i&gt;Cell&lt;/i&gt;"),
            "table cell should be escaped, got: {}",
            out
        );
    }
}
