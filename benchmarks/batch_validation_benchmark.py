import json
import time
from pathlib import Path
from typing import Any

from kreuzberg import extract_file_sync
from kreuzberg._types import ExtractionConfig


def benchmark_real_world_scenario(file_paths: list[Path], scenario_name: str) -> dict[str, Any]:
    config = ExtractionConfig(use_cache=False)

    start = time.perf_counter()
    results = []
    for path in file_paths:
        result = extract_file_sync(path, config=config)
        results.append(len(result.content))

    duration = time.perf_counter() - start

    return {
        "scenario": scenario_name,
        "file_count": len(file_paths),
        "duration": duration,
        "per_file": duration / len(file_paths),
        "total_chars": sum(results),
    }


def main() -> None:
    test_dir = Path("/Users/naamanhirschfeld/workspace/kreuzberg/tests/test_source_files")

    scenarios = []

    mixed_files = []
    for ext in ["*.pdf", "*.docx", "*.xlsx", "*.pptx"]:
        mixed_files.extend(list(test_dir.glob(ext))[:2])
    if mixed_files:
        result = benchmark_real_world_scenario(mixed_files, "Mixed Office Documents")
        scenarios.append(result)

    image_files = []
    for ext in ["*.png", "*.jpg", "*.jpeg"]:
        image_files.extend(list(test_dir.glob(ext))[:3])
    if image_files:
        result = benchmark_real_world_scenario(image_files, "Image Batch Processing")
        scenarios.append(result)

    pdf_files = list(test_dir.glob("*.pdf"))[:5]
    if pdf_files:
        result = benchmark_real_world_scenario(pdf_files, "PDF Document Processing")
        scenarios.append(result)

    small_files = []
    for ext in ["*.txt", "*.md", "*.html"]:
        small_files.extend(list(test_dir.glob(ext))[:3])
    if small_files:
        result = benchmark_real_world_scenario(small_files, "Small Text Files")
        scenarios.append(result)

    total_files = sum(s["file_count"] for s in scenarios)
    total_time = sum(s["duration"] for s in scenarios)
    total_chars = sum(s["total_chars"] for s in scenarios)

    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenarios": scenarios,
        "summary": {
            "total_files": total_files,
            "total_time": total_time,
            "avg_per_file": total_time / total_files if total_files > 0 else 0,
            "total_chars": total_chars,
            "throughput": total_chars / total_time if total_time > 0 else 0,
        },
    }

    output_file = Path("results/final_batch_validation.json")
    with output_file.open("w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
