from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click
import matplotlib.pyplot as plt
import msgspec
import plotly.graph_objects as go  # type: ignore[import-not-found]
import seaborn as sns  # type: ignore[import-untyped]
from plotly.subplots import make_subplots  # type: ignore[import-not-found]
from rich.console import Console

console = Console()

FRAMEWORK_COLORS = {
    "kreuzberg_sync": "#2E86AB",
    "kreuzberg_async": "#A23B72",
    "kreuzberg_v4_sync": "#1E5A8A",
    "kreuzberg_v4_async": "#8A1E5A",
    "docling": "#F18F01",
    "markitdown": "#C73E1D",
    "unstructured": "#5B9A8B",
    "extractous": "#FF6B35",
}


class FrameworkSummary(msgspec.Struct):
    """Data structure for benchmark framework summary statistics."""

    framework: str
    total_files: int
    successful_extractions: int
    failed_extractions: int
    timeout_count: int
    success_rate: float
    avg_extraction_time: float
    median_extraction_time: float
    p90_extraction_time: float
    p99_extraction_time: float
    avg_memory_mb: float
    peak_memory_mb: float
    avg_cpu_percent: float
    total_time_seconds: float
    files_per_second: float
    avg_quality_score: float | None = None


def load_aggregated_results(file_path: Path) -> dict[str, Any]:
    """Load aggregated benchmark results from JSON file."""
    with file_path.open("r") as f:
        return json.load(f)  # type: ignore[no-any-return]


def setup_plotting_style() -> None:
    """Configure matplotlib and seaborn plotting styles."""
    plt.style.use("default")
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 150,
            "font.size": 12,
            "axes.titlesize": 16,
            "axes.labelsize": 14,
            "xtick.labelsize": 12,
            "ytick.labelsize": 12,
            "legend.fontsize": 12,
        }
    )
    sns.set_palette(list(FRAMEWORK_COLORS.values()))


def create_performance_comparison_chart(data: dict[str, Any], output_dir: Path) -> Path:
    """Create performance comparison chart showing extraction time and success rate."""
    console.print("📊 Creating performance comparison chart...")

    frameworks = []
    avg_times = []
    success_rates = []

    for fw_name, summary in data.get("framework_summaries", {}).items():
        summary_data = summary[0] if isinstance(summary, list) and summary else summary
        frameworks.append(fw_name)
        avg_times.append(summary_data.get("avg_extraction_time", 0))
        success_rates.append(summary_data.get("success_rate", 0) * 100)

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Average Extraction Time", "Success Rate"),
        specs=[[{"type": "bar"}, {"type": "bar"}]],
    )

    fig.add_trace(
        go.Bar(
            x=frameworks,
            y=avg_times,
            name="Avg Time (s)",
            marker_color=[FRAMEWORK_COLORS.get(fw, "#666") for fw in frameworks],
            text=[f"{t:.2f}s" for t in avg_times],
            textposition="auto",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=frameworks,
            y=success_rates,
            name="Success Rate (%)",
            marker_color=[FRAMEWORK_COLORS.get(fw, "#666") for fw in frameworks],
            text=[f"{r:.1f}%" for r in success_rates],
            textposition="auto",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title="Framework Performance Comparison",
        showlegend=False,
        height=500,
        template="plotly_white",
    )

    fig.update_yaxes(title_text="Time (seconds)", row=1, col=1)
    fig.update_yaxes(title_text="Success Rate (%)", row=1, col=2)

    output_path = output_dir / "performance_comparison.html"
    fig.write_html(output_path)
    console.print(f"  ✅ Saved to {output_path}")
    return output_path


def create_memory_usage_chart(data: dict[str, Any], output_dir: Path) -> Path:
    """Create memory usage chart showing average and peak memory consumption."""
    console.print("💾 Creating memory usage chart...")

    frameworks = []
    avg_memory = []
    peak_memory = []

    for fw_name, summary in data.get("framework_summaries", {}).items():
        summary_data = summary[0] if isinstance(summary, list) and summary else summary
        frameworks.append(fw_name)
        avg_memory.append(summary_data.get("avg_memory_mb", 0))
        peak_memory.append(summary_data.get("peak_memory_mb", 0))

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Average Memory",
            x=frameworks,
            y=avg_memory,
            marker_color="lightblue",
            text=[f"{m:.1f} MB" for m in avg_memory],
            textposition="auto",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Peak Memory",
            x=frameworks,
            y=peak_memory,
            marker_color="darkblue",
            text=[f"{m:.1f} MB" for m in peak_memory],
            textposition="auto",
        )
    )

    fig.update_layout(
        title="Memory Usage by Framework",
        xaxis_title="Framework",
        yaxis_title="Memory (MB)",
        barmode="group",
        template="plotly_white",
        height=500,
    )

    output_path = output_dir / "memory_usage.html"
    fig.write_html(output_path)
    console.print(f"  ✅ Saved to {output_path}")
    return output_path


def create_throughput_chart(data: dict[str, Any], output_dir: Path) -> Path:
    """Create throughput chart showing files processed per second."""
    console.print("⚡ Creating throughput chart...")

    frameworks = []
    throughput = []

    for fw_name, summary in data.get("framework_summaries", {}).items():
        summary_data = summary[0] if isinstance(summary, list) and summary else summary
        frameworks.append(fw_name)
        fps = summary_data.get("files_per_second", 0)
        if fps == 0 and summary_data.get("total_time_seconds", 0) > 0:
            fps = summary_data.get("total_files", 0) / summary_data.get("total_time_seconds", 1)
        throughput.append(fps)

    fig = go.Figure(
        data=[
            go.Bar(
                x=frameworks,
                y=throughput,
                marker_color=[FRAMEWORK_COLORS.get(fw, "#666") for fw in frameworks],
                text=[f"{t:.2f} files/s" for t in throughput],
                textposition="auto",
            )
        ]
    )

    fig.update_layout(
        title="Throughput Comparison (Files per Second)",
        xaxis_title="Framework",
        yaxis_title="Files per Second",
        template="plotly_white",
        height=500,
    )

    output_path = output_dir / "throughput.html"
    fig.write_html(output_path)
    console.print(f"  ✅ Saved to {output_path}")
    return output_path


def create_category_performance_chart(data: dict[str, Any], output_dir: Path) -> Path:
    """Create category performance chart showing performance by document type."""
    console.print("📁 Creating category performance chart...")

    categories = []
    category_data: dict[str, dict[str, float]] = {}

    for cat_name, summaries in data.get("category_summaries", {}).items():
        if summaries:
            categories.append(cat_name)
            for summary in summaries:
                fw = summary.get("framework", "unknown")
                if fw not in category_data:
                    category_data[fw] = {}
                category_data[fw][cat_name] = summary.get("avg_extraction_time", 0)

    if not categories:
        console.print("  ⚠️ No category data available")
        return output_dir / "category_performance.html"

    fig = go.Figure()

    for framework, cat_times in category_data.items():
        times = [cat_times.get(cat, 0) for cat in categories]
        fig.add_trace(
            go.Bar(
                name=framework,
                x=categories,
                y=times,
                marker_color=FRAMEWORK_COLORS.get(framework, "#666"),
                text=[f"{t:.2f}s" for t in times],
                textposition="auto",
            )
        )

    fig.update_layout(
        title="Performance by Document Category",
        xaxis_title="Document Category",
        yaxis_title="Average Time (seconds)",
        barmode="group",
        template="plotly_white",
        height=500,
    )

    output_path = output_dir / "category_performance.html"
    fig.write_html(output_path)
    console.print(f"  ✅ Saved to {output_path}")
    return output_path


def create_interactive_dashboard(data: dict[str, Any], output_dir: Path) -> Path:
    """Create comprehensive interactive dashboard with all key metrics."""
    console.print("🎯 Creating interactive dashboard...")

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Extraction Time",
            "Success Rate",
            "Memory Usage",
            "Throughput",
        ),
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "bar"}, {"type": "scatter"}],
        ],
    )

    frameworks = []
    metrics: dict[str, list[float]] = {
        "avg_time": [],
        "success_rate": [],
        "memory": [],
        "throughput": [],
    }

    for fw_name, summary in data.get("framework_summaries", {}).items():
        summary_data = summary[0] if isinstance(summary, list) and summary else summary
        frameworks.append(fw_name)
        metrics["avg_time"].append(summary_data.get("avg_extraction_time", 0))
        metrics["success_rate"].append(summary_data.get("success_rate", 0) * 100)
        metrics["memory"].append(summary_data.get("avg_memory_mb", 0))

        fps = summary_data.get("files_per_second", 0)
        if fps == 0 and summary_data.get("total_time_seconds", 0) > 0:
            fps = summary_data.get("total_files", 0) / summary_data.get("total_time_seconds", 1)
        metrics["throughput"].append(fps)

    colors = [FRAMEWORK_COLORS.get(fw, "#666") for fw in frameworks]

    fig.add_trace(
        go.Bar(x=frameworks, y=metrics["avg_time"], marker_color=colors, name="Time"),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(x=frameworks, y=metrics["success_rate"], marker_color=colors, name="Success"),
        row=1,
        col=2,
    )

    fig.add_trace(
        go.Bar(x=frameworks, y=metrics["memory"], marker_color=colors, name="Memory"),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=frameworks,
            y=metrics["throughput"],
            mode="markers+lines",
            marker={"size": 12, "color": colors},
            name="Throughput",
        ),
        row=2,
        col=2,
    )

    fig.update_layout(
        title="Benchmark Dashboard",
        showlegend=False,
        height=800,
        template="plotly_white",
    )

    fig.update_yaxes(title_text="Time (s)", row=1, col=1)
    fig.update_yaxes(title_text="Success (%)", row=1, col=2)
    fig.update_yaxes(title_text="Memory (MB)", row=2, col=1)
    fig.update_yaxes(title_text="Files/sec", row=2, col=2)

    output_path = output_dir / "dashboard.html"
    fig.write_html(output_path)
    console.print(f"  ✅ Saved to {output_path}")
    return output_path


@click.command()
@click.option(
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True, path_type=Path),
    default=Path("benchmarks/aggregated-results/aggregated_results.json"),
    help="Path to aggregated results JSON file",
)
@click.option(
    "--output",
    "-o",
    "output_dir",
    type=click.Path(path_type=Path),
    default=Path("docs/benchmarks/charts"),
    help="Output directory for charts",
)
@click.option(
    "--chart",
    "-c",
    "charts",
    multiple=True,
    default=["all"],
    help="Charts to generate (performance/memory/throughput/category/dashboard/all)",
)
def main(input_file: Path, output_dir: Path, charts: tuple[str, ...]) -> None:
    """Generate benchmark visualization charts from aggregated results."""
    console.print("[bold blue]Benchmark Visualization Generator[/bold blue]")
    console.print(f"Input: {input_file}")
    console.print(f"Output: {output_dir}\n")

    if not input_file.exists():
        console.print(f"[red]Error: Input file {input_file} not found[/red]")
        raise SystemExit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    console.print("Loading aggregated results...")
    data = load_aggregated_results(input_file)

    setup_plotting_style()

    generated = []
    charts_list = list(charts)
    chart_types = (
        charts_list if "all" not in charts_list else ["performance", "memory", "throughput", "category", "dashboard"]
    )

    if "performance" in chart_types:
        generated.append(create_performance_comparison_chart(data, output_dir))

    if "memory" in chart_types:
        generated.append(create_memory_usage_chart(data, output_dir))

    if "throughput" in chart_types:
        generated.append(create_throughput_chart(data, output_dir))

    if "category" in chart_types:
        generated.append(create_category_performance_chart(data, output_dir))

    if "dashboard" in chart_types:
        generated.append(create_interactive_dashboard(data, output_dir))

    console.print(f"\n[green]✨ Generated {len(generated)} visualizations[/green]")


if __name__ == "__main__":
    main()
