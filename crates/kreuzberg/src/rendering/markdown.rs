//! Render a `DocumentStructure` tree to Markdown.

use crate::types::document_structure::{
    AnnotationKind, ContentLayer, DocumentStructure, NodeContent, NodeIndex, TableGrid, TextAnnotation,
};

/// Render a `DocumentStructure` to Markdown.
///
/// Walks body roots in reading order, recursing through children.
/// Furniture (headers/footers/footnotes) is appended at the end.
pub fn render_to_markdown(doc: &DocumentStructure) -> String {
    let mut out = String::new();

    // Render body content
    for (idx, _node) in doc.body_roots() {
        render_node(doc, idx, &mut out, 0);
    }

    // Render footnotes at the end
    let footnotes: Vec<_> = doc
        .furniture_roots()
        .filter(|(_, n)| n.content_layer == ContentLayer::Footnote)
        .collect();
    if !footnotes.is_empty() {
        out.push_str("\n---\n\n");
        for (idx, _) in footnotes {
            render_node(doc, idx, &mut out, 0);
        }
    }

    // Trim trailing whitespace but keep single trailing newline
    let trimmed = out.trim_end();
    if trimmed.is_empty() {
        return String::new();
    }
    let mut result = trimmed.to_string();
    result.push('\n');
    result
}

fn render_node(doc: &DocumentStructure, idx: NodeIndex, out: &mut String, depth: usize) {
    let node = match doc.get(idx) {
        Some(n) => n,
        None => return,
    };

    match &node.content {
        NodeContent::Title { text } => {
            out.push_str("# ");
            push_annotated(out, text, &node.annotations);
            out.push_str("\n\n");
        }
        NodeContent::Heading { level, text } => {
            for _ in 0..*level {
                out.push('#');
            }
            out.push(' ');
            push_annotated(out, text, &node.annotations);
            out.push_str("\n\n");
        }
        NodeContent::Paragraph { text } => {
            push_annotated(out, text, &node.annotations);
            out.push_str("\n\n");
        }
        NodeContent::List { .. } => {
            // Children are list items
            for (i, child_idx) in node.children.iter().enumerate() {
                if let Some(child) = doc.get(*child_idx)
                    && let NodeContent::ListItem { text } = &child.content
                {
                    let ordered = matches!(node.content, NodeContent::List { ordered: true });
                    let indent = "  ".repeat(depth);
                    if ordered {
                        out.push_str(&format!("{}{}. ", indent, i + 1));
                    } else {
                        out.push_str(&format!("{}- ", indent));
                    }
                    push_annotated(out, text, &child.annotations);
                    out.push('\n');
                    // Render nested children of this list item (e.g. nested lists) with increased depth
                    for grandchild_idx in &child.children {
                        render_node(doc, *grandchild_idx, out, depth + 1);
                    }
                }
            }
            out.push('\n'); // Children already handled
        }
        NodeContent::ListItem { text } => {
            // Standalone list item (shouldn't happen normally)
            out.push_str("- ");
            push_annotated(out, text, &node.annotations);
            out.push_str("\n\n");
        }
        NodeContent::Table { grid } => {
            render_table_grid(out, grid);
            out.push('\n');
        }
        NodeContent::Image { description, .. } => {
            out.push_str("![");
            if let Some(desc) = description {
                out.push_str(desc);
            }
            out.push_str("]()\n\n");
        }
        NodeContent::Code { text, language } => {
            out.push_str("```");
            if let Some(lang) = language {
                out.push_str(lang);
            }
            out.push('\n');
            out.push_str(text);
            if !text.ends_with('\n') {
                out.push('\n');
            }
            out.push_str("```\n\n");
        }
        NodeContent::Quote => {
            // Children carry the quoted content
            for child_idx in &node.children {
                let mut child_out = String::new();
                render_node(doc, *child_idx, &mut child_out, depth);
                for line in child_out.lines() {
                    out.push_str("> ");
                    out.push_str(line);
                    out.push('\n');
                }
            }
            out.push('\n'); // Children already handled
        }
        NodeContent::Formula { text } => {
            out.push_str("$$\n");
            out.push_str(text);
            if !text.ends_with('\n') {
                out.push('\n');
            }
            out.push_str("$$\n\n");
        }
        NodeContent::Footnote { text } => {
            push_annotated(out, text, &node.annotations);
            out.push_str("\n\n");
        }
        NodeContent::Group {
            heading_level,
            heading_text,
            ..
        } => {
            // If the Group has heading metadata but no Heading child, render
            // the heading directly before recursing into children.
            let has_heading_child = node.children.iter().any(|child_idx| {
                doc.get(*child_idx)
                    .is_some_and(|c| matches!(c.content, NodeContent::Heading { .. }))
            });
            if !has_heading_child && let (Some(level), Some(text)) = (heading_level, heading_text) {
                for _ in 0..*level {
                    out.push('#');
                }
                out.push(' ');
                out.push_str(text);
                out.push_str("\n\n");
            }
            // Container — render children
            for child_idx in &node.children {
                render_node(doc, *child_idx, out, depth);
            } // Children already handled
        }
        NodeContent::PageBreak => {
            out.push_str("\n<!-- page break -->\n\n");
        }
        NodeContent::Slide { .. } => {
            out.push_str("\n---\n\n");
            // Title is metadata; children (including any Heading) handle content rendering
            for child_idx in &node.children {
                render_node(doc, *child_idx, out, depth);
            }
        }
        NodeContent::DefinitionList => {
            for child_idx in &node.children {
                render_node(doc, *child_idx, out, depth);
            }
        }
        NodeContent::DefinitionItem { term, definition } => {
            out.push_str(term);
            out.push_str("\n: ");
            out.push_str(definition);
            out.push_str("\n\n");
        }
        NodeContent::Citation { key, text } => {
            out.push_str(&format!("[^{}]: {}\n\n", key, text));
        }
        NodeContent::Admonition { kind, title } => {
            out.push_str("> **");
            if let Some(t) = title {
                out.push_str(t);
            } else {
                // Capitalize kind
                let mut chars = kind.chars();
                if let Some(first) = chars.next() {
                    out.push(first.to_ascii_uppercase());
                    out.extend(chars);
                }
            }
            out.push_str("**\n");
            for child_idx in &node.children {
                let mut child_out = String::new();
                render_node(doc, *child_idx, &mut child_out, depth);
                for line in child_out.lines() {
                    out.push_str("> ");
                    out.push_str(line);
                    out.push('\n');
                }
            }
            out.push('\n');
        }
        NodeContent::RawBlock { content, .. } => {
            out.push_str(content);
            if !content.ends_with('\n') {
                out.push('\n');
            }
            out.push('\n');
        }
        NodeContent::MetadataBlock { entries } => {
            for (key, value) in entries {
                out.push_str(&format!("**{}**: {}\n", key, value));
            }
            out.push('\n');
        }
    }
}

/// Push text with inline annotations rendered as markdown.
fn push_annotated(out: &mut String, text: &str, annotations: &[TextAnnotation]) {
    if annotations.is_empty() {
        out.push_str(text);
        return;
    }

    // Sort annotations by start position
    let mut sorted: Vec<&TextAnnotation> = annotations.iter().collect();
    sorted.sort_by_key(|a| (a.start, a.end));

    let bytes = text.as_bytes();
    let mut pos: u32 = 0;

    for ann in &sorted {
        let start = ann.start.min(bytes.len() as u32);
        let end = ann.end.min(bytes.len() as u32);
        // Skip overlapping annotations (start is before current position)
        if start < pos {
            continue;
        }
        if start > pos {
            out.push_str(&text[pos as usize..start as usize]);
        }
        let span = &text[start as usize..end as usize];
        match &ann.kind {
            AnnotationKind::Bold => {
                out.push_str("**");
                out.push_str(span);
                out.push_str("**");
            }
            AnnotationKind::Italic => {
                out.push('*');
                out.push_str(span);
                out.push('*');
            }
            AnnotationKind::Underline => {
                // No standard markdown for underline; use HTML
                out.push_str("<u>");
                out.push_str(span);
                out.push_str("</u>");
            }
            AnnotationKind::Strikethrough => {
                out.push_str("~~");
                out.push_str(span);
                out.push_str("~~");
            }
            AnnotationKind::Code => {
                out.push('`');
                out.push_str(span);
                out.push('`');
            }
            AnnotationKind::Subscript => {
                out.push_str("<sub>");
                out.push_str(span);
                out.push_str("</sub>");
            }
            AnnotationKind::Superscript => {
                out.push_str("<sup>");
                out.push_str(span);
                out.push_str("</sup>");
            }
            AnnotationKind::Link { url, title } => {
                out.push('[');
                out.push_str(span);
                out.push_str("](");
                out.push_str(url);
                if let Some(t) = title {
                    out.push_str(" \"");
                    out.push_str(t);
                    out.push('"');
                }
                out.push(')');
            }
            AnnotationKind::Highlight => {
                out.push_str("<mark>");
                out.push_str(span);
                out.push_str("</mark>");
            }
            AnnotationKind::Color { .. } | AnnotationKind::FontSize { .. } | AnnotationKind::Custom { .. } => {
                // No standard markdown representation; output plain text
                out.push_str(span);
            }
        }
        pos = end;
    }

    // Remaining text after last annotation
    if (pos as usize) < bytes.len() {
        out.push_str(&text[pos as usize..]);
    }
}

/// Render a `TableGrid` as a markdown pipe table.
fn render_table_grid(out: &mut String, grid: &TableGrid) {
    if grid.rows == 0 || grid.cols == 0 {
        return;
    }

    // Build 2D array
    let mut rows: Vec<Vec<&str>> = vec![vec![""; grid.cols as usize]; grid.rows as usize];
    for cell in &grid.cells {
        if (cell.row as usize) < rows.len() && (cell.col as usize) < rows[0].len() {
            rows[cell.row as usize][cell.col as usize] = &cell.content;
        }
    }

    // Render header row
    if let Some(header) = rows.first() {
        out.push('|');
        for cell in header {
            out.push(' ');
            out.push_str(&cell.replace('|', "\\|"));
            out.push_str(" |");
        }
        out.push('\n');

        // Separator
        out.push('|');
        for _ in 0..grid.cols {
            out.push_str(" --- |");
        }
        out.push('\n');
    }

    // Data rows
    for row in rows.iter().skip(1) {
        out.push('|');
        for cell in row {
            out.push(' ');
            out.push_str(&cell.replace('|', "\\|"));
            out.push_str(" |");
        }
        out.push('\n');
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::builder::DocumentStructureBuilder;
    use crate::types::document_structure::ContentLayer;

    #[test]
    fn test_render_paragraphs() {
        let mut b = DocumentStructureBuilder::new();
        b.push_paragraph("Hello world.", vec![], None, None);
        b.push_paragraph("Second paragraph.", vec![], None, None);
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert_eq!(md, "Hello world.\n\nSecond paragraph.\n");
    }

    #[test]
    fn test_render_headings() {
        let mut b = DocumentStructureBuilder::new();
        b.push_heading(1, "Title", None, None);
        b.push_paragraph("Content.", vec![], None, None);
        b.push_heading(2, "Subtitle", None, None);
        b.push_paragraph("Sub content.", vec![], None, None);
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains("# Title"));
        assert!(md.contains("## Subtitle"));
        assert!(md.contains("Content."));
        assert!(md.contains("Sub content."));
    }

    #[test]
    fn test_render_list() {
        let mut b = DocumentStructureBuilder::new();
        let list = b.push_list(false, None);
        b.push_list_item(list, "Item 1", None);
        b.push_list_item(list, "Item 2", None);
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains("- Item 1"));
        assert!(md.contains("- Item 2"));
    }

    #[test]
    fn test_render_ordered_list() {
        let mut b = DocumentStructureBuilder::new();
        let list = b.push_list(true, None);
        b.push_list_item(list, "First", None);
        b.push_list_item(list, "Second", None);
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains("1. First"));
        assert!(md.contains("2. Second"));
    }

    #[test]
    fn test_render_code_block() {
        let mut b = DocumentStructureBuilder::new();
        b.push_code("fn main() {}", Some("rust"), None);
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains("```rust\nfn main() {}\n```"));
    }

    #[test]
    fn test_render_table() {
        let mut b = DocumentStructureBuilder::new();
        b.push_table_from_cells(
            &[
                vec!["Name".to_string(), "Age".to_string()],
                vec!["Alice".to_string(), "30".to_string()],
            ],
            None,
        );
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains("| Name | Age |"));
        assert!(md.contains("| --- | --- |"));
        assert!(md.contains("| Alice | 30 |"));
    }

    #[test]
    fn test_render_annotations() {
        let mut b = DocumentStructureBuilder::new();
        b.push_paragraph("Hello bold world", vec![crate::types::builder::bold(6, 10)], None, None);
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains("Hello **bold** world"));
    }

    #[test]
    fn test_render_formula() {
        let mut b = DocumentStructureBuilder::new();
        b.push_formula("E = mc^2", None);
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains("$$\nE = mc^2\n$$"));
    }

    #[test]
    fn test_render_empty() {
        let doc = DocumentStructureBuilder::new().build();
        let md = render_to_markdown(&doc);
        assert_eq!(md, "");
    }

    #[test]
    fn test_render_definition_list() {
        let mut b = DocumentStructureBuilder::new();
        let dl = b.push_definition_list(None);
        b.push_definition_item(dl, "Term", "Definition", None);
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains("Term\n: Definition"));
    }

    #[test]
    fn test_render_citation() {
        let mut b = DocumentStructureBuilder::new();
        b.push_citation("doe2024", "Doe, J. (2024). Paper Title.", None);
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains("[^doe2024]: Doe, J. (2024). Paper Title."));
    }

    #[test]
    fn test_render_metadata_block() {
        let mut b = DocumentStructureBuilder::new();
        b.push_metadata_block(
            vec![
                ("From".to_string(), "alice@example.com".to_string()),
                ("Subject".to_string(), "Hello".to_string()),
            ],
            None,
        );
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains("**From**: alice@example.com"));
        assert!(md.contains("**Subject**: Hello"));
    }

    #[test]
    fn test_overlapping_annotations() {
        // Two annotations overlap: bold(0,8) and italic(4,12) on "Hello World!"
        // The italic annotation starts inside the bold range, so it should be skipped.
        let mut b = DocumentStructureBuilder::new();
        b.push_paragraph(
            "Hello World!",
            vec![crate::types::builder::bold(0, 8), crate::types::builder::italic(4, 12)],
            None,
            None,
        );
        let doc = b.build();

        let md = render_to_markdown(&doc);
        // Bold renders "Hello Wo" (0..8), italic (4..12) is skipped because it overlaps.
        // Remaining text "rld!" is appended as plain text.
        assert!(md.contains("**Hello Wo**rld!"));
        // Should NOT contain broken nested markdown
        assert!(!md.contains("***"));
    }

    #[test]
    fn test_table_with_pipe_in_content() {
        let mut b = DocumentStructureBuilder::new();
        b.push_table_from_cells(
            &[
                vec!["Header".to_string(), "Value".to_string()],
                vec!["a | b".to_string(), "x|y".to_string()],
            ],
            None,
        );
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(md.contains(r"a \| b"));
        assert!(md.contains(r"x\|y"));
        // Headers should still be clean
        assert!(md.contains("| Header | Value |"));
    }

    #[test]
    fn test_group_heading_fallback_no_heading_child() {
        // Create a Group with heading_text/heading_level but no Heading child node.
        let mut b = DocumentStructureBuilder::new();
        let group_idx = b.push_raw(
            NodeContent::Group {
                label: None,
                heading_level: Some(2),
                heading_text: Some("Section Title".to_string()),
            },
            None,
            None,
            ContentLayer::Body,
            vec![],
        );
        // Add a paragraph as child of the group (but no Heading child)
        let para_idx = b.push_raw(
            NodeContent::Paragraph {
                text: "Group content.".to_string(),
            },
            None,
            None,
            ContentLayer::Body,
            vec![],
        );
        b.add_child(group_idx, para_idx);
        let doc = b.build();

        let md = render_to_markdown(&doc);
        assert!(
            md.contains("## Section Title"),
            "Group heading should be rendered as fallback: {md}"
        );
        assert!(md.contains("Group content."));
    }

    #[test]
    fn test_nested_list_rendering() {
        // Create an outer list with an item that has a nested list as a child.
        let mut b = DocumentStructureBuilder::new();
        let outer_list = b.push_list(false, None);
        let item1 = b.push_list_item(outer_list, "Outer item", None);

        // Create a nested list as a child of item1
        let inner_content = NodeContent::List { ordered: false };
        let inner_list = b.push_raw(inner_content, None, None, ContentLayer::Body, vec![]);
        b.add_child(item1, inner_list);

        let inner_item_content = NodeContent::ListItem {
            text: "Nested item".to_string(),
        };
        let inner_item = b.push_raw(inner_item_content, None, None, ContentLayer::Body, vec![]);
        b.add_child(inner_list, inner_item);

        let doc = b.build();
        let md = render_to_markdown(&doc);

        // Outer item at depth 0, inner item at depth 1 (indented by 2 spaces)
        assert!(md.contains("- Outer item"), "Should have outer item: {md}");
        assert!(md.contains("  - Nested item"), "Nested item should be indented: {md}");
    }
}
