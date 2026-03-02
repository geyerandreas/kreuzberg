//! PDF markdown structural quality A/B test: baseline vs layout-detection-enhanced.
//!
//! Extracts documents with and without layout detection, compares structural F1 scores
//! (heading accuracy, code block detection, etc.) and measures performance overhead.
//!
//! Requires markdown ground truth files in `test_documents/ground_truth/pdf/<name>.md`.
//!
//! Usage:
//!   # Run A/B comparison (requires layout-detection + pdf + bundled-pdfium):
//!   cargo test -p kreuzberg --features "pdf,layout-detection,bundled-pdfium" \
//!     --test pdf_markdown_quality -- --nocapture
//!
//!   # Run baseline-only (no layout detection):
//!   cargo test -p kreuzberg --features "pdf,bundled-pdfium" \
//!     --test pdf_markdown_quality -- --nocapture

#![cfg(feature = "pdf")]

mod helpers;

use helpers::*;
use kreuzberg::core::config::{ExtractionConfig, OutputFormat};
use kreuzberg::extract_file_sync;
use std::collections::HashMap;
use std::time::Instant;

// ═══════════════════════════════════════════════════════════════════
// Markdown block parser (self-contained, mirrors benchmark-harness)
// ═══════════════════════════════════════════════════════════════════

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum MdBlockType {
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
            MdBlockType::Paragraph => "Para",
            MdBlockType::CodeBlock => "Code",
            MdBlockType::Formula => "Formula",
            MdBlockType::Table => "Table",
            MdBlockType::ListItem => "List",
            MdBlockType::Image => "Image",
        }
    }
}

impl std::fmt::Display for MdBlockType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.name())
    }
}

#[derive(Debug, Clone)]
struct MdBlock {
    block_type: MdBlockType,
    content: String,
    index: usize,
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

fn parse_markdown_blocks(md: &str) -> Vec<MdBlock> {
    let mut blocks: Vec<MdBlock> = Vec::new();
    let lines: Vec<&str> = md.lines().collect();
    let mut i = 0;
    let mut index = 0;

    while i < lines.len() {
        let trimmed = lines[i].trim();

        if trimmed.is_empty() {
            i += 1;
            continue;
        }

        // Code block (fenced)
        if trimmed.starts_with("```") {
            let mut content = String::new();
            i += 1;
            while i < lines.len() && !lines[i].trim().starts_with("```") {
                if !content.is_empty() {
                    content.push('\n');
                }
                content.push_str(lines[i]);
                i += 1;
            }
            if i < lines.len() {
                i += 1;
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
                i += 1;
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

        // Table
        if trimmed.starts_with('|') {
            let mut content = String::new();
            while i < lines.len() && lines[i].trim().starts_with('|') {
                let table_line = lines[i].trim();
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
            blocks.push(MdBlock {
                block_type: MdBlockType::ListItem,
                content: strip_list_prefix(trimmed),
                index,
            });
            index += 1;
            i += 1;
            continue;
        }

        // Paragraph
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

// ═══════════════════════════════════════════════════════════════════
// Scoring utilities
// ═══════════════════════════════════════════════════════════════════

fn tokenize(text: &str) -> Vec<String> {
    text.split_whitespace()
        .map(|w| w.trim_matches(|c: char| c.is_ascii_punctuation()).to_lowercase())
        .filter(|w| !w.is_empty())
        .collect()
}

fn compute_token_f1(extracted: &[String], ground_truth: &[String]) -> f64 {
    if ground_truth.is_empty() && extracted.is_empty() {
        return 1.0;
    }
    if ground_truth.is_empty() || extracted.is_empty() {
        return 0.0;
    }

    let mut gt_bag: HashMap<&str, usize> = HashMap::new();
    for t in ground_truth {
        *gt_bag.entry(t.as_str()).or_insert(0) += 1;
    }

    let mut ext_bag: HashMap<&str, usize> = HashMap::new();
    for t in extracted {
        *ext_bag.entry(t.as_str()).or_insert(0) += 1;
    }

    let mut matching = 0usize;
    for (word, &ext_count) in &ext_bag {
        if let Some(&gt_count) = gt_bag.get(word) {
            matching += ext_count.min(gt_count);
        }
    }

    let precision = matching as f64 / extracted.len() as f64;
    let recall = matching as f64 / ground_truth.len() as f64;
    if precision + recall > 0.0 {
        2.0 * precision * recall / (precision + recall)
    } else {
        0.0
    }
}

fn word_f1(extracted: &str, ground_truth: &str) -> f64 {
    compute_token_f1(&tokenize(extracted), &tokenize(ground_truth))
}

#[derive(Debug, Clone)]
struct TypeScore {
    precision: f64,
    recall: f64,
    f1: f64,
    count_extracted: usize,
    count_gt: usize,
}

#[derive(Debug, Clone)]
struct StructuralQuality {
    structural_f1: f64,
    per_type: HashMap<MdBlockType, TypeScore>,
    order_score: f64,
    text_f1: f64,
}

fn score_structural_quality(extracted_md: &str, ground_truth_md: &str) -> StructuralQuality {
    let ext_blocks = parse_markdown_blocks(extracted_md);
    let gt_blocks = parse_markdown_blocks(ground_truth_md);

    let mut all_types: Vec<MdBlockType> = Vec::new();
    for b in ext_blocks.iter().chain(gt_blocks.iter()) {
        if !all_types.contains(&b.block_type) {
            all_types.push(b.block_type);
        }
    }

    let mut per_type: HashMap<MdBlockType, TypeScore> = HashMap::new();
    let mut all_matches: Vec<(usize, usize)> = Vec::new();

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

    let structural_f1 = compute_weighted_f1(&per_type);
    let order_score = compute_order_score(&all_matches);
    let text_f1 = word_f1(extracted_md, ground_truth_md);

    StructuralQuality {
        structural_f1,
        per_type,
        order_score,
        text_f1,
    }
}

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

    let gt_tokens: Vec<Vec<String>> = gt_blocks.iter().map(|b| tokenize(&b.content)).collect();
    let ext_tokens: Vec<Vec<String>> = ext_blocks.iter().map(|b| tokenize(&b.content)).collect();

    // Candidates: (gt_idx, ext_idx, similarity, is_concat)
    let mut candidates: Vec<(usize, usize, f64, bool)> = Vec::new();

    for (gi, gt_tok) in gt_tokens.iter().enumerate() {
        for (ei, ext_tok) in ext_tokens.iter().enumerate() {
            let sim = compute_token_f1(ext_tok, gt_tok);
            if sim >= 0.3 {
                candidates.push((gi, ei, sim, false));
            }
            // Adjacent concatenation
            if ei + 1 < ext_tokens.len() {
                let mut concat = ext_tok.clone();
                concat.extend(ext_tokens[ei + 1].iter().cloned());
                let concat_sim = compute_token_f1(&concat, gt_tok);
                if concat_sim > sim && concat_sim >= 0.3 {
                    candidates.push((gi, ei, concat_sim, true));
                }
            }
        }
    }

    candidates.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal));

    let mut matched_gt = vec![false; count_gt];
    let mut matched_ext = vec![false; count_ext];
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

fn compute_order_score(matches: &[(usize, usize)]) -> f64 {
    if matches.is_empty() {
        return 1.0;
    }
    let mut sorted = matches.to_vec();
    sorted.sort_by_key(|m| m.0);
    let ext_indices: Vec<usize> = sorted.iter().map(|m| m.1).collect();
    let lis = lis_length(&ext_indices);
    lis as f64 / matches.len() as f64
}

fn lis_length(seq: &[usize]) -> usize {
    if seq.is_empty() {
        return 0;
    }
    let mut tails: Vec<usize> = Vec::new();
    for &val in seq {
        match tails.binary_search(&val) {
            Ok(_) => {}
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

// ═══════════════════════════════════════════════════════════════════
// Test documents with markdown ground truth
// ═══════════════════════════════════════════════════════════════════

/// Documents that have both a PDF and a markdown ground truth file.
/// (name, pdf_relative_path, markdown_gt_relative_path)
const MARKDOWN_GT_DOCS: &[(&str, &str, &str)] = &[("docling", "pdf/docling.pdf", "ground_truth/pdf/docling.md")];

// ═══════════════════════════════════════════════════════════════════
// Extraction helpers
// ═══════════════════════════════════════════════════════════════════

fn extract_baseline(pdf_path: &std::path::Path) -> Option<(String, std::time::Duration)> {
    let config = ExtractionConfig {
        output_format: OutputFormat::Markdown,
        ..Default::default()
    };
    let start = Instant::now();
    let result = extract_file_sync(pdf_path, None, &config).ok()?;
    let duration = start.elapsed();
    Some((result.content, duration))
}

#[cfg(feature = "layout-detection")]
fn extract_with_layout(pdf_path: &std::path::Path, preset: &str) -> Option<(String, std::time::Duration)> {
    use kreuzberg::core::config::layout::LayoutDetectionConfig;

    let config = ExtractionConfig {
        output_format: OutputFormat::Markdown,
        layout: Some(LayoutDetectionConfig {
            preset: preset.to_string(),
            ..Default::default()
        }),
        ..Default::default()
    };
    let start = Instant::now();
    let result = extract_file_sync(pdf_path, None, &config).ok()?;
    let duration = start.elapsed();
    Some((result.content, duration))
}

// ═══════════════════════════════════════════════════════════════════
// A/B Quality Gate Test
// ═══════════════════════════════════════════════════════════════════

#[test]
fn test_markdown_structural_quality_baseline() {
    if !test_documents_available() {
        println!("Skipping: test_documents not available");
        return;
    }

    println!("\n{}", "=".repeat(110));
    println!("Markdown Structural Quality — Baseline (no layout detection)");
    println!("{}", "=".repeat(110));
    println!(
        "{:<20} {:>10} {:>10} {:>10} {:>10} {:>10}",
        "Document", "Struct F1", "Text F1", "Order", "Time (ms)", "Status"
    );
    println!("{}", "-".repeat(110));

    let mut all_pass = true;

    for &(name, pdf_rel, md_gt_rel) in MARKDOWN_GT_DOCS {
        let pdf_path = get_test_file_path(pdf_rel);
        let gt_path = get_test_file_path(md_gt_rel);

        if !pdf_path.exists() || !gt_path.exists() {
            println!(
                "{:<20} {:>10} {:>10} {:>10} {:>10} {:>10}",
                name, "-", "-", "-", "-", "SKIP"
            );
            continue;
        }

        let gt_md = std::fs::read_to_string(&gt_path).expect("read GT markdown");

        let (content, duration) = match extract_baseline(&pdf_path) {
            Some(r) => r,
            None => {
                println!(
                    "{:<20} {:>10} {:>10} {:>10} {:>10} {:>10}",
                    name, "-", "-", "-", "-", "ERR"
                );
                all_pass = false;
                continue;
            }
        };

        let quality = score_structural_quality(&content, &gt_md);
        let time_ms = duration.as_secs_f64() * 1000.0;

        let status = if quality.text_f1 >= 0.5 { "PASS" } else { "FAIL" };
        if quality.text_f1 < 0.5 {
            all_pass = false;
        }

        println!(
            "{:<20} {:>9.1}% {:>9.1}% {:>9.1}% {:>9.0} {:>10}",
            name,
            quality.structural_f1 * 100.0,
            quality.text_f1 * 100.0,
            quality.order_score * 100.0,
            time_ms,
            status
        );

        // Print per-type breakdown
        print_type_breakdown(name, &quality);
    }

    assert!(all_pass, "One or more documents failed baseline quality gate");
}

#[cfg(feature = "layout-detection")]
#[test]
fn test_markdown_structural_quality_ab_comparison() {
    if !test_documents_available() {
        println!("Skipping: test_documents not available");
        return;
    }

    println!("\n{}", "=".repeat(130));
    println!("Markdown Structural Quality — A/B Comparison (Baseline vs Layout Detection)");
    println!("{}", "=".repeat(130));
    println!(
        "{:<15} {:>9} {:>9} {:>8} {:>9} {:>9} {:>8} {:>10} {:>10} {:>10}",
        "Document",
        "Base F1",
        "Layout F1",
        "Delta",
        "Base Txt",
        "Lay Txt",
        "Txt Dlt",
        "Base ms",
        "Layout ms",
        "Overhead"
    );
    println!("{}", "-".repeat(130));

    let mut all_pass = true;

    for &(name, pdf_rel, md_gt_rel) in MARKDOWN_GT_DOCS {
        let pdf_path = get_test_file_path(pdf_rel);
        let gt_path = get_test_file_path(md_gt_rel);

        if !pdf_path.exists() || !gt_path.exists() {
            println!("{:<15} SKIP (files not found)", name);
            continue;
        }

        let gt_md = std::fs::read_to_string(&gt_path).expect("read GT markdown");

        // Baseline extraction (no layout detection)
        let (base_content, base_duration) = match extract_baseline(&pdf_path) {
            Some(r) => r,
            None => {
                println!("{:<15} ERR (baseline extraction failed)", name);
                all_pass = false;
                continue;
            }
        };

        // Layout-enhanced extraction
        let (layout_content, layout_duration) = match extract_with_layout(&pdf_path, "fast") {
            Some(r) => r,
            None => {
                println!("{:<15} ERR (layout extraction failed)", name);
                all_pass = false;
                continue;
            }
        };

        let base_quality = score_structural_quality(&base_content, &gt_md);
        let layout_quality = score_structural_quality(&layout_content, &gt_md);

        let delta_f1 = layout_quality.structural_f1 - base_quality.structural_f1;
        let delta_txt = layout_quality.text_f1 - base_quality.text_f1;
        let base_ms = base_duration.as_secs_f64() * 1000.0;
        let layout_ms = layout_duration.as_secs_f64() * 1000.0;
        let overhead = if base_ms > 0.0 {
            format!("{:.1}x", layout_ms / base_ms)
        } else {
            "N/A".to_string()
        };

        println!(
            "{:<15} {:>8.1}% {:>8.1}% {:>+7.1}% {:>8.1}% {:>8.1}% {:>+7.1}% {:>9.0} {:>9.0} {:>10}",
            name,
            base_quality.structural_f1 * 100.0,
            layout_quality.structural_f1 * 100.0,
            delta_f1 * 100.0,
            base_quality.text_f1 * 100.0,
            layout_quality.text_f1 * 100.0,
            delta_txt * 100.0,
            base_ms,
            layout_ms,
            overhead,
        );

        // Per-type A/B breakdown
        print_ab_type_breakdown(name, &base_quality, &layout_quality);

        // Assertions:
        // 1. Layout-enhanced structural F1 should not regress more than 2% from baseline
        if layout_quality.structural_f1 < base_quality.structural_f1 - 0.02 {
            println!(
                "  WARNING: Layout structural F1 ({:.3}) regressed vs baseline ({:.3})",
                layout_quality.structural_f1, base_quality.structural_f1
            );
            all_pass = false;
        }

        // 2. Text F1 (bag-of-words) must not regress more than 1%
        if layout_quality.text_f1 < base_quality.text_f1 - 0.01 {
            println!(
                "  WARNING: Layout text F1 ({:.3}) regressed vs baseline ({:.3})",
                layout_quality.text_f1, base_quality.text_f1
            );
            all_pass = false;
        }
    }

    println!("{}", "-".repeat(130));

    assert!(
        all_pass,
        "A/B comparison detected quality regressions — see warnings above"
    );
}

// ═══════════════════════════════════════════════════════════════════
// Display helpers
// ═══════════════════════════════════════════════════════════════════

fn print_type_breakdown(name: &str, quality: &StructuralQuality) {
    let mut types: Vec<_> = quality.per_type.iter().collect();
    types.sort_by_key(|(t, _)| t.name());

    println!("  {} type breakdown:", name);
    for (block_type, score) in &types {
        if score.count_gt > 0 || score.count_extracted > 0 {
            println!(
                "    {:<8} P={:.2} R={:.2} F1={:.2}  (GT={}, Ext={})",
                block_type.name(),
                score.precision,
                score.recall,
                score.f1,
                score.count_gt,
                score.count_extracted,
            );
        }
    }
}

#[cfg(feature = "layout-detection")]
fn print_ab_type_breakdown(name: &str, base: &StructuralQuality, layout: &StructuralQuality) {
    // Collect all types from both
    let mut all_types: Vec<MdBlockType> = Vec::new();
    for t in base.per_type.keys().chain(layout.per_type.keys()) {
        if !all_types.contains(t) {
            all_types.push(*t);
        }
    }
    all_types.sort_by_key(|t| t.name());

    println!("  {} per-type A/B:", name);
    for block_type in &all_types {
        let empty = TypeScore {
            precision: 0.0,
            recall: 0.0,
            f1: 0.0,
            count_extracted: 0,
            count_gt: 0,
        };
        let base_score = base.per_type.get(block_type).unwrap_or(&empty);
        let layout_score = layout.per_type.get(block_type).unwrap_or(&empty);

        if base_score.count_gt > 0
            || base_score.count_extracted > 0
            || layout_score.count_gt > 0
            || layout_score.count_extracted > 0
        {
            let delta = layout_score.f1 - base_score.f1;
            let indicator = if delta > 0.01 {
                "+"
            } else if delta < -0.01 {
                "-"
            } else {
                "="
            };
            println!(
                "    {:<8} Base F1={:.2}  Layout F1={:.2}  ({}{:.2})  [GT={}, Base Ext={}, Layout Ext={}]",
                block_type.name(),
                base_score.f1,
                layout_score.f1,
                indicator,
                delta.abs(),
                base_score.count_gt.max(layout_score.count_gt),
                base_score.count_extracted,
                layout_score.count_extracted,
            );
        }
    }
}

// ═══════════════════════════════════════════════════════════════════
// Scoring unit tests
// ═══════════════════════════════════════════════════════════════════

#[cfg(test)]
mod scoring_tests {
    use super::*;

    #[test]
    fn test_identical_markdown_scores_perfect() {
        let md = "# Title\n\nBody text.\n\n## Section\n\nMore text.\n";
        let result = score_structural_quality(md, md);
        assert!(
            (result.structural_f1 - 1.0).abs() < 0.01,
            "struct_f1={}",
            result.structural_f1
        );
        assert!((result.order_score - 1.0).abs() < 0.01, "order={}", result.order_score);
        assert!((result.text_f1 - 1.0).abs() < 0.01, "text_f1={}", result.text_f1);
    }

    #[test]
    fn test_heading_level_mismatch_penalizes() {
        let extracted = "## Title\n\nBody.\n";
        let gt = "# Title\n\nBody.\n";
        let result = score_structural_quality(extracted, gt);
        // H1 and H2 are different types, so structural F1 should be below perfect
        assert!(result.structural_f1 < 0.9);
    }

    #[test]
    fn test_missing_code_block_penalizes() {
        let extracted = "# Title\n\nSome code text here\n";
        let gt = "# Title\n\n```\nSome code text here\n```\n";
        let result = score_structural_quality(extracted, gt);
        // Extracted has paragraph instead of code block
        let code_score = result.per_type.get(&MdBlockType::CodeBlock);
        assert!(code_score.is_none() || code_score.unwrap().recall < 0.01);
    }

    #[test]
    fn test_word_f1_identical() {
        assert!((word_f1("hello world", "hello world") - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_word_f1_no_overlap() {
        assert!(word_f1("hello world", "foo bar") < 0.001);
    }

    #[test]
    fn test_lis_basic() {
        assert_eq!(lis_length(&[1, 3, 2, 4, 5]), 4);
        assert_eq!(lis_length(&[5, 4, 3, 2, 1]), 1);
        assert_eq!(lis_length(&[1, 2, 3, 4, 5]), 5);
    }
}
