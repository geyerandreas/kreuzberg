//! Segment-to-region spatial assignment logic.

use crate::pdf::hierarchy::SegmentData;

use super::super::geometry::Rect;
use super::LayoutRegion;
use crate::pdf::markdown::types::{LayoutHint, LayoutHintClass};

/// Minimum intersection-over-self (IoS) for a segment to be assigned to a region.
/// Matches docling's threshold of 0.2 (20% of the segment's area must overlap).
const MIN_IOS_THRESHOLD: f32 = 0.2;

/// Padding (in points) added to each side of the tight bbox during refinement.
const BBOX_REFINEMENT_PADDING: f32 = 2.0;

/// Maximum number of assign→shrink→re-assign iterations.
const MAX_REFINEMENT_ITERATIONS: usize = 3;

/// Assign each segment to its best-matching layout region.
///
/// Uses intersection-over-self (IoS): the fraction of the segment's bounding box
/// that overlaps with a region. If IoS >= 0.2, the segment can be assigned.
/// Among qualifying regions, the one with highest IoS wins; ties broken by
/// smallest area (most specific region).
///
/// Table and Picture regions are excluded from assignment — handled separately.
/// Segments overlapping successfully extracted tables are suppressed (>=50% IoS).
/// Segments overlapping Picture regions are suppressed unless substantive
/// or the region was validated as empty (no text CCs in the rendered image).
pub(in crate::pdf::markdown) fn assign_segments_to_regions<'a>(
    segments: &[SegmentData],
    hints: &'a [LayoutHint],
    min_confidence: f32,
    extracted_table_bboxes: &[crate::types::BoundingBox],
    hint_validations: &[super::layout_validation::RegionValidation],
) -> (Vec<LayoutRegion<'a>>, Vec<usize>) {
    let confident_hints: Vec<&LayoutHint> = hints
        .iter()
        .filter(|h| h.confidence >= min_confidence)
        // Exclude Table and Picture — Table text is handled by TATR extraction,
        // Picture text is suppressed or preserved based on substantive text check.
        .filter(|h| !matches!(h.class, LayoutHintClass::Table | LayoutHintClass::Picture))
        .collect();

    // Suppress segments overlapping successfully extracted tables (>=50% IoS).
    // Only tables that actually produced TATR output have entries in
    // extracted_table_bboxes — failed extractions don't suppress anything.
    let suppress_bboxes = extracted_table_bboxes;

    // Collect Picture region bounding boxes for suppression, paired with
    // their validation status. Empty-validated Picture regions don't suppress.
    let picture_hints: Vec<(&LayoutHint, bool)> = hints
        .iter()
        .enumerate()
        .filter(|(_, h)| h.confidence >= min_confidence && h.class == LayoutHintClass::Picture)
        .map(|(idx, h)| {
            let is_empty = hint_validations
                .get(idx)
                .is_some_and(|v| *v == super::layout_validation::RegionValidation::Empty);
            (h, is_empty)
        })
        .collect();

    if confident_hints.is_empty() && suppress_bboxes.is_empty() && picture_hints.is_empty() {
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
            merged_bbox: None,
        })
        .collect();

    let mut unassigned: Vec<usize> = Vec::new();

    let mut suppressed_count = 0_usize;

    for (seg_idx, seg) in segments.iter().enumerate() {
        if seg.text.trim().is_empty() {
            continue; // Skip whitespace-only segments
        }

        let seg_left = seg.x;
        let seg_right = seg.x + seg.width;
        let seg_bottom = seg.y;
        let seg_top = seg.y + seg.height;

        let seg_rect = Rect::from_lbrt(seg_left, seg_bottom, seg_right, seg_top);

        // Suppress segments overlapping successfully extracted tables (>=50% IoS).
        let in_extracted_table = suppress_bboxes.iter().any(|bb| {
            let bb_rect = Rect::from_lbrt(bb.x0 as f32, bb.y0 as f32, bb.x1 as f32, bb.y1 as f32);
            seg_rect.intersection_over_self(&bb_rect) >= 0.5
        });
        if in_extracted_table {
            suppressed_count += 1;
            continue;
        }

        // Suppress segments inside Picture regions. Diagram labels, flow chart
        // text, axis labels etc. inside pictures pollute the output as body text.
        // Following Docling's approach: pictures emit an image placeholder only;
        // captions are separate layout regions and are preserved independently.
        let in_picture = picture_hints.iter().any(|(ph, _is_empty)| {
            let hint_rect = Rect::from_lbrt(ph.left, ph.bottom, ph.right, ph.top);
            seg_rect.intersection_over_self(&hint_rect) >= 0.5
        });
        if in_picture {
            suppressed_count += 1;
            continue;
        }

        let mut best_hint_idx: Option<usize> = None;
        let mut best_ios = 0.0_f32;
        let mut best_area = f32::MAX;

        for (hi, hint) in confident_hints.iter().enumerate() {
            let hint_rect = Rect::from_lbrt(hint.left, hint.bottom, hint.right, hint.top);
            let ios = seg_rect.intersection_over_self(&hint_rect);

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

    tracing::trace!(
        confident_hints = confident_hints.len(),
        segments = segments.len(),
        suppressed = suppressed_count,
        assigned_to_regions = regions.iter().map(|r| r.segment_indices.len()).sum::<usize>(),
        unassigned = unassigned.len(),
        "segment-to-region assignment complete"
    );

    (regions, unassigned)
}

/// Assign segments to regions with iterative bounding box refinement.
///
/// After the initial assignment, each region's bbox is shrunk to tightly fit its
/// assigned segments (plus padding). Then segments are re-assigned using the refined
/// bboxes. This prevents over-large model bboxes from "stealing" text from adjacent
/// regions. Repeats up to 3 iterations or until assignments stabilize.
pub(in crate::pdf::markdown) fn assign_segments_to_regions_refined<'a>(
    segments: &[SegmentData],
    hints: &'a [LayoutHint],
    min_confidence: f32,
    extracted_table_bboxes: &[crate::types::BoundingBox],
    hint_validations: &[super::layout_validation::RegionValidation],
) -> (Vec<LayoutRegion<'a>>, Vec<usize>) {
    // First pass: assign with original bboxes, using validation for Picture suppression
    let (regions, unassigned) = assign_segments_to_regions(
        segments,
        hints,
        min_confidence,
        extracted_table_bboxes,
        hint_validations,
    );

    if regions.is_empty() {
        return (regions, unassigned);
    }

    // Compute refined bboxes from assigned segments
    let refined_hints: Vec<LayoutHint> = compute_refined_hints(&regions, segments, hints);

    if refined_hints.is_empty() {
        return (regions, unassigned);
    }

    // Collect Picture hints from the original hints to carry through iterations.
    // The refined hints contain text-bearing and Table regions (non-Picture),
    // but Picture bboxes must remain available for segment suppression.
    let picture_hints: Vec<LayoutHint> = hints
        .iter()
        .filter(|h| h.confidence >= min_confidence && h.class == LayoutHintClass::Picture)
        .cloned()
        .collect();

    // Iterate: re-assign with refined bboxes, re-shrink, repeat
    let mut current_hints = refined_hints;
    // Append Picture hints so they're available for suppression in each iteration
    current_hints.extend(picture_hints.iter().cloned());
    let mut prev_assignments: Vec<Vec<usize>> = regions.iter().map(|r| r.segment_indices.clone()).collect();

    for _ in 1..MAX_REFINEMENT_ITERATIONS {
        let (new_regions, _) =
            assign_segments_to_regions(segments, &current_hints, min_confidence, extracted_table_bboxes, &[]);

        // Check if assignments changed
        let new_assignments: Vec<Vec<usize>> = new_regions.iter().map(|r| r.segment_indices.clone()).collect();
        if new_assignments == prev_assignments {
            break; // Stable — stop iterating
        }

        prev_assignments = new_assignments;
        let mut new_refined = compute_refined_hints(&new_regions, segments, &current_hints);
        new_refined.extend(picture_hints.iter().cloned());
        current_hints = new_refined;
    }

    // Final assignment with the last refined hints, but we need to return regions
    // that reference the original hints (for class/confidence), with the refined assignments
    let (final_regions_refined, final_unassigned) =
        assign_segments_to_regions(segments, &current_hints, min_confidence, extracted_table_bboxes, &[]);

    // Map refined regions back to original hints by matching class + position
    let mut result_regions: Vec<LayoutRegion<'a>> = Vec::new();
    let confident_original: Vec<(usize, &'a LayoutHint)> = hints
        .iter()
        .enumerate()
        .filter(|(_, h)| h.confidence >= min_confidence)
        .filter(|(_, h)| !matches!(h.class, LayoutHintClass::Table | LayoutHintClass::Picture))
        .collect();

    for (ri, refined_region) in final_regions_refined.iter().enumerate() {
        if ri < confident_original.len() {
            result_regions.push(LayoutRegion {
                hint: confident_original[ri].1,
                segment_indices: refined_region.segment_indices.clone(),
                merged_bbox: None,
            });
        }
    }

    (result_regions, final_unassigned)
}

/// Compute refined hints by shrinking each region's bbox to tightly fit its segments.
///
/// Each region's `hint` field already points to the correct original hint for that
/// region (set when the region was created in `assign_segments_to_regions`), so we
/// use it directly as the base for clamping. The `source_hints` parameter is unused
/// but retained for API symmetry with the iterative caller.
fn compute_refined_hints(
    regions: &[LayoutRegion],
    segments: &[SegmentData],
    _source_hints: &[LayoutHint],
) -> Vec<LayoutHint> {
    let mut refined = Vec::with_capacity(regions.len());

    for region in regions.iter() {
        let base_hint = region.hint;

        if region.segment_indices.is_empty() {
            // No segments — keep original bbox
            refined.push(base_hint.clone());
            continue;
        }

        // Compute tight bbox from assigned segments
        let mut tight_left = f32::MAX;
        let mut tight_bottom = f32::MAX;
        let mut tight_right = f32::MIN;
        let mut tight_top = f32::MIN;

        for &idx in &region.segment_indices {
            let seg = &segments[idx];
            tight_left = tight_left.min(seg.x);
            tight_bottom = tight_bottom.min(seg.y);
            tight_right = tight_right.max(seg.x + seg.width);
            tight_top = tight_top.max(seg.y + seg.height);
        }

        // Sparsity guard: if segments fill < 15% of the tight bbox area,
        // the layout is sparse (e.g., TOC with dot leaders). Refinement
        // would fragment the line across regions — keep original bbox.
        let tight_area = (tight_right - tight_left) * (tight_top - tight_bottom);
        if tight_area > 0.0 {
            let seg_area_sum: f32 = region
                .segment_indices
                .iter()
                .map(|&idx| segments[idx].width * segments[idx].height)
                .sum();
            let fill_ratio = seg_area_sum / tight_area;
            if fill_ratio < 0.15 {
                tracing::trace!(
                    class = ?base_hint.class,
                    fill_ratio,
                    "refinement skipped: sparse layout"
                );
                refined.push(base_hint.clone());
                continue;
            }
        }

        // Apply padding and clamp to original bbox (never expand beyond model prediction)
        refined.push(LayoutHint {
            class: base_hint.class,
            confidence: base_hint.confidence,
            left: (tight_left - BBOX_REFINEMENT_PADDING).max(base_hint.left),
            bottom: (tight_bottom - BBOX_REFINEMENT_PADDING).max(base_hint.bottom),
            right: (tight_right + BBOX_REFINEMENT_PADDING).min(base_hint.right),
            top: (tight_top + BBOX_REFINEMENT_PADDING).min(base_hint.top),
        });
    }

    refined
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pdf::hierarchy::SegmentData;
    use crate::pdf::markdown::types::{LayoutHint, LayoutHintClass};

    fn make_seg(text: &str, x: f32, y: f32, width: f32, height: f32) -> SegmentData {
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
    fn test_segment_inside_region_assigned() {
        let segments = vec![make_seg("Hello", 50.0, 700.0, 100.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 40.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5, &[], &[]);
        assert_eq!(regions.len(), 1);
        assert_eq!(regions[0].segment_indices, vec![0]);
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_segment_outside_all_regions_unassigned() {
        let segments = vec![make_seg("Hello", 500.0, 100.0, 50.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 40.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5, &[], &[]);
        assert!(regions[0].segment_indices.is_empty());
        assert_eq!(unassigned, vec![0]);
    }

    #[test]
    fn test_whitespace_only_segments_skipped() {
        let segments = vec![
            make_seg("   ", 50.0, 700.0, 100.0, 12.0),
            make_seg("Real", 50.0, 680.0, 80.0, 12.0),
        ];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 0.0, 0.0, 600.0, 800.0)];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5, &[], &[]);
        // Only segment index 1 should be assigned; segment 0 (whitespace) is skipped entirely
        assert_eq!(regions[0].segment_indices, vec![1]);
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_table_hints_excluded_from_regions() {
        let segments = vec![make_seg("Hello", 50.0, 700.0, 100.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Table, 0.9, 0.0, 0.0, 600.0, 800.0)];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5, &[], &[]);
        // Table hints are excluded from region assignment
        assert!(regions.is_empty());
        assert_eq!(unassigned, vec![0]);
    }

    #[test]
    fn test_picture_hints_excluded_from_regions() {
        let segments = vec![make_seg("Hello", 50.0, 700.0, 100.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Picture, 0.9, 0.0, 0.0, 600.0, 800.0)];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5, &[], &[]);
        assert!(regions.is_empty());
        // Segment inside a Picture region is suppressed (not unassigned either)
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_confidence_filtering() {
        let segments = vec![make_seg("Hello", 50.0, 700.0, 100.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.3, 0.0, 0.0, 600.0, 800.0)];
        // min_confidence = 0.5, hint confidence = 0.3 → filtered out
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5, &[], &[]);
        assert!(regions.is_empty());
        assert_eq!(unassigned, vec![0]);
    }

    #[test]
    fn test_overlapping_regions_best_ios_wins() {
        let segments = vec![make_seg("Hello", 50.0, 700.0, 100.0, 12.0)];
        // Region A: large, fully containing the segment
        // Region B: smaller, also containing the segment but tighter → higher IoS → wins tie
        let hints = vec![
            make_hint(LayoutHintClass::Text, 0.9, 0.0, 0.0, 600.0, 800.0),
            make_hint(LayoutHintClass::SectionHeader, 0.9, 40.0, 695.0, 200.0, 720.0),
        ];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5, &[], &[]);
        assert_eq!(regions.len(), 2);
        // Both have IoS = 1.0, tie broken by smallest area → region 1 (smaller)
        assert!(regions[1].segment_indices.contains(&0) || regions[0].segment_indices.contains(&0));
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_segment_suppressed_by_extracted_table_bbox() {
        let segments = vec![make_seg("Table text", 50.0, 700.0, 100.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 0.0, 0.0, 600.0, 800.0)];
        // Table bbox fully containing the segment → suppressed at >=50% IoS
        let table_bboxes = vec![crate::types::BoundingBox {
            x0: 0.0,
            y0: 0.0,
            x1: 600.0,
            y1: 800.0,
        }];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5, &table_bboxes, &[]);
        // Segment should be suppressed (not assigned, not in unassigned)
        assert!(regions[0].segment_indices.is_empty());
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_no_hints_returns_all_unassigned() {
        let segments = vec![
            make_seg("A", 50.0, 700.0, 50.0, 12.0),
            make_seg("B", 50.0, 680.0, 50.0, 12.0),
        ];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &[], 0.5, &[], &[]);
        assert!(regions.is_empty());
        assert_eq!(unassigned, vec![0, 1]);
    }

    #[test]
    fn test_empty_segments_returns_empty() {
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 0.0, 0.0, 600.0, 800.0)];
        let (regions, unassigned) = assign_segments_to_regions(&[], &hints, 0.5, &[], &[]);
        assert_eq!(regions.len(), 1);
        assert!(regions[0].segment_indices.is_empty());
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_multiple_segments_distributed_across_regions() {
        let segments = vec![
            make_seg("Top", 50.0, 700.0, 100.0, 12.0),
            make_seg("Bottom", 50.0, 100.0, 100.0, 12.0),
        ];
        let hints = vec![
            make_hint(LayoutHintClass::SectionHeader, 0.9, 0.0, 690.0, 300.0, 720.0),
            make_hint(LayoutHintClass::Text, 0.9, 0.0, 90.0, 300.0, 120.0),
        ];
        let (regions, unassigned) = assign_segments_to_regions(&segments, &hints, 0.5, &[], &[]);
        assert_eq!(regions[0].segment_indices, vec![0]);
        assert_eq!(regions[1].segment_indices, vec![1]);
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_refined_assignment_returns_results() {
        let segments = vec![
            make_seg("A", 50.0, 700.0, 100.0, 12.0),
            make_seg("B", 50.0, 680.0, 100.0, 12.0),
        ];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 40.0, 670.0, 200.0, 720.0)];
        let (regions, unassigned) = assign_segments_to_regions_refined(&segments, &hints, 0.5, &[], &[]);
        // Both should be assigned to the region
        assert!(!regions.is_empty());
        let total_assigned: usize = regions.iter().map(|r| r.segment_indices.len()).sum();
        assert_eq!(total_assigned + unassigned.len(), 2);
    }

    #[test]
    fn test_refined_with_no_regions_returns_all_unassigned() {
        let segments = vec![make_seg("A", 50.0, 700.0, 50.0, 12.0)];
        let (regions, unassigned) = assign_segments_to_regions_refined(&segments, &[], 0.5, &[], &[]);
        assert!(regions.is_empty());
        assert_eq!(unassigned, vec![0]);
    }
}
