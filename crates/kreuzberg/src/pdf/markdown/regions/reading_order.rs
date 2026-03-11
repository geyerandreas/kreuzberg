//! Reading order sorting for layout regions.

use super::LayoutRegion;
use crate::pdf::markdown::constants::REGION_SAME_ROW_FRACTION;
use crate::pdf::markdown::types::LayoutHintClass;

/// Fraction of content width above which a region is considered "full-width"
/// and should not be assigned to a column.
const FULLWIDTH_FRACTION: f32 = 0.7;

/// Sort regions in reading order: top-to-bottom, left-to-right within same row.
///
/// First detects if the page has a multi-column layout by analyzing horizontal
/// gaps between region bounding boxes. If columns are detected, full-width
/// regions (spanning >70% of content width) are interleaved at their Y positions
/// between column groups. Narrow regions are processed column-by-column
/// (left column first, then right column). Otherwise falls back to simple
/// Y-ordering with same-row left-to-right sorting.
pub(in crate::pdf::markdown) fn order_regions_reading_order(regions: &mut [LayoutRegion], page_height: f32) {
    if regions.is_empty() {
        return;
    }

    // Compute content width from region extents
    let content_left = regions.iter().map(|r| r.hint.left).fold(f32::MAX, f32::min);
    let content_right = regions.iter().map(|r| r.hint.right).fold(f32::MIN, f32::max);
    let content_width = content_right - content_left;

    if let Some(split_x) = detect_region_column_split_narrow(regions, content_width) {
        // Partition into full-width and narrow regions (by index)
        let mut fullwidth_indices: Vec<usize> = Vec::new();
        let mut narrow_indices: Vec<usize> = Vec::new();

        for (i, r) in regions.iter().enumerate() {
            let region_width = r.hint.right - r.hint.left;
            if content_width > 0.0 && region_width / content_width >= FULLWIDTH_FRACTION {
                fullwidth_indices.push(i);
            } else {
                narrow_indices.push(i);
            }
        }

        // If no full-width regions, just do column sort on everything (original behavior)
        if fullwidth_indices.is_empty() {
            sort_by_columns(regions, split_x);
            return;
        }

        // Build ordered index list: interleave full-width at Y positions between column groups
        // First, sort narrow indices by column then Y
        narrow_indices.sort_by(|&a, &b| {
            let a_cx = (regions[a].hint.left + regions[a].hint.right) / 2.0;
            let b_cx = (regions[b].hint.left + regions[b].hint.right) / 2.0;
            let a_col = if a_cx < split_x { 0u8 } else { 1 };
            let b_col = if b_cx < split_x { 0u8 } else { 1 };

            if a_col != b_col {
                return a_col.cmp(&b_col);
            }
            let a_cy = (regions[a].hint.top + regions[a].hint.bottom) / 2.0;
            let b_cy = (regions[b].hint.top + regions[b].hint.bottom) / 2.0;
            b_cy.total_cmp(&a_cy)
        });

        // Sort full-width indices by Y (top first)
        fullwidth_indices.sort_by(|&a, &b| {
            let a_cy = (regions[a].hint.top + regions[a].hint.bottom) / 2.0;
            let b_cy = (regions[b].hint.top + regions[b].hint.bottom) / 2.0;
            b_cy.total_cmp(&a_cy)
        });

        // Interleave: process full-width regions at their Y positions relative to column groups.
        // A full-width region is placed before the first column region whose center Y is below it.
        let mut ordered: Vec<usize> = Vec::with_capacity(regions.len());
        let mut fw_iter = fullwidth_indices.iter().peekable();

        // Split narrow into left-column and right-column groups
        let mut left_col: Vec<usize> = Vec::new();
        let mut right_col: Vec<usize> = Vec::new();
        for &idx in &narrow_indices {
            let cx = (regions[idx].hint.left + regions[idx].hint.right) / 2.0;
            if cx < split_x {
                left_col.push(idx);
            } else {
                right_col.push(idx);
            }
        }
        // Both are already sorted top-to-bottom within column

        // Walk through Y bands: for each Y band, emit full-width regions above it,
        // then the column pair (left column group, right column group) for that band.
        // Strategy: collect all regions with their Y centers and a type tag,
        // then build reading order.

        // Simpler approach: iterate top-to-bottom. At each step, pick the highest-Y
        // unprocessed region. If it's full-width, emit it. If it's a column region,
        // emit all left-column regions above the next full-width boundary, then
        // all right-column regions above the same boundary.

        let mut left_pos = 0;
        let mut right_pos = 0;

        while fw_iter.peek().is_some() || left_pos < left_col.len() || right_pos < right_col.len() {
            // Find the next full-width region's Y center (if any)
            let fw_y = fw_iter
                .peek()
                .map(|&&idx| (regions[idx].hint.top + regions[idx].hint.bottom) / 2.0);

            // Find the next column region's Y center
            let col_y = {
                let left_y = left_col
                    .get(left_pos)
                    .map(|&idx| (regions[idx].hint.top + regions[idx].hint.bottom) / 2.0);
                let right_y = right_col
                    .get(right_pos)
                    .map(|&idx| (regions[idx].hint.top + regions[idx].hint.bottom) / 2.0);
                match (left_y, right_y) {
                    (Some(ly), Some(ry)) => Some(ly.max(ry)),
                    (Some(ly), None) => Some(ly),
                    (None, Some(ry)) => Some(ry),
                    (None, None) => None,
                }
            };

            match (fw_y, col_y) {
                (Some(fy), Some(cy)) if fy >= cy => {
                    // Full-width region is above (or same level as) next column content → emit it
                    ordered.push(*fw_iter.next().unwrap());
                }
                (Some(_fy), Some(_cy)) => {
                    // Column content is above next full-width → emit column regions down to the full-width Y
                    let boundary_y = _fy;
                    // Emit left column regions above the boundary
                    while left_pos < left_col.len() {
                        let idx = left_col[left_pos];
                        let y = (regions[idx].hint.top + regions[idx].hint.bottom) / 2.0;
                        if y > boundary_y {
                            ordered.push(idx);
                            left_pos += 1;
                        } else {
                            break;
                        }
                    }
                    // Emit right column regions above the boundary
                    while right_pos < right_col.len() {
                        let idx = right_col[right_pos];
                        let y = (regions[idx].hint.top + regions[idx].hint.bottom) / 2.0;
                        if y > boundary_y {
                            ordered.push(idx);
                            right_pos += 1;
                        } else {
                            break;
                        }
                    }
                }
                (Some(_), None) => {
                    // Only full-width left
                    ordered.push(*fw_iter.next().unwrap());
                }
                (None, Some(_)) => {
                    // Only column content left — emit remaining left then right
                    while left_pos < left_col.len() {
                        ordered.push(left_col[left_pos]);
                        left_pos += 1;
                    }
                    while right_pos < right_col.len() {
                        ordered.push(right_col[right_pos]);
                        right_pos += 1;
                    }
                }
                (None, None) => break,
            }
        }

        // Reorder regions in-place using the computed order
        reorder_by_indices(regions, &ordered);
    } else {
        let y_tolerance = page_height * REGION_SAME_ROW_FRACTION;

        // Bucket into rows using y_tolerance, then sort within rows by x.
        // A direct sort_by with tolerance can violate transitivity.
        regions.sort_by(|a, b| {
            let a_cy = (a.hint.top + a.hint.bottom) / 2.0;
            let b_cy = (b.hint.top + b.hint.bottom) / 2.0;
            // Quantize to row buckets to ensure transitivity
            let a_row = (a_cy / y_tolerance).round() as i64;
            let b_row = (b_cy / y_tolerance).round() as i64;
            // Higher row number = lower on page in PDF coords → comes later
            b_row.cmp(&a_row).then_with(|| a.hint.left.total_cmp(&b.hint.left))
        });
    }
}

/// Simple column sort: left column first (top-to-bottom), then right column (top-to-bottom).
fn sort_by_columns(regions: &mut [LayoutRegion], split_x: f32) {
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
}

/// Reorder a slice in-place according to the given index order.
fn reorder_by_indices<T>(slice: &mut [T], order: &[usize]) {
    debug_assert_eq!(slice.len(), order.len());
    // Build inverse permutation and apply via swaps
    let mut perm: Vec<usize> = vec![0; slice.len()];
    for (new_pos, &old_pos) in order.iter().enumerate() {
        perm[new_pos] = old_pos;
    }

    // Apply permutation in-place using cycle decomposition
    let mut visited = vec![false; slice.len()];
    for i in 0..slice.len() {
        if visited[i] || perm[i] == i {
            visited[i] = true;
            continue;
        }
        let mut j = i;
        loop {
            let next = perm[j];
            visited[j] = true;
            if next == i {
                break;
            }
            slice.swap(j, next);
            // Update perm to reflect the swap
            perm[j] = j;
            j = next;
        }
        // Final element in cycle: swap it into place
        slice.swap(j, i);
        perm[j] = j;
    }
}

/// Minimum absolute gap (in points) between region columns.
const MIN_REGION_COLUMN_GAP: f32 = 5.0;

/// Minimum vertical extent (fraction) that each column must span.
const MIN_COLUMN_VERTICAL_FRACTION: f32 = 0.3;

/// Detect if layout regions form two distinct columns, considering only narrow regions.
///
/// Returns the x-position to split at, or None if no column layout detected.
/// Excludes PageHeader/PageFooter and full-width regions from column detection.
fn detect_region_column_split_narrow(regions: &[LayoutRegion], content_width: f32) -> Option<f32> {
    if regions.len() < 4 {
        return None;
    }

    // Collect horizontal edges of narrow content regions only
    let mut edges: Vec<(f32, f32)> = regions
        .iter()
        .filter(|r| !matches!(r.hint.class, LayoutHintClass::PageHeader | LayoutHintClass::PageFooter))
        .filter(|r| {
            let w = r.hint.right - r.hint.left;
            content_width <= 0.0 || w / content_width < FULLWIDTH_FRACTION
        })
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

    // Validate: both sides have at least 2 narrow content regions
    let narrow_regions: Vec<&LayoutRegion> = regions
        .iter()
        .filter(|r| {
            let w = r.hint.right - r.hint.left;
            content_width <= 0.0 || w / content_width < FULLWIDTH_FRACTION
        })
        .collect();

    let left_count = narrow_regions
        .iter()
        .filter(|r| (r.hint.left + r.hint.right) / 2.0 < split_x)
        .count();
    let right_count = narrow_regions
        .iter()
        .filter(|r| (r.hint.left + r.hint.right) / 2.0 >= split_x)
        .count();

    if left_count < 2 || right_count < 2 {
        return None;
    }

    // Validate: both columns span a significant portion of vertical extent
    let y_min = narrow_regions.iter().map(|r| r.hint.bottom).fold(f32::MAX, f32::min);
    let y_max = narrow_regions.iter().map(|r| r.hint.top).fold(f32::MIN, f32::max);
    let y_span = y_max - y_min;

    if y_span < 1.0 {
        return None;
    }

    let left_y_span = {
        let mut lo = f32::MAX;
        let mut hi = f32::MIN;
        for r in narrow_regions
            .iter()
            .filter(|r| (r.hint.left + r.hint.right) / 2.0 < split_x)
        {
            lo = lo.min(r.hint.bottom);
            hi = hi.max(r.hint.top);
        }
        hi - lo
    };
    let right_y_span = {
        let mut lo = f32::MAX;
        let mut hi = f32::MIN;
        for r in narrow_regions
            .iter()
            .filter(|r| (r.hint.left + r.hint.right) / 2.0 >= split_x)
        {
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
