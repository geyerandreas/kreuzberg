//! Example demonstrating HTML report generation from profiling data
//!
//! This example shows how to create and generate comprehensive profiling reports
//! with hotspot analysis and recommendations.
//!
//! Run with: cargo run --example profile_report_demo --features profiling

use benchmark_harness::profile_report::{Hotspot, ProfileReport};
use std::time::Duration;

fn main() {
    // Create a sample profiling report
    let mut report = ProfileReport {
        sample_count: 2500,
        duration: Duration::from_millis(2500),
        effective_frequency: 1000.0,
        top_hotspots: vec![
            Hotspot {
                function_name: "extract_text_from_pdf".to_string(),
                samples: 875,
                percentage: 35.0,
                file_location: Some("crates/kreuzberg/src/pdf/text.rs:156".to_string()),
            },
            Hotspot {
                function_name: "parse_pdf_objects".to_string(),
                samples: 625,
                percentage: 25.0,
                file_location: Some("crates/kreuzberg/src/pdf/parser.rs:89".to_string()),
            },
            Hotspot {
                function_name: "decompress_stream_data".to_string(),
                samples: 375,
                percentage: 15.0,
                file_location: Some("crates/kreuzberg/src/pdf/compression.rs:201".to_string()),
            },
            Hotspot {
                function_name: "apply_text_transformations".to_string(),
                samples: 250,
                percentage: 10.0,
                file_location: Some("crates/kreuzberg/src/text/transform.rs:312".to_string()),
            },
            Hotspot {
                function_name: "validate_character_encoding".to_string(),
                samples: 200,
                percentage: 8.0,
                file_location: Some("crates/kreuzberg/src/text/encoding.rs:45".to_string()),
            },
            Hotspot {
                function_name: "compute_layout_metrics".to_string(),
                samples: 150,
                percentage: 6.0,
                file_location: Some("crates/kreuzberg/src/core/layout.rs:178".to_string()),
            },
            Hotspot {
                function_name: "allocate_memory_pool".to_string(),
                samples: 25,
                percentage: 1.0,
                file_location: Some("crates/kreuzberg/src/utils/memory.rs:92".to_string()),
            },
        ],
        memory_trajectory: vec![],
        recommendations: vec![
            "Excellent sample count (2500): Profile has high statistical confidence. Hotspot percentages are reliable for optimization decisions.".to_string(),
            "Kreuzberg profile analysis: Focus on PDF parsing (pdf module) and text extraction (text module) hotspots.".to_string(),
            "Key finding: extract_text_from_pdf is consuming 35% of samples. Consider optimizing PDF content stream parsing or text layout calculations.".to_string(),
            "Opportunity: The top 3 functions (extract_text, parse_pdf_objects, decompress_stream) account for 75% of CPU time. Targeting these will have high impact.".to_string(),
            "Memory efficient: Character encoding validation and memory allocation are minimal hotspots (<10%), suggesting good memory performance.".to_string(),
        ],
    };

    // Generate HTML report
    let html = report.generate_html();

    // Write to file
    let output_path = "target/profile_report_example.html";
    std::fs::write(output_path, &html).expect("Failed to write HTML report");

    println!("Profile report generated: {}", output_path);
    println!("\nReport Summary:");
    println!("- Samples collected: {}", report.sample_count);
    println!("- Duration: {:?}", report.duration);
    println!("- Effective frequency: {:.1} Hz", report.effective_frequency);
    println!(
        "- Quality: {}",
        if report.sample_count >= 1000 {
            "Excellent"
        } else {
            "Good"
        }
    );
    println!("\nTop hotspots:");
    for (idx, hotspot) in report.top_hotspots.iter().take(3).enumerate() {
        println!("  {}. {} ({:.1}%)", idx + 1, hotspot.function_name, hotspot.percentage);
    }
    println!("\nRecommendations:");
    for rec in &report.recommendations {
        println!("  - {}", rec);
    }
    println!("\nOpen {} in a web browser to view the interactive report", output_path);
}
