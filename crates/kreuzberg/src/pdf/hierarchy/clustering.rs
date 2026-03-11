//! Font size clustering for PDF hierarchy extraction.
//!
//! This module implements k-means clustering on font sizes to identify
//! document hierarchy levels (headings vs body text).

use super::extraction::TextBlock;
use crate::pdf::error::{PdfError, Result};

// K-means algorithm constants
const KMEANS_MAX_ITERATIONS: usize = 100;
const KMEANS_CONVERGENCE_THRESHOLD: f32 = 0.01;

/// A cluster of text blocks with the same font size characteristics.
#[derive(Debug, Clone)]
pub struct FontSizeCluster {
    /// The centroid (mean) font size of this cluster
    pub centroid: f32,
    /// The text blocks that belong to this cluster
    pub members: Vec<TextBlock>,
}

/// Cluster text blocks by font size using k-means algorithm.
///
/// Uses k-means clustering to group text blocks by their font size, which helps
/// identify document hierarchy levels (H1, H2, Body, etc.). The algorithm:
/// 1. Extracts font sizes from text blocks
/// 2. Applies k-means clustering to group similar font sizes
/// 3. Sorts clusters by centroid size in descending order (largest = H1)
/// 4. Returns clusters with their member blocks
///
/// # Arguments
///
/// * `blocks` - Slice of TextBlock objects to cluster
/// * `k` - Number of clusters to create
///
/// # Returns
///
/// Result with vector of FontSizeCluster ordered by size (descending),
/// or an error if clustering fails
///
/// # Example
///
/// ```rust,no_run
/// # #[cfg(feature = "pdf")]
/// # {
/// use kreuzberg::pdf::hierarchy::{TextBlock, BoundingBox, cluster_font_sizes};
///
/// let blocks = vec![
///     TextBlock {
///         text: "Title".to_string(),
///         bbox: BoundingBox { left: 0.0, top: 0.0, right: 100.0, bottom: 24.0 },
///         font_size: 24.0,
///     },
///     TextBlock {
///         text: "Body".to_string(),
///         bbox: BoundingBox { left: 0.0, top: 30.0, right: 100.0, bottom: 42.0 },
///         font_size: 12.0,
///     },
/// ];
///
/// let clusters = cluster_font_sizes(&blocks, 2).unwrap();
/// assert_eq!(clusters.len(), 2);
/// assert_eq!(clusters[0].centroid, 24.0); // Largest is first
/// # }
/// ```
pub fn cluster_font_sizes(blocks: &[TextBlock], k: usize) -> Result<Vec<FontSizeCluster>> {
    if blocks.is_empty() {
        return Ok(Vec::new());
    }

    if k == 0 {
        return Err(PdfError::TextExtractionFailed("K must be greater than 0".to_string()));
    }

    let actual_k = k.min(blocks.len());

    // Extract unique font sizes for initialization
    let mut font_sizes: Vec<f32> = blocks
        .iter()
        .map(|b| b.font_size)
        .filter(|fs| fs.is_finite()) // Filter out NaN/Inf from corrupt PDFs
        .collect();
    font_sizes.sort_by(|a, b| b.total_cmp(a)); // Sort descending
    // Tolerance-based dedup: merge font sizes within 0.05pt (float imprecision)
    font_sizes.dedup_by(|a, b| (*a - *b).abs() < 0.05);

    // Initialize centroids using actual font sizes from the data
    // This is more robust than dividing the range uniformly
    let mut centroids: Vec<f32> = Vec::new();

    if font_sizes.len() >= actual_k {
        // If we have at least k unique font sizes, pick them evenly spaced
        let step = font_sizes.len() / actual_k;
        for i in 0..actual_k {
            let idx = i * step;
            centroids.push(font_sizes[idx.min(font_sizes.len() - 1)]);
        }
    } else {
        // If we have fewer unique sizes than k, use all of them and fill with interpolated values
        centroids = font_sizes.clone();

        // Add interpolated centroids between existing ones to reach desired k
        let min_font = font_sizes[font_sizes.len() - 1];
        let max_font = font_sizes[0];
        let range = max_font - min_font;

        while centroids.len() < actual_k {
            let t = centroids.len() as f32 / (actual_k - 1) as f32;
            let interpolated = max_font - t * range;
            centroids.push(interpolated);
        }

        centroids.sort_by(|a, b| b.total_cmp(a));
        // Keep sorted descending
    }

    // Extract font sizes once for iteration loop
    let font_sizes: Vec<f32> = blocks.iter().map(|b| b.font_size).collect();

    // Run k-means clustering for a fixed number of iterations
    for _ in 0..KMEANS_MAX_ITERATIONS {
        // Assign font sizes to nearest centroid
        let size_clusters = assign_sizes_to_centroids(&font_sizes, &centroids);

        // Update centroids
        let mut new_centroids = Vec::with_capacity(actual_k);
        for (i, cluster) in size_clusters.iter().enumerate() {
            if !cluster.is_empty() {
                new_centroids.push(cluster.iter().sum::<f32>() / cluster.len() as f32);
            } else {
                new_centroids.push(centroids[i]);
            }
        }

        // Check for convergence
        let converged = centroids
            .iter()
            .zip(new_centroids.iter())
            .all(|(old, new)| (old - new).abs() < KMEANS_CONVERGENCE_THRESHOLD);

        std::mem::swap(&mut centroids, &mut new_centroids);

        if converged {
            break;
        }
    }

    // Final assignment to create result
    let clusters = assign_blocks_to_centroids(blocks, &centroids);

    // Create FontSizeCluster objects with centroids
    let mut result: Vec<FontSizeCluster> = Vec::new();

    for i in 0..actual_k {
        if !clusters[i].is_empty() {
            let centroid_value = centroids[i];
            result.push(FontSizeCluster {
                centroid: centroid_value,
                members: clusters[i].clone(),
            });
        }
    }

    // Sort by centroid size in descending order (largest font = H1)
    result.sort_by(|a, b| b.centroid.total_cmp(&a.centroid));

    Ok(result)
}

/// Assign heading levels using the "most frequent cluster = Body" rule.
///
/// Instead of naively mapping the largest font size to H1, this function
/// identifies the cluster with the most members as body text. Only clusters
/// with fewer members AND sufficiently larger font size than body become headings.
///
/// # Arguments
///
/// * `clusters` - Slice of FontSizeCluster objects (sorted by centroid descending)
/// * `min_heading_ratio` - Minimum ratio of heading centroid to body centroid (e.g. 1.15)
/// * `min_heading_gap` - Minimum absolute font-size difference in points (e.g. 1.5)
///
/// # Returns
///
/// Vector of tuples `(centroid, heading_level)` where `None` means body text
/// and `Some(1..=6)` means H1-H6. Sorted by centroid descending.
pub fn assign_heading_levels_smart(
    clusters: &[FontSizeCluster],
    min_heading_ratio: f32,
    min_heading_gap: f32,
) -> Vec<(f32, Option<u8>)> {
    if clusters.is_empty() {
        return Vec::new();
    }

    // Single cluster means everything is body
    if clusters.len() == 1 {
        return vec![(clusters[0].centroid, None)];
    }

    // Find the cluster with the most members (this is body text)
    let body_idx = clusters
        .iter()
        .enumerate()
        .max_by_key(|(_, c)| c.members.len())
        .map(|(i, _)| i)
        .unwrap_or(0);

    let body_centroid = clusters[body_idx].centroid;

    // Collect heading candidates: clusters with sufficiently larger font size than body
    // Must pass both ratio gate AND absolute gap gate
    let min_heading_size = body_centroid * min_heading_ratio;
    let min_heading_abs = body_centroid + min_heading_gap;
    let heading_threshold = min_heading_size.max(min_heading_abs);

    let mut heading_candidates: Vec<(usize, f32)> = clusters
        .iter()
        .enumerate()
        .filter(|(i, c)| *i != body_idx && c.centroid >= heading_threshold)
        .map(|(i, c)| (i, c.centroid))
        .collect();

    // Sort heading candidates by centroid descending (largest = H1)
    heading_candidates.sort_by(|a, b| b.1.total_cmp(&a.1));

    // Assign heading levels H1-H6 (max 6 heading levels)
    let max_headings = 6usize;
    let mut result: Vec<(f32, Option<u8>)> = Vec::with_capacity(clusters.len());

    for (i, cluster) in clusters.iter().enumerate() {
        if i == body_idx {
            result.push((cluster.centroid, None));
        } else if let Some(pos) = heading_candidates.iter().position(|(idx, _)| *idx == i) {
            if pos < max_headings {
                result.push((cluster.centroid, Some((pos + 1) as u8)));
            } else {
                // More than 6 heading levels, treat as body
                result.push((cluster.centroid, None));
            }
        } else {
            // Smaller font size than body, treat as body
            result.push((cluster.centroid, None));
        }
    }

    result
}

/// Helper function to assign font sizes to their nearest centroid (for iteration loop).
///
/// Assigns font sizes to clusters without cloning full TextBlock objects.
/// Used during k-means iterations to compute new centroids efficiently.
///
/// # Arguments
///
/// * `font_sizes` - Slice of font size values to assign
/// * `centroids` - Slice of centroid values (one per cluster)
///
/// # Returns
///
/// A vector of clusters, where each cluster contains the font sizes assigned to that centroid
fn assign_sizes_to_centroids(font_sizes: &[f32], centroids: &[f32]) -> Vec<Vec<f32>> {
    let mut clusters: Vec<Vec<f32>> = vec![Vec::new(); centroids.len()];

    for &size in font_sizes {
        let mut min_distance = f32::INFINITY;
        let mut best_cluster = 0;

        for (i, &centroid) in centroids.iter().enumerate() {
            let distance = (size - centroid).abs();
            if distance < min_distance {
                min_distance = distance;
                best_cluster = i;
            }
        }

        clusters[best_cluster].push(size);
    }

    clusters
}

/// Helper function to assign blocks to their nearest centroid.
///
/// Iterates through blocks and finds the closest centroid for each block,
/// grouping them into clusters. Used in the final assignment step after convergence.
///
/// # Arguments
///
/// * `blocks` - Slice of TextBlock objects to assign
/// * `centroids` - Slice of centroid values (one per cluster)
///
/// # Returns
///
/// A vector of clusters, where each cluster contains the TextBlock objects
/// assigned to that centroid
fn assign_blocks_to_centroids(blocks: &[TextBlock], centroids: &[f32]) -> Vec<Vec<TextBlock>> {
    let mut clusters: Vec<Vec<TextBlock>> = vec![Vec::new(); centroids.len()];

    for block in blocks {
        let mut min_distance = f32::INFINITY;
        let mut best_cluster = 0;

        for (i, &centroid) in centroids.iter().enumerate() {
            let distance = (block.font_size - centroid).abs();
            if distance < min_distance {
                min_distance = distance;
                best_cluster = i;
            }
        }

        clusters[best_cluster].push(block.clone());
    }

    clusters
}
