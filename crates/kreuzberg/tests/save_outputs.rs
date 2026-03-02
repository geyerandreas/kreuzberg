#![cfg(all(feature = "pdf", feature = "layout-detection"))]
mod helpers;
use helpers::*;

#[test]
fn save_extraction_outputs() {
    if !test_documents_available() {
        return;
    }
    let pdf_path = get_test_file_path("pdf/docling.pdf");

    // Baseline
    let config_base = kreuzberg::ExtractionConfig {
        output_format: kreuzberg::core::config::OutputFormat::Markdown,
        ..Default::default()
    };
    let result_base = kreuzberg::extract_file_sync(&pdf_path, None, &config_base).expect("base");
    std::fs::write("/tmp/kreuzberg_baseline.md", &result_base.content).expect("write");
    eprintln!("Baseline: {} chars", result_base.content.len());

    // With layout
    let config_layout = kreuzberg::ExtractionConfig {
        output_format: kreuzberg::core::config::OutputFormat::Markdown,
        layout: Some(kreuzberg::core::config::layout::LayoutDetectionConfig {
            preset: "fast".to_string(),
            ..Default::default()
        }),
        ..Default::default()
    };
    let result_layout = kreuzberg::extract_file_sync(&pdf_path, None, &config_layout).expect("layout");
    std::fs::write("/tmp/kreuzberg_layout.md", &result_layout.content).expect("write");
    eprintln!("Layout: {} chars", result_layout.content.len());
}
