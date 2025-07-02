# Kreuzberg Benchmarks

Performance benchmarking suite for the Kreuzberg text extraction library, focusing on sync vs async performance comparison and regression detection.

## Features

- **Comprehensive Performance Metrics**: Memory usage, CPU utilization, execution time
- **Sync vs Async Comparison**: Direct performance comparison between synchronous and asynchronous implementations
- **Flame Graph Generation**: Visual profiling with py-spy integration
- **JSON Output**: Structured results for CI/CD integration and historical tracking
- **Rich CLI Interface**: Beautiful terminal output with progress bars and tables
- **Regression Detection**: Automated performance regression analysis
- **CI Integration**: GitHub Actions workflow with PR comments

## Installation

From the workspace root:

```bash
# Install all workspace packages including benchmarks
uv sync --all-packages

# The CLI tool will be available
uv run kreuzberg-bench --help
```

## Usage

### Basic Benchmarking

```bash
# Run sync vs async comparison benchmarks
uv run kreuzberg-bench run --comparison-only

# Run with custom test files
uv run kreuzberg-bench run --test-files-dir /path/to/test/files

# Generate flame graphs for performance profiling
uv run kreuzberg-bench run --flame

# Run stress tests
uv run kreuzberg-bench run --stress
```

### Advanced Options

```bash
# Run only sync benchmarks
uv run kreuzberg-bench run --sync-only

# Run only async benchmarks
uv run kreuzberg-bench run --async-only

# Custom output directory
uv run kreuzberg-bench run --output-dir custom_results

# Custom suite name
uv run kreuzberg-bench run --suite-name my_benchmark_suite
```

### Analysis Commands

```bash
# Analyze benchmark results
uv run kreuzberg-bench analyze results/latest.json

# Compare two benchmark runs
uv run kreuzberg-bench compare results/baseline.json results/current.json
```

## Output Format

Results are saved in JSON format for CI integration:

```json
{
  "suite_name": "kreuzberg_sync_vs_async",
  "timestamp": "2024-07-01T07:38:05.123456",
  "summary": {
    "total_time": 0.111,
    "average_time": 0.056,
    "success_rate": 100.0,
    "peak_memory": 83165184
  },
  "benchmarks": [
    {
      "name": "comparison_sync_default",
      "success": true,
      "duration": 0.110,
      "memory_peak": 77000000,
      "cpu_avg": 26.8
    }
  ],
  "system_info": {
    "platform": "arm64",
    "cpu_count": 14,
    "python_version": "3.13.3"
  }
}
```

## CI Integration

### GitHub Actions Workflow

The benchmarking suite integrates with CI through `.github/workflows/benchmark.yml`:

#### Triggers

- **Pull Requests**: Automatic benchmark comparison
- **Main Branch**: Baseline storage for future comparisons
- **Weekly**: Scheduled comprehensive benchmarking
- **Manual**: On-demand execution with custom parameters

#### Features

- **Automated PR Comments**: Performance results posted directly to PRs
- **Regression Detection**: Automatic failure on significant performance drops
- **Artifact Storage**: 30-day retention of detailed results
- **Baseline Tracking**: Historical performance tracking on main branch

#### Example PR Comment

```markdown
## 🚀 Performance Benchmark Results

**Suite:** ci_sync_vs_async
**Total Duration:** 111.0ms
**Peak Memory:** 79.2MB
**Success Rate:** 100%

### Individual Benchmarks

| Benchmark | Status | Duration | Memory Peak | CPU Avg |
|-----------|--------|----------|-------------|----------|
| comparison_sync_default | ✅ | 110.0ms | 77.0MB | 26.8% |
| comparison_async_default | ✅ | 1.0ms | 79.2MB | 0.0% |

**System:** arm64 (14 cores)
**Python:** 3.13.3
```

### Regression Detection

Performance regressions are detected by comparing against baseline results:

```bash
# Compare current results against baseline
python ../scripts/compare_benchmarks.py \
  ../.github/benchmarks/baseline.json \
  benchmark_results/latest.json \
  --threshold 0.2 \
  --fail-on-regression
```

**Threshold**: 20% performance degradation triggers failure by default.

## Benchmark Types

### Comparison Benchmarks

- **Purpose**: Direct sync vs async performance comparison
- **Metrics**: Duration, memory usage, CPU utilization
- **Use Case**: Ensuring sync implementations aren't significantly slower

### Stress Tests

- **Purpose**: High-load performance testing
- **Metrics**: Throughput, memory scaling, error rates
- **Use Case**: Identifying performance bottlenecks under load

### Individual Component Tests

- **Purpose**: Isolated testing of specific extractors
- **Metrics**: Per-extractor performance characteristics
- **Use Case**: Optimizing specific components

## Performance Monitoring

### Key Metrics

1. **Duration**: Total execution time per benchmark
1. **Memory Peak**: Maximum memory usage during execution
1. **CPU Average**: Average CPU utilization percentage
1. **Success Rate**: Percentage of successful benchmark runs

### Expected Performance Characteristics

#### Sync vs Async Comparison

- **Sync implementations**: Should be within 20% of async performance
- **Memory usage**: Similar memory profiles between sync/async
- **CPU utilization**: May be higher for sync due to direct execution

#### Document Type Performance

- **PDF**: Text extraction ~10-50ms, OCR ~100-500ms
- **Images**: OCR processing ~50-200ms depending on size
- **Spreadsheets**: Processing ~10-100ms depending on size
- **Office Documents**: Pandoc processing ~50-200ms

## Flame Graph Profiling

For detailed performance analysis, flame graphs can be generated:

```bash
# Generate flame graphs
uv run kreuzberg-bench run --flame

# Results include SVG flame graphs
ls benchmark_results/flame_graphs/
```

**Requirements**: Requires `py-spy` for CPU profiling.

## Development

### Adding New Benchmarks

1. **Define Benchmark Function**:

    ```python
    def benchmark_new_feature():
        # Your benchmark code here
        return result
    ```

1. **Register with Suite**:

    ```python
    # In benchmarks.py
    ("new_feature_sync", benchmark_new_feature, {"type": "sync"})
    ```

1. **Test Locally**:

    ```bash
    uv run kreuzberg-bench run --sync-only
    ```

### Profiling Integration

Custom profilers can be integrated through the `BenchmarkRunner` class:

```python
from kreuzberg_benchmarks import BenchmarkRunner

runner = BenchmarkRunner()
runner.add_profiler(my_custom_profiler)
results = runner.run_benchmark_suite(benchmarks)
```

## Troubleshooting

### Common Issues

#### Benchmark Failures

```bash
# Check detailed error information
cat benchmark_results/latest.json | jq '.benchmarks[] | select(.success == false)'
```

#### Missing Dependencies

```bash
# Ensure all system dependencies are installed
sudo apt-get install pandoc tesseract-ocr  # Linux
brew install pandoc tesseract              # macOS
```

#### Performance Variations

- **System Load**: Run benchmarks on idle systems
- **File System**: SSD vs HDD can significantly impact results
- **Python Version**: Different versions may show performance differences

### Best Practices

1. **Consistent Environment**: Run benchmarks in consistent environments
1. **Multiple Runs**: Average results across multiple runs for stability
1. **Baseline Updates**: Update baselines when significant improvements are made
1. **Load Testing**: Include stress tests for production readiness

## Architecture

The benchmarking suite consists of:

- **CLI (`cli.py`)**: Command-line interface using Typer
- **Benchmarks (`benchmarks.py`)**: Benchmark definitions and test data
- **Runner (`runner.py`)**: Execution engine with profiling support
- **Models (`models.py`)**: Data structures for results and configuration
- **Profiler (`profiler.py`)**: Performance metric collection utilities

## Contributing

When adding new benchmarks:

1. Follow the existing naming convention: `{type}_{component}_{test_case}`
1. Include appropriate metadata for filtering and analysis
1. Test both sync and async variants where applicable
1. Update this README with any new features or requirements
