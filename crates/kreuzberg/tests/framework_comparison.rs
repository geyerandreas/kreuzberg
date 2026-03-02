//! Compare kreuzberg (baseline, layout) vs docling against ground truth.
#![cfg(all(feature = "pdf", feature = "layout-detection"))]

mod helpers;
use helpers::*;
use std::collections::HashMap;

// --- Markdown block parser (same as quality test) ---

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

#[derive(Debug, Clone)]
#[allow(dead_code)]
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
    let mut blocks = Vec::new();
    let lines: Vec<&str> = md.lines().collect();
    let (mut i, mut index) = (0, 0);
    while i < lines.len() {
        let trimmed = lines[i].trim();
        if trimmed.is_empty() {
            i += 1;
            continue;
        }
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
        if trimmed.starts_with('|') {
            let mut content = String::new();
            while i < lines.len() && lines[i].trim().starts_with('|') {
                let tl = lines[i].trim();
                if !tl.chars().all(|c| c == '|' || c == '-' || c == ':' || c == ' ') {
                    if !content.is_empty() {
                        content.push('\n');
                    }
                    content.push_str(tl);
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

fn word_f1(a: &str, b: &str) -> f64 {
    compute_token_f1(&tokenize(a), &tokenize(b))
}

#[derive(Debug)]
#[allow(dead_code)]
struct TypeScore {
    precision: f64,
    recall: f64,
    f1: f64,
    count_ext: usize,
    count_gt: usize,
}
#[derive(Debug)]
#[allow(dead_code)]
struct Quality {
    structural_f1: f64,
    per_type: HashMap<MdBlockType, TypeScore>,
    text_f1: f64,
}

fn match_blocks(gt_blocks: &[&MdBlock], ext_blocks: &[&MdBlock]) -> TypeScore {
    let (count_gt, count_ext) = (gt_blocks.len(), ext_blocks.len());
    if count_gt == 0 && count_ext == 0 {
        return TypeScore {
            precision: 1.0,
            recall: 1.0,
            f1: 1.0,
            count_ext: 0,
            count_gt: 0,
        };
    }
    if count_gt == 0 {
        return TypeScore {
            precision: 0.0,
            recall: 1.0,
            f1: 0.0,
            count_ext,
            count_gt: 0,
        };
    }
    if count_ext == 0 {
        return TypeScore {
            precision: 1.0,
            recall: 0.0,
            f1: 0.0,
            count_ext: 0,
            count_gt,
        };
    }

    let gt_tokens: Vec<Vec<String>> = gt_blocks.iter().map(|b| tokenize(&b.content)).collect();
    let ext_tokens: Vec<Vec<String>> = ext_blocks.iter().map(|b| tokenize(&b.content)).collect();

    let mut candidates: Vec<(usize, usize, f64)> = Vec::new();
    for (gi, gt_tok) in gt_tokens.iter().enumerate() {
        for (ei, ext_tok) in ext_tokens.iter().enumerate() {
            let sim = compute_token_f1(ext_tok, gt_tok);
            if sim >= 0.3 {
                candidates.push((gi, ei, sim));
            }
        }
    }
    candidates.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal));

    let mut matched_gt = vec![false; count_gt];
    let mut matched_ext = vec![false; count_ext];
    let mut match_scores = Vec::new();
    for (gi, ei, sim) in &candidates {
        if matched_gt[*gi] || matched_ext[*ei] {
            continue;
        }
        matched_gt[*gi] = true;
        matched_ext[*ei] = true;
        match_scores.push(*sim);
    }

    let sum: f64 = match_scores.iter().sum();
    let precision = if count_ext > 0 { sum / count_ext as f64 } else { 0.0 };
    let recall = if count_gt > 0 { sum / count_gt as f64 } else { 0.0 };
    let f1 = if precision + recall > 0.0 {
        2.0 * precision * recall / (precision + recall)
    } else {
        0.0
    };
    TypeScore {
        precision,
        recall,
        f1,
        count_ext,
        count_gt,
    }
}

fn score(extracted: &str, gt: &str) -> Quality {
    let ext_blocks = parse_markdown_blocks(extracted);
    let gt_blocks = parse_markdown_blocks(gt);
    let mut all_types = Vec::new();
    for b in ext_blocks.iter().chain(gt_blocks.iter()) {
        if !all_types.contains(&b.block_type) {
            all_types.push(b.block_type);
        }
    }

    let mut per_type: HashMap<MdBlockType, TypeScore> = HashMap::new();
    for &bt in &all_types {
        let gt_of: Vec<&MdBlock> = gt_blocks.iter().filter(|b| b.block_type == bt).collect();
        let ext_of: Vec<&MdBlock> = ext_blocks.iter().filter(|b| b.block_type == bt).collect();
        if gt_of.is_empty() && ext_of.is_empty() {
            continue;
        }
        per_type.insert(bt, match_blocks(&gt_of, &ext_of));
    }

    let mut wsum = 0.0;
    let mut wden = 0.0;
    for (bt, sc) in &per_type {
        let w = bt.weight();
        wsum += w * sc.f1;
        wden += w;
    }
    let structural_f1 = if wden > 0.0 { wsum / wden } else { 0.0 };
    let text_f1 = word_f1(extracted, gt);
    Quality {
        structural_f1,
        per_type,
        text_f1,
    }
}

struct BenchDoc {
    name: &'static str,
    pdf_path: &'static str,
    gt_path: &'static str,
    docling_path: Option<&'static str>,
}

const DOCS: &[BenchDoc] = &[
    BenchDoc {
        name: "docling",
        pdf_path: "pdf/docling.pdf",
        gt_path: "ground_truth/pdf/docling.md",
        docling_path: None,
    },
    BenchDoc {
        name: "table-paper",
        pdf_path: "vendored/docling/pdf/2305.03393v1-pg9.pdf",
        gt_path: "ground_truth/pdf/2305.03393v1-pg9.md",
        docling_path: Some("vendored/docling/md/2305.03393v1-pg9.md"),
    },
    BenchDoc {
        name: "handbook",
        pdf_path: "vendored/docling/pdf/amt_handbook_sample.pdf",
        gt_path: "ground_truth/pdf/amt_handbook_sample.md",
        docling_path: Some("vendored/docling/md/amt_handbook_sample.md"),
    },
    BenchDoc {
        name: "multi-page",
        pdf_path: "pdf/multi_page.pdf",
        gt_path: "ground_truth/pdf/multi_page.md",
        docling_path: Some("vendored/docling/md/multi_page.md"),
    },
    BenchDoc {
        name: "code-formula",
        pdf_path: "pdf/code_and_formula.pdf",
        gt_path: "ground_truth/pdf/code_and_formula.md",
        docling_path: Some("vendored/docling/md/code_and_formula.md"),
    },
    BenchDoc {
        name: "rtl-arabic",
        pdf_path: "pdf/right_to_left_01.pdf",
        gt_path: "ground_truth/pdf/right_to_left_01.md",
        docling_path: Some("vendored/docling/md/right_to_left_01.md"),
    },
    BenchDoc {
        name: "doclaynet-paper",
        pdf_path: "vendored/docling/pdf/2206.01062.pdf",
        gt_path: "ground_truth/pdf/2206.01062.md",
        docling_path: Some("vendored/docling/md/2206.01062.md"),
    },
];

const ALL_TYPES: [MdBlockType; 10] = [
    MdBlockType::Heading1,
    MdBlockType::Heading2,
    MdBlockType::Heading3,
    MdBlockType::Heading4,
    MdBlockType::Heading5,
    MdBlockType::Heading6,
    MdBlockType::CodeBlock,
    MdBlockType::Table,
    MdBlockType::ListItem,
    MdBlockType::Paragraph,
];

#[allow(dead_code)]
struct DocResult {
    name: String,
    base_sf1: f64,
    base_tf1: f64,
    base_ms: f64,
    layout_sf1: f64,
    layout_tf1: f64,
    layout_ms: f64,
    docling_sf1: Option<f64>,
    docling_tf1: Option<f64>,
}

fn run_doc(doc: &BenchDoc) -> DocResult {
    let gt_path = get_test_file_path(doc.gt_path);
    let gt = std::fs::read_to_string(&gt_path).unwrap_or_else(|e| panic!("read GT {}: {}", doc.gt_path, e));

    let pdf_path = get_test_file_path(doc.pdf_path);

    // Kreuzberg baseline
    let config_base = kreuzberg::ExtractionConfig {
        output_format: kreuzberg::core::config::OutputFormat::Markdown,
        ..Default::default()
    };
    let t = std::time::Instant::now();
    let base = kreuzberg::extract_file_sync(&pdf_path, None, &config_base)
        .unwrap_or_else(|e| panic!("base {}: {}", doc.name, e));
    let base_ms = t.elapsed().as_secs_f64() * 1000.0;

    // Kreuzberg + layout
    let config_layout = kreuzberg::ExtractionConfig {
        output_format: kreuzberg::core::config::OutputFormat::Markdown,
        layout: Some(kreuzberg::core::config::layout::LayoutDetectionConfig {
            preset: "fast".to_string(),
            ..Default::default()
        }),
        ..Default::default()
    };
    let t = std::time::Instant::now();
    let layout = kreuzberg::extract_file_sync(&pdf_path, None, &config_layout)
        .unwrap_or_else(|e| panic!("layout {}: {}", doc.name, e));
    let layout_ms = t.elapsed().as_secs_f64() * 1000.0;

    // Save extraction outputs for offline analysis.
    let _ = std::fs::write(format!("/tmp/kreuzberg_{}_baseline.md", doc.name), &base.content);
    let _ = std::fs::write(format!("/tmp/kreuzberg_{}_layout.md", doc.name), &layout.content);

    // Docling output (vendored or /tmp fallback for docling doc)
    let docling_md = if let Some(rel) = doc.docling_path {
        let p = get_test_file_path(rel);
        std::fs::read_to_string(&p).ok()
    } else if doc.name == "docling" {
        std::fs::read_to_string("/tmp/docling_output.md").ok()
    } else {
        None
    };

    let base_q = score(&base.content, &gt);
    let layout_q = score(&layout.content, &gt);

    // Print per-document detail
    eprintln!("\n{}", "=".repeat(100));
    eprintln!("  {} ({})", doc.name, doc.pdf_path);
    eprintln!("{}", "=".repeat(100));
    eprintln!(
        "{:<25} {:>10} {:>10} {:>10}",
        "Framework", "Struct F1", "Text F1", "Time (ms)"
    );
    eprintln!("{}", "-".repeat(60));
    eprintln!(
        "{:<25} {:>9.1}% {:>9.1}% {:>9.0}",
        "Kreuzberg (baseline)",
        base_q.structural_f1 * 100.0,
        base_q.text_f1 * 100.0,
        base_ms
    );
    eprintln!(
        "{:<25} {:>9.1}% {:>9.1}% {:>9.0}",
        "Kreuzberg (+ layout ML)",
        layout_q.structural_f1 * 100.0,
        layout_q.text_f1 * 100.0,
        layout_ms
    );

    let (docling_sf1, docling_tf1) = if let Some(ref dmd) = docling_md {
        let docling_q = score(dmd, &gt);
        eprintln!(
            "{:<25} {:>9.1}% {:>9.1}%",
            "Docling",
            docling_q.structural_f1 * 100.0,
            docling_q.text_f1 * 100.0
        );

        // Per-type comparison (only when docling available)
        let empty = TypeScore {
            precision: 0.0,
            recall: 0.0,
            f1: 0.0,
            count_ext: 0,
            count_gt: 0,
        };
        eprintln!(
            "\n{:<10} {:>18} {:>18} {:>18}",
            "Type", "Kreuzberg Base", "Kreuzberg+ML", "Docling"
        );
        eprintln!("{}", "-".repeat(70));
        for bt in &ALL_TYPES {
            let b = base_q.per_type.get(bt).unwrap_or(&empty);
            let l = layout_q.per_type.get(bt).unwrap_or(&empty);
            let d = docling_q.per_type.get(bt).unwrap_or(&empty);
            if b.count_gt == 0 && b.count_ext == 0 && l.count_ext == 0 && d.count_ext == 0 {
                continue;
            }
            eprintln!(
                "{:<10} F1={:.2} ({:>2}/{:>2})   F1={:.2} ({:>2}/{:>2})   F1={:.2} ({:>2}/{:>2})",
                bt.name(),
                b.f1,
                b.count_ext,
                b.count_gt,
                l.f1,
                l.count_ext,
                l.count_gt,
                d.f1,
                d.count_ext,
                d.count_gt
            );
        }

        (Some(docling_q.structural_f1), Some(docling_q.text_f1))
    } else {
        // Per-type without docling
        let empty = TypeScore {
            precision: 0.0,
            recall: 0.0,
            f1: 0.0,
            count_ext: 0,
            count_gt: 0,
        };
        eprintln!("\n{:<10} {:>18} {:>18}", "Type", "Kreuzberg Base", "Kreuzberg+ML");
        eprintln!("{}", "-".repeat(50));
        for bt in &ALL_TYPES {
            let b = base_q.per_type.get(bt).unwrap_or(&empty);
            let l = layout_q.per_type.get(bt).unwrap_or(&empty);
            if b.count_gt == 0 && b.count_ext == 0 && l.count_ext == 0 {
                continue;
            }
            eprintln!(
                "{:<10} F1={:.2} ({:>2}/{:>2})   F1={:.2} ({:>2}/{:>2})",
                bt.name(),
                b.f1,
                b.count_ext,
                b.count_gt,
                l.f1,
                l.count_ext,
                l.count_gt
            );
        }

        (None, None)
    };

    DocResult {
        name: doc.name.to_string(),
        base_sf1: base_q.structural_f1,
        base_tf1: base_q.text_f1,
        base_ms,
        layout_sf1: layout_q.structural_f1,
        layout_tf1: layout_q.text_f1,
        layout_ms,
        docling_sf1,
        docling_tf1,
    }
}

#[test]
fn compare_frameworks() {
    if !test_documents_available() {
        eprintln!("Skipping: test_documents not available");
        return;
    }

    let results: Vec<DocResult> = DOCS.iter().map(run_doc).collect();

    // Aggregate summary
    eprintln!("\n{}", "=".repeat(110));
    eprintln!("  AGGREGATE SUMMARY");
    eprintln!("{}", "=".repeat(110));
    eprintln!(
        "{:<16} {:>12} {:>12} {:>8} {:>12} {:>12} {:>8} {:>12}",
        "Document", "Base SF1", "Layout SF1", "Delta", "Base TF1", "Layout TF1", "Delta", "Docling SF1"
    );
    eprintln!("{}", "-".repeat(110));

    let (mut sum_base_sf1, mut sum_layout_sf1, mut sum_base_tf1, mut sum_layout_tf1) = (0.0, 0.0, 0.0, 0.0);
    let mut sum_docling_sf1 = 0.0;
    let mut docling_count = 0usize;

    for r in &results {
        let sf1_delta = r.layout_sf1 - r.base_sf1;
        let tf1_delta = r.layout_tf1 - r.base_tf1;
        let docling_str = match r.docling_sf1 {
            Some(d) => format!("{:>10.1}%", d * 100.0),
            None => format!("{:>11}", "-"),
        };
        eprintln!(
            "{:<16} {:>10.1}% {:>10.1}% {:>+7.1}% {:>10.1}% {:>10.1}% {:>+7.1}% {}",
            r.name,
            r.base_sf1 * 100.0,
            r.layout_sf1 * 100.0,
            sf1_delta * 100.0,
            r.base_tf1 * 100.0,
            r.layout_tf1 * 100.0,
            tf1_delta * 100.0,
            docling_str
        );

        sum_base_sf1 += r.base_sf1;
        sum_layout_sf1 += r.layout_sf1;
        sum_base_tf1 += r.base_tf1;
        sum_layout_tf1 += r.layout_tf1;
        if let Some(d) = r.docling_sf1 {
            sum_docling_sf1 += d;
            docling_count += 1;
        }
    }

    let n = results.len() as f64;
    let avg_base_sf1 = sum_base_sf1 / n;
    let avg_layout_sf1 = sum_layout_sf1 / n;
    let avg_base_tf1 = sum_base_tf1 / n;
    let avg_layout_tf1 = sum_layout_tf1 / n;
    let avg_docling_str = if docling_count > 0 {
        format!("{:>10.1}%", sum_docling_sf1 / docling_count as f64 * 100.0)
    } else {
        format!("{:>11}", "-")
    };

    eprintln!("{}", "-".repeat(110));
    eprintln!(
        "{:<16} {:>10.1}% {:>10.1}% {:>+7.1}% {:>10.1}% {:>10.1}% {:>+7.1}% {}",
        "AVERAGE",
        avg_base_sf1 * 100.0,
        avg_layout_sf1 * 100.0,
        (avg_layout_sf1 - avg_base_sf1) * 100.0,
        avg_base_tf1 * 100.0,
        avg_layout_tf1 * 100.0,
        (avg_layout_tf1 - avg_base_tf1) * 100.0,
        avg_docling_str
    );
    eprintln!();

    // ============================================================
    // Quality guardrails: prevent regressions
    // ============================================================
    // Minimum SF1 thresholds (set ~10% below current performance).
    // If any threshold is violated, the test fails.
    let sf1_guardrails: &[(&str, f64)] = &[
        ("multi-page", 0.55),      // Current: 0.615
        ("code-formula", 0.75),    // Current: 0.811
        ("docling", 0.60),         // Current: 0.651
        ("doclaynet-paper", 0.30), // Current: 0.357
        ("rtl-arabic", 0.30),      // Current: 0.672
        ("table-paper", 0.90),     // Current: 0.994
    ];
    let tf1_guardrails: &[(&str, f64)] = &[
        ("multi-page", 0.95),      // Current: 0.995
        ("code-formula", 0.95),    // Current: 0.986
        ("docling", 0.85),         // Current: 0.880
        ("doclaynet-paper", 0.82), // Current: 0.868
    ];

    let mut failures = Vec::new();
    for (name, min_sf1) in sf1_guardrails {
        if let Some(r) = results.iter().find(|r| r.name == *name)
            && r.layout_sf1 < *min_sf1
        {
            failures.push(format!(
                "SF1 regression: {} layout SF1 {:.1}% < minimum {:.1}%",
                name,
                r.layout_sf1 * 100.0,
                min_sf1 * 100.0,
            ));
        }
    }
    for (name, min_tf1) in tf1_guardrails {
        if let Some(r) = results.iter().find(|r| r.name == *name)
            && r.layout_tf1 < *min_tf1
        {
            failures.push(format!(
                "TF1 regression: {} layout TF1 {:.1}% < minimum {:.1}%",
                name,
                r.layout_tf1 * 100.0,
                min_tf1 * 100.0,
            ));
        }
    }

    if !failures.is_empty() {
        for f in &failures {
            eprintln!("GUARDRAIL FAIL: {}", f);
        }
        panic!("{} quality guardrail(s) violated", failures.len());
    }
}
