//! Multi-model evaluation benchmarks for layout detection.
//!
//! Downloads ONNX models from HuggingFace and measures:
//!   1. Cold-start latency (first model load)
//!   2. Hot inference latency (per-image, model already loaded)
//!   3. Detection quality (what layout elements are found)
//!
//! Run with: cargo test --release -p kreuzberg-docling-layout --test evaluation -- --nocapture

use std::path::PathBuf;
use std::time::{Duration, Instant};

use kreuzberg_docling_layout::{
    Detectron2Model, Detectron2Variant, LayoutDetection, LayoutModel, RtDetrModel, YoloModel, YoloVariant,
};

/// ORT discovery — mirrors kreuzberg's ort_discovery.rs pattern.
fn discover_ort() {
    if let Ok(path) = std::env::var("ORT_DYLIB_PATH")
        && std::path::Path::new(&path).exists()
    {
        return;
    }

    #[cfg(target_os = "macos")]
    let candidates = &[
        "/opt/homebrew/lib/libonnxruntime.dylib",
        "/usr/local/lib/libonnxruntime.dylib",
    ];
    #[cfg(target_os = "linux")]
    let candidates = &[
        "/usr/lib/libonnxruntime.so",
        "/usr/local/lib/libonnxruntime.so",
        "/usr/lib/x86_64-linux-gnu/libonnxruntime.so",
        "/usr/lib/aarch64-linux-gnu/libonnxruntime.so",
    ];
    #[cfg(not(any(target_os = "macos", target_os = "linux")))]
    let candidates: &[&str] = &[];

    for path in candidates {
        if std::path::Path::new(path).exists() {
            unsafe {
                std::env::set_var("ORT_DYLIB_PATH", path);
            }
            eprintln!("[ort] Auto-discovered ONNX Runtime at {path}");
            return;
        }
    }

    panic!("ONNX Runtime not found. Install it or set ORT_DYLIB_PATH.");
}

/// Download a model from HuggingFace.
fn download_hf_model(repo_id: &str, filename: &str) -> PathBuf {
    let api = hf_hub::api::sync::ApiBuilder::new()
        .with_progress(true)
        .build()
        .expect("Failed to build HuggingFace API");

    let repo = api.model(repo_id.to_string());
    repo.get(filename)
        .unwrap_or_else(|e| panic!("Failed to download {filename} from {repo_id}: {e}"))
}

/// Try downloading with multiple candidate filenames.
fn try_download_hf_model(repo_id: &str, filenames: &[&str]) -> Result<PathBuf, String> {
    for filename in filenames {
        let api = hf_hub::api::sync::ApiBuilder::new()
            .with_progress(true)
            .build()
            .map_err(|e| format!("HF API error: {e}"))?;
        let repo = api.model(repo_id.to_string());
        match repo.get(filename) {
            Ok(path) => {
                println!("  Downloaded: {filename}");
                return Ok(path);
            }
            Err(_) => continue,
        }
    }
    Err(format!("Could not download any ONNX file from {repo_id}"))
}

/// Load the test image(s).
fn load_test_image() -> image::RgbImage {
    let test_image_path =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../test_documents/images/complex_document.png");

    match image::open(&test_image_path) {
        Ok(img) => img.to_rgb8(),
        Err(_) => {
            eprintln!("  (test image not found, using synthetic image)");
            let mut img = image::RgbImage::new(800, 1100);
            for pixel in img.pixels_mut() {
                *pixel = image::Rgb([255, 255, 255]);
            }
            // Draw dark rectangles to simulate text blocks.
            for y in 50..80 {
                for x in 100..700 {
                    img.put_pixel(x, y, image::Rgb([0, 0, 0]));
                }
            }
            for y in 100..300 {
                for x in 50..750 {
                    if y % 15 < 10 {
                        img.put_pixel(x, y, image::Rgb([30, 30, 30]));
                    }
                }
            }
            img
        }
    }
}

fn print_detections(detections: &[LayoutDetection]) {
    println!("  Detections ({} total):", detections.len());
    for det in detections {
        println!("    {det}");
    }
}

struct BenchmarkResult {
    name: String,
    cold_start: Duration,
    warmup: Duration,
    hot_avg: Duration,
    hot_min: Duration,
    hot_max: Duration,
    hot_p50: Duration,
    hot_p95: Duration,
    num_detections: usize,
    avg_confidence: f32,
}

fn benchmark_model(
    model: &mut dyn LayoutModel,
    img: &image::RgbImage,
    cold_start: Duration,
    n_runs: usize,
) -> BenchmarkResult {
    let name = model.name().to_string();

    // Warm-up run.
    let warmup_start = Instant::now();
    let warmup_results = model.detect(img).expect("Warm-up inference failed");
    let warmup = warmup_start.elapsed();

    println!("\n  [{name}] Warm-up: {warmup:?} ({} detections)", warmup_results.len());
    print_detections(&warmup_results);

    // Hot inference benchmark.
    let mut times = Vec::with_capacity(n_runs);
    for _ in 0..n_runs {
        let start = Instant::now();
        let _results = model.detect(img).expect("Inference failed");
        times.push(start.elapsed());
    }
    times.sort();

    let total: Duration = times.iter().sum();
    let hot_avg = total / n_runs as u32;
    let hot_min = times[0];
    let hot_max = times[n_runs - 1];
    let hot_p50 = times[n_runs / 2];
    let hot_p95 = times[(n_runs as f64 * 0.95) as usize];

    let num_detections = warmup_results.len();
    let avg_confidence = if num_detections > 0 {
        warmup_results.iter().map(|d| d.confidence).sum::<f32>() / num_detections as f32
    } else {
        0.0
    };

    println!("\n  [{name}] Hot inference ({n_runs} runs):");
    println!("    avg={hot_avg:?}  min={hot_min:?}  max={hot_max:?}  p50={hot_p50:?}  p95={hot_p95:?}");

    BenchmarkResult {
        name,
        cold_start,
        warmup,
        hot_avg,
        hot_min,
        hot_max,
        hot_p50,
        hot_p95,
        num_detections,
        avg_confidence,
    }
}

fn print_comparison_table(results: &[BenchmarkResult]) {
    println!("\n{}", "=".repeat(130));
    println!("  COMPARISON TABLE");
    println!("{}", "=".repeat(130));
    println!(
        "  {:<35} {:>12} {:>12} {:>12} {:>12} {:>12} {:>8} {:>8}",
        "Model", "Cold Start", "Hot Avg", "Hot Min", "Hot P50", "Hot P95", "Dets", "AvgConf"
    );
    println!("  {}", "-".repeat(120));
    for r in results {
        println!(
            "  {:<35} {:>12?} {:>12?} {:>12?} {:>12?} {:>12?} {:>8} {:>8.3}",
            r.name, r.cold_start, r.hot_avg, r.hot_min, r.hot_p50, r.hot_p95, r.num_detections, r.avg_confidence,
        );
    }
    println!("{}", "=".repeat(130));
}

#[test]
fn evaluate_all_models() {
    discover_ort();

    println!("\n{}", "=".repeat(80));
    println!("  Multi-Model Layout Detection Evaluation (5 models)");
    println!("{}", "=".repeat(80));

    let img = load_test_image();
    println!("\n  Test image: {}x{}", img.width(), img.height());

    let n_runs = 20;
    let mut results = Vec::new();

    // ── Model 1: Docling RT-DETR v2 ─────────────────────────────────────
    println!("\n{}", "-".repeat(80));
    println!("  [1] Docling RT-DETR v2 (docling-project/docling-layout-heron-onnx)");
    println!("{}", "-".repeat(80));

    let model_path = download_hf_model("docling-project/docling-layout-heron-onnx", "model.onnx");
    println!("  Model path: {}", model_path.display());

    let cold_start = Instant::now();
    let mut rtdetr = RtDetrModel::from_file(model_path.to_str().unwrap()).expect("Failed to load RT-DETR model");
    let cold_time = cold_start.elapsed();
    println!("  Cold start: {cold_time:?}");

    results.push(benchmark_model(&mut rtdetr, &img, cold_time, n_runs));

    // ── Model 2: YOLOv10m DocLayNet ─────────────────────────────────────
    println!("\n{}", "-".repeat(80));
    println!("  [2] YOLOv10m DocLayNet (Oblix/yolov10m-doclaynet_ONNX_document-layout-analysis)");
    println!("{}", "-".repeat(80));

    match try_download_and_benchmark_yolo(
        "Oblix/yolov10m-doclaynet_ONNX_document-layout-analysis",
        &["model.onnx", "model_quantized.onnx", "onnx/model.onnx"],
        YoloVariant::DocLayNet,
        640,
        640,
        "YOLOv10m DocLayNet",
        &img,
        n_runs,
    ) {
        Ok(result) => results.push(result),
        Err(e) => println!("  SKIPPED: {e}"),
    }

    // ── Model 3: DocLayout-YOLO DocStructBench ──────────────────────────
    println!("\n{}", "-".repeat(80));
    println!("  [3] DocLayout-YOLO DocStructBench (wybxc/DocLayout-YOLO-DocStructBench-onnx)");
    println!("{}", "-".repeat(80));

    match try_download_and_benchmark_yolo(
        "wybxc/DocLayout-YOLO-DocStructBench-onnx",
        &["doclayout_yolo_docstructbench_imgsz1024.onnx", "model.onnx"],
        YoloVariant::DocStructBench,
        1024,
        1024,
        "DocLayout-YOLO DSB",
        &img,
        n_runs,
    ) {
        Ok(result) => results.push(result),
        Err(e) => println!("  SKIPPED: {e}"),
    }

    // ── Model 4: Detectron2 Faster R-CNN (unstructuredio) ────────────────
    println!("\n{}", "-".repeat(80));
    println!("  [4] Detectron2 Faster R-CNN (unstructuredio/detectron2_faster_rcnn_R_50_FPN_3x)");
    println!("{}", "-".repeat(80));

    match try_download_and_benchmark_detectron2(
        "unstructuredio/detectron2_faster_rcnn_R_50_FPN_3x",
        &["model.onnx"],
        Detectron2Variant::FasterRcnn,
        "Detectron2 Faster R-CNN",
        &img,
        n_runs,
    ) {
        Ok(result) => results.push(result),
        Err(e) => println!("  SKIPPED: {e}"),
    }

    // ── Model 5: YOLOX Large (unstructuredio) ────────────────────────────
    println!("\n{}", "-".repeat(80));
    println!("  [5] YOLOX Large (unstructuredio/yolo_x_layout)");
    println!("{}", "-".repeat(80));

    match try_download_and_benchmark_yolo(
        "unstructuredio/yolo_x_layout",
        &["yolox_l0.05.onnx"],
        YoloVariant::Yolox,
        768,  // width
        1024, // height
        "YOLOX Large",
        &img,
        n_runs,
    ) {
        Ok(result) => results.push(result),
        Err(e) => println!("  SKIPPED: {e}"),
    }

    // ── Comparison ──────────────────────────────────────────────────────
    print_comparison_table(&results);

    // ── Multi-image quality comparison ──────────────────────────────────
    println!("\n  Multi-image quality comparison:");
    let image_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../test_documents/images");
    if image_dir.exists() {
        for entry in std::fs::read_dir(&image_dir).unwrap() {
            let entry = entry.unwrap();
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) == Some("png") {
                let test_img = match image::open(&path) {
                    Ok(img) => img.to_rgb8(),
                    Err(_) => continue,
                };
                println!(
                    "\n  --- {} ({}x{}) ---",
                    path.file_name().unwrap().to_string_lossy(),
                    test_img.width(),
                    test_img.height(),
                );
                let dets = rtdetr.detect(&test_img).expect("RT-DETR inference failed");
                println!("  RT-DETR: {} detections", dets.len());
                print_detections(&dets);
            }
        }
    }
}

fn try_download_and_benchmark_yolo(
    repo_id: &str,
    filenames: &[&str],
    variant: YoloVariant,
    input_width: u32,
    input_height: u32,
    model_name: &str,
    img: &image::RgbImage,
    n_runs: usize,
) -> Result<BenchmarkResult, String> {
    let model_path = try_download_hf_model(repo_id, filenames)?;
    println!("  Model path: {}", model_path.display());

    let cold_start = Instant::now();
    let mut model = YoloModel::from_file(
        model_path.to_str().unwrap(),
        variant,
        input_width,
        input_height,
        model_name,
    )
    .map_err(|e| format!("Failed to load model: {e}"))?;
    let cold_time = cold_start.elapsed();
    println!("  Cold start: {cold_time:?}");

    Ok(benchmark_model(&mut model, img, cold_time, n_runs))
}

fn try_download_and_benchmark_detectron2(
    repo_id: &str,
    filenames: &[&str],
    variant: Detectron2Variant,
    model_name: &str,
    img: &image::RgbImage,
    n_runs: usize,
) -> Result<BenchmarkResult, String> {
    let model_path = try_download_hf_model(repo_id, filenames)?;
    println!("  Model path: {}", model_path.display());

    let cold_start = Instant::now();
    let mut model = Detectron2Model::from_file(model_path.to_str().unwrap(), variant, model_name)
        .map_err(|e| format!("Failed to load model: {e}"))?;
    let cold_time = cold_start.elapsed();
    println!("  Cold start: {cold_time:?}");

    Ok(benchmark_model(&mut model, img, cold_time, n_runs))
}
