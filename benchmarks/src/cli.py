# mypy: disable-error-code="index,unused-ignore,misc"

from __future__ import annotations

import asyncio
import json
import statistics
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
import msgpack
from rich.console import Console
from rich.table import Table

from kreuzberg import (
    ExtractionConfig,
    ExtractionResult,
    batch_extract_file,
    extract_file,
    extract_file_sync,
)
from kreuzberg._utils._cache import clear_all_caches

from .benchmarks import KreuzbergBenchmarks
from .models import FlameGraphConfig
from .runner import BenchmarkRunner

SyncBench = tuple[str, Callable[[], ExtractionResult], dict[str, str]]
AsyncBench = tuple[str, Callable[[], Awaitable[ExtractionResult]], dict[str, str]]


@click.group(help="Kreuzberg Performance Benchmarking Suite")
def cli() -> None:
    pass


console = Console()


def _generate_quality_report(data: dict[str, Any], console: Console) -> None:
    console.print("\n[bold]METADATA QUALITY REPORT[/bold]")
    console.print("=" * 80)

    quality_results = [
        r
        for r in data["results"]
        if r.get("extraction_quality") and r.get("extraction_quality", {}).get("metadata_quality")
    ]

    if not quality_results:
        console.print("[yellow]No extraction quality data available[/yellow]")
        return

    backend_stats: dict[str, dict[str, Any]] = {}
    for result in quality_results:
        metadata = result.get("metadata", {})
        backend = metadata.get("backend", "unknown")

        if backend not in backend_stats:
            backend_stats[backend] = {
                "results": [],
                "file_types": set(),
                "total_metadata_fields": 0,
                "unique_fields": set(),
                "avg_completeness": 0,
                "avg_richness": 0,
            }

        quality = result["extraction_quality"]["metadata_quality"]
        backend_stats[backend]["results"].append(quality)
        backend_stats[backend]["file_types"].add(metadata.get("file_type", "unknown"))
        backend_stats[backend]["total_metadata_fields"] += quality["metadata_count"]
        backend_stats[backend]["unique_fields"].update(quality["metadata_fields"])

    for stats in backend_stats.values():
        results = stats["results"]
        if results:
            stats["avg_completeness"] = sum(r["metadata_completeness"] for r in results) / len(results)
            stats["avg_richness"] = sum(r["metadata_richness"] for r in results) / len(results)
            stats["avg_metadata_count"] = stats["total_metadata_fields"] / len(results)

    table = Table(title="Backend Metadata Quality Comparison")
    table.add_column("Backend", style="bold")
    table.add_column("Files Tested", justify="right")
    table.add_column("Avg Fields", justify="right")
    table.add_column("Unique Fields", justify="right")
    table.add_column("Completeness %", justify="right")
    table.add_column("Richness Score", justify="right")

    for backend in sorted(backend_stats.keys()):
        stats = backend_stats[backend]
        table.add_row(
            backend,
            str(len(stats["results"])),
            f"{stats['avg_metadata_count']:.1f}",
            str(len(stats["unique_fields"])),
            f"{stats['avg_completeness']:.1f}%",
            f"{stats['avg_richness']:.2f}",
        )

    console.print(table)

    console.print("\n[bold]Metadata Quality by File Type and Backend:[/bold]")

    file_type_stats: dict[str, dict[str, list[Any]]] = {}
    for result in quality_results:
        metadata = result.get("metadata", {})
        file_type = metadata.get("file_type", "unknown")
        backend = metadata.get("backend", "unknown")
        quality = result["extraction_quality"]["metadata_quality"]

        if file_type not in file_type_stats:
            file_type_stats[file_type] = {}

        if backend not in file_type_stats[file_type]:
            file_type_stats[file_type][backend] = []

        file_type_stats[file_type][backend].append(quality)

    for file_type in sorted(file_type_stats.keys()):
        console.print(f"\n{file_type.upper()}:")
        for backend in sorted(file_type_stats[file_type].keys()):
            qualities = file_type_stats[file_type][backend]
            avg_count = sum(q["metadata_count"] for q in qualities) / len(qualities)
            has_title = sum(1 for q in qualities if q["has_title"]) / len(qualities) * 100
            has_author = sum(1 for q in qualities if q["has_author"]) / len(qualities) * 100

            console.print(
                f"  {backend}: {avg_count:.1f} fields, {has_title:.0f}% with title, {has_author:.0f}% with author"
            )

    console.print("\n[bold]Most Common Metadata Fields:[/bold]")
    all_fields: dict[str, set[str]] = {}
    for stats in backend_stats.values():
        for field in stats["unique_fields"]:
            if field not in all_fields:
                all_fields[field] = set()
            all_fields[field].add(backend)

    sorted_fields = sorted(all_fields.items(), key=lambda x: len(x[1]), reverse=True)[:20]

    for field, backends in sorted_fields:
        console.print(f"  {field}: {', '.join(sorted(backends))}")


@cli.command()
@click.option(
    "--output-dir",
    "output_dir",
    type=click.Path(path_type=Path),
    default=Path("results"),
    show_default=True,
    help="Directory to save benchmark results",
)
@click.option(
    "--test-files-dir",
    "test_files_dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory containing test files for benchmarking",
)
@click.option("--flame", "include_flame", is_flag=True, help="Generate flame graphs for performance profiling")
@click.option(
    "--suite-name",
    "suite_name",
    type=str,
    default="kreuzberg_sync_vs_async",
    show_default=True,
    help="Name of the benchmark suite",
)
@click.option("--sync-only", "sync_only", is_flag=True, help="Run only synchronous benchmarks")
@click.option("--async-only", "async_only", is_flag=True, help="Run only asynchronous benchmarks")
@click.option(
    "--comparison-only", "comparison_only", is_flag=True, help="Run only direct sync vs async comparison benchmarks"
)
@click.option("--stress", "include_stress", is_flag=True, help="Include stress test benchmarks")
@click.option("--backend-comparison", "backend_comparison", is_flag=True, help="Run backend comparison benchmarks")
@click.option("--images", "include_images", is_flag=True, help="Include image extraction benchmarks")
@click.option(
    "--images-stress", "images_stress", is_flag=True, help="Include image stress (memory/throughput) benchmarks"
)
@click.option("--tesseract", "include_tesseract", is_flag=True, help="Include Tesseract OCR benchmarks")
@click.option(
    "--tesseract-matrix",
    "tesseract_matrix",
    is_flag=True,
    help="Include expanded Tesseract variant matrix (formats/PSM)",
)
@click.option(
    "--tesseract-arch",
    "tesseract_arch",
    is_flag=True,
    help="Compare Tesseract architectures (threads vs processes) across worker counts",
)
@click.option(
    "--workers",
    "workers_csv",
    type=str,
    default=None,
    help="Comma-separated worker counts for --tesseract-arch (e.g., 1,4,8)",
)
def run(  # noqa: PLR0913
    output_dir: Path,
    test_files_dir: Path | None,
    include_flame: bool,
    suite_name: str,
    sync_only: bool,
    async_only: bool,
    comparison_only: bool,
    include_stress: bool,
    backend_comparison: bool,
    include_images: bool,
    images_stress: bool,
    include_tesseract: bool,
    tesseract_matrix: bool,
    tesseract_arch: bool,
    workers_csv: str | None,
) -> None:
    console.print("[bold blue]Kreuzberg Performance Benchmarks[/bold blue]")
    console.print(f"Suite: {suite_name}")

    benchmarks = KreuzbergBenchmarks(test_files_dir)

    if not benchmarks.test_files:
        console.print("[red]Error:[/red] No test files found for benchmarking")
        console.print(f"Looking in: {benchmarks.test_files_dir}")
        console.print("Please ensure test files exist or specify --test-files-dir")
        raise click.Abort from None

    console.print(f"Found {len(benchmarks.test_files)} test files")

    flame_config = FlameGraphConfig(enabled=include_flame) if include_flame else None

    runner = BenchmarkRunner(console=console, flame_config=flame_config)

    sync_benchmarks: list[SyncBench] = []
    async_benchmarks: list[AsyncBench] = []

    if backend_comparison:
        backend_benchmarks = benchmarks.get_backend_benchmarks()
        sync_benchmarks = backend_benchmarks  # type: ignore[assignment]
        async_benchmarks = []
    elif comparison_only:
        comparison_benchmarks = benchmarks.get_comparison_benchmarks()

        sync_benchmarks = [  # type: ignore[list-item]
            (name, func, meta) for name, func, meta in comparison_benchmarks if meta.get("type") == "sync"
        ]
        async_benchmarks = [  # type: ignore[list-item]
            (name, func, meta) for name, func, meta in comparison_benchmarks if meta.get("type") == "async"
        ]
    else:
        if not async_only:
            sync_benchmarks = benchmarks.get_sync_benchmarks()
            if include_stress:
                sync_benchmarks.extend(benchmarks.get_stress_benchmarks())  # type: ignore[arg-type]

        if not sync_only:
            async_benchmarks = benchmarks.get_async_benchmarks()
            if include_stress:
                async_benchmarks.extend(benchmarks.get_stress_benchmarks())  # type: ignore[arg-type]

        if include_images:
            image_benchmarks = benchmarks.get_image_benchmarks()
            sync_benchmarks.extend([(n, f, m) for (n, f, m) in image_benchmarks if n.startswith("sync_")])  # type: ignore[list-item]
            if not sync_only:
                async_benchmarks.extend([(n, f, m) for (n, f, m) in image_benchmarks if n.startswith("async_")])  # type: ignore[list-item]

        if images_stress:
            image_stress = benchmarks.get_image_stress_benchmarks()
            sync_benchmarks.extend([(n, f, m) for (n, f, m) in image_stress if n.startswith("sync_")])  # type: ignore[list-item]
            if not sync_only:
                async_benchmarks.extend([(n, f, m) for (n, f, m) in image_stress if n.startswith("async_")])  # type: ignore[list-item]

        if include_tesseract:
            console.print("Including Tesseract OCR benchmarks…")
            sync_benchmarks.extend(benchmarks.get_tesseract_ocr_benchmarks())  # type: ignore[arg-type]
            if tesseract_matrix:
                sync_benchmarks.extend(benchmarks.get_tesseract_variant_benchmarks())  # type: ignore[arg-type]
            if tesseract_arch:
                worker_list = None
                if workers_csv:
                    try:
                        worker_list = [int(x.strip()) for x in workers_csv.split(",") if x.strip()]
                    except ValueError:
                        console.print("[yellow]Invalid --workers list; falling back to defaults[/yellow]")
                        worker_list = None
                sync_benchmarks.extend(benchmarks.get_tesseract_architecture_benchmarks(worker_list))  # type: ignore[arg-type]

    if not sync_benchmarks and not async_benchmarks:
        console.print("[red]Error:[/red] No benchmarks to run")
        raise click.Abort from None

    console.print(f"Running {len(sync_benchmarks)} sync + {len(async_benchmarks)} async benchmarks")

    try:
        suite = runner.run_benchmark_suite(
            suite_name=suite_name,
            benchmarks=sync_benchmarks,  # type: ignore[arg-type]
            async_benchmarks=async_benchmarks if async_benchmarks else None,  # type: ignore[arg-type]
        )

        runner.print_summary(suite)

        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{suite_name}.json"
        runner.save_results(suite, output_file)

        latest_file = output_dir / "latest.json"
        runner.save_results(suite, latest_file)

        console.print("\n[green]Benchmark completed successfully![/green]")
        console.print(f"Results saved to: {output_file}")

    except KeyboardInterrupt:
        console.print("\n[yellow]Benchmark interrupted by user[/yellow]")
        raise click.Abort from None
    except Exception as e:
        console.print(f"\n[red]Benchmark failed:[/red] {e}")
        raise click.Abort from e


@cli.command()
@click.argument("result1", type=click.Path(path_type=Path))
@click.argument("result2", type=click.Path(path_type=Path))
@click.option("--output", "output", type=click.Path(path_type=Path), default=None, help="Save comparison to file")
def compare(result1: Path, result2: Path, output: Path | None) -> None:
    console.print("[bold blue]Benchmark Comparison[/bold blue]")

    try:
        with result1.open() as f:
            data1 = json.load(f)
        with result2.open() as f:
            data2 = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading files:[/red] {e}")
        raise click.Abort from e

    console.print("Comparing:")
    console.print(f"  {result1.name}: {data1['name']} ({data1['timestamp']})")
    console.print(f"  {result2.name}: {data2['name']} ({data2['timestamp']})")

    rate1 = data1["summary"]["success_rate_percent"]
    rate2 = data2["summary"]["success_rate_percent"]
    console.print(f"\nSuccess Rate: {rate1:.1f}% vs {rate2:.1f}% ({rate2 - rate1:+.1f}%)")

    duration1 = data1["summary"]["total_duration_seconds"]
    duration2 = data2["summary"]["total_duration_seconds"]
    console.print(f"Total Duration: {duration1:.3f}s vs {duration2:.3f}s ({duration2 - duration1:+.3f}s)")

    if output:
        comparison_data = {
            "comparison_timestamp": datetime.now(timezone.utc).isoformat(),
            "file1": {"path": str(result1), "data": data1},
            "file2": {"path": str(result2), "data": data2},
            "summary": {
                "success_rate_diff": rate2 - rate1,
                "duration_diff": duration2 - duration1,
            },
        }

        with output.open("w") as f:
            json.dump(comparison_data, f, indent=2)
        console.print(f"\nComparison saved to: {output}")


@cli.command()
def tesseract() -> None:
    """Run Tesseract OCR output format benchmarks (DEPRECATED)."""
    console.print(
        "[yellow]This command is deprecated. Use 'baseline', 'statistical', or 'serialization' commands instead.[/yellow]"
    )


@cli.command()
@click.argument("result_file", type=click.Path(path_type=Path))
@click.option("--quality", "quality_report", is_flag=True, help="Generate metadata quality report")
def analyze(result_file: Path, quality_report: bool) -> None:
    console.print("[bold blue]Benchmark Analysis[/bold blue]")

    try:
        with result_file.open() as f:
            data = json.load(f)
    except Exception as e:
        console.print(f"[red]Error loading file:[/red] {e}")
        raise click.Abort from e

    console.print(f"Analyzing: {data['name']} ({data['timestamp']})")

    successful_results = [r for r in data["results"] if r["success"] and r["performance"]]

    if not successful_results:
        console.print("[red]No successful results to analyze[/red]")
        return

    durations = [r["performance"]["duration_seconds"] for r in successful_results]
    memory_peaks = [r["performance"]["memory_peak_mb"] for r in successful_results]

    console.print("\n[bold]Performance Analysis:[/bold]")
    console.print(f"  Successful benchmarks: {len(successful_results)}")
    console.print(f"  Duration range: {min(durations):.3f}s - {max(durations):.3f}s")
    console.print(f"  Memory range: {min(memory_peaks):.1f}MB - {max(memory_peaks):.1f}MB")

    sync_results = [r for r in successful_results if "sync" in r["name"]]
    async_results = [r for r in successful_results if "async" in r["name"]]

    if sync_results and async_results:
        sync_avg = sum(r["performance"]["duration_seconds"] for r in sync_results) / len(sync_results)
        async_avg = sum(r["performance"]["duration_seconds"] for r in async_results) / len(async_results)

        console.print("\n[bold]Sync vs Async:[/bold]")
        console.print(f"  Sync average: {sync_avg:.3f}s ({len(sync_results)} benchmarks)")
        console.print(f"  Async average: {async_avg:.3f}s ({len(async_results)} benchmarks)")
        console.print(f"  Performance difference: {async_avg - sync_avg:+.3f}s")

    arch_results: dict[str, list[Any]] = {}
    for r in successful_results:
        meta = r.get("metadata") or {}
        if meta.get("backend") == "tesseract" and meta.get("arch") in {"threads", "processes"}:
            arch = meta.get("arch")
            if arch:
                arch_results.setdefault(arch, []).append(r)

    if arch_results:
        console.print("\n[bold]Tesseract Architecture Comparison:[/bold]")
        for arch, items in arch_results.items():
            avg = sum(i["performance"]["duration_seconds"] for i in items) / len(items)
            console.print(f"  {arch}: avg {avg:.3f}s over {len(items)} benches")

        if {"threads", "processes"}.issubset(arch_results.keys()):
            thr_avg = sum(i["performance"]["duration_seconds"] for i in arch_results["threads"]) / len(
                arch_results["threads"]
            )
            proc_avg = sum(i["performance"]["duration_seconds"] for i in arch_results["processes"]) / len(
                arch_results["processes"]
            )
            console.print(f"  processes - threads: {proc_avg - thr_avg:+.3f}s (negative favors processes)")

    if quality_report:
        _generate_quality_report(data, console)


@cli.command()
@click.option("--output", "output_file", type=click.Path(path_type=Path), default=None, help="Save results to file")
def baseline(output_file: Path | None) -> None:
    console.print("[bold blue]Baseline Performance Benchmark[/bold blue]")

    test_files_dir = Path("tests/test_source_files")
    test_files = list(test_files_dir.glob("*.pdf"))

    if not test_files:
        console.print("[red]No test files found in tests/test_source_files[/red]")
        return

    single_file = test_files[0]
    mixed_files = test_files[:3] if len(test_files) >= 3 else [single_file] * 3

    results = {}
    console.print(f"Testing with file: {single_file.name}")

    clear_all_caches()
    start_time = time.time()
    result = extract_file_sync(single_file)
    cold_duration = time.time() - start_time

    start_time = time.time()
    result = extract_file_sync(single_file)
    warm_duration = time.time() - start_time

    clear_all_caches()
    start_time = time.time()

    async def run_batch() -> list[ExtractionResult]:
        return await batch_extract_file(mixed_files)

    asyncio.run(run_batch())
    batch_duration = time.time() - start_time

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_file": str(single_file),
        "cold_cache_duration": cold_duration,
        "warm_cache_duration": warm_duration,
        "batch_duration": batch_duration,
        "speedup_factor": cold_duration / warm_duration if warm_duration > 0 else 0,
        "content_length": len(result.content),
    }

    console.print(f"\n[green]Cold cache extraction: {cold_duration:.3f}s[/green]")
    console.print(f"[green]Warm cache extraction: {warm_duration:.3f}s[/green]")
    console.print(f"[green]Batch extraction: {batch_duration:.3f}s[/green]")
    console.print(f"[yellow]Cache speedup: {results['speedup_factor']:.2f}x[/yellow]")

    if output_file:
        with output_file.open("w") as f:
            json.dump(results, f, indent=2)
        console.print(f"[blue]Results saved to {output_file}[/blue]")
    else:
        output_dir = Path("results")
        output_dir.mkdir(parents=True, exist_ok=True)
        default_file = output_dir / "baseline.json"
        with default_file.open("w") as f:
            json.dump(results, f, indent=2)
        console.print(f"[blue]Results saved to {default_file}[/blue]")


@cli.command()
@click.option("--trials", "trials", type=int, default=5, show_default=True, help="Number of trials to run")
@click.option("--output", "output_file", type=click.Path(path_type=Path), default=None, help="Save results to file")
def statistical(trials: int, output_file: Path | None) -> None:
    console.print("[bold blue]Statistical Performance Benchmark[/bold blue]")

    test_files_dir = Path("tests/test_source_files")
    pdf_files = list(test_files_dir.glob("*.pdf"))

    if not pdf_files:
        console.print("[red]No PDF test files found[/red]")
        return

    single_file = pdf_files[0]
    config = ExtractionConfig(force_ocr=True, ocr_backend="tesseract", extract_tables=True, chunk_content=True)

    console.print(f"File: {single_file.name}")
    console.print(f"Trials: {trials}")
    console.print("=" * 60)

    cold_times = []
    warm_times = []

    async def run_trial() -> tuple[float, float]:
        clear_all_caches()
        start_time = time.time()
        await extract_file(single_file, config=config)
        cold_time = time.time() - start_time
        cold_times.append(cold_time)

        start_time = time.time()
        await extract_file(single_file, config=config)
        warm_time = time.time() - start_time
        warm_times.append(warm_time)

        return cold_time, warm_time

    console.print("Running trials...")
    for i in range(trials):
        cold_time, warm_time = asyncio.run(run_trial())
        console.print(f"Trial {i + 1}: Cold={cold_time:.3f}s, Warm={warm_time:.3f}s")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_file": str(single_file),
        "trials": trials,
        "cold_cache": {
            "mean": statistics.mean(cold_times),
            "stdev": statistics.stdev(cold_times) if len(cold_times) > 1 else 0,
            "median": statistics.median(cold_times),
            "min": min(cold_times),
            "max": max(cold_times),
            "raw_times": cold_times,
        },
        "warm_cache": {
            "mean": statistics.mean(warm_times),
            "stdev": statistics.stdev(warm_times) if len(warm_times) > 1 else 0,
            "median": statistics.median(warm_times),
            "min": min(warm_times),
            "max": max(warm_times),
            "raw_times": warm_times,
        },
    }

    cold_cache = results["cold_cache"]
    warm_cache = results["warm_cache"]

    console.print(
        f"\n[green]Cold cache - Mean: {cold_cache['mean']:.3f}s ± {cold_cache['stdev']:.3f}s[/green]"  # type: ignore[index]
    )
    console.print(
        f"[green]Warm cache - Mean: {warm_cache['mean']:.3f}s ± {warm_cache['stdev']:.3f}s[/green]"  # type: ignore[index]
    )
    speedup = cold_cache["mean"] / warm_cache["mean"] if warm_cache["mean"] > 0 else 0  # type: ignore[index]
    console.print(f"[yellow]Average speedup: {speedup:.2f}x[/yellow]")

    if output_file:
        with output_file.open("w") as f:
            json.dump(results, f, indent=2)
        console.print(f"[blue]Results saved to {output_file}[/blue]")
    else:
        output_dir = Path("results")
        output_dir.mkdir(parents=True, exist_ok=True)
        default_file = output_dir / "statistical.json"
        with default_file.open("w") as f:
            json.dump(results, f, indent=2)
        console.print(f"[blue]Results saved to {default_file}[/blue]")


@cli.command()
@click.option("--output", "output_file", type=click.Path(path_type=Path), default=None, help="Save results to file")
def serialization(output_file: Path | None) -> None:
    console.print("[bold blue]Serialization Performance Benchmark[/bold blue]")

    large_content = "This is a realistic OCR result content. " * 500
    metadata: dict[str, Any] = {
        "file_path": "/some/long/path/to/document.pdf",
        "ocr_backend": "tesseract",
        "ocr_config": {"language": "eng", "psm": 3},
        "processing_time": 15.234,
        "confidence_scores": [0.95, 0.87, 0.92, 0.88, 0.94],
        "page_count": 10,
    }

    test_result = ExtractionResult(
        content=large_content,
        mime_type="text/plain",
        metadata=metadata,  # type: ignore[arg-type]
        chunks=["chunk1", "chunk2", "chunk3"] * 20,
    )

    cache_data = {
        "type": "ExtractionResult",
        "data": test_result,
        "timestamp": time.time(),
        "version": "1.0.0",
    }

    trials = 100
    json_serialize_times = []
    json_deserialize_times = []

    console.print("Benchmarking JSON serialization...")
    for _ in range(trials):
        start_time = time.time()
        json_str = json.dumps(cache_data, default=str)
        json_serialize_times.append(time.time() - start_time)

        start_time = time.time()
        json.loads(json_str)
        json_deserialize_times.append(time.time() - start_time)

    msgpack_serialize_times = []
    msgpack_deserialize_times = []

    if msgpack is not None:
        console.print("Benchmarking msgpack serialization...")

        for _ in range(trials):
            start_time = time.time()
            msgpack_bytes = msgpack.packb(cache_data, default=str)
            msgpack_serialize_times.append(time.time() - start_time)

            start_time = time.time()
            msgpack.unpackb(msgpack_bytes, raw=False)
            msgpack_deserialize_times.append(time.time() - start_time)
    else:
        console.print("[yellow]msgpack not available - skipping msgpack benchmarks[/yellow]")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trials": trials,
        "data_size_chars": len(large_content),
        "json": {
            "serialize_mean": statistics.mean(json_serialize_times),
            "serialize_stdev": statistics.stdev(json_serialize_times),
            "deserialize_mean": statistics.mean(json_deserialize_times),
            "deserialize_stdev": statistics.stdev(json_deserialize_times),
        },
    }

    if msgpack_serialize_times:
        results["msgpack"] = {
            "serialize_mean": statistics.mean(msgpack_serialize_times),
            "serialize_stdev": statistics.stdev(msgpack_serialize_times),
            "deserialize_mean": statistics.mean(msgpack_deserialize_times),
            "deserialize_stdev": statistics.stdev(msgpack_deserialize_times),
        }

        json_data = results["json"]
        msgpack_data = results["msgpack"]

        json_total = json_data["serialize_mean"] + json_data["deserialize_mean"]  # type: ignore[index]
        msgpack_total = (
            msgpack_data["serialize_mean"] + msgpack_data["deserialize_mean"]  # type: ignore[index]
        )
        speedup = json_total / msgpack_total if msgpack_total > 0 else 0
        results["msgpack_speedup"] = speedup

    json_data = results["json"]
    console.print(
        f"\n[green]JSON serialize: {json_data['serialize_mean']:.6f}s ± {json_data['serialize_stdev']:.6f}s[/green]"  # type: ignore[index]
    )
    console.print(
        f"[green]JSON deserialize: {json_data['deserialize_mean']:.6f}s ± {json_data['deserialize_stdev']:.6f}s[/green]"  # type: ignore[index]
    )

    if "msgpack" in results:
        msgpack_data = results["msgpack"]
        console.print(
            f"[green]msgpack serialize: {msgpack_data['serialize_mean']:.6f}s ± {msgpack_data['serialize_stdev']:.6f}s[/green]"  # type: ignore[index]
        )
        console.print(
            f"[green]msgpack deserialize: {msgpack_data['deserialize_mean']:.6f}s ± {msgpack_data['deserialize_stdev']:.6f}s[/green]"  # type: ignore[index]
        )
        speedup_val = results["msgpack_speedup"]
        console.print(f"[yellow]msgpack speedup: {speedup_val:.2f}x[/yellow]")

    if output_file:
        with output_file.open("w") as f:
            json.dump(results, f, indent=2)
        console.print(f"[blue]Results saved to {output_file}[/blue]")
    else:
        output_dir = Path("results")
        output_dir.mkdir(parents=True, exist_ok=True)
        default_file = output_dir / "serialization.json"
        with default_file.open("w") as f:
            json.dump(results, f, indent=2)
        console.print(f"[blue]Results saved to {default_file}[/blue]")


if __name__ == "__main__":
    cli()
