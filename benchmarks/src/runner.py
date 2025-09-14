from __future__ import annotations

import asyncio
import json
import time
import traceback
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from .models import (
    BenchmarkResult,
    BenchmarkSuite,
    ExtractionQualityMetrics,
    FlameGraphConfig,
    MetadataQualityMetrics,
    PerformanceMetrics,
    SystemInfo,
)
from .profiler import PerformanceProfiler

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from kreuzberg import ExtractionResult


class BenchmarkRunner:
    def __init__(
        self,
        console: Console | None = None,
        flame_config: FlameGraphConfig | None = None,
    ) -> None:
        self.console = console or Console()
        self.flame_config = flame_config or FlameGraphConfig()
        self.system_info = SystemInfo.collect()

    def _analyze_extraction_result(self, result: ExtractionResult) -> ExtractionQualityMetrics | None:
        try:
            if not hasattr(result, "content") or not hasattr(result, "metadata"):
                return None

            text_length = len(result.content) if result.content else 0
            word_count = len(result.content.split()) if result.content else 0
            line_count = result.content.count("\n") + 1 if result.content else 0

            has_tables = bool(getattr(result, "tables", []))
            table_count = len(result.tables) if has_tables else 0

            has_ocr = False
            if result.metadata:
                ocr_keywords = ["ocr", "tesseract", "easyocr", "paddleocr"]
                has_ocr = any(key in str(result.metadata).lower() for key in ocr_keywords)

            detected_languages = []
            if hasattr(result, "detected_languages") and result.detected_languages:
                detected_languages = list(result.detected_languages)

            metadata_quality = None
            if result.metadata:
                metadata_fields = list(result.metadata.keys())
                metadata_count = len(metadata_fields)

                has_title = any(k.lower() in ["title", "dc:title"] for k in metadata_fields)
                has_author = any(k.lower() in ["author", "creator", "dc:creator"] for k in metadata_fields)
                has_created_date = any("creat" in k.lower() or "date" in k.lower() for k in metadata_fields)
                has_modified_date = any("modif" in k.lower() for k in metadata_fields)

                standard_fields = {
                    "title",
                    "author",
                    "creator",
                    "created",
                    "modified",
                    "date",
                    "subject",
                    "keywords",
                    "description",
                    "producer",
                    "creationdate",
                    "moddate",
                    "pages",
                    "page_count",
                }
                custom_fields_count = sum(1 for f in metadata_fields if f.lower() not in standard_fields)

                expected_fields = {"title", "author", "created", "modified"}
                present_expected = sum(1 for ef in expected_fields if any(ef in f.lower() for f in metadata_fields))
                metadata_completeness = (present_expected / len(expected_fields)) * 100

                metadata_richness = min(metadata_count / 10.0, 1.0)

                backend_val = result.metadata.get("extraction_backend")
                extraction_backend = backend_val if isinstance(backend_val, str) else None

                metadata_quality = MetadataQualityMetrics(
                    metadata_count=metadata_count,
                    metadata_fields=metadata_fields[:50],
                    metadata_completeness=metadata_completeness,
                    metadata_richness=metadata_richness,
                    has_title=has_title,
                    has_author=has_author,
                    has_created_date=has_created_date,
                    has_modified_date=has_modified_date,
                    custom_fields_count=custom_fields_count,
                    extraction_backend=extraction_backend,
                )

            has_images = bool(getattr(result, "images", []))
            image_count = len(result.images) if has_images else 0
            image_formats = (
                sorted({getattr(img, "format", "") for img in getattr(result, "images", [])}) if has_images else []
            )
            total_image_size_mb = (
                sum(len(getattr(img, "data", b"")) for img in getattr(result, "images", [])) / (1024 * 1024)
                if has_images
                else 0.0
            )
            avg_dims = None
            dims = [img.dimensions for img in getattr(result, "images", []) if getattr(img, "dimensions", None)]
            if dims:
                w = int(sum(d[0] for d in dims) / len(dims))
                h = int(sum(d[1] for d in dims) / len(dims))
                avg_dims = (w, h)

            return ExtractionQualityMetrics(
                text_length=text_length,
                word_count=word_count,
                line_count=line_count,
                has_tables=has_tables,
                table_count=table_count,
                has_ocr=has_ocr,
                mime_type=result.mime_type if hasattr(result, "mime_type") else None,
                detected_languages=detected_languages,
                metadata_quality=metadata_quality,
                has_images=has_images,
                image_count=image_count,
                image_formats=image_formats,
                total_image_size_mb=total_image_size_mb,
                average_image_dimensions=avg_dims,
            )

        except Exception:
            return None

    def run_sync_benchmark(
        self,
        name: str,
        func: Callable[[], ExtractionResult],
        metadata: dict[str, str] | None = None,
    ) -> BenchmarkResult:
        profiler = PerformanceProfiler()

        try:
            profiler.start_monitoring()
            start_time = time.perf_counter()

            result = func()

            end_time = time.perf_counter()
            performance_metrics = profiler.stop_monitoring()

            performance_metrics.duration_seconds = end_time - start_time

            extraction_quality = self._analyze_extraction_result(result)

            return BenchmarkResult(
                name=name,
                success=True,
                performance=performance_metrics,
                metadata=metadata or {},
                extraction_quality=extraction_quality,
            )

        except Exception as e:
            try:
                performance_metrics = profiler.stop_monitoring()
                performance_metrics.exception_info = str(e)
            except Exception:
                performance_metrics = PerformanceMetrics(
                    duration_seconds=0.0,
                    memory_peak_mb=0.0,
                    memory_average_mb=0.0,
                    cpu_percent_average=0.0,
                    cpu_percent_peak=0.0,
                    gc_collections={},
                    exception_info=str(e),
                )

            return BenchmarkResult(
                name=name,
                success=False,
                performance=performance_metrics,
                metadata={
                    **(metadata or {}),
                    "error_traceback": traceback.format_exc(),
                },
            )

    async def run_async_benchmark(
        self,
        name: str,
        func: Callable[[], Awaitable[ExtractionResult]],
        metadata: dict[str, str] | None = None,
    ) -> BenchmarkResult:
        profiler = PerformanceProfiler()

        try:
            profiler.start_monitoring()
            start_time = time.perf_counter()

            result = await func()

            end_time = time.perf_counter()
            performance_metrics = profiler.stop_monitoring()

            performance_metrics.duration_seconds = end_time - start_time

            extraction_quality = self._analyze_extraction_result(result)

            return BenchmarkResult(
                name=name,
                success=True,
                performance=performance_metrics,
                metadata=metadata or {},
                extraction_quality=extraction_quality,
            )

        except Exception as e:
            try:
                performance_metrics = profiler.stop_monitoring()
                performance_metrics.exception_info = str(e)
            except Exception:
                performance_metrics = PerformanceMetrics(
                    duration_seconds=0.0,
                    memory_peak_mb=0.0,
                    memory_average_mb=0.0,
                    cpu_percent_average=0.0,
                    cpu_percent_peak=0.0,
                    gc_collections={},
                    exception_info=str(e),
                )

            return BenchmarkResult(
                name=name,
                success=False,
                performance=performance_metrics,
                metadata={
                    **(metadata or {}),
                    "error_traceback": traceback.format_exc(),
                },
            )

    def run_benchmark_suite(
        self,
        suite_name: str,
        benchmarks: list[tuple[str, Callable[[], ExtractionResult], dict[str, str] | None]],
        async_benchmarks: list[tuple[str, Callable[[], Awaitable[ExtractionResult]], dict[str, str] | None]]
        | None = None,
    ) -> BenchmarkSuite:
        start_time = time.perf_counter()
        results: list[BenchmarkResult] = []

        total_benchmarks = len(benchmarks) + (len(async_benchmarks) if async_benchmarks else 0)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Running {suite_name}", total=total_benchmarks)

            for name, func, metadata in benchmarks:
                progress.update(task, description=f"Running sync: {name}")
                result = self.run_sync_benchmark(name, func, metadata)
                results.append(result)
                progress.advance(task)

                status = "✓" if result.success else "✗"
                duration = result.performance.duration_seconds if result.performance else 0
                self.console.print(f"  {status} {name}: {duration:.3f}s")

            if async_benchmarks:

                async def run_async_suite() -> list[BenchmarkResult]:
                    async_results = []
                    for name, func, metadata in async_benchmarks:
                        progress.update(task, description=f"Running async: {name}")
                        result = await self.run_async_benchmark(name, func, metadata)
                        async_results.append(result)
                        progress.advance(task)

                        status = "✓" if result.success else "✗"
                        duration = result.performance.duration_seconds if result.performance else 0
                        self.console.print(f"  {status} {name}: {duration:.3f}s")

                    return async_results

                async_results = asyncio.run(run_async_suite())
                results.extend(async_results)

        total_duration = time.perf_counter() - start_time

        return BenchmarkSuite(
            name=suite_name,
            system_info=self.system_info,
            results=results,
            total_duration_seconds=total_duration,
        )

    def print_summary(self, suite: BenchmarkSuite) -> None:
        table = Table(title=f"Benchmark Results: {suite.name}")
        table.add_column("Benchmark", style="cyan", no_wrap=True)
        table.add_column("Status", style="green", justify="center")
        table.add_column("Duration", style="magenta", justify="right")
        table.add_column("Memory Peak", style="blue", justify="right")
        table.add_column("CPU Avg", style="yellow", justify="right")

        for result in suite.results:
            status = "✓" if result.success else "✗"
            status_style = "green" if result.success else "red"

            if result.performance:
                duration = f"{result.performance.duration_seconds:.3f}s"
                memory = f"{result.performance.memory_peak_mb:.1f}MB"
                cpu = f"{result.performance.cpu_percent_average:.1f}%"

                if result.performance.exception_info:
                    duration += f" ({result.performance.exception_info[:30]}...)"
            else:
                duration = memory = cpu = "N/A"

            table.add_row(
                result.name,
                f"[{status_style}]{status}[/{status_style}]",
                duration,
                memory,
                cpu,
            )

        self.console.print(table)

        successful = suite.successful_results
        if successful:
            total_time = sum(r.performance.duration_seconds for r in successful if r.performance)
            successful_with_perf = [r for r in successful if r.performance]
            if successful_with_perf:
                avg_time = total_time / len(successful_with_perf)
                max_memory = max(r.performance.memory_peak_mb for r in successful_with_perf if r.performance)

                self.console.print("\n[bold]Summary:[/bold]")
                self.console.print(f"  Success Rate: {suite.success_rate:.1f}%")
                self.console.print(f"  Total Time: {total_time:.3f}s")
                self.console.print(f"  Average Time: {avg_time:.3f}s")
                self.console.print(f"  Peak Memory: {max_memory:.1f}MB")
                self.console.print(f"  System: {suite.system_info.machine} ({suite.system_info.cpu_count} cores)")

    def save_results(self, suite: BenchmarkSuite, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w") as f:
            json.dump(suite.to_dict(), f, indent=2, default=str)

        self.console.print(f"\n[green]Results saved to:[/green] {output_path}")
