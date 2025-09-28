from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

from .aggregate import ResultAggregator
from .benchmark import ComprehensiveBenchmarkRunner
from .logger import get_logger
from .types import BenchmarkConfig, DocumentCategory, Framework

console = Console()
logger = get_logger(__name__)


@click.command()
@click.option(
    "--iterations",
    "-i",
    type=int,
    default=3,
    help="Number of benchmark iterations",
)
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=300,
    help="Timeout in seconds for each extraction",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    default="results/aggregated.json",
    help="Output file for aggregated results",
)
def main(iterations: int, timeout: int, output: Path) -> None:
    """Run benchmarks for all frameworks and categories."""
    console.print("[bold]Starting Benchmark Suite[/bold]")
    console.print(f"  Iterations: {iterations}")
    console.print(f"  Timeout: {timeout}s")
    console.print(f"  Output: {output}")
    console.print()

    # Always use all frameworks and categories
    frameworks = list(Framework)
    categories = list(DocumentCategory)

    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)

    config = BenchmarkConfig(
        frameworks=frameworks,
        categories=categories,
        file_types=None,
        iterations=iterations,
        warmup_runs=1,
        timeout_seconds=timeout,
        output_dir=output_dir,
        continue_on_error=True,
        max_run_duration_minutes=360,
        save_extracted_text=False,
        enable_quality_assessment=False,
    )

    console.print("[cyan]Running benchmarks...[/cyan]")

    runner = ComprehensiveBenchmarkRunner(config)
    runner.use_subprocess_isolation = True

    try:
        results = asyncio.run(runner.run_benchmark_suite())
        console.print(f"[green]✓ Completed {len(results)} benchmarks[/green]")

        # Aggregate results immediately
        console.print("[cyan]Aggregating results...[/cyan]")
        aggregator = ResultAggregator()
        aggregated = aggregator.aggregate_results([output_dir])

        # Save to output file
        output.parent.mkdir(parents=True, exist_ok=True)
        aggregator.save_results(aggregated, output.parent, output.name)
        console.print(f"[green]✓ Results saved to {output}[/green]")

    except KeyboardInterrupt:
        console.print("[yellow]Benchmark interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Benchmark failed: {e}[/red]")
        logger.error("Benchmark failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
