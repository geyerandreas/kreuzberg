use std::time::Instant;

#[test]
fn test_engine_smoke() {
    println!("Loading engine...");
    let t = Instant::now();
    let mut engine = kreuzberg_layout::LayoutEngine::from_preset(kreuzberg_layout::LayoutPreset::Fast)
        .expect("engine creation failed");
    println!("Engine loaded in {:.1}ms", t.elapsed().as_secs_f64() * 1000.0);

    println!("Creating 640x640 test image...");
    let img = image::RgbImage::new(640, 640);

    println!("Running inference...");
    let t = Instant::now();
    match engine.detect(&img) {
        Ok(result) => println!(
            "Inference OK in {:.1}ms, {} detections",
            t.elapsed().as_secs_f64() * 1000.0,
            result.detections.len()
        ),
        Err(e) => panic!("Inference FAILED in {:.1}ms: {}", t.elapsed().as_secs_f64() * 1000.0, e),
    }
}
