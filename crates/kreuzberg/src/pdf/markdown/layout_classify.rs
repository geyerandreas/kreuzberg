//! Layout-detection-based paragraph classification overrides.
//!
//! When layout detection is enabled, this module applies layout hints
//! to override or augment the font-size-based paragraph classification
//! from the standard markdown pipeline.

use super::types::{LayoutHint, LayoutHintClass, PdfParagraph};

/// Apply layout detection overrides to classified paragraphs.
///
/// Uses two matching strategies:
/// 1. **Spatial matching** (heuristic pages): computes bounding boxes from segment
///    positions and matches by containment overlap.
/// 2. **Proportional matching** (structure tree pages): paragraphs without positional
///    data are matched to hints by estimated vertical position, since both are in
///    reading order.
///
/// Structure-tree headings are preserved: only paragraphs without existing
/// heading classification receive heading overrides from layout detection.
pub(super) fn apply_layout_overrides(
    paragraphs: &mut [PdfParagraph],
    hints: &[LayoutHint],
    min_confidence: f32,
    min_containment: f32,
) {
    if hints.is_empty() {
        return;
    }

    // Separate paragraphs into those with and without positional data.
    let has_any_positions = paragraphs.iter().any(|p| compute_paragraph_bbox(p).is_some());

    if has_any_positions {
        // Spatial matching for paragraphs with positional data
        apply_spatial_overrides(paragraphs, hints, min_confidence, min_containment);
    } else {
        // Proportional matching for structure tree pages (no positional data)
        apply_proportional_overrides(paragraphs, hints, min_confidence);
    }
}

/// Spatial matching: match paragraphs to hints by bounding box overlap.
///
/// Uses a two-tier strategy:
/// 1. **2D containment** (intersection_area / paragraph_area): best for paragraphs
///    that horizontally overlap with the layout hint.
/// 2. **Vertical-only overlap** (vertical_intersection / paragraph_height): fallback
///    for paragraphs where horizontal alignment differs (e.g., centered text vs
///    left-aligned detection box).
///
/// The vertical fallback requires higher confidence to reduce false positives.
fn apply_spatial_overrides(
    paragraphs: &mut [PdfParagraph],
    hints: &[LayoutHint],
    min_confidence: f32,
    min_containment: f32,
) {
    let confident_hints: Vec<&LayoutHint> = hints.iter().filter(|h| h.confidence >= min_confidence).collect();

    for para in paragraphs.iter_mut() {
        let para_bbox = match compute_paragraph_bbox(para) {
            Some(bbox) => bbox,
            None => continue,
        };

        let para_height = para_bbox.top - para_bbox.bottom;
        if para_height <= 0.0 {
            continue;
        }

        // Try 2D containment first (most precise).
        let best_2d = confident_hints
            .iter()
            .filter_map(|hint| {
                let containment = hint_containment(hint, &para_bbox);
                if containment >= min_containment {
                    Some((*hint, containment))
                } else {
                    None
                }
            })
            .max_by(|a, b| a.1.total_cmp(&b.1));

        if let Some((hint, _)) = best_2d {
            apply_hint_to_paragraph(para, hint);
        }
    }
}

/// Proportional matching: match paragraphs to hints using range-overlap.
///
/// Structure tree paragraphs have no positional data but are in reading order
/// (top-to-bottom). Layout hints have PDF coordinates with known bounding boxes.
///
/// Strategy:
/// 1. Sort hints by vertical position (top-to-bottom in reading order).
/// 2. Each paragraph occupies a fractional range `[i/n, (i+1)/n]` of the page.
/// 3. Each hint occupies a fractional range `[(page_height - top)/page_height, (page_height - bottom)/page_height]`.
/// 4. Match each paragraph to the hint with the most fractional overlap.
///
/// This is more accurate than point-estimate matching because it accounts for
/// hints that span large vertical ranges (e.g., a code block or table covering
/// half the page).
fn apply_proportional_overrides(paragraphs: &mut [PdfParagraph], hints: &[LayoutHint], min_confidence: f32) {
    let n = paragraphs.len();
    if n == 0 {
        return;
    }

    // Filter hints by confidence.
    let confident_hints: Vec<&LayoutHint> = hints.iter().filter(|h| h.confidence >= min_confidence).collect();
    if confident_hints.is_empty() {
        return;
    }

    // Infer page height from hint coordinates (max top value).
    let page_height = hints.iter().map(|h| h.top).fold(0.0_f32, f32::max);
    if page_height <= 0.0 {
        return;
    }

    tracing::debug!(
        paragraph_count = n,
        hint_count = confident_hints.len(),
        page_height,
        "Proportional matching: structure tree paragraphs without positions"
    );

    // Precompute each hint's fractional range on the page.
    // In PDF coords, y=0 is bottom, y=page_height is top.
    // Reading order: top-to-bottom → fraction 0.0 = top of page, 1.0 = bottom.
    let hint_ranges: Vec<(f32, f32, &LayoutHint)> = confident_hints
        .iter()
        .map(|h| {
            let frac_start = (page_height - h.top) / page_height; // top of hint → lower fraction
            let frac_end = (page_height - h.bottom) / page_height; // bottom of hint → higher fraction
            (frac_start.max(0.0), frac_end.min(1.0), *h)
        })
        .collect();

    for (i, para) in paragraphs.iter_mut().enumerate() {
        // This paragraph occupies fractional range [i/n, (i+1)/n]
        let para_start = i as f32 / n as f32;
        let para_end = (i as f32 + 1.0) / n as f32;

        // Find the hint with the most overlap.
        let best = hint_ranges
            .iter()
            .filter_map(|&(h_start, h_end, hint)| {
                let overlap_start = para_start.max(h_start);
                let overlap_end = para_end.min(h_end);
                let overlap = (overlap_end - overlap_start).max(0.0);
                if overlap > 0.0 { Some((hint, overlap)) } else { None }
            })
            .max_by(|a, b| a.1.total_cmp(&b.1));

        if let Some((hint, overlap)) = best {
            tracing::trace!(
                para_idx = i,
                total_paragraphs = n,
                ?hint.class,
                hint_confidence = hint.confidence,
                overlap,
                para_frac = format_args!("[{:.2}, {:.2}]", para_start, para_end),
                "Proportional match candidate"
            );
            let para_span = para_end - para_start;
            let overlap_frac = if para_span > 0.0 { overlap / para_span } else { 0.0 };

            match hint.class {
                // Furniture: reliably at page extremes, lower overlap threshold
                LayoutHintClass::PageHeader if i == 0 && overlap_frac > 0.25 => {
                    tracing::trace!(para_idx = i, ?hint.class, "Applying furniture override");
                    apply_hint_to_paragraph(para, hint);
                }
                LayoutHintClass::PageFooter if i == n - 1 && overlap_frac > 0.25 => {
                    tracing::trace!(para_idx = i, ?hint.class, "Applying furniture override");
                    apply_hint_to_paragraph(para, hint);
                }
                // Headings: apply layout model heading detection to struct tree
                // paragraphs that don't already have a heading from the tree.
                // Requires high overlap and word count guard.
                LayoutHintClass::SectionHeader | LayoutHintClass::Title
                    if para.heading_level.is_none()
                        && !para.is_list_item
                        && !para.is_code_block
                        && overlap_frac > 0.7 =>
                {
                    let word_count: usize = para
                        .lines
                        .iter()
                        .flat_map(|l| l.segments.iter())
                        .map(|s| s.text.split_whitespace().count())
                        .sum();
                    if word_count <= 12 {
                        let text: String = para
                            .lines
                            .iter()
                            .flat_map(|l| l.segments.iter())
                            .map(|s| s.text.as_str())
                            .collect::<Vec<_>>()
                            .join(" ");
                        if !is_separator_text(&text) {
                            let level = infer_heading_level_from_text(&text, hint.class);
                            tracing::trace!(
                                para_idx = i,
                                ?hint.class,
                                level,
                                word_count,
                                overlap_frac,
                                "Applying heading override from layout model"
                            );
                            para.heading_level = Some(level);
                            para.layout_class = Some(hint.class);
                        }
                    }
                }
                _ => {}
            }
        }
    }
}

/// Split paragraphs at layout heading boundaries with line-level matching.
///
/// Operates at **line-level granularity** rather than paragraph-level: each line's
/// bounding box is matched against SectionHeader/Title layout hints using
/// intersection-over-self (fraction of line area inside hint area). When a line
/// matches a heading hint, the paragraph is split and the matched line becomes
/// its own heading paragraph with `heading_level` directly assigned.
///
/// This solves the core problem where `lines_to_paragraphs` merges section
/// headers with body text into multi-line paragraphs — making paragraph-level
/// spatial matching ineffective because the paragraph bbox is too large.
///
/// Line-level matching is much more precise because a single-line bbox is narrow
/// (one line height), so containment with a similarly-sized SectionHeader hint
/// is high for true matches and low for false matches.
#[allow(dead_code)]
pub(super) fn split_and_classify_with_layout(
    paragraphs: &mut Vec<PdfParagraph>,
    hints: &[LayoutHint],
    min_confidence: f32,
    doc_body_font_size: Option<f32>,
) {
    let confident_hints: Vec<&LayoutHint> = hints.iter().filter(|h| h.confidence >= min_confidence).collect();

    if confident_hints.is_empty() {
        return;
    }

    let heading_hints: Vec<&LayoutHint> = confident_hints
        .iter()
        .filter(|h| matches!(h.class, LayoutHintClass::Title | LayoutHintClass::SectionHeader))
        .copied()
        .collect();

    // Use the document-level body font size (from font clustering across all pages)
    // to distinguish section headers (typically larger) from bold sub-headings
    // that have the same font size as body text. This is more reliable than
    // per-page computation because body text font is consistent across all pages,
    // even appendix pages where figure content might skew page-level estimates.
    let body_font_size = doc_body_font_size.unwrap_or(0.0);

    let mut new_paragraphs = Vec::with_capacity(paragraphs.len());

    for para in paragraphs.drain(..) {
        // Single-line paragraph: check for heading match directly
        if para.lines.len() <= 1 {
            let mut p = para;
            if p.heading_level.is_none() && !p.lines.is_empty() {
                let line = &p.lines[0];
                let word_count: usize = line.segments.iter().map(|s| s.text.split_whitespace().count()).sum();
                // For single-line paragraphs, trust the ML model with basic guards.
                // Use a tighter word count (8) than font-size-based classification (12)
                // because ML false positives (author names, captions) tend to be longer
                // than real section headers (typically 1-6 words).
                const MAX_LAYOUT_HEADING_WORDS: usize = 8;
                if !line.is_monospace
                    && word_count <= MAX_LAYOUT_HEADING_WORDS
                    && let Some(hint_class) = best_line_heading_match(line, &heading_hints)
                {
                    let line_text: String = line
                        .segments
                        .iter()
                        .map(|s| s.text.as_str())
                        .collect::<Vec<_>>()
                        .join(" ");
                    // Filter text patterns that are never section headings:
                    // - Ends with colon → introductory body text ("Here is what:")
                    // - Contains only digits and dots/spaces → version numbers ("1.0")
                    // - Starts with "Version" → version labels ("Version 1.0")
                    let trimmed = line_text.trim();
                    let ends_with_colon = trimmed.ends_with(':');
                    let is_version_like = trimmed.chars().all(|c| c.is_ascii_digit() || c == '.' || c == ' ')
                        || trimmed.to_ascii_lowercase().starts_with("version");
                    // For un-numbered headings, require the font to be larger
                    // than body text. Bold sub-headings (like "Layout Analysis
                    // Model" under "3.2 AI models") have body font size and
                    // should not be promoted to H2.
                    let inferred_level = infer_heading_level_from_text(&line_text, hint_class);
                    let is_unnumbered_at_body_size =
                        inferred_level == 2 && body_font_size > 0.0 && line.dominant_font_size <= body_font_size + 0.5;

                    if !ends_with_colon
                        && !is_version_like
                        && !is_unnumbered_at_body_size
                        && !is_separator_text(trimmed)
                    {
                        p.heading_level = Some(inferred_level);
                        p.layout_class = Some(hint_class);
                    }
                }
            }
            new_paragraphs.push(p);
            continue;
        }

        // Already classified as heading — don't split
        if para.heading_level.is_some() {
            new_paragraphs.push(para);
            continue;
        }

        // Multi-line body paragraph: check each line for heading match.
        // Apply heuristic guards to avoid false positives:
        // - Not monospace (avoid classifying code as headings)
        // - Limited word count
        // - Bold or distinctly larger font (heading lines look different from body text)
        let mut matched_lines: Vec<(usize, LayoutHintClass)> = Vec::new();
        for (li, line) in para.lines.iter().enumerate() {
            if line.is_monospace {
                continue; // Don't classify code lines as headings
            }
            let word_count: usize = line.segments.iter().map(|s| s.text.split_whitespace().count()).sum();
            // Tighter word limit for layout-detected headings than font-size-based (12).
            // ML false positives (author names, captions) tend to be longer than
            // real section headers (typically 1-6 words).
            const MAX_LAYOUT_HEADING_WORDS: usize = 8;
            if word_count > MAX_LAYOUT_HEADING_WORDS {
                continue; // Too many words for a heading
            }
            // Require the line to look like a heading: bold or larger font than the
            // paragraph's dominant font size. This prevents body text and code lines
            // from being classified as headings even when the ML model has a false
            // positive SectionHeader detection at their position.
            let has_heading_style = line.is_bold || line.dominant_font_size > para.dominant_font_size + 1.0;
            if !has_heading_style {
                continue; // Line doesn't look like a heading
            }
            if let Some(hint_class) = best_line_heading_match(line, &heading_hints) {
                matched_lines.push((li, hint_class));
            }
        }

        if matched_lines.is_empty() {
            new_paragraphs.push(para);
            continue;
        }

        // Split at matched line boundaries and assign heading levels
        let mut current_start = 0;
        let is_list_item = para.is_list_item;
        let is_code_block = para.is_code_block;
        let all_lines = para.lines;

        for &(li, hint_class) in &matched_lines {
            // Push lines before the heading as a body paragraph
            if li > current_start {
                let before: Vec<_> = all_lines[current_start..li].to_vec();
                new_paragraphs.push(make_paragraph_from_lines(before, is_list_item, is_code_block));
            }
            // Push the matched line as a heading paragraph
            let mut heading_para = make_paragraph_from_lines(
                vec![all_lines[li].clone()],
                false, // headings aren't list items
                false, // headings aren't code blocks
            );
            let line_text: String = all_lines[li]
                .segments
                .iter()
                .map(|s| s.text.as_str())
                .collect::<Vec<_>>()
                .join(" ");
            if !is_separator_text(&line_text) {
                heading_para.heading_level = Some(infer_heading_level_from_text(&line_text, hint_class));
                heading_para.layout_class = Some(hint_class);
            }
            new_paragraphs.push(heading_para);
            current_start = li + 1;
        }

        // Push remaining lines as body paragraph
        if current_start < all_lines.len() {
            let remaining: Vec<_> = all_lines[current_start..].to_vec();
            new_paragraphs.push(make_paragraph_from_lines(remaining, is_list_item, is_code_block));
        }
    }

    // Phase 2: Apply non-heading layout classes (Code, Formula,
    // PageHeader/Footer) to paragraphs via containment matching.
    //
    // ListItem is excluded: the model's ListItem bbox covers the full bullet
    // region (including wrapped continuation lines), but our paragraph splitter
    // breaks wrapped list items into multiple paragraphs. Each sub-paragraph
    // would get tagged as a new list item, inflating list count. The heuristic
    // prefix detection ("- ", "1. ", etc.) already handles list items correctly.
    let non_heading_hints: Vec<&LayoutHint> = confident_hints
        .iter()
        .filter(|h| {
            matches!(
                h.class,
                LayoutHintClass::Code
                    | LayoutHintClass::Formula
                    | LayoutHintClass::PageHeader
                    | LayoutHintClass::PageFooter
            )
        })
        .copied()
        .collect();

    if !non_heading_hints.is_empty() {
        for para in &mut new_paragraphs {
            // Skip paragraphs already classified as headings by the heading phase.
            if para.heading_level.is_some() {
                continue;
            }
            let para_bbox = match compute_paragraph_bbox(para) {
                Some(bbox) => bbox,
                None => continue,
            };
            let para_area = (para_bbox.right - para_bbox.left) * (para_bbox.top - para_bbox.bottom);
            if para_area <= 0.0 {
                continue;
            }

            // Find the best-matching non-heading hint by containment.
            let best = non_heading_hints
                .iter()
                .filter_map(|hint| {
                    let containment = hint_containment(hint, &para_bbox);
                    if containment >= 0.3 {
                        Some((*hint, containment))
                    } else {
                        None
                    }
                })
                .max_by(|a, b| a.1.total_cmp(&b.1));

            if let Some((hint, _)) = best {
                // Guard: Formula bboxes are often larger than the actual formula.
                // Only apply if the paragraph is short (formulas are typically 1-3 lines).
                if hint.class == LayoutHintClass::Formula && para.lines.len() > 3 {
                    para.layout_class = Some(hint.class);
                    continue;
                }
                apply_hint_to_paragraph(para, hint);
            }
        }
    }

    *paragraphs = new_paragraphs;
}

/// Check if text is a separator/filler line (dashes, underscores, tildes, etc.)
/// that should never be classified as a heading.
pub(super) fn is_separator_text(text: &str) -> bool {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        return false;
    }
    let total = trimmed.chars().count();
    let alnum = trimmed.chars().filter(|c| c.is_alphanumeric()).count();
    // Pure separator: no alphanumeric characters at all
    if alnum == 0 {
        return true;
    }
    // Mostly separator: very few alphanumeric chars among filler (dashes, underscores, tildes, etc.)
    // e.g. "------------- M W _ _ _ _ _ _" or "---~ ---------"
    // Require at least 6 total chars and <15% alphanumeric ratio
    total >= 6 && (alnum as f64 / total as f64) < 0.15
}

/// Infer heading level from section numbering in the text.
///
/// Academic papers use numbering to indicate heading depth:
/// - "1 Introduction" → H2 (top-level section)
/// - "3.2 AI models" → H3 (sub-section)
/// - "3.2.1 Details" → H4 (sub-sub-section)
/// - "Layout Analysis Model" (no number) → H2 (default for SectionHeader)
pub(super) fn infer_heading_level_from_text(text: &str, hint_class: LayoutHintClass) -> u8 {
    if hint_class == LayoutHintClass::Title {
        return 1;
    }

    let trimmed = text.trim();
    // Check for section numbering pattern: digits and dots at the start
    let numbering_end = trimmed.find(|c: char| !c.is_ascii_digit() && c != '.').unwrap_or(0);

    if numbering_end == 0 {
        // No numbering → default H2 for SectionHeader
        return 2;
    }

    let numbering = &trimmed[..numbering_end];
    // Count dots to determine depth: "3" → 0 dots → H2, "3.2" → 1 dot → H3
    let dot_count = numbering.chars().filter(|&c| c == '.').count();

    // Trailing dot (e.g., "3.") doesn't count as depth indicator
    let effective_dots = if numbering.ends_with('.') {
        dot_count.saturating_sub(1)
    } else {
        dot_count
    };

    match effective_dots {
        0 => 2, // "1 Introduction" → H2
        1 => 3, // "3.2 AI models" → H3
        _ => 4, // "3.2.1 Details" → H4
    }
}

/// Find the best heading hint match for a single line using centroid-based spatial matching.
///
/// Uses two criteria:
/// 1. **Vertical proximity**: the line's vertical center must be within one line-height
///    of the hint's vertical center. This handles the systematic coordinate offset
///    between pdfium text positions and layout detection bounding boxes.
/// 2. **Horizontal overlap**: at least 30% of the narrower bbox (line or hint) must
///    overlap horizontally, ensuring the text is in the same column/region.
///
/// Returns the matched hint class, or `None` if no hint matches.
#[allow(dead_code)]
fn best_line_heading_match(line: &super::types::PdfLine, hints: &[&LayoutHint]) -> Option<LayoutHintClass> {
    let (bottom, top, left, right) = line_bbox(line);
    let line_height = top - bottom;
    let line_width = right - left;
    if line_height <= 0.0 || line_width <= 0.0 {
        return None;
    }
    let line_cy = (top + bottom) / 2.0;

    hints
        .iter()
        .filter_map(|hint| {
            let hint_height = hint.top - hint.bottom;
            let hint_width = hint.right - hint.left;
            let hint_cy = (hint.top + hint.bottom) / 2.0;

            // Vertical proximity: centers within max_height of each other
            let max_h = line_height.max(hint_height);
            let v_dist = (line_cy - hint_cy).abs();
            if v_dist > max_h {
                return None;
            }

            // Horizontal overlap: at least 30% of the narrower bbox
            let h_overlap = (right.min(hint.right) - left.max(hint.left)).max(0.0);
            let min_w = line_width.min(hint_width);
            if min_w <= 0.0 || h_overlap / min_w < 0.3 {
                return None;
            }

            // Score: prefer closer vertical match and better horizontal overlap
            let v_score = 1.0 - v_dist / max_h;
            let h_score = h_overlap / min_w;
            Some((hint.class, v_score * h_score))
        })
        .max_by(|a, b| a.1.total_cmp(&b.1))
        .map(|(class, _)| class)
}

/// Get the bounding box (bottom, top, left, right) of a line from its segments.
#[allow(dead_code)]
fn line_bbox(line: &super::types::PdfLine) -> (f32, f32, f32, f32) {
    let mut bottom = f32::MAX;
    let mut top = f32::MIN;
    let mut left = f32::MAX;
    let mut right = f32::MIN;
    let mut has_data = false;

    for seg in &line.segments {
        if seg.x == 0.0 && seg.width == 0.0 && seg.y == 0.0 && seg.height == 0.0 {
            continue;
        }
        has_data = true;
        left = left.min(seg.x);
        right = right.max(seg.x + seg.width);
        // seg.y = baseline, text extends upward by seg.height
        bottom = bottom.min(seg.y);
        top = top.max(seg.y + seg.height);
    }

    if has_data {
        (bottom, top, left, right)
    } else {
        (0.0, 0.0, 0.0, 0.0)
    }
}

/// Create a paragraph from lines, inheriting structural properties.
#[allow(dead_code)]
fn make_paragraph_from_lines(
    lines: Vec<super::types::PdfLine>,
    is_list_item: bool,
    is_code_block: bool,
) -> PdfParagraph {
    let dominant_font_size = lines.iter().map(|l| l.dominant_font_size).fold(0.0_f32, f32::max);
    let is_bold = lines.iter().all(|l| l.is_bold);

    PdfParagraph {
        lines,
        dominant_font_size,
        heading_level: None, // Will be classified later
        is_bold,
        is_list_item,
        is_code_block,
        is_formula: false,
        is_page_furniture: false,
        layout_class: None,
        caption_for: None,
    }
}

/// Apply a single hint's classification to a paragraph.
pub(super) fn apply_hint_to_paragraph(para: &mut PdfParagraph, hint: &LayoutHint) {
    para.layout_class = Some(hint.class);

    let para_text: String = para
        .lines
        .iter()
        .flat_map(|l| l.segments.iter())
        .map(|s| s.text.as_str())
        .collect::<Vec<_>>()
        .join(" ");
    let is_sep = is_separator_text(&para_text);

    match hint.class {
        LayoutHintClass::Title => {
            if para.heading_level.is_none() && !is_sep {
                para.heading_level = Some(1);
            }
        }
        LayoutHintClass::SectionHeader => {
            if para.heading_level.is_none() && !is_sep {
                para.heading_level = Some(2);
            }
        }
        LayoutHintClass::Code => {
            para.is_code_block = true;
            para.heading_level = None;
        }
        LayoutHintClass::Formula => {
            para.is_formula = true;
            para.heading_level = None;
        }
        LayoutHintClass::ListItem => {
            para.is_list_item = true;
        }
        LayoutHintClass::PageHeader | LayoutHintClass::PageFooter => {
            para.is_page_furniture = true;
        }
        _ => {}
    }
}

/// Simple bounding box for a paragraph in PDF coordinate space.
struct ParaBBox {
    left: f32,
    bottom: f32,
    right: f32,
    top: f32,
}

/// Compute a paragraph's bounding box from its line segments' positional data.
///
/// Returns `None` if the paragraph has no segments with valid positional data.
///
/// In PDF coordinates (y=0 at bottom, y increases upward):
/// - `seg.y` / `seg.baseline_y` is the text baseline (near the bottom of glyphs).
/// - Text extends UPWARD from the baseline by roughly the ascent (~80% of font size).
/// - Text extends DOWNWARD from the baseline by the descent (~20% of font size).
///
/// For layout detection matching, we approximate the visual text extent as:
/// - top = baseline + height (covers ascenders)
/// - bottom = baseline (descent is small and usually within the layout hint's margin)
fn compute_paragraph_bbox(para: &PdfParagraph) -> Option<ParaBBox> {
    let mut left = f32::MAX;
    let mut right = f32::MIN;
    let mut bottom = f32::MAX;
    let mut top = f32::MIN;
    let mut has_data = false;

    for line in &para.lines {
        for seg in &line.segments {
            // Skip segments with no positional data (structure tree path)
            if seg.x == 0.0 && seg.width == 0.0 && seg.y == 0.0 && seg.height == 0.0 {
                continue;
            }
            has_data = true;
            left = left.min(seg.x);
            right = right.max(seg.x + seg.width);
            // seg.y is the baseline. Text extends upward by ~font_size (seg.height).
            top = top.max(seg.y + seg.height);
            bottom = bottom.min(seg.y);
        }
    }

    if has_data {
        Some(ParaBBox {
            left,
            bottom,
            right,
            top,
        })
    } else {
        None
    }
}

/// Compute what fraction of the paragraph bbox is contained within the hint bbox.
///
/// Both are in PDF coordinate space (points, y=0 at bottom).
fn hint_containment(hint: &LayoutHint, para: &ParaBBox) -> f32 {
    let para_area = (para.right - para.left) * (para.top - para.bottom);
    if para_area <= 0.0 {
        return 0.0;
    }

    // Intersection
    let ix1 = hint.left.max(para.left);
    let iy1 = hint.bottom.max(para.bottom);
    let ix2 = hint.right.min(para.right);
    let iy2 = hint.top.min(para.top);

    let inter_area = (ix2 - ix1).max(0.0) * (iy2 - iy1).max(0.0);
    inter_area / para_area
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pdf::hierarchy::SegmentData;
    use crate::pdf::markdown::types::PdfLine;

    fn make_segment(text: &str, x: f32, y: f32, width: f32, height: f32) -> SegmentData {
        SegmentData {
            text: text.to_string(),
            x,
            y,
            width,
            height,
            font_size: 12.0,
            is_bold: false,
            is_italic: false,
            is_monospace: false,
            baseline_y: y,
        }
    }

    fn make_line_at(segments: Vec<SegmentData>, baseline_y: f32) -> PdfLine {
        PdfLine {
            segments,
            baseline_y,
            dominant_font_size: 12.0,
            is_bold: false,
            is_monospace: false,
        }
    }

    fn make_bold_line_at(segments: Vec<SegmentData>, baseline_y: f32, font_size: f32) -> PdfLine {
        PdfLine {
            segments,
            baseline_y,
            dominant_font_size: font_size,
            is_bold: true,
            is_monospace: false,
        }
    }

    fn make_line(segments: Vec<SegmentData>) -> PdfLine {
        make_line_at(segments, 700.0)
    }

    fn make_para(x: f32, y: f32, width: f32, height: f32) -> PdfParagraph {
        PdfParagraph {
            lines: vec![make_line(vec![make_segment("text", x, y, width, height)])],
            dominant_font_size: 12.0,
            heading_level: None,
            is_bold: false,
            is_list_item: false,
            is_code_block: false,
            is_formula: false,
            is_page_furniture: false,
            layout_class: None,
            caption_for: None,
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

    // ── apply_layout_overrides tests (paragraph-level, used for struct tree path) ──

    #[test]
    fn test_title_override() {
        let mut paragraphs = vec![make_para(50.0, 750.0, 500.0, 20.0)];
        let hints = vec![make_hint(LayoutHintClass::Title, 0.9, 40.0, 745.0, 560.0, 775.0)];
        apply_layout_overrides(&mut paragraphs, &hints, 0.5, 0.5);
        assert_eq!(paragraphs[0].heading_level, Some(1));
        assert_eq!(paragraphs[0].layout_class, Some(LayoutHintClass::Title));
    }

    #[test]
    fn test_section_header_override() {
        let mut paragraphs = vec![make_para(50.0, 600.0, 300.0, 16.0)];
        let hints = vec![make_hint(
            LayoutHintClass::SectionHeader,
            0.85,
            40.0,
            598.0,
            400.0,
            620.0,
        )];
        apply_layout_overrides(&mut paragraphs, &hints, 0.5, 0.5);
        assert_eq!(paragraphs[0].heading_level, Some(2));
    }

    #[test]
    fn test_low_confidence_ignored() {
        let mut paragraphs = vec![make_para(50.0, 750.0, 500.0, 20.0)];
        let hints = vec![make_hint(LayoutHintClass::Title, 0.3, 40.0, 745.0, 560.0, 775.0)];
        apply_layout_overrides(&mut paragraphs, &hints, 0.5, 0.5);
        assert_eq!(paragraphs[0].heading_level, None);
        assert_eq!(paragraphs[0].layout_class, None);
    }

    #[test]
    fn test_existing_heading_preserved() {
        let mut paragraphs = vec![make_para(50.0, 750.0, 500.0, 20.0)];
        paragraphs[0].heading_level = Some(3);
        let hints = vec![make_hint(
            LayoutHintClass::SectionHeader,
            0.9,
            40.0,
            745.0,
            560.0,
            775.0,
        )];
        apply_layout_overrides(&mut paragraphs, &hints, 0.5, 0.5);
        assert_eq!(paragraphs[0].heading_level, Some(3));
    }

    #[test]
    fn test_empty_hints() {
        let mut paragraphs = vec![make_para(50.0, 750.0, 500.0, 20.0)];
        apply_layout_overrides(&mut paragraphs, &[], 0.5, 0.5);
        assert_eq!(paragraphs[0].heading_level, None);
    }

    #[test]
    fn test_hint_containment_full() {
        let hint = make_hint(LayoutHintClass::Text, 0.9, 0.0, 0.0, 612.0, 792.0);
        let para = ParaBBox {
            left: 50.0,
            bottom: 100.0,
            right: 550.0,
            top: 200.0,
        };
        let containment = hint_containment(&hint, &para);
        assert!(
            (containment - 1.0).abs() < 0.01,
            "Full containment expected: {}",
            containment
        );
    }

    #[test]
    fn test_hint_containment_none() {
        let hint = make_hint(LayoutHintClass::Text, 0.9, 0.0, 500.0, 100.0, 600.0);
        let para = ParaBBox {
            left: 200.0,
            bottom: 100.0,
            right: 500.0,
            top: 200.0,
        };
        let containment = hint_containment(&hint, &para);
        assert!(
            (containment - 0.0).abs() < 0.01,
            "No containment expected: {}",
            containment
        );
    }

    // ── split_and_classify_with_layout tests (line-level, used for heuristic path) ──

    #[test]
    fn test_split_single_line_heading_match() {
        // Single-line paragraph with a SectionHeader hint covering it
        let mut paragraphs = vec![make_para(50.0, 600.0, 300.0, 14.0)];
        let hints = vec![make_hint(
            LayoutHintClass::SectionHeader,
            0.9,
            40.0,
            598.0,
            400.0,
            618.0,
        )];
        split_and_classify_with_layout(&mut paragraphs, &hints, 0.5, None);
        assert_eq!(paragraphs.len(), 1);
        assert_eq!(paragraphs[0].heading_level, Some(2));
        assert_eq!(paragraphs[0].layout_class, Some(LayoutHintClass::SectionHeader));
    }

    #[test]
    fn test_split_single_line_title_match() {
        let mut paragraphs = vec![make_para(50.0, 750.0, 500.0, 20.0)];
        let hints = vec![make_hint(LayoutHintClass::Title, 0.9, 40.0, 745.0, 560.0, 775.0)];
        split_and_classify_with_layout(&mut paragraphs, &hints, 0.5, None);
        assert_eq!(paragraphs[0].heading_level, Some(1));
        assert_eq!(paragraphs[0].layout_class, Some(LayoutHintClass::Title));
    }

    #[test]
    fn test_split_multiline_paragraph_at_heading() {
        // A multi-line paragraph where the first line is a bold section header
        // and the remaining lines are body text.
        let mut paragraphs = vec![PdfParagraph {
            lines: vec![
                make_bold_line_at(
                    vec![make_segment("1 Introduction", 50.0, 700.0, 200.0, 14.0)],
                    700.0,
                    14.0,
                ),
                make_line_at(
                    vec![make_segment("Body text line one.", 50.0, 680.0, 400.0, 12.0)],
                    680.0,
                ),
                make_line_at(
                    vec![make_segment("Body text line two.", 50.0, 665.0, 400.0, 12.0)],
                    665.0,
                ),
            ],
            dominant_font_size: 12.0,
            heading_level: None,
            is_bold: false,
            is_list_item: false,
            is_code_block: false,
            is_formula: false,
            is_page_furniture: false,
            layout_class: None,
            caption_for: None,
        }];

        // SectionHeader hint covers line 1 area: baseline 700, extends to 714
        let hints = vec![make_hint(
            LayoutHintClass::SectionHeader,
            0.9,
            40.0,
            698.0,
            300.0,
            718.0,
        )];
        split_and_classify_with_layout(&mut paragraphs, &hints, 0.5, None);

        // Should split into 2 paragraphs: heading + body
        assert_eq!(paragraphs.len(), 2);
        assert_eq!(paragraphs[0].heading_level, Some(2));
        assert_eq!(paragraphs[0].layout_class, Some(LayoutHintClass::SectionHeader));
        assert_eq!(paragraphs[0].lines.len(), 1);
        assert_eq!(paragraphs[1].heading_level, None);
        assert_eq!(paragraphs[1].lines.len(), 2);
    }

    #[test]
    fn test_split_heading_in_middle_of_paragraph() {
        // Body, then bold heading, then more body
        let mut paragraphs = vec![PdfParagraph {
            lines: vec![
                make_line_at(
                    vec![make_segment("End of previous section.", 50.0, 720.0, 400.0, 12.0)],
                    720.0,
                ),
                make_bold_line_at(vec![make_segment("2 Methods", 50.0, 700.0, 150.0, 14.0)], 700.0, 14.0),
                make_line_at(
                    vec![make_segment("This section describes...", 50.0, 680.0, 400.0, 12.0)],
                    680.0,
                ),
            ],
            dominant_font_size: 12.0,
            heading_level: None,
            is_bold: false,
            is_list_item: false,
            is_code_block: false,
            is_formula: false,
            is_page_furniture: false,
            layout_class: None,
            caption_for: None,
        }];

        let hints = vec![make_hint(
            LayoutHintClass::SectionHeader,
            0.85,
            40.0,
            698.0,
            250.0,
            718.0,
        )];
        split_and_classify_with_layout(&mut paragraphs, &hints, 0.5, None);

        // Should split into 3: body before, heading, body after
        assert_eq!(paragraphs.len(), 3);
        assert_eq!(paragraphs[0].heading_level, None); // body before
        assert_eq!(paragraphs[0].lines.len(), 1);
        assert_eq!(paragraphs[1].heading_level, Some(2)); // heading
        assert_eq!(paragraphs[1].lines.len(), 1);
        assert_eq!(paragraphs[2].heading_level, None); // body after
        assert_eq!(paragraphs[2].lines.len(), 1);
    }

    #[test]
    fn test_split_low_confidence_ignored() {
        let mut paragraphs = vec![PdfParagraph {
            lines: vec![
                make_line_at(vec![make_segment("1 Introduction", 50.0, 700.0, 200.0, 14.0)], 700.0),
                make_line_at(vec![make_segment("Body text.", 50.0, 680.0, 400.0, 12.0)], 680.0),
            ],
            dominant_font_size: 12.0,
            heading_level: None,
            is_bold: false,
            is_list_item: false,
            is_code_block: false,
            is_formula: false,
            is_page_furniture: false,
            layout_class: None,
            caption_for: None,
        }];

        // Low confidence hint — should be ignored
        let hints = vec![make_hint(
            LayoutHintClass::SectionHeader,
            0.3,
            40.0,
            698.0,
            300.0,
            718.0,
        )];
        split_and_classify_with_layout(&mut paragraphs, &hints, 0.5, None);

        // No split
        assert_eq!(paragraphs.len(), 1);
        assert_eq!(paragraphs[0].lines.len(), 2);
    }

    #[test]
    fn test_split_no_match_when_hint_doesnt_overlap() {
        let mut paragraphs = vec![PdfParagraph {
            lines: vec![
                make_line_at(vec![make_segment("Some text", 50.0, 700.0, 200.0, 12.0)], 700.0),
                make_line_at(vec![make_segment("More text", 50.0, 685.0, 200.0, 12.0)], 685.0),
            ],
            dominant_font_size: 12.0,
            heading_level: None,
            is_bold: false,
            is_list_item: false,
            is_code_block: false,
            is_formula: false,
            is_page_furniture: false,
            layout_class: None,
            caption_for: None,
        }];

        // Hint is far away from both lines
        let hints = vec![make_hint(
            LayoutHintClass::SectionHeader,
            0.9,
            40.0,
            300.0,
            400.0,
            320.0,
        )];
        split_and_classify_with_layout(&mut paragraphs, &hints, 0.5, None);

        assert_eq!(paragraphs.len(), 1);
        assert_eq!(paragraphs[0].lines.len(), 2);
    }

    #[test]
    fn test_split_preserves_existing_heading() {
        // Paragraph already classified as heading — should not be split
        let mut paragraphs = vec![PdfParagraph {
            lines: vec![
                make_line_at(vec![make_segment("Title", 50.0, 700.0, 300.0, 18.0)], 700.0),
                make_line_at(vec![make_segment("Subtitle", 50.0, 675.0, 300.0, 18.0)], 675.0),
            ],
            dominant_font_size: 18.0,
            heading_level: Some(1),
            is_bold: true,
            is_list_item: false,
            is_code_block: false,
            is_formula: false,
            is_page_furniture: false,
            layout_class: None,
            caption_for: None,
        }];

        let hints = vec![make_hint(
            LayoutHintClass::SectionHeader,
            0.9,
            40.0,
            698.0,
            400.0,
            720.0,
        )];
        split_and_classify_with_layout(&mut paragraphs, &hints, 0.5, None);

        // No split, existing H1 preserved
        assert_eq!(paragraphs.len(), 1);
        assert_eq!(paragraphs[0].heading_level, Some(1));
    }

    #[test]
    fn test_split_empty_hints() {
        let mut paragraphs = vec![make_para(50.0, 700.0, 300.0, 12.0)];
        split_and_classify_with_layout(&mut paragraphs, &[], 0.5, None);
        assert_eq!(paragraphs.len(), 1);
        assert_eq!(paragraphs[0].heading_level, None);
    }

    // ── infer_heading_level_from_text tests ──

    #[test]
    fn test_infer_heading_level_title() {
        assert_eq!(
            infer_heading_level_from_text("Docling Report", LayoutHintClass::Title),
            1
        );
    }

    #[test]
    fn test_infer_heading_level_top_section() {
        // "3 Processing pipeline" → H2
        assert_eq!(
            infer_heading_level_from_text("3 Processing pipeline", LayoutHintClass::SectionHeader),
            2
        );
    }

    #[test]
    fn test_infer_heading_level_subsection() {
        // "3.2 AI models" → H3
        assert_eq!(
            infer_heading_level_from_text("3.2 AI models", LayoutHintClass::SectionHeader),
            3
        );
    }

    #[test]
    fn test_infer_heading_level_subsubsection() {
        // "3.2.1 Details" → H4
        assert_eq!(
            infer_heading_level_from_text("3.2.1 Details", LayoutHintClass::SectionHeader),
            4
        );
    }

    #[test]
    fn test_infer_heading_level_trailing_dot() {
        // "3. Processing" → trailing dot, still H2
        assert_eq!(
            infer_heading_level_from_text("3. Processing", LayoutHintClass::SectionHeader),
            2
        );
    }

    #[test]
    fn test_infer_heading_level_no_number() {
        // "Layout Analysis Model" → no number, default H2
        assert_eq!(
            infer_heading_level_from_text("Layout Analysis Model", LayoutHintClass::SectionHeader),
            2
        );
    }

    #[test]
    fn test_split_single_line_subsection_gets_h3() {
        // Single-line paragraph with "3.2 AI models" should get H3, not H2
        let seg = make_segment("3.2 AI models", 50.0, 600.0, 150.0, 14.0);
        let mut paragraphs = vec![PdfParagraph {
            lines: vec![make_line_at(vec![seg], 600.0)],
            dominant_font_size: 14.0,
            heading_level: None,
            is_bold: false,
            is_list_item: false,
            is_code_block: false,
            is_formula: false,
            is_page_furniture: false,
            layout_class: None,
            caption_for: None,
        }];
        let hints = vec![make_hint(
            LayoutHintClass::SectionHeader,
            0.9,
            40.0,
            598.0,
            250.0,
            618.0,
        )];
        split_and_classify_with_layout(&mut paragraphs, &hints, 0.5, None);
        assert_eq!(paragraphs[0].heading_level, Some(3));
    }

    #[test]
    fn test_split_multiline_subsection_gets_h3() {
        // Multi-line paragraph where first line is "3.2 AI models" (bold) — should split and get H3
        let mut paragraphs = vec![PdfParagraph {
            lines: vec![
                make_bold_line_at(
                    vec![make_segment("3.2 AI models", 50.0, 700.0, 150.0, 14.0)],
                    700.0,
                    14.0,
                ),
                make_line_at(
                    vec![make_segment("Body text about AI.", 50.0, 680.0, 400.0, 12.0)],
                    680.0,
                ),
            ],
            dominant_font_size: 12.0,
            heading_level: None,
            is_bold: false,
            is_list_item: false,
            is_code_block: false,
            is_formula: false,
            is_page_furniture: false,
            layout_class: None,
            caption_for: None,
        }];
        let hints = vec![make_hint(
            LayoutHintClass::SectionHeader,
            0.9,
            40.0,
            698.0,
            250.0,
            718.0,
        )];
        split_and_classify_with_layout(&mut paragraphs, &hints, 0.5, None);
        assert_eq!(paragraphs.len(), 2);
        assert_eq!(paragraphs[0].heading_level, Some(3)); // H3 from "3.2"
        assert_eq!(paragraphs[1].heading_level, None);
    }

    // ── proportional matching tests (structure tree path) ──

    #[test]
    fn test_no_positional_data_proportional_applies_page_furniture() {
        // Proportional matching only applies PageHeader/PageFooter (furniture)
        // because positional imprecision makes heading/list/code overrides unreliable.
        let mut paragraphs = vec![PdfParagraph {
            lines: vec![make_line(vec![make_segment("text", 0.0, 0.0, 0.0, 0.0)])],
            dominant_font_size: 12.0,
            heading_level: None,
            is_bold: false,
            is_list_item: false,
            is_code_block: false,
            is_formula: false,
            is_page_furniture: false,
            layout_class: None,
            caption_for: None,
        }];

        // Title hint should NOT be applied via proportional matching
        let hints = vec![make_hint(LayoutHintClass::Title, 0.9, 40.0, 0.0, 560.0, 760.0)];
        apply_layout_overrides(&mut paragraphs, &hints, 0.5, 0.5);
        assert_eq!(paragraphs[0].heading_level, None);
        assert_eq!(paragraphs[0].layout_class, None);

        // PageHeader hint SHOULD be applied via proportional matching
        let hints = vec![make_hint(LayoutHintClass::PageHeader, 0.9, 40.0, 0.0, 560.0, 760.0)];
        apply_layout_overrides(&mut paragraphs, &hints, 0.5, 0.5);
        assert!(paragraphs[0].is_page_furniture);
        assert_eq!(paragraphs[0].layout_class, Some(LayoutHintClass::PageHeader));
    }
}
