//! Segment-to-region spatial assignment logic.

use crate::pdf::hierarchy::SegmentData;

use super::LayoutRegion;
use crate::pdf::markdown::types::{LayoutHint, LayoutHintClass};

/// Minimum intersection-over-self (IoS) for a segment to be assigned to a region.
/// Matches docling's threshold of 0.2 (20% of the segment's area must overlap).
const MIN_IOS_THRESHOLD: f32 = 0.2;

/// Assign each segment to its best-matching layout region.
///
/// Uses intersection-over-self (IoS): the fraction of the segment's bounding box
/// that overlaps with a region. If IoS >= 0.2, the segment can be assigned.
/// Among qualifying regions, the one with highest IoS wins; ties broken by
/// smallest area (most specific region).
///
/// Table and Picture regions are excluded from text assignment (handled by
/// separate pipelines). Segments within those regions are dropped entirely
/// to avoid duplicating content that appears in the extracted tables.
pub(in crate::pdf::markdown) fn assign_segments_to_regions<'a>(
    segments: &[SegmentData],
    hints: &'a [LayoutHint],
    min_confidence: f32,
    extracted_table_bboxes: &[crate::types::BoundingBox],
) -> (Vec<LayoutRegion<'a>>, Vec<usize>) {
    let confident_hints: Vec<&LayoutHint> = hints
        .iter()
        .filter(|h| h.confidence >= min_confidence)
        // Exclude Table and Picture — handled by separate pipelines
        .filter(|h| !matches!(h.class, LayoutHintClass::Table | LayoutHintClass::Picture))
        .collect();

    // Only suppress segments in Table bboxes that actually produced valid tables.
    // If a Table hint failed extraction, its segments should fall through to
    // the unassigned pool so text isn't silently lost.
    let suppress_bboxes = extracted_table_bboxes;

    if confident_hints.is_empty() && suppress_bboxes.is_empty() {
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

        let seg_left = seg.x;
        let seg_right = seg.x + seg.width;
        let seg_bottom = seg.y;
        let seg_top = seg.y + seg.height;
        let cx = seg.x + seg.width / 2.0;
        let cy = seg.y + seg.height / 2.0;

        // Check if this segment falls within a successfully extracted table.
        let in_extracted_table = suppress_bboxes
            .iter()
            .any(|bb| (cx as f64) >= bb.x0 && (cx as f64) <= bb.x1 && (cy as f64) >= bb.y0 && (cy as f64) <= bb.y1);
        if in_extracted_table {
            continue;
        }

        // Find the region with highest intersection-over-self (IoS)
        let seg_area = seg.width * seg.height;
        let mut best_hint_idx: Option<usize> = None;
        let mut best_ios = 0.0_f32;
        let mut best_area = f32::MAX;

        for (hi, hint) in confident_hints.iter().enumerate() {
            let ios = intersection_over_self(
                seg_left,
                seg_bottom,
                seg_right,
                seg_top,
                seg_area,
                hint.left,
                hint.bottom,
                hint.right,
                hint.top,
            );

            if ios >= MIN_IOS_THRESHOLD {
                // Prefer higher IoS; break ties by smallest area
                if ios > best_ios || (ios == best_ios && hint_areas[hi] < best_area) {
                    best_ios = ios;
                    best_area = hint_areas[hi];
                    best_hint_idx = Some(hi);
                }
            }
        }

        match best_hint_idx {
            Some(hi) => regions[hi].segment_indices.push(seg_idx),
            None => unassigned.push(seg_idx),
        }
    }

    (regions, unassigned)
}

/// Compute intersection-over-self: the fraction of the segment's area that
/// overlaps with the region's bounding box.
fn intersection_over_self(
    seg_left: f32,
    seg_bottom: f32,
    seg_right: f32,
    seg_top: f32,
    seg_area: f32,
    hint_left: f32,
    hint_bottom: f32,
    hint_right: f32,
    hint_top: f32,
) -> f32 {
    if seg_area <= 0.0 {
        return 0.0;
    }

    let inter_left = seg_left.max(hint_left);
    let inter_right = seg_right.min(hint_right);
    let inter_bottom = seg_bottom.max(hint_bottom);
    let inter_top = seg_top.min(hint_top);

    if inter_left >= inter_right || inter_bottom >= inter_top {
        return 0.0;
    }

    let inter_area = (inter_right - inter_left) * (inter_top - inter_bottom);
    inter_area / seg_area
}
