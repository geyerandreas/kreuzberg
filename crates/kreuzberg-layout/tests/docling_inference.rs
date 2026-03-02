use std::time::Instant;

#[test]
fn test_docling_pdf_inference() {
    let _pdf_path = std::env::var("TEST_PDF").unwrap_or_else(|_| "../../test_documents/pdf/docling.pdf".to_string());

    // Read PDF and render page 1 using image crate (not pdfium)
    // We need to test just the ML inference, not pdfium rendering
    // Let's create a simple white image and see what the model detects
    println!("Loading engine...");
    let t = Instant::now();
    let mut engine = kreuzberg_layout::LayoutEngine::from_preset(kreuzberg_layout::LayoutPreset::Fast)
        .expect("engine creation failed");
    println!("Engine loaded in {:.1}ms", t.elapsed().as_secs_f64() * 1000.0);

    // Create a simple test image with some text-like patterns
    let img = image::RgbImage::new(640, 640);

    let t = Instant::now();
    let result = engine.detect(&img).expect("inference");
    println!(
        "Blank image: {:.1}ms, {} detections",
        t.elapsed().as_secs_f64() * 1000.0,
        result.detections.len()
    );

    for det in &result.detections {
        println!(
            "  {:?} conf={:.3} bbox=({:.0},{:.0},{:.0},{:.0})",
            det.class, det.confidence, det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2
        );
    }
}
