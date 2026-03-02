//! Structural quality scoring for markdown extraction.
//!
//! Parses markdown into typed blocks (headings, paragraphs, code, formulas, etc.)
//! and computes structural F1 scores by matching extracted blocks against ground truth.

use std::collections::HashMap;

use crate::quality::tokenize;

/// Block types in a markdown document.
///
/// Heading levels are distinct types so level accuracy is measured automatically
/// (H1 ≠ H2).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MdBlockType {
    Heading1,
    Heading2,
    Heading3,
    Heading4,
    Heading5,
    Heading6,
    Paragraph,
    CodeBlock,
    Formula,
    Table,
    ListItem,
    Image,
}

impl MdBlockType {
    /// Weight for structural F1 scoring.
    /// Higher weights for elements that layout detection directly influences.
    fn weight(&self) -> f64 {
        match self {
            MdBlockType::Heading1
            | MdBlockType::Heading2
            | MdBlockType::Heading3
            | MdBlockType::Heading4
            | MdBlockType::Heading5
            | MdBlockType::Heading6 => 2.0,
            MdBlockType::CodeBlock | MdBlockType::Formula | MdBlockType::Table => 1.5,
            MdBlockType::ListItem => 1.0,
            MdBlockType::Paragraph | MdBlockType::Image => 0.5,
        }
    }

    fn name(&self) -> &'static str {
        match self {
            MdBlockType::Heading1 => "H1",
            MdBlockType::Heading2 => "H2",
            MdBlockType::Heading3 => "H3",
            MdBlockType::Heading4 => "H4",
            MdBlockType::Heading5 => "H5",
            MdBlockType::Heading6 => "H6",
            MdBlockType::Paragraph => "Paragraph",
            MdBlockType::CodeBlock => "Code",
            MdBlockType::Formula => "Formula",
            MdBlockType::Table => "Table",
            MdBlockType::ListItem => "ListItem",
            MdBlockType::Image => "Image",
        }
    }
}

impl std::fmt::Display for MdBlockType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.name())
    }
}

/// A parsed markdown block with its type and content.
#[derive(Debug, Clone)]
pub struct MdBlock {
    pub block_type: MdBlockType,
    pub content: String,
    pub index: usize,
}

/// Per-type precision, recall, and F1.
#[derive(Debug, Clone)]
pub struct TypeScore {
    pub precision: f64,
    pub recall: f64,
    pub f1: f64,
    pub count_extracted: usize,
    pub count_gt: usize,
}

/// Overall structural quality metrics.
#[derive(Debug, Clone)]
pub struct StructuralQuality {
    /// Weighted structural F1 across all block types.
    pub structural_f1: f64,
    /// Per-block-type scores.
    pub per_type: HashMap<MdBlockType, TypeScore>,
    /// Reading order score (LIS-based, 0.0-1.0).
    pub order_score: f64,
    /// Bag-of-words text F1 (regression guard).
    pub text_f1: f64,
}

/// Parse a markdown string into a sequence of typed blocks.
pub fn parse_markdown_blocks(md: &str) -> Vec<MdBlock> {
    let mut blocks: Vec<MdBlock> = Vec::new();
    let lines: Vec<&str> = md.lines().collect();
    let mut i = 0;
    let mut index = 0;

    while i < lines.len() {
        let line = lines[i];
        let trimmed = line.trim();

        // Skip blank lines
        if trimmed.is_empty() {
            i += 1;
            continue;
        }

        // Code block (fenced)
        if trimmed.starts_with("```") {
            let mut content = String::new();
            i += 1; // skip opening fence
            while i < lines.len() && !lines[i].trim().starts_with("```") {
                if !content.is_empty() {
                    content.push('\n');
                }
                content.push_str(lines[i]);
                i += 1;
            }
            if i < lines.len() {
                i += 1; // skip closing fence
            }
            blocks.push(MdBlock {
                block_type: MdBlockType::CodeBlock,
                content,
                index,
            });
            index += 1;
            continue;
        }

        // Formula block ($$...$$)
        if trimmed.starts_with("$$") && !trimmed[2..].contains("$$") {
            let mut content = String::new();
            i += 1;
            while i < lines.len() && !lines[i].trim().starts_with("$$") {
                if !content.is_empty() {
                    content.push('\n');
                }
                content.push_str(lines[i].trim());
                i += 1;
            }
            if i < lines.len() {
                i += 1; // skip closing $$
            }
            blocks.push(MdBlock {
                block_type: MdBlockType::Formula,
                content,
                index,
            });
            index += 1;
            continue;
        }

        // Headings
        if let Some(heading) = parse_heading(trimmed) {
            blocks.push(MdBlock {
                block_type: heading.0,
                content: heading.1.to_string(),
                index,
            });
            index += 1;
            i += 1;
            continue;
        }

        // Table (consecutive lines starting with |)
        if trimmed.starts_with('|') {
            let mut content = String::new();
            while i < lines.len() && lines[i].trim().starts_with('|') {
                let table_line = lines[i].trim();
                // Skip separator lines (|---|---|)
                if !table_line.chars().all(|c| c == '|' || c == '-' || c == ':' || c == ' ') {
                    if !content.is_empty() {
                        content.push('\n');
                    }
                    content.push_str(table_line);
                }
                i += 1;
            }
            if !content.is_empty() {
                blocks.push(MdBlock {
                    block_type: MdBlockType::Table,
                    content,
                    index,
                });
                index += 1;
            }
            continue;
        }

        // Image
        if trimmed.starts_with("![") {
            blocks.push(MdBlock {
                block_type: MdBlockType::Image,
                content: trimmed.to_string(),
                index,
            });
            index += 1;
            i += 1;
            continue;
        }

        // List item
        if is_list_item(trimmed) {
            let content = strip_list_prefix(trimmed);
            blocks.push(MdBlock {
                block_type: MdBlockType::ListItem,
                content,
                index,
            });
            index += 1;
            i += 1;
            continue;
        }

        // Paragraph (group consecutive non-blank, non-special lines)
        let mut content = String::new();
        while i < lines.len() {
            let line = lines[i].trim();
            if line.is_empty()
                || line.starts_with('#')
                || line.starts_with("```")
                || line.starts_with("$$")
                || line.starts_with('|')
                || line.starts_with("![")
                || is_list_item(line)
            {
                break;
            }
            if !content.is_empty() {
                content.push(' ');
            }
            content.push_str(line);
            i += 1;
        }
        if !content.is_empty() {
            blocks.push(MdBlock {
                block_type: MdBlockType::Paragraph,
                content,
                index,
            });
            index += 1;
        }
    }

    blocks
}

fn parse_heading(line: &str) -> Option<(MdBlockType, &str)> {
    if let Some(rest) = line.strip_prefix("######") {
        Some((MdBlockType::Heading6, rest.trim_start()))
    } else if let Some(rest) = line.strip_prefix("#####") {
        Some((MdBlockType::Heading5, rest.trim_start()))
    } else if let Some(rest) = line.strip_prefix("####") {
        Some((MdBlockType::Heading4, rest.trim_start()))
    } else if let Some(rest) = line.strip_prefix("###") {
        Some((MdBlockType::Heading3, rest.trim_start()))
    } else if let Some(rest) = line.strip_prefix("##") {
        // Must have space after ## to be a heading
        if rest.starts_with(' ') || rest.is_empty() {
            Some((MdBlockType::Heading2, rest.trim_start()))
        } else {
            None
        }
    } else if let Some(rest) = line.strip_prefix('#') {
        if rest.starts_with(' ') || rest.is_empty() {
            Some((MdBlockType::Heading1, rest.trim_start()))
        } else {
            None
        }
    } else {
        None
    }
}

fn is_list_item(line: &str) -> bool {
    line.starts_with("- ")
        || line.starts_with("* ")
        || line.starts_with("+ ")
        || (line.len() >= 3 && line.chars().next().is_some_and(|c| c.is_ascii_digit()) && line.contains(". "))
}

fn strip_list_prefix(line: &str) -> String {
    if line.starts_with("- ") || line.starts_with("* ") || line.starts_with("+ ") {
        line[2..].to_string()
    } else if let Some(dot_pos) = line.find(". ") {
        if line[..dot_pos].chars().all(|c| c.is_ascii_digit()) {
            line[dot_pos + 2..].to_string()
        } else {
            line.to_string()
        }
    } else {
        line.to_string()
    }
}

/// Compute structural quality by comparing extracted markdown against ground truth.
pub fn score_structural_quality(extracted_md: &str, ground_truth_md: &str) -> StructuralQuality {
    let ext_blocks = parse_markdown_blocks(extracted_md);
    let gt_blocks = parse_markdown_blocks(ground_truth_md);

    // Collect all block types present in either
    let mut all_types: Vec<MdBlockType> = Vec::new();
    for b in ext_blocks.iter().chain(gt_blocks.iter()) {
        if !all_types.contains(&b.block_type) {
            all_types.push(b.block_type);
        }
    }

    // Per-type scoring
    let mut per_type: HashMap<MdBlockType, TypeScore> = HashMap::new();
    let mut all_matches: Vec<(usize, usize)> = Vec::new(); // (gt_index, ext_index) for order scoring

    for &block_type in &all_types {
        let gt_of_type: Vec<&MdBlock> = gt_blocks.iter().filter(|b| b.block_type == block_type).collect();
        let ext_of_type: Vec<&MdBlock> = ext_blocks.iter().filter(|b| b.block_type == block_type).collect();

        if gt_of_type.is_empty() && ext_of_type.is_empty() {
            continue;
        }

        let (score, matches) = match_blocks(&gt_of_type, &ext_of_type);
        all_matches.extend(matches);
        per_type.insert(block_type, score);
    }

    // Weighted structural F1
    let structural_f1 = compute_weighted_f1(&per_type);

    // Order score using longest increasing subsequence
    let order_score = compute_order_score(&all_matches);

    // Text F1 (bag-of-words regression guard)
    let ext_tokens = tokenize(extracted_md);
    let gt_tokens = tokenize(ground_truth_md);
    let text_f1 = crate::quality::compute_f1(&ext_tokens, &gt_tokens);

    StructuralQuality {
        structural_f1,
        per_type,
        order_score,
        text_f1,
    }
}

/// Match GT blocks against extracted blocks using greedy matching with adjacent concatenation.
///
/// Returns the per-type score and a list of matched pairs (gt_index, ext_index) for order scoring.
fn match_blocks(gt_blocks: &[&MdBlock], ext_blocks: &[&MdBlock]) -> (TypeScore, Vec<(usize, usize)>) {
    let count_gt = gt_blocks.len();
    let count_ext = ext_blocks.len();

    if count_gt == 0 && count_ext == 0 {
        return (
            TypeScore {
                precision: 1.0,
                recall: 1.0,
                f1: 1.0,
                count_extracted: 0,
                count_gt: 0,
            },
            Vec::new(),
        );
    }
    if count_gt == 0 {
        return (
            TypeScore {
                precision: 0.0,
                recall: 1.0,
                f1: 0.0,
                count_extracted: count_ext,
                count_gt: 0,
            },
            Vec::new(),
        );
    }
    if count_ext == 0 {
        return (
            TypeScore {
                precision: 1.0,
                recall: 0.0,
                f1: 0.0,
                count_extracted: 0,
                count_gt,
            },
            Vec::new(),
        );
    }

    // Build similarity matrix (single blocks + adjacent concatenation)
    let gt_tokens: Vec<Vec<String>> = gt_blocks.iter().map(|b| tokenize(&b.content)).collect();
    let ext_tokens: Vec<Vec<String>> = ext_blocks.iter().map(|b| tokenize(&b.content)).collect();

    // Candidate matches: (gt_idx, ext_idx, similarity, is_concat)
    let mut candidates: Vec<(usize, usize, f64, bool)> = Vec::new();

    for (gi, gt_tok) in gt_tokens.iter().enumerate() {
        for (ei, ext_tok) in ext_tokens.iter().enumerate() {
            let sim = crate::quality::compute_f1(ext_tok, gt_tok);
            if sim >= 0.3 {
                candidates.push((gi, ei, sim, false));
            }

            // Adjacent concatenation: try ext[ei] + ext[ei+1]
            if ei + 1 < ext_tokens.len() {
                let mut concat_tokens = ext_tok.clone();
                concat_tokens.extend(ext_tokens[ei + 1].iter().cloned());
                let concat_sim = crate::quality::compute_f1(&concat_tokens, gt_tok);
                if concat_sim > sim && concat_sim >= 0.3 {
                    candidates.push((gi, ei, concat_sim, true));
                }
            }
        }
    }

    // Greedy matching: sort by similarity descending, match greedily
    candidates.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal));

    let mut matched_gt: Vec<bool> = vec![false; count_gt];
    let mut matched_ext: Vec<bool> = vec![false; count_ext];
    let mut match_scores: Vec<f64> = Vec::new();
    let mut matches: Vec<(usize, usize)> = Vec::new();

    for (gi, ei, sim, is_concat) in &candidates {
        if matched_gt[*gi] || matched_ext[*ei] {
            continue;
        }
        if *is_concat && *ei + 1 < count_ext && matched_ext[*ei + 1] {
            continue;
        }

        matched_gt[*gi] = true;
        matched_ext[*ei] = true;
        if *is_concat && *ei + 1 < count_ext {
            matched_ext[*ei + 1] = true;
        }

        match_scores.push(*sim);
        matches.push((gt_blocks[*gi].index, ext_blocks[*ei].index));
    }

    let sum_scores: f64 = match_scores.iter().sum();
    let precision = if count_ext > 0 {
        sum_scores / count_ext as f64
    } else {
        0.0
    };
    let recall = if count_gt > 0 {
        sum_scores / count_gt as f64
    } else {
        0.0
    };
    let f1 = if precision + recall > 0.0 {
        2.0 * precision * recall / (precision + recall)
    } else {
        0.0
    };

    (
        TypeScore {
            precision,
            recall,
            f1,
            count_extracted: count_ext,
            count_gt,
        },
        matches,
    )
}

/// Compute weighted structural F1 across all block types.
fn compute_weighted_f1(per_type: &HashMap<MdBlockType, TypeScore>) -> f64 {
    let mut weighted_sum = 0.0;
    let mut weight_sum = 0.0;

    for (block_type, score) in per_type {
        let w = block_type.weight();
        weighted_sum += w * score.f1;
        weight_sum += w;
    }

    if weight_sum > 0.0 {
        weighted_sum / weight_sum
    } else {
        0.0
    }
}

/// Compute reading order score using longest increasing subsequence.
///
/// For each matched pair (gt_idx, ext_idx), we look at the ext_idx values
/// sorted by gt_idx. The LIS length / num_matches gives the order score.
fn compute_order_score(matches: &[(usize, usize)]) -> f64 {
    if matches.is_empty() {
        return 1.0; // No matches = vacuously correct order
    }

    // Sort by GT index
    let mut sorted: Vec<(usize, usize)> = matches.to_vec();
    sorted.sort_by_key(|m| m.0);

    // Extract ext indices in GT order
    let ext_indices: Vec<usize> = sorted.iter().map(|m| m.1).collect();

    let lis_len = longest_increasing_subsequence_length(&ext_indices);
    lis_len as f64 / matches.len() as f64
}

/// Compute the length of the longest increasing subsequence.
fn longest_increasing_subsequence_length(seq: &[usize]) -> usize {
    if seq.is_empty() {
        return 0;
    }

    // Patience sorting approach: O(n log n)
    let mut tails: Vec<usize> = Vec::new();
    for &val in seq {
        match tails.binary_search(&val) {
            Ok(_) => {} // exact match, don't change
            Err(pos) => {
                if pos == tails.len() {
                    tails.push(val);
                } else {
                    tails[pos] = val;
                }
            }
        }
    }
    tails.len()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_heading_levels() {
        let md = "# Title\n\n## Section\n\n### Subsection\n\nBody text.\n";
        let blocks = parse_markdown_blocks(md);
        assert_eq!(blocks.len(), 4);
        assert_eq!(blocks[0].block_type, MdBlockType::Heading1);
        assert_eq!(blocks[0].content, "Title");
        assert_eq!(blocks[1].block_type, MdBlockType::Heading2);
        assert_eq!(blocks[1].content, "Section");
        assert_eq!(blocks[2].block_type, MdBlockType::Heading3);
        assert_eq!(blocks[2].content, "Subsection");
        assert_eq!(blocks[3].block_type, MdBlockType::Paragraph);
    }

    #[test]
    fn test_parse_code_block() {
        let md = "Some text.\n\n```python\ndef hello():\n    print('hi')\n```\n\nMore text.\n";
        let blocks = parse_markdown_blocks(md);
        assert_eq!(blocks.len(), 3);
        assert_eq!(blocks[0].block_type, MdBlockType::Paragraph);
        assert_eq!(blocks[1].block_type, MdBlockType::CodeBlock);
        assert!(blocks[1].content.contains("def hello()"));
        assert_eq!(blocks[2].block_type, MdBlockType::Paragraph);
    }

    #[test]
    fn test_parse_formula() {
        let md = "Before.\n\n$$\nE = mc^2\n$$\n\nAfter.\n";
        let blocks = parse_markdown_blocks(md);
        assert_eq!(blocks.len(), 3);
        assert_eq!(blocks[1].block_type, MdBlockType::Formula);
        assert_eq!(blocks[1].content, "E = mc^2");
    }

    #[test]
    fn test_parse_table() {
        let md = "| Name | Age |\n|------|-----|\n| Alice | 30 |\n| Bob | 25 |\n";
        let blocks = parse_markdown_blocks(md);
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, MdBlockType::Table);
        assert!(blocks[0].content.contains("Alice"));
    }

    #[test]
    fn test_parse_list_items() {
        let md = "- Item one\n- Item two\n- Item three\n";
        let blocks = parse_markdown_blocks(md);
        assert_eq!(blocks.len(), 3);
        assert!(blocks.iter().all(|b| b.block_type == MdBlockType::ListItem));
        assert_eq!(blocks[0].content, "Item one");
    }

    #[test]
    fn test_parse_numbered_list() {
        let md = "1. First\n2. Second\n";
        let blocks = parse_markdown_blocks(md);
        assert_eq!(blocks.len(), 2);
        assert!(blocks.iter().all(|b| b.block_type == MdBlockType::ListItem));
    }

    #[test]
    fn test_parse_image() {
        let md = "![Alt text](image.png)\n";
        let blocks = parse_markdown_blocks(md);
        assert_eq!(blocks.len(), 1);
        assert_eq!(blocks[0].block_type, MdBlockType::Image);
    }

    #[test]
    fn test_parse_paragraph_grouping() {
        let md = "Line one of a paragraph.\nLine two of the same paragraph.\n\nNew paragraph.\n";
        let blocks = parse_markdown_blocks(md);
        assert_eq!(blocks.len(), 2);
        assert!(blocks[0].content.contains("Line one"));
        assert!(blocks[0].content.contains("Line two"));
    }

    #[test]
    fn test_identical_markdown() {
        let md = "# Title\n\nBody text here.\n\n## Section\n\nMore text.\n";
        let result = score_structural_quality(md, md);
        assert!((result.structural_f1 - 1.0).abs() < 0.01, "f1={}", result.structural_f1);
        assert!((result.order_score - 1.0).abs() < 0.01, "order={}", result.order_score);
        assert!((result.text_f1 - 1.0).abs() < 0.01, "text_f1={}", result.text_f1);
    }

    #[test]
    fn test_completely_different() {
        let extracted = "# Title\n\nSome content here.\n";
        let gt = "## Other\n\nDifferent content entirely.\n";
        let result = score_structural_quality(extracted, gt);
        assert!(result.structural_f1 < 0.5);
    }

    #[test]
    fn test_heading_level_mismatch() {
        let extracted = "## Title\n\nBody.\n";
        let gt = "# Title\n\nBody.\n";
        let result = score_structural_quality(extracted, gt);
        // H1 and H2 are different types, so heading detection should fail
        let h1_score = result.per_type.get(&MdBlockType::Heading1);
        let h2_score = result.per_type.get(&MdBlockType::Heading2);
        // GT has H1, extracted has H2 → H1 recall=0, H2 precision=low
        assert!(h1_score.is_some_and(|s| s.recall < 0.01));
        assert!(h2_score.is_some_and(|s| s.count_gt == 0));
    }

    #[test]
    fn test_lis_length() {
        assert_eq!(longest_increasing_subsequence_length(&[1, 3, 2, 4, 5]), 4);
        assert_eq!(longest_increasing_subsequence_length(&[5, 4, 3, 2, 1]), 1);
        assert_eq!(longest_increasing_subsequence_length(&[1, 2, 3, 4, 5]), 5);
        assert_eq!(longest_increasing_subsequence_length(&[]), 0);
    }

    #[test]
    fn test_order_score_perfect() {
        let matches = vec![(0, 0), (1, 1), (2, 2)];
        assert!((compute_order_score(&matches) - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_order_score_reversed() {
        let matches = vec![(0, 2), (1, 1), (2, 0)];
        // LIS of [2, 1, 0] = 1
        assert!((compute_order_score(&matches) - 1.0 / 3.0).abs() < 0.01);
    }
}
