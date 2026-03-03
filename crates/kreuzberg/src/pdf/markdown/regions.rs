//! Layout-guided segment assembly using model bounding boxes.
//!
//! When layout detection is enabled, this module assigns text segments to
//! layout regions *before* line/paragraph assembly, ensuring paragraph
//! boundaries align with the model's structural predictions.

use crate::pdf::hierarchy::SegmentData;
use crate::pdf::table_reconstruct::{post_process_table, reconstruct_table, table_to_markdown};
use crate::types::Table;

use super::classify::{classify_paragraphs, find_heading_level, precompute_gap_info};
use super::columns::split_segments_into_columns;
use super::constants::{MAX_BOLD_HEADING_WORD_COUNT, MAX_HEADING_WORD_COUNT, REGION_SAME_ROW_FRACTION};
use super::layout_classify::{apply_hint_to_paragraph, infer_heading_level_from_text};
use super::lines::segments_to_lines;
use super::paragraphs::{lines_to_paragraphs, merge_continuation_paragraphs};
use super::types::{LayoutHint, LayoutHintClass, PdfParagraph};

/// A layout region with its assigned segment indices.
struct LayoutRegion<'a> {
    hint: &'a LayoutHint,
    segment_indices: Vec<usize>,
}

/// Assemble paragraphs using layout-region-guided segment assignment.
///
/// Instead of assembling all segments into paragraphs first and then matching
/// to layout hints, this assigns segments to layout regions *before* assembly.
/// Each region's segments are independently assembled into lines and paragraphs,
/// then the region's layout class is applied directly.
///
/// Segments not covered by any layout region fall through to the standard
/// pipeline (XY-Cut → lines → paragraphs → font-size classification).
pub(super) fn assemble_region_paragraphs(
    segments: Vec<SegmentData>,
    hints: &[LayoutHint],
    heading_map: &[(f32, Option<u8>)],
    min_confidence: f32,
    doc_body_font_size: Option<f32>,
    page_index: usize,
) -> Vec<PdfParagraph> {
    let (mut regions, unassigned_indices) = assign_segments_to_regions(&segments, hints, min_confidence);

    if regions.is_empty() {
        // No confident hints matched — fall through to standard pipeline
        return assemble_fallback(segments, heading_map);
    }

    // Determine page height for reading order (from segment extents)
    let page_height = segments.iter().map(|s| s.y + s.height).fold(0.0_f32, f32::max);

    order_regions_reading_order(&mut regions, page_height);

    // Count heading-class regions with segments (for H1 promotion heuristic).
    // When there's only 1 heading region on the page and font size says H1,
    // it's very likely a document title. With multiple heading regions, the
    // single-cluster font level H1 is ambiguous (could be section headers).
    let heading_region_count = regions
        .iter()
        .filter(|r| {
            matches!(r.hint.class, LayoutHintClass::Title | LayoutHintClass::SectionHeader)
                && !r.segment_indices.is_empty()
        })
        .count();

    let mut all_paragraphs: Vec<PdfParagraph> = Vec::new();

    // Assemble paragraphs per region
    for region in &regions {
        if region.segment_indices.is_empty() {
            continue;
        }

        let region_segments: Vec<SegmentData> = region
            .segment_indices
            .iter()
            .map(|&idx| segments[idx].clone())
            .collect();

        let lines = segments_to_lines(region_segments);
        let mut paragraphs = lines_to_paragraphs(lines);

        // For ListItem regions, the layout model identifies one bbox per list item.
        // If paragraph splitting created multiple paragraphs, merge them back into
        // a single list item before applying the class.
        if region.hint.class == LayoutHintClass::ListItem && paragraphs.len() > 1 {
            let mut merged_lines = Vec::new();
            for para in paragraphs.drain(..) {
                merged_lines.extend(para.lines);
            }
            paragraphs.push(super::paragraphs::finalize_paragraph(merged_lines));
        }

        apply_region_class(
            &mut paragraphs,
            region.hint,
            heading_map,
            doc_body_font_size,
            page_height,
            heading_region_count,
            page_index,
        );

        all_paragraphs.extend(paragraphs);
    }

    // Handle unassigned segments via standard pipeline
    if !unassigned_indices.is_empty() {
        let unassigned_segments: Vec<SegmentData> =
            unassigned_indices.iter().map(|&idx| segments[idx].clone()).collect();
        let mut fallback = assemble_fallback(unassigned_segments, heading_map);
        all_paragraphs.append(&mut fallback);
    }

    // Merge continuation paragraphs, but only within same layout class
    merge_continuation_paragraphs_region_aware(&mut all_paragraphs);

    // Merge consecutive code blocks (layout model often gives one region per line)
    merge_consecutive_code_blocks(&mut all_paragraphs);

    // Validate code blocks: reject those that look like image data or artifacts
    // rather than actual code (e.g., hex dumps from embedded images).
    demote_non_code_blocks(&mut all_paragraphs);

    // Merge list item continuations (layout model may split one reference across bboxes)
    merge_list_continuations(&mut all_paragraphs);

    all_paragraphs
}

/// Assign each segment to its best-matching layout region.
///
/// Uses center-point containment: a segment is assigned to the region whose
/// bbox contains the segment's center. If multiple regions overlap at that
/// point, the smallest-area region wins (most specific).
///
/// Table and Picture regions are excluded from text assignment (handled by
/// separate pipelines). Segments within those regions are dropped entirely
/// to avoid duplicating content that appears in the extracted tables.
fn assign_segments_to_regions<'a>(
    segments: &[SegmentData],
    hints: &'a [LayoutHint],
    min_confidence: f32,
) -> (Vec<LayoutRegion<'a>>, Vec<usize>) {
    let confident_hints: Vec<&LayoutHint> = hints
        .iter()
        .filter(|h| h.confidence >= min_confidence)
        // Exclude Table and Picture — handled by separate pipelines
        .filter(|h| !matches!(h.class, LayoutHintClass::Table | LayoutHintClass::Picture))
        .collect();

    // Collect Table bboxes to suppress their segments from paragraphs.
    // Table content is extracted separately via extract_tables_from_layout_hints().
    // Picture regions still allow segments through (no separate text extraction for them).
    let table_hints: Vec<&LayoutHint> = hints
        .iter()
        .filter(|h| h.confidence >= min_confidence)
        .filter(|h| h.class == LayoutHintClass::Table)
        .collect();

    if confident_hints.is_empty() && table_hints.is_empty() {
        let all_indices: Vec<usize> = (0..segments.len()).collect();
        return (Vec::new(), all_indices);
    }

    // Pre-compute hint areas for tie-breaking
    let hint_areas: Vec<f32> = confident_hints
        .iter()
        .map(|h| (h.right - h.left) * (h.top - h.bottom))
        .collect();

    // Build region containers
    let mut regions: Vec<LayoutRegion> = confident_hints
        .iter()
        .map(|&hint| LayoutRegion {
            hint,
            segment_indices: Vec::new(),
        })
        .collect();

    let mut unassigned: Vec<usize> = Vec::new();

    for (seg_idx, seg) in segments.iter().enumerate() {
        if seg.text.trim().is_empty() {
            continue; // Skip whitespace-only segments
        }

        let cx = seg.x + seg.width / 2.0;
        let cy = seg.y + seg.height / 2.0;

        // Check if this segment falls within a Table region.
        // If so, skip it — the content is handled by the table extraction pipeline.
        let in_excluded = table_hints
            .iter()
            .any(|h| cx >= h.left && cx <= h.right && cy >= h.bottom && cy <= h.top);
        if in_excluded {
            continue;
        }

        // Find the containing hint with smallest area
        let mut best_hint_idx: Option<usize> = None;
        let mut best_area = f32::MAX;

        for (hi, hint) in confident_hints.iter().enumerate() {
            if cx >= hint.left && cx <= hint.right && cy >= hint.bottom && cy <= hint.top && hint_areas[hi] < best_area
            {
                best_area = hint_areas[hi];
                best_hint_idx = Some(hi);
            }
        }

        match best_hint_idx {
            Some(hi) => regions[hi].segment_indices.push(seg_idx),
            None => unassigned.push(seg_idx),
        }
    }

    (regions, unassigned)
}

/// Sort regions in reading order: top-to-bottom, left-to-right within same row.
///
/// First detects if the page has a multi-column layout by analyzing horizontal
/// gaps between region bounding boxes. If columns are detected, processes each
/// column top-to-bottom (left column first, then right column). Otherwise
/// falls back to simple Y-ordering with same-row left-to-right sorting.
fn order_regions_reading_order(regions: &mut [LayoutRegion], page_height: f32) {
    if let Some(split_x) = detect_region_column_split(regions) {
        // Column-aware ordering: left column first, then right
        regions.sort_by(|a, b| {
            let a_cx = (a.hint.left + a.hint.right) / 2.0;
            let b_cx = (b.hint.left + b.hint.right) / 2.0;
            let a_col = if a_cx < split_x { 0u8 } else { 1 };
            let b_col = if b_cx < split_x { 0u8 } else { 1 };

            if a_col != b_col {
                return a_col.cmp(&b_col);
            }

            // Same column: higher Y = top of page → comes first
            let a_cy = (a.hint.top + a.hint.bottom) / 2.0;
            let b_cy = (b.hint.top + b.hint.bottom) / 2.0;
            b_cy.total_cmp(&a_cy)
        });
    } else {
        let y_tolerance = page_height * REGION_SAME_ROW_FRACTION;

        regions.sort_by(|a, b| {
            let a_cy = (a.hint.top + a.hint.bottom) / 2.0;
            let b_cy = (b.hint.top + b.hint.bottom) / 2.0;

            // If vertical centers are close, they're in the same row → sort left-to-right
            if (a_cy - b_cy).abs() < y_tolerance {
                a.hint.left.total_cmp(&b.hint.left)
            } else {
                // Higher Y = top of page in PDF coords → comes first in reading order
                b_cy.total_cmp(&a_cy)
            }
        });
    }
}

/// Minimum absolute gap (in points) between region columns.
const MIN_REGION_COLUMN_GAP: f32 = 5.0;

/// Minimum vertical extent (fraction) that each column must span.
const MIN_COLUMN_VERTICAL_FRACTION: f32 = 0.3;

/// Detect if layout regions form two distinct columns.
///
/// Returns the x-position to split at, or None if no column layout detected.
/// Only considers content regions (excludes PageHeader/PageFooter).
fn detect_region_column_split(regions: &[LayoutRegion]) -> Option<f32> {
    if regions.len() < 4 {
        return None;
    }

    // Collect horizontal edges of content regions
    let mut edges: Vec<(f32, f32)> = regions
        .iter()
        .filter(|r| !matches!(r.hint.class, LayoutHintClass::PageHeader | LayoutHintClass::PageFooter))
        .map(|r| (r.hint.left, r.hint.right))
        .collect();

    if edges.len() < 4 {
        return None;
    }

    edges.sort_by(|a, b| a.0.total_cmp(&b.0));

    // Find the largest horizontal gap
    let mut max_right = f32::MIN;
    let mut best_gap = 0.0_f32;
    let mut best_split: Option<f32> = None;

    for &(left, right) in &edges {
        if max_right > f32::MIN {
            let gap = left - max_right;
            if gap > best_gap {
                best_gap = gap;
                best_split = Some((max_right + left) / 2.0);
            }
        }
        max_right = max_right.max(right);
    }

    if best_gap < MIN_REGION_COLUMN_GAP {
        return None;
    }

    let split_x = best_split?;

    // Validate: both sides have at least 2 content regions
    let left_count = regions
        .iter()
        .filter(|r| (r.hint.left + r.hint.right) / 2.0 < split_x)
        .count();
    let right_count = regions
        .iter()
        .filter(|r| (r.hint.left + r.hint.right) / 2.0 >= split_x)
        .count();

    if left_count < 2 || right_count < 2 {
        return None;
    }

    // Validate: both columns span a significant portion of vertical extent
    let y_min = regions.iter().map(|r| r.hint.bottom).fold(f32::MAX, f32::min);
    let y_max = regions.iter().map(|r| r.hint.top).fold(f32::MIN, f32::max);
    let y_span = y_max - y_min;

    if y_span < 1.0 {
        return None;
    }

    let left_y_span = {
        let mut lo = f32::MAX;
        let mut hi = f32::MIN;
        for r in regions.iter().filter(|r| (r.hint.left + r.hint.right) / 2.0 < split_x) {
            lo = lo.min(r.hint.bottom);
            hi = hi.max(r.hint.top);
        }
        hi - lo
    };
    let right_y_span = {
        let mut lo = f32::MAX;
        let mut hi = f32::MIN;
        for r in regions.iter().filter(|r| (r.hint.left + r.hint.right) / 2.0 >= split_x) {
            lo = lo.min(r.hint.bottom);
            hi = hi.max(r.hint.top);
        }
        hi - lo
    };

    if left_y_span < y_span * MIN_COLUMN_VERTICAL_FRACTION || right_y_span < y_span * MIN_COLUMN_VERTICAL_FRACTION {
        return None;
    }

    Some(split_x)
}

/// Apply a layout region's class to all paragraphs assembled from it.
fn apply_region_class(
    paragraphs: &mut Vec<PdfParagraph>,
    hint: &LayoutHint,
    heading_map: &[(f32, Option<u8>)],
    doc_body_font_size: Option<f32>,
    page_height: f32,
    heading_region_count: usize,
    page_index: usize,
) {
    match hint.class {
        LayoutHintClass::Title | LayoutHintClass::SectionHeader => {
            apply_heading_region(
                paragraphs,
                hint,
                heading_map,
                doc_body_font_size,
                heading_region_count,
                page_index,
            );
        }
        LayoutHintClass::Text => {
            // Text regions: run font-size-based heading classification
            classify_paragraphs(paragraphs, heading_map);
            for para in paragraphs.iter_mut() {
                para.layout_class = Some(LayoutHintClass::Text);
            }
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
                // Region is in the body of the page — treat as Text, not furniture
                classify_paragraphs(paragraphs, heading_map);
                for para in paragraphs.iter_mut() {
                    para.layout_class = Some(LayoutHintClass::Text);
                }
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
    heading_region_count: usize,
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
        if trimmed.ends_with(':') {
            continue; // Introductory body text
        }

        // Guard: headings don't end with a period. Captions, taglines, and
        // figure descriptions do (e.g., "Figure 7-26. Self-locking nuts.",
        // "Looking back on 175 years of looking forward.").
        if trimmed.ends_with('.') {
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
            // Font-size says H1 AND there are 2+ heading clusters → trust it
            (_, Some(1)) if heading_cluster_count >= 2 => 1,
            // Title promotion: sole heading region on first page with font size
            // significantly larger than body text (≥1.5×). With only 1 heading
            // font cluster, a section header at 1.2× body won't match,
            // but a document title at 2×+ will.
            (_, Some(1))
                if heading_cluster_count == 1
                    && heading_region_count == 1
                    && page_index == 0
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
                !t.contains('@') && !t.contains(',') && t.chars().next().is_some_and(|c| c.is_ascii_uppercase())
            } else {
                true
            };
            if italic_ok && !t.ends_with('.') && !t.ends_with(':') && !looks_like_figure_label(t) {
                para.heading_level = Some(2);
            }
        }
    }
}

/// Check if text looks like a figure/diagram label rather than a real heading.
///
/// Catches concatenated figure labels (e.g., "Tightened nut Flexloc nut
/// Fiber locknut Elastic stop nut") and pure single-letter sequences ("A B C").
pub(super) fn looks_like_figure_label(text: &str) -> bool {
    let words: Vec<&str> = text.split_whitespace().collect();

    // All single-character words (3+): "A B C", "D E F"
    if words.len() >= 3 && words.iter().all(|w| w.len() <= 1) {
        return true;
    }

    // Concatenated labels: same word appears 3+ times (e.g., "nut" in figure parts)
    if words.len() >= 5 {
        for w in &words {
            let lw = w.to_ascii_lowercase();
            if words.iter().filter(|x| x.to_ascii_lowercase() == lw).count() >= 3 {
                return true;
            }
        }
    }

    false
}

/// Merge continuation paragraphs, respecting layout class boundaries.
///
/// Like `merge_continuation_paragraphs` but also prevents merging
/// across different layout classes.
fn merge_continuation_paragraphs_region_aware(paragraphs: &mut Vec<PdfParagraph>) {
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
fn merge_consecutive_code_blocks(paragraphs: &mut Vec<PdfParagraph>) {
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
fn merge_list_continuations(paragraphs: &mut Vec<PdfParagraph>) {
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
                    super::paragraphs::is_list_prefix(first_word)
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
fn demote_non_code_blocks(paragraphs: &mut [PdfParagraph]) {
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

        // Check that each line is short enough to be a heading
        let all_lines_short = para.lines.iter().all(|line| {
            let word_count: usize = line.segments.iter().map(|s| s.text.split_whitespace().count()).sum();
            word_count <= MAX_HEADING_WORD_COUNT
        });

        if !all_lines_short {
            i += 1;
            continue;
        }

        // Split: replace this paragraph with one paragraph per line
        let original = paragraphs.remove(i);
        for (j, line) in original.lines.into_iter().enumerate() {
            let mut new_para = super::paragraphs::finalize_paragraph(vec![line]);
            new_para.layout_class = original.layout_class;
            paragraphs.insert(i + j, new_para);
        }

        i += 1; // Move past the first split paragraph (others will be processed next)
    }
}

/// Extract tables from layout-detected Table regions using character-level words.
///
/// Uses `extract_words_from_page()` for accurate word positions (character-level
/// splitting via pdfium), then filters words by Table hint bboxes. This is more
/// accurate than using segment-level data which may merge multiple table columns
/// into one segment.
pub(super) fn extract_tables_from_layout_hints(
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
        // Filter words whose center falls within the table hint bbox.
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
                let cx = w.left as f32 + w.width as f32 / 2.0;
                let cy = w.top as f32 + w.height as f32 / 2.0;
                cx >= hint.left && cx <= hint.right && cy >= hint_img_top && cy <= hint_img_bottom
            })
            .cloned()
            .collect();

        // Need at least 4 words for a meaningful table
        if table_words.len() < 4 {
            continue;
        }

        // Use tighter column threshold since we're already within a table bbox
        let table_cells = reconstruct_table(&table_words, 30, 0.5);

        if table_cells.is_empty() || table_cells[0].is_empty() {
            continue;
        }

        // Validate with layout_guided=true (relaxes min columns from 3 to 2)
        let table_cells = match post_process_table(table_cells, true) {
            Some(cleaned) => cleaned,
            None => continue,
        };

        let markdown = table_to_markdown(&table_cells);

        // Bounding box from the layout hint (already in PDF coordinates)
        let bounding_box = Some(crate::types::BoundingBox {
            x0: hint.left as f64,
            y0: hint.bottom as f64,
            x1: hint.right as f64,
            y1: hint.top as f64,
        });

        tables.push(Table {
            cells: table_cells,
            markdown,
            page_number: page_index + 1,
            bounding_box,
        });
    }

    tables
}

/// Standard pipeline fallback for segments not covered by layout regions.
fn assemble_fallback(segments: Vec<SegmentData>, heading_map: &[(f32, Option<u8>)]) -> Vec<PdfParagraph> {
    let column_groups = split_segments_into_columns(&segments);
    let mut paragraphs: Vec<PdfParagraph> = if column_groups.len() <= 1 {
        let lines = segments_to_lines(segments);
        lines_to_paragraphs(lines)
    } else {
        let mut all_paragraphs = Vec::new();
        for group in column_groups {
            let col_segments: Vec<_> = group.into_iter().map(|idx| segments[idx].clone()).collect();
            let lines = segments_to_lines(col_segments);
            all_paragraphs.extend(lines_to_paragraphs(lines));
        }
        all_paragraphs
    };
    classify_paragraphs(&mut paragraphs, heading_map);
    merge_continuation_paragraphs(&mut paragraphs);
    paragraphs
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pdf::hierarchy::SegmentData;

    fn make_segment(text: &str, x: f32, y: f32, width: f32, height: f32) -> SegmentData {
        SegmentData {
            text: text.to_string(),
            x,
            y,
            width,
            height,
            font_size: height,
            is_bold: false,
            is_italic: false,
            is_monospace: false,
            baseline_y: y,
        }
    }

    fn make_hint(class: LayoutHintClass, confidence: f32, left: f32, bottom: f32, right: f32, top: f32) -> LayoutHint {
        LayoutHint {
            class,
            confidence,
            left,
            bottom,
            right,
            top,
        }
    }

    #[test]
    fn test_assign_segments_single_region() {
        let segments = vec![
            make_segment("Hello", 10.0, 700.0, 40.0, 12.0),
            make_segment("world", 55.0, 700.0, 40.0, 12.0),
        ];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 0.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5);
        assert_eq!(regions.len(), 1);
        assert_eq!(regions[0].segment_indices.len(), 2);
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_assign_segments_two_columns() {
        let segments = vec![
            make_segment("Left", 10.0, 700.0, 40.0, 12.0),
            make_segment("Right", 300.0, 700.0, 40.0, 12.0),
        ];
        let hints = vec![
            make_hint(LayoutHintClass::Text, 0.9, 0.0, 690.0, 200.0, 720.0),
            make_hint(LayoutHintClass::Text, 0.9, 250.0, 690.0, 500.0, 720.0),
        ];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5);
        assert_eq!(regions.len(), 2);
        assert_eq!(regions[0].segment_indices.len(), 1);
        assert_eq!(regions[1].segment_indices.len(), 1);
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_assign_segments_unassigned() {
        let segments = vec![
            make_segment("Inside", 10.0, 700.0, 40.0, 12.0),
            make_segment("Outside", 500.0, 100.0, 40.0, 12.0),
        ];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 0.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5);
        assert_eq!(regions[0].segment_indices.len(), 1);
        assert_eq!(unassigned.len(), 1);
    }

    #[test]
    fn test_assign_segments_smallest_area_wins() {
        let segments = vec![make_segment("text", 50.0, 700.0, 40.0, 12.0)];
        let hints = vec![
            make_hint(LayoutHintClass::Text, 0.9, 0.0, 0.0, 600.0, 800.0), // large
            make_hint(LayoutHintClass::Code, 0.9, 30.0, 690.0, 200.0, 720.0), // small
        ];
        let (regions, _) = assign_segments_to_regions(&segments, &hints, 0.5);
        // Segment should be in the Code region (smaller area)
        assert!(regions[0].segment_indices.is_empty()); // Text (large)
        assert_eq!(regions[1].segment_indices.len(), 1); // Code (small)
    }

    #[test]
    fn test_reading_order_two_columns() {
        let hints = vec![
            make_hint(LayoutHintClass::Text, 0.9, 300.0, 400.0, 550.0, 700.0), // right column
            make_hint(LayoutHintClass::Text, 0.9, 10.0, 400.0, 250.0, 700.0),  // left column
        ];
        let mut regions: Vec<LayoutRegion> = hints
            .iter()
            .map(|h| LayoutRegion {
                hint: h,
                segment_indices: Vec::new(),
            })
            .collect();
        order_regions_reading_order(&mut regions, 800.0);
        // Left column should come first (same y-band, smaller x)
        assert!(regions[0].hint.left < regions[1].hint.left);
    }

    #[test]
    fn test_reading_order_vertical() {
        let hints = vec![
            make_hint(LayoutHintClass::Text, 0.9, 10.0, 100.0, 500.0, 300.0), // bottom
            make_hint(LayoutHintClass::Title, 0.9, 10.0, 600.0, 500.0, 750.0), // top
        ];
        let mut regions: Vec<LayoutRegion> = hints
            .iter()
            .map(|h| LayoutRegion {
                hint: h,
                segment_indices: Vec::new(),
            })
            .collect();
        order_regions_reading_order(&mut regions, 800.0);
        // Title (top of page, higher Y) should come first
        assert_eq!(regions[0].hint.class, LayoutHintClass::Title);
    }

    #[test]
    fn test_assemble_code_region() {
        let segments = vec![
            make_segment("fn main() {", 10.0, 700.0, 80.0, 12.0),
            make_segment("println!(\"hi\");", 10.0, 685.0, 100.0, 12.0),
            make_segment("}", 10.0, 670.0, 10.0, 12.0),
        ];
        let hints = vec![make_hint(LayoutHintClass::Code, 0.9, 0.0, 660.0, 200.0, 720.0)];
        let paragraphs = assemble_region_paragraphs(segments, &hints, &[], 0.5, None, 0);
        assert!(!paragraphs.is_empty());
        assert!(paragraphs[0].is_code_block);
    }

    #[test]
    fn test_assemble_heading_region() {
        let segments = vec![make_segment("1 Introduction", 10.0, 700.0, 120.0, 18.0)];
        let hints = vec![make_hint(LayoutHintClass::SectionHeader, 0.9, 0.0, 690.0, 200.0, 725.0)];
        let paragraphs = assemble_region_paragraphs(segments, &hints, &[], 0.5, None, 0);
        assert_eq!(paragraphs.len(), 1);
        assert_eq!(paragraphs[0].heading_level, Some(2));
    }

    #[test]
    fn test_low_confidence_hints_ignored() {
        let segments = vec![make_segment("text", 10.0, 700.0, 40.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Code, 0.3, 0.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5);
        assert!(regions.is_empty());
        assert_eq!(unassigned.len(), 1);
    }

    #[test]
    fn test_table_regions_excluded_from_text() {
        // Segments within Table bboxes are dropped entirely (extracted separately).
        let segments = vec![make_segment("text", 10.0, 700.0, 40.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Table, 0.9, 0.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5);
        assert!(regions.is_empty());
        assert_eq!(unassigned.len(), 0); // dropped, not unassigned
    }

    #[test]
    fn test_picture_regions_excluded_from_regions_but_unassigned() {
        // Picture regions are excluded from region assignment but segments
        // go to unassigned (no separate text extraction for pictures).
        let segments = vec![make_segment("text", 10.0, 700.0, 40.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Picture, 0.9, 0.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5);
        assert!(regions.is_empty());
        assert_eq!(unassigned.len(), 1); // still goes to fallback
    }

    #[test]
    fn test_assemble_mixed_regions() {
        // Title at top, body text below, code at bottom
        let segments = vec![
            make_segment("Title Text", 10.0, 750.0, 100.0, 18.0),
            make_segment("Body paragraph here.", 10.0, 700.0, 150.0, 12.0),
            make_segment("let x = 1;", 10.0, 650.0, 80.0, 12.0),
        ];
        let hints = vec![
            make_hint(LayoutHintClass::Title, 0.9, 0.0, 740.0, 200.0, 775.0),
            make_hint(LayoutHintClass::Text, 0.9, 0.0, 690.0, 200.0, 720.0),
            make_hint(LayoutHintClass::Code, 0.9, 0.0, 640.0, 200.0, 665.0),
        ];
        let paragraphs = assemble_region_paragraphs(segments, &hints, &[], 0.5, None, 0);
        assert_eq!(paragraphs.len(), 3);
        assert_eq!(paragraphs[0].heading_level, Some(1)); // Title
        assert_eq!(paragraphs[0].layout_class, Some(LayoutHintClass::Title));
        assert!(paragraphs[1].heading_level.is_none()); // Body
        assert!(paragraphs[2].is_code_block); // Code
    }
}
