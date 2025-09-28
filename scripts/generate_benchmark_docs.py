#!/usr/bin/env python3
# /// script
# dependencies = [
#   "msgspec>=0.18.0",
#   "typer>=0.15.0",
#   "rich>=13.0.0",
#   "jinja2>=3.1.0",
# ]
# requires-python = ">=3.11"
# ///

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

console = Console()


def load_aggregated_results(file_path: Path) -> dict[str, Any]:
    """Load aggregated benchmark results from JSON file."""
    with file_path.open("r") as f:
        return json.load(f)  # type: ignore[no-any-return]


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with specified decimal places."""
    return f"{value:.{decimals}f}"


def format_percentage(value: float) -> str:
    """Format a decimal value as a percentage."""
    return f"{value * 100:.1f}%"


def format_memory(value: float) -> str:
    """Format memory value in MB."""
    return f"{value:.1f} MB"


def get_framework_emoji(framework: str) -> str:
    """Get emoji representation for a framework."""
    emojis = {
        "kreuzberg": "🚀",
        "docling": "📄",
        "markitdown": "📝",
        "unstructured": "🔧",
        "extractous": "⚡",
    }
    for key, emoji in emojis.items():
        if key in framework.lower():
            return emoji
    return "📊"


def generate_index_page(data: dict[str, Any], output_dir: Path) -> None:
    """Generate the main benchmark dashboard page."""
    console.print("📊 Generating benchmark dashboard...")

    best_speed = None
    best_memory = None
    best_success = None
    best_quality = None

    for fw_name, summary in data.get("framework_summaries", {}).items():
        summary_data = summary[0] if isinstance(summary, list) and summary else summary

        if not best_speed or summary_data.get("avg_extraction_time", float("inf")) < best_speed[1]:
            best_speed = (fw_name, summary_data.get("avg_extraction_time", 0))

        if not best_memory or summary_data.get("avg_memory_mb", float("inf")) < best_memory[1]:
            best_memory = (fw_name, summary_data.get("avg_memory_mb", 0))

        if not best_success or summary_data.get("success_rate", 0) > best_success[1]:
            best_success = (fw_name, summary_data.get("success_rate", 0))

        if summary_data.get("avg_quality_score") is not None and (
            not best_quality or summary_data.get("avg_quality_score", 0) > best_quality[1]
        ):
            best_quality = (fw_name, summary_data.get("avg_quality_score", 0))

    content = f"""# Kreuzberg Performance Benchmarks

> Last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} | [View Detailed Results →](latest-results.md)

## 🏆 Performance Leaders

| Metric | Winner | Score |
|--------|--------|-------|
| **Speed Champion** | {get_framework_emoji(best_speed[0]) if best_speed else ""} {best_speed[0] if best_speed else "N/A"} | {format_number(best_speed[1]) if best_speed else "N/A"}s avg |
| **Memory Efficient** | {get_framework_emoji(best_memory[0]) if best_memory else ""} {best_memory[0] if best_memory else "N/A"} | {format_memory(best_memory[1]) if best_memory else "N/A"} |
| **Best Success Rate** | {get_framework_emoji(best_success[0]) if best_success else ""} {best_success[0] if best_success else "N/A"} | {format_percentage(best_success[1]) if best_success else "N/A"} |
{"| **Quality Leader** | " + (get_framework_emoji(best_quality[0]) + " " + best_quality[0] + " | " + format_percentage(best_quality[1]) + " |") if best_quality else ""}

## 📊 Latest Benchmark Run

<iframe src="charts/dashboard.html" width="100%" height="850" frameborder="0"></iframe>

## Quick Stats

- **Total Files Tested**: {data.get("total_files_processed", 0):,}
- **Total Benchmark Runs**: {data.get("total_runs", 0):,}
- **Total Time**: {format_number(data.get("total_time_seconds", 0) / 60, 1)} minutes
- **Frameworks Tested**: {len(data.get("framework_summaries", {}))}

## Framework Comparison

| Framework | Success Rate | Avg Time | Avg Memory | Throughput |
|-----------|-------------|----------|------------|------------|
"""

    for fw_name, summary in sorted(data.get("framework_summaries", {}).items()):
        summary_data = summary[0] if isinstance(summary, list) and summary else summary

        fps = summary_data.get("files_per_second", 0)
        if fps == 0 and summary_data.get("total_time_seconds", 0) > 0:
            fps = summary_data.get("total_files", 0) / summary_data.get("total_time_seconds", 1)

        content += f"| {get_framework_emoji(fw_name)} **{fw_name}** | "
        content += f"{format_percentage(summary_data.get('success_rate', 0))} | "
        content += f"{format_number(summary_data.get('avg_extraction_time', 0))}s | "
        content += f"{format_memory(summary_data.get('avg_memory_mb', 0))} | "
        content += f"{format_number(fps, 2)} files/s |\n"

    content += """

## Navigation

- 📈 [**Performance Comparison** →](framework-comparison.md) - Head-to-head framework analysis
- 📊 [**Detailed Results** →](latest-results.md) - Complete benchmark data
- 📉 [**Historical Trends** →](historical-trends.md) - Performance over time
- 🔬 [**Methodology** →](methodology.md) - How we benchmark

## Interactive Charts

- [Performance Comparison](charts/performance_comparison.html)
- [Memory Usage Analysis](charts/memory_usage.html)
- [Throughput Metrics](charts/throughput.html)
- [Category Performance](charts/category_performance.html)
"""

    output_path = output_dir / "index.md"
    output_path.write_text(content)
    console.print(f"  ✅ Generated {output_path}")


def generate_latest_results_page(data: dict[str, Any], output_dir: Path) -> None:
    """Generate detailed results page with comprehensive metrics."""
    console.print("📋 Generating detailed results page...")

    content = f"""# Latest Benchmark Results

> Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}

## Summary Statistics

- **Total Files Processed**: {data.get("total_files_processed", 0):,}
- **Total Benchmark Runs**: {data.get("total_runs", 0):,}
- **Total Time**: {format_number(data.get("total_time_seconds", 0) / 60, 1)} minutes

## Performance by Framework

<iframe src="charts/performance_comparison.html" width="100%" height="550" frameborder="0"></iframe>

### Detailed Metrics

| Framework | Files | Success | Failed | Timeout | Success Rate | Avg Time | P50 Time | P90 Time | P99 Time |
|-----------|-------|---------|--------|---------|--------------|----------|----------|----------|----------|
"""

    for fw_name, summary in sorted(data.get("framework_summaries", {}).items()):
        summary_data = summary[0] if isinstance(summary, list) and summary else summary

        content += f"| **{fw_name}** | "
        content += f"{summary_data.get('total_files', 0)} | "
        content += f"{summary_data.get('successful_extractions', 0)} | "
        content += f"{summary_data.get('failed_extractions', 0)} | "
        content += f"{summary_data.get('timeout_count', 0)} | "
        content += f"{format_percentage(summary_data.get('success_rate', 0))} | "
        content += f"{format_number(summary_data.get('avg_extraction_time', 0))}s | "
        content += f"{format_number(summary_data.get('median_extraction_time', 0))}s | "
        content += f"{format_number(summary_data.get('p90_extraction_time', 0))}s | "
        content += f"{format_number(summary_data.get('p99_extraction_time', 0))}s |\n"

    content += """

## Memory Usage Analysis

<iframe src="charts/memory_usage.html" width="100%" height="550" frameborder="0"></iframe>

### Memory Statistics

| Framework | Avg Memory | Peak Memory | Memory/File |
|-----------|------------|-------------|-------------|
"""

    for fw_name, summary in sorted(data.get("framework_summaries", {}).items()):
        summary_data = summary[0] if isinstance(summary, list) and summary else summary

        mem_per_file = summary_data.get("avg_memory_mb", 0) / max(summary_data.get("total_files", 1), 1)

        content += f"| **{fw_name}** | "
        content += f"{format_memory(summary_data.get('avg_memory_mb', 0))} | "
        content += f"{format_memory(summary_data.get('peak_memory_mb', 0))} | "
        content += f"{format_memory(mem_per_file)} |\n"

    content += """

## Performance by Document Category

<iframe src="charts/category_performance.html" width="100%" height="550" frameborder="0"></iframe>

"""

    if "category_summaries" in data:
        content += "### Category Details\n\n"

        for cat_name, summaries in sorted(data.get("category_summaries", {}).items()):
            content += f"#### {cat_name.replace('_', ' ').title()}\n\n"
            content += "| Framework | Files | Success Rate | Avg Time | Avg Memory |\n"
            content += "|-----------|-------|--------------|----------|------------|\n"

            for summary in summaries:
                content += f"| {summary.get('framework', 'N/A')} | "
                content += f"{summary.get('total_files', 0)} | "
                content += f"{format_percentage(summary.get('success_rate', 0))} | "
                content += f"{format_number(summary.get('avg_extraction_time', 0))}s | "
                content += f"{format_memory(summary.get('avg_memory_mb', 0))} |\n"

            content += "\n"

    content += """

## Failure Analysis

"""

    if data.get("failure_patterns"):
        content += "### Common Failure Patterns\n\n"
        content += "| Error Pattern | Count |\n"
        content += "|---------------|-------|\n"

        for pattern, count in sorted(data["failure_patterns"].items(), key=lambda x: x[1], reverse=True)[:10]:
            content += f"| {pattern[:50]}... | {count} |\n"

    if data.get("timeout_files"):
        content += "\n### Files with Timeouts\n\n"
        content += f"Total timeout files: {len(data['timeout_files'])}\n\n"
        for file in data["timeout_files"][:10]:
            content += f"- {Path(file).name}\n"

    content += """

## Raw Data

- [Download JSON Results](data/latest.json)
- [View All Charts](charts/)
"""

    output_path = output_dir / "latest-results.md"
    output_path.write_text(content)
    console.print(f"  ✅ Generated {output_path}")


def _calculate_score_bounds(data: dict[str, Any]) -> tuple[float, float, float, float]:
    """Calculate min/max bounds for time and memory metrics."""
    min_time = float("inf")
    max_time = 0
    min_mem = float("inf")
    max_mem = 0

    for summary in data.get("framework_summaries", {}).values():
        summary_data = summary[0] if isinstance(summary, list) and summary else summary

        avg_time = summary_data.get("avg_extraction_time", 0)
        avg_mem = summary_data.get("avg_memory_mb", 0)

        if avg_time > 0:
            min_time = min(min_time, avg_time)
            max_time = max(max_time, avg_time)
        if avg_mem > 0:
            min_mem = min(min_mem, avg_mem)
            max_mem = max(max_mem, avg_mem)

    return min_time, max_time, min_mem, max_mem


def _calculate_framework_scores(
    data: dict[str, Any], bounds: tuple[float, float, float, float]
) -> dict[str, dict[str, float]]:
    """Calculate scores for all frameworks."""
    min_time, max_time, min_mem, max_mem = bounds
    scores = {}

    for fw_name, summary in sorted(data.get("framework_summaries", {}).items()):
        summary_data = summary[0] if isinstance(summary, list) and summary else summary

        avg_time = summary_data.get("avg_extraction_time", 0)
        if avg_time > 0 and max_time > min_time:
            speed_score = 100 * (1 - (avg_time - min_time) / (max_time - min_time))
        else:
            speed_score = 50

        avg_mem = summary_data.get("avg_memory_mb", 0)
        if avg_mem > 0 and max_mem > min_mem:
            memory_score = 100 * (1 - (avg_mem - min_mem) / (max_mem - min_mem))
        else:
            memory_score = 50

        quality_score = (summary_data.get("avg_quality_score", 0) * 100) if summary_data.get("avg_quality_score") else 0
        reliability_score = summary_data.get("success_rate", 0) * 100

        overall = speed_score * 0.3 + memory_score * 0.2 + quality_score * 0.3 + reliability_score * 0.2

        scores[fw_name] = {
            "speed": speed_score,
            "memory": memory_score,
            "quality": quality_score,
            "reliability": reliability_score,
            "overall": overall,
        }

    return scores


def _generate_scores_table(scores: dict[str, dict[str, float]]) -> str:
    """Generate the scores comparison table."""
    content = ""
    for fw_name, score_data in sorted(scores.items()):
        content += f"| **{fw_name}** | "
        content += f"{score_data['speed']:.1f} | "
        content += f"{score_data['memory']:.1f} | "
        content += f"{score_data['quality']:.1f} | "
        content += f"{score_data['reliability']:.1f} | "
        content += f"**{score_data['overall']:.1f}** |\n"
    return content


def _generate_strengths_weaknesses(scores: dict[str, dict[str, float]]) -> str:
    """Generate strengths and weaknesses analysis."""
    content = ""
    for fw_name, score_data in sorted(scores.items(), key=lambda x: x[1]["overall"], reverse=True):
        content += f"### {get_framework_emoji(fw_name)} {fw_name}\n\n"

        strengths = []
        weaknesses = []

        if score_data["speed"] > 70:
            strengths.append("Fast extraction")
        elif score_data["speed"] < 40:
            weaknesses.append("Slower extraction")

        if score_data["memory"] > 70:
            strengths.append("Memory efficient")
        elif score_data["memory"] < 40:
            weaknesses.append("High memory usage")

        if score_data["quality"] > 70:
            strengths.append("High quality extraction")
        elif score_data["quality"] < 40:
            weaknesses.append("Lower extraction quality")

        if score_data["reliability"] > 90:
            strengths.append("Very reliable")
        elif score_data["reliability"] < 70:
            weaknesses.append("Lower success rate")

        if strengths:
            content += f"**Strengths**: {', '.join(strengths)}\n\n"
        if weaknesses:
            content += f"**Areas for improvement**: {', '.join(weaknesses)}\n\n"

    return content


def generate_framework_comparison_page(data: dict[str, Any], output_dir: Path) -> None:
    """Generate framework comparison page with scoring analysis."""
    console.print("⚖️ Generating framework comparison page...")

    content = """# Framework Comparison

> Head-to-head comparison of text extraction frameworks

## Performance Overview

<iframe src="charts/dashboard.html" width="100%" height="850" frameborder="0"></iframe>

## Throughput Comparison

<iframe src="charts/throughput.html" width="100%" height="550" frameborder="0"></iframe>

## Scoring Methodology

Each framework is scored on four key metrics:

1. **Speed (30%)** - Average extraction time (lower is better)
2. **Memory (20%)** - Average memory usage (lower is better)
3. **Quality (30%)** - Extraction quality score (higher is better)
4. **Reliability (20%)** - Success rate (higher is better)

### Overall Scores

| Framework | Speed Score | Memory Score | Quality Score | Reliability | **Overall** |
|-----------|-------------|--------------|---------------|-------------|-------------|
"""

    bounds = _calculate_score_bounds(data)
    scores = _calculate_framework_scores(data, bounds)
    content += _generate_scores_table(scores)

    content += """\n
## Strengths & Weaknesses

"""
    content += _generate_strengths_weaknesses(scores)

    content += """

## Recommendations

Based on the benchmark results:

- **For speed-critical applications**: Choose the framework with the highest speed score
- **For memory-constrained environments**: Select the most memory-efficient option
- **For quality-critical extraction**: Prioritize frameworks with high quality scores
- **For production reliability**: Focus on frameworks with >90% success rates

## Additional Resources

- [Detailed Results](latest-results.md)
- [Benchmark Methodology](methodology.md)
- [Raw Data](data/latest.json)
"""

    output_path = output_dir / "framework-comparison.md"
    output_path.write_text(content)
    console.print(f"  ✅ Generated {output_path}")


def generate_methodology_page(output_dir: Path) -> None:
    """Generate benchmark methodology documentation page."""
    console.print("🔬 Generating methodology page...")

    content = """# Benchmark Methodology

## Overview

Our benchmarking process is designed to provide fair, reproducible, and comprehensive performance measurements across all text extraction frameworks.

## Test Environment

### Hardware
- **Platform**: GitHub Actions Ubuntu Latest
- **CPU**: Variable (cloud environment)
- **Memory**: Variable (typically 7GB available)
- **Storage**: SSD

### Software
- **Python**: 3.11+
- **OS**: Ubuntu Linux
- **Dependencies**: Latest stable versions

## Frameworks Tested

| Framework | Version | Description |
|-----------|---------|-------------|
| **kreuzberg** | Latest | High-performance extraction library (this project) |
| **docling** | Latest | IBM's document understanding library |
| **markitdown** | Latest | Microsoft's markdown conversion tool |
| **unstructured** | Latest | Unstructured data processing library |
| **extractous** | Latest | Fast text extraction library |

## Test Corpus

### Document Categories

- **Tiny** (<100KB): Small text files, simple documents
- **Small** (100KB-1MB): Typical documents, reports
- **Medium** (1MB-10MB): Large documents, books
- **Large** (10MB-50MB): Very large documents
- **Huge** (>50MB): Extreme cases

### File Formats

Each framework is tested against its supported formats:
- PDF documents
- Office documents (DOCX, XLSX, PPTX)
- Images (PNG, JPEG, TIFF)
- Web formats (HTML, XML)
- Plain text and markdown
- Specialized formats (EPUB, RTF, etc.)

## Metrics Collected

### Performance Metrics
- **Extraction Time**: Wall-clock time for complete extraction
- **Memory Usage**: Peak RSS during extraction
- **CPU Utilization**: Average processor usage
- **Throughput**: Files processed per second

### Quality Metrics
- **Character Count**: Total extracted characters
- **Word Count**: Total extracted words
- **Quality Score**: Extraction completeness/accuracy (when available)

### Reliability Metrics
- **Success Rate**: Percentage of successful extractions
- **Timeout Rate**: Files exceeding time limit
- **Error Categories**: Types of failures encountered

## Test Execution

### Process
1. **Cache Clearing**: Framework caches cleared before each run
2. **Warm-up**: Initial extraction to eliminate cold-start effects
3. **Multiple Iterations**: Default 3 iterations per file for statistical significance
4. **Isolation**: Each framework tested separately
5. **Timeout Protection**: 300-second timeout per file

### Resource Monitoring
- CPU and memory sampled at 50ms intervals
- Process-level monitoring using psutil
- Subprocess isolation for crash protection

## Statistical Analysis

### Central Tendency
- **Mean**: Average across all iterations
- **Median (P50)**: Middle value when sorted
- **P90/P99**: 90th and 99th percentile values

### Variability
- **Standard Deviation**: Measure of result spread
- **Min/Max**: Range of observed values

## Scoring Methodology

### Overall Score Calculation
```
Overall = (Speed * 0.3) + (Memory * 0.2) + (Quality * 0.3) + (Reliability * 0.2)
```

### Normalization
- Metrics normalized to 0-100 scale
- Speed/Memory: Lower is better (inverted scale)
- Quality/Reliability: Higher is better

## Reproducibility

### Version Control
- All benchmark code version controlled
- Framework versions pinned in CI
- Test document set versioned

### CI/CD Integration
- Automated execution via GitHub Actions
- Results archived as artifacts
- Historical data preserved

## Limitations

- **Cloud Environment**: Performance varies with cloud instance
- **Concurrency**: Single-threaded testing only
- **Quality Assessment**: Not available for all frameworks
- **Format Support**: Frameworks tested only on supported formats

## Continuous Improvement

The benchmark suite is continuously updated to:
- Add new frameworks as they emerge
- Expand test document corpus
- Refine quality metrics
- Improve statistical analysis

## Running Benchmarks

### Local Execution
```bash
cd benchmarks
uv run python -m src.cli benchmark --framework all --iterations 3
```

### CI Execution
Triggered via GitHub Actions workflow dispatch with configurable parameters.

## Contact

For questions or suggestions about the benchmark methodology:
- Open an issue on GitHub
- Contribute improvements via pull requests
"""

    output_path = output_dir / "methodology.md"
    output_path.write_text(content)
    console.print(f"  ✅ Generated {output_path}")


def main(
    input_file: Path = Path("benchmarks/aggregated-results/aggregated_results.json"),
    output_dir: Path = Path("docs/benchmarks"),
    charts_dir: Path | None = None,
) -> None:
    """Generate comprehensive benchmark documentation from aggregated results."""
    console.print("[bold blue]Benchmark Documentation Generator[/bold blue]")
    console.print(f"Input: {input_file}")
    console.print(f"Output: {output_dir}\n")

    if not input_file.exists():
        console.print(f"[red]Error: Input file {input_file} not found[/red]")
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data").mkdir(exist_ok=True)
    (output_dir / "charts").mkdir(exist_ok=True)

    console.print("Loading aggregated results...")
    data = load_aggregated_results(input_file)

    shutil.copy2(input_file, output_dir / "data" / "latest.json")
    console.print(f"  ✅ Copied data to {output_dir}/data/latest.json")

    if charts_dir and charts_dir.exists():
        console.print(f"Copying charts from {charts_dir}...")
        for chart_file in charts_dir.glob("*.html"):
            shutil.copy2(chart_file, output_dir / "charts" / chart_file.name)
            console.print(f"  ✅ Copied {chart_file.name}")

    generate_index_page(data, output_dir)
    generate_latest_results_page(data, output_dir)
    generate_framework_comparison_page(data, output_dir)
    generate_methodology_page(output_dir)

    console.print("\n[green]✨ Documentation generated successfully![/green]")
    console.print(f"View at: {output_dir}/index.md")


if __name__ == "__main__":
    typer.run(main)
