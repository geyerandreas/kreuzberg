//! pdf_oxide vs pdfium (kreuzberg) comparison tool.
//!
//! Compares text extraction correctness, speed, and markdown quality.
//!
//! Usage:
//!   cargo run -p pdf-oxide-comparison --release -- --mode all
//!   cargo run -p pdf-oxide-comparison --release -- --mode dump
//!   cargo run -p pdf-oxide-comparison --release -- --mode speed

use anyhow::Result;
use clap::Parser;
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

/// Curated set of PDFs with text layers for thorough comparison.
const CURATED_PDFS: &[&str] = &[
    "docling.pdf",                                // complex academic paper, headings+tables+lists
    "fake_memo.pdf",                              // simple structured memo
    "google_doc_document.pdf",                    // Google Docs export
    "code_and_formula.pdf",                       // technical with code/formulas
    "sample_contract.pdf",                        // legal document
    "test_article.pdf",                           // standard article
    "searchable.pdf",                             // simple searchable PDF
    "multi_page.pdf",                             // multi-page document
    "right_to_left_01.pdf",                       // RTL text (Arabic/Hebrew)
    "non_ascii_text.pdf",                         // international/non-ASCII text
    "copy_protected.pdf",                         // encrypted PDF
    "perfect_hash_functions_slides.pdf",          // presentation slides
    "the_hideous_name_1985_pike85hideous.pdf",    // older academic paper
    "program_design_in_the_unix_environment.pdf", // classic CS paper
    "5_level_paging_and_5_level_ept_intel_revision_1_1_may_2017.pdf", // Intel spec
    "scanned.pdf",                                // scanned with text layer
    "tiny.pdf",                                   // minimal PDF
    "large.pdf",                                  // larger document
];

#[derive(Parser)]
#[command(name = "pdf-oxide-comparison")]
#[command(about = "Compare pdf_oxide vs pdfium (kreuzberg) for PDF extraction")]
struct Cli {
    /// Comparison mode: dump, speed, or all
    #[arg(long, default_value = "all")]
    mode: String,

    /// Number of iterations for speed benchmark
    #[arg(long, default_value = "20")]
    iterations: usize,

    /// Output directory
    #[arg(long, default_value = "/tmp/pdf_oxide_comparison")]
    output_dir: String,
}

fn test_documents_dir() -> PathBuf {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("test_documents")
        .join("pdf")
}

fn curated_files(pdf_dir: &Path) -> Vec<PathBuf> {
    CURATED_PDFS
        .iter()
        .filter_map(|name| {
            let p = pdf_dir.join(name);
            if p.exists() { Some(p) } else { None }
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Extraction wrappers
// ---------------------------------------------------------------------------

fn kreuzberg_extract_text(path: &Path) -> Result<String> {
    use kreuzberg::core::config::ExtractionConfig;
    let config = ExtractionConfig::default();
    let result = kreuzberg::extract_file_sync(path, None, &config).map_err(|e| anyhow::anyhow!("kreuzberg: {e}"))?;
    Ok(result.content)
}

fn kreuzberg_extract_markdown(path: &Path) -> Result<String> {
    use kreuzberg::core::config::{ExtractionConfig, OutputFormat};
    let config = ExtractionConfig {
        output_format: OutputFormat::Markdown,
        ..Default::default()
    };
    let result = kreuzberg::extract_file_sync(path, None, &config).map_err(|e| anyhow::anyhow!("kreuzberg: {e}"))?;
    Ok(result.content)
}

fn pdf_oxide_extract_text(path: &Path) -> Result<String> {
    let mut doc = pdf_oxide::PdfDocument::open(path).map_err(|e| anyhow::anyhow!("pdf_oxide open: {e}"))?;
    let page_count = doc
        .page_count()
        .map_err(|e| anyhow::anyhow!("pdf_oxide page_count: {e}"))?;

    let mut text = String::new();
    for i in 0..page_count {
        let page_text = doc
            .extract_text(i)
            .map_err(|e| anyhow::anyhow!("pdf_oxide page {i}: {e}"))?;
        if !text.is_empty() && !page_text.is_empty() {
            text.push('\n');
        }
        text.push_str(&page_text);
    }
    Ok(text)
}

fn pdf_oxide_extract_markdown(path: &Path) -> Result<String> {
    let mut doc = pdf_oxide::PdfDocument::open(path).map_err(|e| anyhow::anyhow!("pdf_oxide open: {e}"))?;
    let options = pdf_oxide::converters::ConversionOptions {
        include_images: false,
        embed_images: false,
        ..Default::default()
    };
    let markdown = doc
        .to_markdown_all(&options)
        .map_err(|e| anyhow::anyhow!("pdf_oxide markdown: {e}"))?;
    Ok(markdown)
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

fn word_set(text: &str) -> HashSet<String> {
    text.split_whitespace().map(|w| w.to_lowercase()).collect()
}

fn jaccard_similarity(a: &HashSet<String>, b: &HashSet<String>) -> f64 {
    if a.is_empty() && b.is_empty() {
        return 1.0;
    }
    let intersection = a.intersection(b).count();
    let union = a.union(b).count();
    if union == 0 {
        0.0
    } else {
        intersection as f64 / union as f64
    }
}

fn compute_timing_stats(mut durations: Vec<Duration>) -> (Duration, Duration, Duration) {
    durations.sort();
    let n = durations.len();
    let sum: Duration = durations.iter().sum();
    let mean = sum / n as u32;
    let median = durations[n / 2];
    let p95_idx = ((n as f64) * 0.95).ceil() as usize - 1;
    let p95 = durations[p95_idx.min(n - 1)];
    (mean, median, p95)
}

fn fmt_dur(d: Duration) -> String {
    let ms = d.as_secs_f64() * 1000.0;
    if ms < 1.0 {
        format!("{:.0}us", ms * 1000.0)
    } else if ms < 1000.0 {
        format!("{:.2}ms", ms)
    } else {
        format!("{:.2}s", ms / 1000.0)
    }
}

fn count_headings(md: &str) -> usize {
    md.lines().filter(|l| l.starts_with('#')).count()
}

fn count_paragraphs(md: &str) -> usize {
    md.matches("\n\n").count()
}

fn count_tables(md: &str) -> usize {
    md.lines()
        .filter(|l| {
            let t = l.trim();
            t.starts_with('|') && t.contains("---")
        })
        .count()
}

// ---------------------------------------------------------------------------
// Dump mode: extract everything and save to files
// ---------------------------------------------------------------------------

fn run_dump(files: &[PathBuf], output_dir: &str) -> Result<()> {
    std::fs::create_dir_all(output_dir)?;

    println!("\nDumping text + markdown for {} files to {output_dir}/\n", files.len());

    for path in files {
        let stem = path.file_stem().unwrap().to_string_lossy();
        let name = path.file_name().unwrap().to_string_lossy();
        println!("--- {name} ---");

        // Text extraction
        let kreuz_text = kreuzberg_extract_text(path);
        let oxide_text = pdf_oxide_extract_text(path);

        match (&kreuz_text, &oxide_text) {
            (Ok(kt), Ok(ot)) => {
                std::fs::write(format!("{output_dir}/{stem}_kreuzberg.txt"), kt)?;
                std::fs::write(format!("{output_dir}/{stem}_pdf_oxide.txt"), ot)?;

                let kw = word_set(kt);
                let ow = word_set(ot);
                let j = jaccard_similarity(&kw, &ow);
                println!(
                    "  text: kreuzberg={} chars/{} words, pdf_oxide={} chars/{} words, jaccard={:.1}%",
                    kt.len(),
                    kw.len(),
                    ot.len(),
                    ow.len(),
                    j * 100.0
                );
            }
            (Err(e), Ok(ot)) => {
                std::fs::write(format!("{output_dir}/{stem}_pdf_oxide.txt"), ot)?;
                println!("  text: kreuzberg FAILED ({e}), pdf_oxide={} chars", ot.len());
            }
            (Ok(kt), Err(e)) => {
                std::fs::write(format!("{output_dir}/{stem}_kreuzberg.txt"), kt)?;
                println!("  text: kreuzberg={} chars, pdf_oxide FAILED ({e})", kt.len());
            }
            (Err(ek), Err(eo)) => {
                println!("  text: BOTH FAILED (kreuzberg: {ek}, pdf_oxide: {eo})");
            }
        }

        // Markdown extraction
        let kreuz_md = kreuzberg_extract_markdown(path);
        let oxide_md = pdf_oxide_extract_markdown(path);

        match (&kreuz_md, &oxide_md) {
            (Ok(km), Ok(om)) => {
                std::fs::write(format!("{output_dir}/{stem}_kreuzberg.md"), km)?;
                std::fs::write(format!("{output_dir}/{stem}_pdf_oxide.md"), om)?;
                println!(
                    "  markdown: kreuzberg={} chars ({}h/{}p/{}t), pdf_oxide={} chars ({}h/{}p/{}t)",
                    km.len(),
                    count_headings(km),
                    count_paragraphs(km),
                    count_tables(km),
                    om.len(),
                    count_headings(om),
                    count_paragraphs(om),
                    count_tables(om),
                );
            }
            (Err(e), Ok(om)) => {
                std::fs::write(format!("{output_dir}/{stem}_pdf_oxide.md"), om)?;
                println!("  markdown: kreuzberg FAILED ({e}), pdf_oxide={} chars", om.len());
            }
            (Ok(km), Err(e)) => {
                std::fs::write(format!("{output_dir}/{stem}_kreuzberg.md"), km)?;
                println!("  markdown: kreuzberg={} chars, pdf_oxide FAILED ({e})", km.len());
            }
            (Err(ek), Err(eo)) => {
                println!("  markdown: BOTH FAILED (kreuzberg: {ek}, pdf_oxide: {eo})");
            }
        }
    }

    println!("\nAll outputs written to {output_dir}/");
    Ok(())
}

// ---------------------------------------------------------------------------
// Speed benchmark
// ---------------------------------------------------------------------------

struct SpeedResult {
    kreuz_mean: Option<Duration>,
    oxide_mean: Option<Duration>,
}

fn run_speed(files: &[PathBuf], iterations: usize) -> Result<Vec<SpeedResult>> {
    println!("\n{}", "=".repeat(110));
    println!("  SPEED BENCHMARK ({iterations} iterations, release mode)");
    println!("{}", "=".repeat(110));
    println!(
        "\n{:<45} {:>12} {:>12} {:>12} {:>12} {:>10}",
        "File", "K-mean", "K-p95", "O-mean", "O-p95", "Speedup"
    );
    println!("{}", "-".repeat(110));

    let mut results = Vec::new();

    for path in files {
        let name = path.file_name().unwrap().to_string_lossy();
        let display = if name.len() > 43 {
            format!("{}...", &name[..40])
        } else {
            name.to_string()
        };

        // Warmup (2 runs each)
        for _ in 0..2 {
            let _ = kreuzberg_extract_text(path);
            let _ = pdf_oxide_extract_text(path);
        }

        // Benchmark kreuzberg
        let mut kreuz_times = Vec::with_capacity(iterations);
        for _ in 0..iterations {
            let start = Instant::now();
            if kreuzberg_extract_text(path).is_ok() {
                kreuz_times.push(start.elapsed());
            }
        }

        // Benchmark pdf_oxide
        let mut oxide_times = Vec::with_capacity(iterations);
        for _ in 0..iterations {
            let start = Instant::now();
            if pdf_oxide_extract_text(path).is_ok() {
                oxide_times.push(start.elapsed());
            }
        }

        let kreuz_stats = if kreuz_times.len() >= 3 {
            Some(compute_timing_stats(kreuz_times))
        } else {
            None
        };
        let oxide_stats = if oxide_times.len() >= 3 {
            Some(compute_timing_stats(oxide_times))
        } else {
            None
        };

        match (&kreuz_stats, &oxide_stats) {
            (Some((km, _, kp)), Some((om, _, op))) => {
                let speedup = km.as_secs_f64() / om.as_secs_f64();
                println!(
                    "{:<45} {:>12} {:>12} {:>12} {:>12} {:>9.1}x",
                    display,
                    fmt_dur(*km),
                    fmt_dur(*kp),
                    fmt_dur(*om),
                    fmt_dur(*op),
                    speedup
                );
            }
            _ => {
                println!("{:<45} {:>12} {:>12}", display, "---", "---");
            }
        }

        results.push(SpeedResult {
            kreuz_mean: kreuz_stats.map(|s| s.0),
            oxide_mean: oxide_stats.map(|s| s.0),
        });
    }

    // Summary
    let (total_k, total_o, n) = results
        .iter()
        .fold((Duration::ZERO, Duration::ZERO, 0u32), |(tk, to, n), r| {
            match (r.kreuz_mean, r.oxide_mean) {
                (Some(k), Some(o)) => (tk + k, to + o, n + 1),
                _ => (tk, to, n),
            }
        });

    println!("{}", "-".repeat(110));
    if n > 0 {
        println!(
            "Aggregate: kreuzberg avg={}, pdf_oxide avg={}, speedup={:.1}x ({} files)",
            fmt_dur(total_k / n),
            fmt_dur(total_o / n),
            total_k.as_secs_f64() / total_o.as_secs_f64(),
            n
        );
    }

    Ok(results)
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

fn main() -> Result<()> {
    let cli = Cli::parse();
    let pdf_dir = test_documents_dir();

    if !pdf_dir.exists() {
        anyhow::bail!("test_documents/pdf/ not found at {}", pdf_dir.display());
    }

    let files = curated_files(&pdf_dir);
    println!("Using {} curated PDF files from {}", files.len(), pdf_dir.display());

    match cli.mode.as_str() {
        "dump" => run_dump(&files, &cli.output_dir)?,
        "speed" => {
            run_speed(&files, cli.iterations)?;
        }
        "all" => {
            run_dump(&files, &cli.output_dir)?;
            run_speed(&files, cli.iterations)?;
        }
        other => anyhow::bail!("Unknown mode: {other}. Use dump, speed, or all"),
    }

    Ok(())
}
