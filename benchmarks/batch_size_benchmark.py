import json
import shutil
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from kreuzberg import extract_file_sync
from kreuzberg._ocr._tesseract import _process_image_with_tesseract
from kreuzberg._types import ExtractionConfig
from kreuzberg._utils._process_pool import get_optimal_worker_count, process_pool


def create_test_images(sizes: list[tuple[int, int]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(exist_ok=True)
    image_paths = []

    for i, (width, height) in enumerate(sizes):
        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)

        for y in range(0, height, 50):
            for x in range(0, width, 100):
                draw.text((x, y), f"Test {i}", fill="black")

        path = output_dir / f"test_{width}x{height}_{i}.png"
        img.save(path)
        image_paths.append(path)

    return image_paths


def benchmark_batch_fixed_workers(images: list[Path], num_workers: int) -> dict[str, Any]:
    start = time.perf_counter()
    config_dict = {"language": "eng", "psm": 3}

    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        futures = [pool.submit(_process_image_with_tesseract, str(p), config_dict) for p in images]
        [f.result() for f in futures]

    duration = time.perf_counter() - start
    return {
        "strategy": "fixed",
        "workers": num_workers,
        "batch_size": len(images),
        "duration": duration,
        "per_image": duration / len(images) if images else 0,
    }


def benchmark_batch_dynamic_workers(images: list[Path]) -> dict[str, Any]:
    start = time.perf_counter()
    config_dict = {"language": "eng", "psm": 3}

    optimal_workers = get_optimal_worker_count(len(images), cpu_intensive=True)

    with ProcessPoolExecutor(max_workers=optimal_workers) as pool:
        futures = [pool.submit(_process_image_with_tesseract, str(p), config_dict) for p in images]
        [f.result() for f in futures]

    duration = time.perf_counter() - start
    return {
        "strategy": "dynamic",
        "workers": optimal_workers,
        "batch_size": len(images),
        "duration": duration,
        "per_image": duration / len(images) if images else 0,
    }


def benchmark_batch_shared_pool(images: list[Path]) -> dict[str, Any]:
    start = time.perf_counter()
    config_dict = {"language": "eng", "psm": 3}

    with process_pool() as pool:
        futures = [pool.submit(_process_image_with_tesseract, str(p), config_dict) for p in images]
        [f.result() for f in futures]

    duration = time.perf_counter() - start
    return {
        "strategy": "shared_pool",
        "workers": 14,
        "batch_size": len(images),
        "duration": duration,
        "per_image": duration / len(images) if images else 0,
    }


def benchmark_extraction_api(images: list[Path]) -> dict[str, Any]:
    start = time.perf_counter()

    config = ExtractionConfig(use_cache=False, force_ocr=True)

    for image_path in images:
        extract_file_sync(image_path, config=config)

    duration = time.perf_counter() - start
    return {
        "strategy": "extraction_api",
        "workers": "auto",
        "batch_size": len(images),
        "duration": duration,
        "per_image": duration / len(images) if images else 0,
    }


def main() -> None:
    batch_sizes = [1, 2, 5, 10, 20]
    image_sizes = [
        (640, 480),
        (1024, 768),
        (1920, 1080),
    ]

    test_dir = Path(tempfile.mkdtemp(prefix="kreuzberg_bench_"))

    results = []

    for img_width, img_height in image_sizes:
        max_batch = max(batch_sizes)
        images = create_test_images([(img_width, img_height)] * max_batch, test_dir)

        for batch_size in batch_sizes:
            batch = images[:batch_size]

            strategies = []

            fixed_result = benchmark_batch_fixed_workers(batch, 14)
            strategies.append(fixed_result)

            dynamic_result = benchmark_batch_dynamic_workers(batch)
            strategies.append(dynamic_result)

            shared_result = benchmark_batch_shared_pool(batch)
            strategies.append(shared_result)

            if batch_size <= 10:
                api_result = benchmark_extraction_api(batch)
                strategies.append(api_result)

            baseline = fixed_result["duration"]
            if baseline > 0:
                for strategy in strategies[1:]:
                    improvement = ((baseline - strategy["duration"]) / baseline) * 100
                    strategy["improvement_pct"] = improvement

            result_entry = {
                "image_size": f"{img_width}x{img_height}",
                "batch_size": batch_size,
                "strategies": strategies,
            }
            results.append(result_entry)

    output_file = Path("results/batch_size_benchmarks.json")
    output_file.parent.mkdir(exist_ok=True)

    with output_file.open("w") as f:
        json.dump({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "results": results}, f, indent=2)

    for img_size in image_sizes:
        size_str = f"{img_size[0]}x{img_size[1]}"

        size_results = [r for r in results if r["image_size"] == size_str]
        for result in size_results:
            batch_size = result["batch_size"]  # type: ignore[assignment]
            strategies = result["strategies"]  # type: ignore[assignment]

            dynamic = next((s for s in strategies if s["strategy"] == "dynamic"), None)
            if dynamic and "improvement_pct" in dynamic:
                pass

    shutil.rmtree(test_dir)


if __name__ == "__main__":
    main()
