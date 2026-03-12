//! Heading classification for layout regions (Title / SectionHeader).

use crate::pdf::markdown::classify::{classify_paragraphs, find_heading_level, precompute_gap_info};
use crate::pdf::markdown::constants::{MAX_BOLD_HEADING_WORD_COUNT, MAX_HEADING_WORD_COUNT};
use crate::pdf::markdown::layout_classify::{apply_hint_to_paragraph, infer_heading_level_from_text};
use crate::pdf::markdown::types::{LayoutHint, LayoutHintClass, PdfParagraph};

/// Apply a layout region's class to all paragraphs assembled from it.
pub(in crate::pdf::markdown) fn apply_region_class(
    paragraphs: &mut Vec<PdfParagraph>,
    hint: &LayoutHint,
    heading_map: &[(f32, Option<u8>)],
    doc_body_font_size: Option<f32>,
    page_height: f32,
    page_index: usize,
) {
    match hint.class {
        LayoutHintClass::Title | LayoutHintClass::SectionHeader => {
            apply_heading_region(paragraphs, hint, heading_map, doc_body_font_size, page_index);
        }
        LayoutHintClass::Text => {
            // Set layout_class BEFORE classification so classify_paragraphs can
            // skip font-size heading heuristics for model-identified Text regions.
            for para in paragraphs.iter_mut() {
                para.layout_class = Some(LayoutHintClass::Text);
            }
            classify_paragraphs(paragraphs, heading_map);
        }
        LayoutHintClass::PageHeader | LayoutHintClass::PageFooter => {
            // Validate position: only mark as page furniture if the region
            // is actually near the page margins. The layout model (trained on
            // academic papers) sometimes misclassifies body text as page
            // furniture on non-standard documents (legal, receipts, etc.).
            let is_near_margin = if page_height > 0.0 {
                let region_center_y = (hint.top + hint.bottom) / 2.0;
                let margin_fraction = 0.12; // top/bottom 12% of page
                let near_top = region_center_y > page_height * (1.0 - margin_fraction);
                let near_bottom = region_center_y < page_height * margin_fraction;
                near_top || near_bottom
            } else {
                true // Can't validate, trust the model
            };

            if is_near_margin {
                for para in paragraphs.iter_mut() {
                    apply_hint_to_paragraph(para, hint);
                }
            } else {
                // Region is in the body of the page — treat as Text, not furniture.
                // Set layout_class before classification for heading suppression.
                for para in paragraphs.iter_mut() {
                    para.layout_class = Some(LayoutHintClass::Text);
                }
                classify_paragraphs(paragraphs, heading_map);
            }
        }
        _ => {
            // Code, Formula, ListItem, Caption, Other
            for para in paragraphs.iter_mut() {
                apply_hint_to_paragraph(para, hint);
            }
        }
    }
}

/// Apply heading classification to paragraphs from a Title/SectionHeader region.
///
/// First tries layout-model-based heading assignment with guards for false positives.
/// Then falls through to `classify_paragraphs` for any paragraphs that weren't
/// assigned a heading level (e.g., bold headings at body font size that fail
/// the unnumbered-at-body-size guard but would be caught by the bold heuristic).
fn apply_heading_region(
    paragraphs: &mut Vec<PdfParagraph>,
    hint: &LayoutHint,
    heading_map: &[(f32, Option<u8>)],
    doc_body_font_size: Option<f32>,
    page_index: usize,
) {
    // Split multi-line paragraphs from SectionHeader regions where each line
    // is a distinct heading (merged by overlapping layout bboxes).
    if hint.class == LayoutHintClass::SectionHeader {
        split_multi_heading_paragraphs(paragraphs);
    }

    let body_font_size = doc_body_font_size.unwrap_or(0.0);
    let gap_info = precompute_gap_info(heading_map);

    for para in paragraphs.iter_mut() {
        para.layout_class = Some(hint.class);

        let word_count: usize = para
            .lines
            .iter()
            .flat_map(|l| l.segments.iter())
            .map(|s| s.text.split_whitespace().count())
            .sum();

        if word_count > MAX_HEADING_WORD_COUNT {
            continue; // Too many words for a heading
        }

        let is_monospace = para.lines.iter().all(|l| l.is_monospace);
        if is_monospace {
            continue; // Don't classify code as headings
        }

        let line_text: String = para
            .lines
            .iter()
            .flat_map(|l| l.segments.iter())
            .map(|s| s.text.as_str())
            .collect::<Vec<_>>()
            .join(" ");

        let trimmed = line_text.trim();
        if crate::pdf::markdown::layout_classify::is_separator_text(trimmed) {
            continue; // Separator lines (dashes, underscores, etc.)
        }
        if trimmed.ends_with(':') {
            continue; // Introductory body text
        }

        // Guard: headings don't end with a period. Captions, taglines, and
        // figure descriptions do (e.g., "Figure 7-26. Self-locking nuts.",
        // "Looking back on 175 years of looking forward.").
        if trimmed.ends_with('.') && !crate::pdf::markdown::classify::is_section_pattern(trimmed) {
            continue;
        }

        // Guard: figure/diagram labels (single-letter sequences, repetitive words)
        if looks_like_figure_label(trimmed) {
            continue;
        }

        // Combine layout model class with font-size clustering and text analysis.
        // The heading_map (from font-size clustering) may know the correct level
        // when the model mislabels a title as SectionHeader. The text-based
        // inference provides depth for numbered sections (H2/H3/H4).
        let text_level = infer_heading_level_from_text(&line_text, hint.class);
        let font_level = find_heading_level(para.dominant_font_size, heading_map, &gap_info);

        // Count heading clusters (entries with Some level) in the heading_map.
        // Only trust font-level H1 when there are 2+ heading clusters,
        // meaning the document has a true title/section hierarchy.
        // With only 1 heading cluster, the largest font is ambiguous — it might
        // be the only heading level (section headers, not a title).
        let heading_cluster_count = heading_map.iter().filter(|(_, level)| level.is_some()).count();

        let inferred_level = match (text_level, font_level) {
            // Font-size says H1 AND there are 2+ heading clusters → trust it,
            // but only for Title regions. SectionHeader at font H1 should stay H2
            // to avoid over-promoting section headers that happen to use a large font.
            (_, Some(1)) if heading_cluster_count >= 2 && hint.class == LayoutHintClass::Title => 1,
            // Title promotion: on the first page, font-size says H1 and is
            // significantly larger than body text (≥1.5×). A heading at 2×+
            // body size is almost certainly a document title, even when the
            // layout model labels it SectionHeader.
            (_, Some(1))
                if page_index == 0
                    && doc_body_font_size.is_some_and(|body| body > 0.0 && para.dominant_font_size / body >= 1.5) =>
            {
                1
            }
            // Font says H2 but text says deeper → trust font (flat heading style)
            // e.g. "5.1 Evaluation Setup" has 1 dot → text H3, but font size = H2
            (level, Some(2)) if level > 2 => 2,
            // Unnumbered header (text=H2) but font says deeper → trust font for demotion
            // e.g. unnumbered sub-section at smaller font size than numbered H2 sections
            (2, Some(font_lvl)) if font_lvl > 2 && heading_cluster_count >= 2 => font_lvl,
            // No heading clusters: can't distinguish heading depths via font size.
            // Cap at H2 — numbering depth ("5.1" vs "5") is unreliable without
            // font-size context (e.g., a single page may only have "5.1"/"5.2").
            (level, _) if level > 2 && heading_cluster_count == 0 => 2,
            // Text has section numbering → use text-based depth
            (level, _) if level > 2 => level,
            // Otherwise use the text-based level (which incorporates the hint class)
            (level, _) => level,
        };

        // Guard: unnumbered section headers at body font size are likely
        // bold sub-headings, not true section headers. Skip layout-based
        // assignment but let the bold heuristic below handle them.
        // Numbered sections (text_level > 2, meaning "3.2" etc.) pass through
        // since numbering IS evidence of a heading, even at body font size.
        if inferred_level == 2
            && text_level == 2
            && body_font_size > 0.0
            && para.dominant_font_size <= body_font_size + 0.5
        {
            continue;
        }

        para.heading_level = Some(inferred_level);
    }

    // Fallback: for paragraphs that weren't assigned heading level by the
    // layout-model logic (e.g., bold headings at body font size), run
    // font-size + bold classification. This catches bold short paragraphs
    // in SectionHeader regions that the unnumbered-at-body-size guard skipped.
    // Only apply to paragraphs without heading_level to avoid overwriting
    // correctly-inferred levels (e.g., layout says H2 but font-size says H1).
    for para in paragraphs.iter_mut() {
        if para.heading_level.is_some() {
            continue;
        }
        // Bold or italic short paragraph heuristic (extends classify.rs Pass 2).
        // Some documents use italic instead of bold for section titles.
        let word_count: usize = para
            .lines
            .iter()
            .flat_map(|l| l.segments.iter())
            .map(|s| s.text.split_whitespace().count())
            .sum();
        // Guard: very short bold text (1-2 words) at body font size in a SectionHeader
        // region is almost always a figure label (e.g., "Untightened nut", "Nut case"),
        // not a real heading. Real 2-word headings use a larger font size.
        if word_count <= 2 && body_font_size > 0.0 && para.dominant_font_size <= body_font_size + 0.5 {
            continue;
        }
        let is_italic = !para.lines.is_empty() && para.lines.iter().all(|l| l.segments.iter().all(|s| s.is_italic));
        if (para.is_bold || is_italic) && !para.is_list_item && word_count <= MAX_BOLD_HEADING_WORD_COUNT {
            // Apply same guards as the main heading assignment path
            let text: String = para
                .lines
                .iter()
                .flat_map(|l| l.segments.iter())
                .map(|s| s.text.as_str())
                .collect::<Vec<_>>()
                .join(" ");
            let t = text.trim();
            // Extra guards for italic-only (not bold): filter affiliations/emails
            let italic_ok = if is_italic && !para.is_bold {
                !t.contains('@') && !t.contains(',') && t.chars().next().is_some_and(|c| c.is_uppercase())
            } else {
                true
            };
            let period_ok = !t.ends_with('.') || crate::pdf::markdown::classify::is_section_pattern(t);
            if italic_ok
                && period_ok
                && !t.ends_with(':')
                && !looks_like_figure_label(t)
                && !crate::pdf::markdown::layout_classify::is_separator_text(t)
            {
                para.heading_level = Some(2);
            }
        }
    }
}

/// Check if text looks like a figure/diagram label rather than a real heading.
///
/// Catches concatenated figure labels (e.g., "Tightened nut Flexloc nut
/// Fiber locknut Elastic stop nut") and pure single-letter sequences ("A B C").
pub(in crate::pdf::markdown) fn looks_like_figure_label(text: &str) -> bool {
    let words: Vec<&str> = text.split_whitespace().collect();

    // All single-character words (3+): "A B C", "D E F"
    if words.len() >= 3 && words.iter().all(|w| w.len() <= 1) {
        return true;
    }

    // Concatenated labels: same word appears 3+ times (e.g., "nut" in figure parts)
    if words.len() >= 5 {
        for w in &words {
            let lw = w.to_lowercase();
            if words.iter().filter(|x| x.to_lowercase() == lw).count() >= 3 {
                return true;
            }
        }
    }

    false
}

/// Split multi-line heading paragraphs from SectionHeader regions.
///
/// When the layout model gives overlapping SectionHeader bboxes, distinct headings
/// (e.g., "Boots Self-Locking Nut" and "Stainless Steel Self-Locking Nut") can merge
/// into one multi-line paragraph. Split them back into separate paragraphs when each
/// line is short enough to be a heading on its own.
fn split_multi_heading_paragraphs(paragraphs: &mut Vec<PdfParagraph>) {
    let mut i = 0;
    while i < paragraphs.len() {
        let para = &paragraphs[i];

        // Only split multi-line paragraphs
        if para.lines.len() <= 1 {
            i += 1;
            continue;
        }

        // Find the longest prefix of consecutive short lines (heading candidates).
        // Lines after the first long line become body text in a separate paragraph.
        // This handles cases where a heading + body text are merged into one paragraph.
        let prefix_len = para
            .lines
            .iter()
            .take_while(|line| {
                let word_count: usize = line.segments.iter().map(|s| s.text.split_whitespace().count()).sum();
                word_count <= MAX_HEADING_WORD_COUNT
            })
            .count();

        if prefix_len == 0 {
            i += 1;
            continue;
        }

        // Split: heading prefix lines become individual paragraphs,
        // remaining lines become a single body paragraph.
        let original = paragraphs.remove(i);
        let mut lines_iter = original.lines.into_iter();
        let layout_class = original.layout_class;

        for j in 0..prefix_len {
            let line = lines_iter.next().unwrap();
            let mut new_para = crate::pdf::markdown::paragraphs::finalize_paragraph(vec![line]);
            new_para.layout_class = layout_class;
            paragraphs.insert(i + j, new_para);
        }

        // Remaining lines become a body paragraph (no layout class override)
        let remaining: Vec<_> = lines_iter.collect();
        if !remaining.is_empty() {
            let body_para = crate::pdf::markdown::paragraphs::finalize_paragraph(remaining);
            paragraphs.insert(i + prefix_len, body_para);
        }

        i += 1; // Move past the first split paragraph (others will be processed next)
    }
}
