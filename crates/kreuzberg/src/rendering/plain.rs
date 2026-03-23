//! Render a `DocumentStructure` tree to plain text.

use crate::types::document_structure::{ContentLayer, DocumentStructure, NodeContent, NodeIndex, TableGrid};

/// Render a `DocumentStructure` to plain text.
///
/// Strips all formatting — headings become plain lines, tables become
/// space-separated text, annotations are ignored.
pub fn render_to_plain(doc: &DocumentStructure) -> String {
    let mut out = String::new();

    for (idx, _node) in doc.body_roots() {
        render_node(doc, idx, &mut out);
    }

    // Footnotes
    let footnotes: Vec<_> = doc
        .furniture_roots()
        .filter(|(_, n)| n.content_layer == ContentLayer::Footnote)
        .collect();
    if !footnotes.is_empty() {
        out.push('\n');
        for (idx, _) in footnotes {
            render_node(doc, idx, &mut out);
        }
    }

    let trimmed = out.trim_end();
    if trimmed.is_empty() {
        return String::new();
    }
    let mut result = trimmed.to_string();
    result.push('\n');
    result
}

fn render_node(doc: &DocumentStructure, idx: NodeIndex, out: &mut String) {
    let node = match doc.get(idx) {
        Some(n) => n,
        None => return,
    };

    match &node.content {
        NodeContent::Title { text }
        | NodeContent::Heading { text, .. }
        | NodeContent::Paragraph { text }
        | NodeContent::Footnote { text } => {
            out.push_str(text);
            out.push_str("\n\n");
        }
        NodeContent::ListItem { text } => {
            out.push_str(text);
            out.push('\n');
        }
        NodeContent::List { .. } => {
            for child_idx in &node.children {
                render_node(doc, *child_idx, out);
            }
            out.push('\n');
        }
        NodeContent::Table { grid } => {
            render_table_plain(out, grid);
            out.push('\n');
        }
        NodeContent::Image { description, .. } => {
            if let Some(desc) = description {
                out.push_str(&format!("[Image: {}]\n\n", desc));
            }
        }
        NodeContent::Code { text, .. } => {
            out.push_str(text);
            if !text.ends_with('\n') {
                out.push('\n');
            }
            out.push('\n');
        }
        NodeContent::Quote => {
            for child_idx in &node.children {
                render_node(doc, *child_idx, out);
            }
        }
        NodeContent::Formula { text } => {
            out.push_str(text);
            out.push_str("\n\n");
        }
        NodeContent::Group { heading_text, .. } => {
            // If the group has heading_text but no Heading child, render it as
            // plain text so the section title is not silently lost.
            if let Some(ht) = heading_text {
                let has_heading_child = node.children.iter().any(|c| {
                    doc.get(*c)
                        .is_some_and(|n| matches!(n.content, NodeContent::Heading { .. }))
                });
                if !has_heading_child {
                    out.push_str(ht);
                    out.push_str("\n\n");
                }
            }
            for child_idx in &node.children {
                render_node(doc, *child_idx, out);
            }
        }
        NodeContent::PageBreak => {
            out.push('\n');
        }
        NodeContent::Slide { title, .. } => {
            if let Some(t) = title {
                out.push_str(t);
                out.push_str("\n\n");
            }
            for child_idx in &node.children {
                render_node(doc, *child_idx, out);
            }
        }
        NodeContent::DefinitionList => {
            for child_idx in &node.children {
                render_node(doc, *child_idx, out);
            }
        }
        NodeContent::DefinitionItem { term, definition } => {
            out.push_str(term);
            out.push_str(": ");
            out.push_str(definition);
            out.push_str("\n\n");
        }
        NodeContent::Citation { text, .. } => {
            out.push_str(text);
            out.push_str("\n\n");
        }
        NodeContent::Admonition { kind, title } => {
            if let Some(t) = title {
                out.push_str(t);
            } else {
                out.push_str(kind);
            }
            out.push_str("\n\n");
            for child_idx in &node.children {
                render_node(doc, *child_idx, out);
            }
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
                out.push_str(key);
                out.push_str(": ");
                out.push_str(value);
                out.push('\n');
            }
            out.push('\n');
        }
    }
}

fn render_table_plain(out: &mut String, grid: &TableGrid) {
    if grid.rows == 0 || grid.cols == 0 {
        return;
    }

    let mut rows: Vec<Vec<&str>> = vec![vec![""; grid.cols as usize]; grid.rows as usize];
    for cell in &grid.cells {
        if (cell.row as usize) < rows.len() && (cell.col as usize) < rows[0].len() {
            rows[cell.row as usize][cell.col as usize] = &cell.content;
        }
    }

    for row in &rows {
        out.push_str(&row.join(" "));
        out.push('\n');
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::builder::DocumentStructureBuilder;

    #[test]
    fn test_plain_paragraphs() {
        let mut b = DocumentStructureBuilder::new();
        b.push_paragraph("Hello.", vec![], None, None);
        b.push_paragraph("World.", vec![], None, None);
        let doc = b.build();

        let plain = render_to_plain(&doc);
        assert_eq!(plain, "Hello.\n\nWorld.\n");
    }

    #[test]
    fn test_plain_headings_are_plain() {
        let mut b = DocumentStructureBuilder::new();
        b.push_heading(1, "Title", None, None);
        b.push_paragraph("Body.", vec![], None, None);
        let doc = b.build();

        let plain = render_to_plain(&doc);
        assert!(plain.contains("Title"));
        assert!(!plain.contains('#'));
    }

    #[test]
    fn test_plain_empty() {
        let doc = DocumentStructureBuilder::new().build();
        assert_eq!(render_to_plain(&doc), "");
    }

    #[test]
    fn test_plain_code_block() {
        let mut b = DocumentStructureBuilder::new();
        b.push_code("fn main() {}", Some("rust"), None);
        let doc = b.build();

        let plain = render_to_plain(&doc);
        assert!(plain.contains("fn main() {}"));
        assert!(!plain.contains("```")); // No markdown fences
    }

    #[test]
    fn test_plain_definition_list() {
        let mut b = DocumentStructureBuilder::new();
        let dl = b.push_definition_list(None);
        b.push_definition_item(dl, "Term", "Definition", None);
        let doc = b.build();

        let plain = render_to_plain(&doc);
        assert!(plain.contains("Term: Definition"));
    }

    #[test]
    fn test_plain_citation() {
        let mut b = DocumentStructureBuilder::new();
        b.push_citation("doe2024", "Doe, J. (2024). Paper.", None);
        let doc = b.build();

        let plain = render_to_plain(&doc);
        assert!(plain.contains("Doe, J. (2024). Paper."));
        assert!(!plain.contains("doe2024")); // Key not shown in plain text
    }

    #[test]
    fn test_plain_metadata_block() {
        let mut b = DocumentStructureBuilder::new();
        b.push_metadata_block(
            vec![
                ("From".to_string(), "alice@example.com".to_string()),
                ("Subject".to_string(), "Hello".to_string()),
            ],
            None,
        );
        let doc = b.build();

        let plain = render_to_plain(&doc);
        assert!(plain.contains("From: alice@example.com"));
        assert!(plain.contains("Subject: Hello"));
    }

    #[test]
    fn test_plain_admonition() {
        let mut b = DocumentStructureBuilder::new();
        b.push_admonition("warning", Some("Danger"), None);
        b.push_paragraph("Be careful.", vec![], None, None);
        b.exit_container();
        let doc = b.build();

        let plain = render_to_plain(&doc);
        assert!(plain.contains("Danger"));
        assert!(plain.contains("Be careful."));
    }

    #[test]
    fn test_plain_list() {
        let mut b = DocumentStructureBuilder::new();
        let list = b.push_list(false, None);
        b.push_list_item(list, "First", None);
        b.push_list_item(list, "Second", None);
        let doc = b.build();

        let plain = render_to_plain(&doc);
        assert!(plain.contains("First"));
        assert!(plain.contains("Second"));
        assert!(!plain.contains('-')); // No markdown bullets
    }
}
