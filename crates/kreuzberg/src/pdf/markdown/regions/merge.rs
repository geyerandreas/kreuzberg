//! Region-aware paragraph merging: continuation, code blocks, list items, code demotion.

use crate::pdf::markdown::types::{LayoutHintClass, PdfParagraph};

/// Merge continuation paragraphs, respecting layout class boundaries.
///
/// Like `merge_continuation_paragraphs` but also prevents merging
/// across different layout classes.
pub(in crate::pdf::markdown) fn merge_continuation_paragraphs_region_aware(paragraphs: &mut Vec<PdfParagraph>) {
    if paragraphs.len() < 2 {
        return;
    }

    let mut i = 0;
    while i + 1 < paragraphs.len() {
        let should_merge = {
            let current = &paragraphs[i];
            let next = &paragraphs[i + 1];

            // Both must be body text
            current.heading_level.is_none()
                && next.heading_level.is_none()
                && !current.is_list_item
                && !next.is_list_item
                && !current.is_code_block
                && !next.is_code_block
                && !current.is_formula
                && !next.is_formula
                // Same layout class (prevents cross-region merging)
                && current.layout_class == next.layout_class
                // Font sizes close enough
                && (current.dominant_font_size - next.dominant_font_size).abs() < 2.0
                // Current paragraph doesn't end with sentence-ending punctuation
                && !ends_with_sentence_terminator(current)
        };

        if should_merge {
            let next = paragraphs.remove(i + 1);
            paragraphs[i].lines.extend(next.lines);
        } else {
            i += 1;
        }
    }
}

/// Merge consecutive code block paragraphs into a single code block.
///
/// The layout model often gives one Code region per visual line, producing
/// multiple tiny code block paragraphs. This merges them back into one.
pub(in crate::pdf::markdown) fn merge_consecutive_code_blocks(paragraphs: &mut Vec<PdfParagraph>) {
    if paragraphs.len() < 2 {
        return;
    }

    let mut i = 0;
    while i + 1 < paragraphs.len() {
        if paragraphs[i].is_code_block && paragraphs[i + 1].is_code_block {
            let next = paragraphs.remove(i + 1);
            paragraphs[i].lines.extend(next.lines);
        } else {
            i += 1;
        }
    }
}

/// Merge consecutive list item paragraphs where the previous item is incomplete
/// (doesn't end with sentence-terminating punctuation) and the next doesn't
/// start with a recognized list prefix.
///
/// The layout model sometimes splits a single list item (e.g., a long reference)
/// across multiple bounding boxes. Each box becomes a separate ListItem paragraph,
/// but only the first has the actual list prefix. The continuation paragraphs
/// start with plain text and should be merged back into the preceding list item.
///
/// We require the previous item to be incomplete (no terminal punctuation) to
/// avoid merging distinct list items that both lack standard bullet/number prefixes
/// (e.g., `[1] ...` reference entries).
pub(in crate::pdf::markdown) fn merge_list_continuations(paragraphs: &mut Vec<PdfParagraph>) {
    if paragraphs.len() < 2 {
        return;
    }

    let mut i = 0;
    while i + 1 < paragraphs.len() {
        if paragraphs[i].is_list_item && paragraphs[i + 1].is_list_item {
            // Only merge if the previous item is incomplete (no sentence terminator)
            let prev_incomplete = !ends_with_sentence_terminator(&paragraphs[i]);

            // And the next paragraph doesn't start with a list prefix
            let next_has_prefix = paragraphs[i + 1]
                .lines
                .first()
                .and_then(|l| l.segments.first())
                .map(|s| {
                    let first_word = s.text.split_whitespace().next().unwrap_or("");
                    crate::pdf::markdown::paragraphs::is_list_prefix(first_word)
                })
                .unwrap_or(false);

            if prev_incomplete && !next_has_prefix {
                let next = paragraphs.remove(i + 1);
                paragraphs[i].lines.extend(next.lines);
                continue; // Re-check same position
            }
        }
        i += 1;
    }
}

/// Check if a paragraph's last line ends with sentence-terminating punctuation.
fn ends_with_sentence_terminator(para: &PdfParagraph) -> bool {
    let last_text = para
        .lines
        .last()
        .and_then(|l| l.segments.last())
        .map(|s| s.text.trim_end())
        .unwrap_or("");
    matches!(last_text.chars().last(), Some('.' | '?' | '!' | ':' | ';'))
}

/// Demote code blocks that don't contain actual code.
///
/// The layout model sometimes labels image data or figure text as Code regions.
/// Examples: hex dumps from embedded images ("5b 96 24\nc0 75 52"), or diagram
/// text fragments ("Assemble results, Serialize as JSON").
///
/// Two checks:
/// 1. Hex dump: >50% of words are short hex tokens (1-2 chars, all hex digits)
/// 2. No code syntax: text lacks code indicators (brackets, operators, keywords)
pub(in crate::pdf::markdown) fn demote_non_code_blocks(paragraphs: &mut [PdfParagraph]) {
    for para in paragraphs.iter_mut() {
        if !para.is_code_block {
            continue;
        }

        let all_text: String = para
            .lines
            .iter()
            .flat_map(|l| l.segments.iter())
            .map(|s| s.text.as_str())
            .collect::<Vec<_>>()
            .join(" ");

        if looks_like_non_code(&all_text) {
            para.is_code_block = false;
            para.layout_class = Some(LayoutHintClass::Text);
        }
    }
}

/// Check if text content doesn't look like code.
fn looks_like_non_code(text: &str) -> bool {
    let words: Vec<&str> = text.split_whitespace().collect();
    if words.is_empty() {
        return false;
    }

    // Check 1: hex dump (>50% of words are 1-2 char hex tokens)
    let hex_count = words
        .iter()
        .filter(|w| w.len() <= 2 && !w.is_empty() && w.chars().all(|c| c.is_ascii_hexdigit()))
        .count();
    if hex_count * 2 > words.len() {
        return true;
    }

    // Check 2: too few code syntax characters
    // Real code has ~10%+ syntax chars (brackets, operators, semicolons).
    // Figure text or prose has <3% even if a stray bracket appears.
    let total_chars = text.len();
    if total_chars < 10 {
        return false; // Too short to judge
    }

    let code_chars: usize = text
        .chars()
        .filter(|c| matches!(c, '(' | ')' | '{' | '}' | '[' | ']' | '=' | '<' | '>' | ';'))
        .count();

    // Require at least 3% syntax density for code
    code_chars * 100 < total_chars * 3
}
