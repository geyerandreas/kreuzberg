//! Heuristic table extraction from layout-detected Table regions.

use crate::pdf::markdown::types::{LayoutHint, LayoutHintClass};
use crate::pdf::table_reconstruct::{post_process_table, reconstruct_table, table_to_markdown};
use crate::types::Table;

use super::slanet::word_hint_iow;

/// Extract tables from layout-detected Table regions using character-level words.
///
/// Uses `extract_words_from_page()` for accurate word positions (character-level
/// splitting via pdfium), then filters words by Table hint bboxes. This is more
/// accurate than using segment-level data which may merge multiple table columns
/// into one segment.
pub(in crate::pdf::markdown) fn extract_tables_from_layout_hints(
    words: &[crate::pdf::table_reconstruct::HocrWord],
    hints: &[LayoutHint],
    page_index: usize,
    page_height: f32,
    min_confidence: f32,
) -> Vec<Table> {
    use crate::pdf::table_reconstruct::HocrWord;

    let table_hints: Vec<&LayoutHint> = hints
        .iter()
        .filter(|h| h.class == LayoutHintClass::Table && h.confidence >= min_confidence)
        .collect();

    if table_hints.is_empty() {
        return Vec::new();
    }

    let mut tables = Vec::new();

    for hint in &table_hints {
        // Filter words that overlap the table hint bbox (≥20% of word area).
        // HocrWord uses image coordinates (y=0 at top), while hint uses PDF
        // coordinates (y=0 at bottom). Convert hint bbox to image coords.
        let hint_img_top = (page_height - hint.top).max(0.0);
        let hint_img_bottom = (page_height - hint.bottom).max(0.0);

        let table_words: Vec<HocrWord> = words
            .iter()
            .filter(|w| {
                if w.text.trim().is_empty() {
                    return false;
                }
                word_hint_iow(w, hint.left, hint_img_top, hint.right, hint_img_bottom) >= 0.2
            })
            .cloned()
            .collect();

        // Need at least 4 words for a meaningful table
        if table_words.len() < 4 {
            continue;
        }

        // Adaptive column gap threshold: scale with table width.
        // Narrow tables (< 300pt) use a tight threshold (15), while wide
        // tables (> 600pt) use a looser threshold (30) to avoid over-splitting.
        let table_width = hint.right - hint.left;
        let col_gap = if table_width < 300.0 {
            15
        } else if table_width < 600.0 {
            20
        } else {
            30
        };
        let table_cells = reconstruct_table(&table_words, col_gap, 0.5);

        if table_cells.is_empty() || table_cells[0].is_empty() {
            continue;
        }

        // Bounding box from the layout hint (already in PDF coordinates)
        let bounding_box = Some(crate::types::BoundingBox {
            x0: hint.left as f64,
            y0: hint.bottom as f64,
            x1: hint.right as f64,
            y1: hint.top as f64,
        });

        // Validate with layout_guided=true (relaxed thresholds)
        let table_cells = match post_process_table(table_cells, true) {
            Some(cleaned) => cleaned,
            None => {
                // Table reconstruction failed — render words as fallback text so
                // content isn't silently dropped. Sort by position (top→bottom,
                // left→right) and group into lines.
                let mut sorted_words = table_words;
                // Use a fixed row threshold based on median height to ensure
                // the comparator implements a total order (transitivity).
                let median_height = {
                    let mut heights: Vec<u32> = sorted_words.iter().map(|w| w.height).collect();
                    heights.sort_unstable();
                    heights.get(heights.len() / 2).copied().unwrap_or(10)
                };
                let row_threshold = median_height / 2;
                sorted_words.sort_by(|a, b| {
                    let ay = a.top;
                    let by = b.top;
                    if ay.abs_diff(by) > row_threshold {
                        ay.cmp(&by)
                    } else {
                        a.left.cmp(&b.left)
                    }
                });

                let mut lines: Vec<String> = Vec::new();
                let mut current_line = String::new();
                let mut last_top: Option<u32> = None;

                for w in &sorted_words {
                    let same_line = last_top.is_some_and(|lt| lt.abs_diff(w.top) <= w.height / 2);
                    if same_line {
                        current_line.push(' ');
                        current_line.push_str(w.text.trim());
                    } else {
                        if !current_line.is_empty() {
                            lines.push(std::mem::take(&mut current_line));
                        }
                        current_line = w.text.trim().to_string();
                    }
                    last_top = Some(w.top);
                }
                if !current_line.is_empty() {
                    lines.push(current_line);
                }

                let markdown = lines.join("\n\n");
                if markdown.is_empty() {
                    continue;
                }

                tables.push(Table {
                    cells: Vec::new(),
                    markdown,
                    page_number: page_index + 1,
                    bounding_box,
                });
                continue;
            }
        };

        let markdown = table_to_markdown(&table_cells);

        tables.push(Table {
            cells: table_cells,
            markdown,
            page_number: page_index + 1,
            bounding_box,
        });
    }

    tables
}
