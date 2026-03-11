//! Layout-guided segment assembly using model bounding boxes.
//!
//! When layout detection is enabled, this module assigns text segments to
//! layout regions *before* line/paragraph assembly, ensuring paragraph
//! boundaries align with the model's structural predictions.

mod assignment;
mod heading;
mod merge;
mod reading_order;
pub(super) mod slanet;
mod tables;

use crate::pdf::hierarchy::SegmentData;

use super::classify::classify_paragraphs;
use super::columns::split_segments_into_columns;
use super::lines::segments_to_lines;
use super::paragraphs::{lines_to_paragraphs, merge_continuation_paragraphs};
use super::types::{LayoutHint, LayoutHintClass, PdfParagraph};

// Re-exports for use by pipeline.rs and other siblings
pub(super) use heading::looks_like_figure_label;
#[cfg(feature = "layout-detection")]
pub(super) use slanet::recognize_tables_for_native_page;
pub(super) use tables::extract_tables_from_layout_hints;

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
    extracted_table_bboxes: &[crate::types::BoundingBox],
) -> Vec<PdfParagraph> {
    let (mut regions, unassigned_indices) =
        assignment::assign_segments_to_regions(&segments, hints, min_confidence, extracted_table_bboxes);

    if regions.is_empty() {
        // No confident hints matched — fall through to standard pipeline
        return assemble_fallback(segments, heading_map);
    }

    // Determine page height for reading order (from segment extents)
    let page_height = segments.iter().map(|s| s.y + s.height).fold(0.0_f32, f32::max);

    reading_order::order_regions_reading_order(&mut regions, page_height);

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

        heading::apply_region_class(
            &mut paragraphs,
            region.hint,
            heading_map,
            doc_body_font_size,
            page_height,
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
    merge::merge_continuation_paragraphs_region_aware(&mut all_paragraphs);

    // Merge consecutive code blocks (layout model often gives one region per line)
    merge::merge_consecutive_code_blocks(&mut all_paragraphs);

    // Validate code blocks: reject those that look like image data or artifacts
    // rather than actual code (e.g., hex dumps from embedded images).
    merge::demote_non_code_blocks(&mut all_paragraphs);

    // Merge list item continuations (layout model may split one reference across bboxes)
    merge::merge_list_continuations(&mut all_paragraphs);

    all_paragraphs
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
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
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
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
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
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
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
        let (regions, _) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
        // Segment should be in the Code region (smaller area)
        assert!(regions[0].segment_indices.is_empty()); // Text (large)
        assert_eq!(regions[1].segment_indices.len(), 1); // Code (small)
    }

    #[test]
    fn test_overlap_partial_assigns() {
        // Segment straddles the right edge of a region — partial overlap should still assign
        // Segment: x=180, w=40 → spans [180, 220], region right=200
        // Center point at x=200 is exactly on the boundary; overlap approach should capture it
        let segments = vec![make_segment("straddling", 180.0, 700.0, 40.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 0.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
        // With overlap-based assignment, partial overlap should assign the segment
        assert_eq!(regions[0].segment_indices.len(), 1);
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_overlap_below_threshold_unassigned() {
        // Segment barely touches region edge — overlap too small to assign
        // Segment: x=195, w=40 → spans [195, 235], region right=200
        // Only 5pt of 40pt width overlaps = 12.5% < 20% threshold
        let segments = vec![make_segment("barely", 195.0, 700.0, 40.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 0.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
        assert!(regions[0].segment_indices.is_empty());
        assert_eq!(unassigned.len(), 1);
    }

    #[test]
    fn test_highest_overlap_wins() {
        // Segment overlaps two regions — should go to the one with higher IoS
        // Segment: x=90, w=40 → spans [90, 130]
        // Region 1: [0, 110] → overlap = 20pt, IoS = 20/40 = 0.50
        // Region 2: [100, 300] → overlap = 30pt, IoS = 30/40 = 0.75
        let segments = vec![make_segment("overlapping", 90.0, 700.0, 40.0, 12.0)];
        let hints = vec![
            make_hint(LayoutHintClass::Text, 0.9, 0.0, 690.0, 110.0, 720.0),
            make_hint(LayoutHintClass::Text, 0.9, 100.0, 690.0, 300.0, 720.0),
        ];
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
        // Should go to region 2 (higher IoS)
        assert!(regions[0].segment_indices.is_empty());
        assert_eq!(regions[1].segment_indices.len(), 1);
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_center_point_regression() {
        // Segments fully inside regions should still work (regression test)
        let segments = vec![make_segment("centered", 50.0, 700.0, 40.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Text, 0.9, 0.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
        assert_eq!(regions[0].segment_indices.len(), 1);
        assert!(unassigned.is_empty());
    }

    #[test]
    fn test_reading_order_two_columns() {
        let hints = [
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
        reading_order::order_regions_reading_order(&mut regions, 800.0);
        // Left column should come first (same y-band, smaller x)
        assert!(regions[0].hint.left < regions[1].hint.left);
    }

    #[test]
    fn test_reading_order_vertical() {
        let hints = [
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
        reading_order::order_regions_reading_order(&mut regions, 800.0);
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
        let paragraphs = assemble_region_paragraphs(segments, &hints, &[], 0.5, None, 0, &[]);
        assert!(!paragraphs.is_empty());
        assert!(paragraphs[0].is_code_block);
    }

    #[test]
    fn test_assemble_heading_region() {
        let segments = vec![make_segment("1 Introduction", 10.0, 700.0, 120.0, 18.0)];
        let hints = vec![make_hint(LayoutHintClass::SectionHeader, 0.9, 0.0, 690.0, 200.0, 725.0)];
        let paragraphs = assemble_region_paragraphs(segments, &hints, &[], 0.5, None, 0, &[]);
        assert_eq!(paragraphs.len(), 1);
        assert_eq!(paragraphs[0].heading_level, Some(2));
    }

    #[test]
    fn test_low_confidence_hints_ignored() {
        let segments = vec![make_segment("text", 10.0, 700.0, 40.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Code, 0.3, 0.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
        assert!(regions.is_empty());
        assert_eq!(unassigned.len(), 1);
    }

    #[test]
    fn test_table_regions_excluded_when_extracted() {
        // Segments within successfully extracted table bboxes are dropped.
        let segments = vec![make_segment("text", 10.0, 700.0, 40.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Table, 0.9, 0.0, 690.0, 200.0, 720.0)];
        let extracted_bbox = crate::types::BoundingBox {
            x0: 0.0,
            y0: 690.0,
            x1: 200.0,
            y1: 720.0,
        };
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[extracted_bbox]);
        assert!(regions.is_empty());
        assert_eq!(unassigned.len(), 0); // dropped, not unassigned
    }

    #[test]
    fn test_table_regions_recovered_when_extraction_fails() {
        // Segments in Table hints that did NOT produce tables should fall through.
        let segments = vec![make_segment("text", 10.0, 700.0, 40.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Table, 0.9, 0.0, 690.0, 200.0, 720.0)];
        // No extracted bboxes → table extraction failed for this hint
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
        assert!(regions.is_empty());
        assert_eq!(unassigned.len(), 1); // recovered to unassigned
    }

    #[test]
    fn test_picture_regions_excluded_from_regions_but_unassigned() {
        // Picture regions are excluded from region assignment but segments
        // go to unassigned (no separate text extraction for pictures).
        let segments = vec![make_segment("text", 10.0, 700.0, 40.0, 12.0)];
        let hints = vec![make_hint(LayoutHintClass::Picture, 0.9, 0.0, 690.0, 200.0, 720.0)];
        let (regions, unassigned) = assignment::assign_segments_to_regions(&segments, &hints, 0.5, &[]);
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
        let paragraphs = assemble_region_paragraphs(segments, &hints, &[], 0.5, None, 0, &[]);
        assert_eq!(paragraphs.len(), 3);
        assert_eq!(paragraphs[0].heading_level, Some(1)); // Title
        assert_eq!(paragraphs[0].layout_class, Some(LayoutHintClass::Title));
        assert!(paragraphs[1].heading_level.is_none()); // Body
        assert!(paragraphs[2].is_code_block); // Code
    }

    #[test]
    fn test_reading_order_fullwidth_interleaved_with_columns() {
        // Page layout: full-width title at top, two text columns below, full-width footer
        // Page is 560pt wide, 800pt tall (PDF coords: y=0 at bottom)
        let hints = [
            make_hint(LayoutHintClass::Title, 0.9, 10.0, 700.0, 550.0, 780.0), // full-width top
            make_hint(LayoutHintClass::Text, 0.9, 10.0, 300.0, 260.0, 690.0),  // left column
            make_hint(LayoutHintClass::Text, 0.9, 280.0, 300.0, 550.0, 690.0), // right column
            make_hint(LayoutHintClass::Text, 0.9, 10.0, 100.0, 550.0, 290.0),  // full-width bottom
        ];
        let mut regions: Vec<LayoutRegion> = hints
            .iter()
            .map(|h| LayoutRegion {
                hint: h,
                segment_indices: Vec::new(),
            })
            .collect();
        reading_order::order_regions_reading_order(&mut regions, 800.0);
        // Expected order: Title (top), Left col, Right col, Bottom full-width
        assert_eq!(regions[0].hint.class, LayoutHintClass::Title); // full-width top
        assert!(regions[1].hint.right < 280.0, "Second should be left column"); // left col
        assert!(regions[2].hint.left >= 270.0, "Third should be right column"); // right col
        assert!(regions[3].hint.top < 300.0, "Fourth should be bottom full-width"); // bottom
    }

    #[test]
    fn test_reading_order_all_narrow_regression() {
        // No full-width elements — should behave same as before (column detection)
        let hints = [
            make_hint(LayoutHintClass::Text, 0.9, 300.0, 400.0, 550.0, 700.0), // right col top
            make_hint(LayoutHintClass::Text, 0.9, 10.0, 400.0, 250.0, 700.0),  // left col top
            make_hint(LayoutHintClass::Text, 0.9, 300.0, 100.0, 550.0, 390.0), // right col bottom
            make_hint(LayoutHintClass::Text, 0.9, 10.0, 100.0, 250.0, 390.0),  // left col bottom
        ];
        let mut regions: Vec<LayoutRegion> = hints
            .iter()
            .map(|h| LayoutRegion {
                hint: h,
                segment_indices: Vec::new(),
            })
            .collect();
        reading_order::order_regions_reading_order(&mut regions, 800.0);
        // Left column first (both top and bottom), then right column
        assert!(regions[0].hint.left < 260.0); // left col
        assert!(regions[1].hint.left < 260.0); // left col
        assert!(regions[2].hint.left >= 260.0); // right col
        assert!(regions[3].hint.left >= 260.0); // right col
    }
}
