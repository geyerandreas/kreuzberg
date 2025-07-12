# Performance & Benchmarks

**Kreuzberg is the fastest document extraction framework for Python** - and we have the data to prove it.

## 🏆 Industry Benchmarks

Our [comprehensive benchmark suite](https://github.com/Goldziher/python-text-extraction-libs-benchmarks) tests real-world performance across 94 documents (~210MB) including:

- **📄 Document Types**: PDFs, Word docs, HTML, images, spreadsheets, presentations
- **🌍 Languages**: English, Hebrew, German, Chinese, Japanese, Korean
- **📏 Size Range**: Small forms to large technical documents (1KB - 50MB+)
- **🔬 Methodology**: Consistent hardware, controlled environment, reproducible tests

## 📊 Head-to-Head Comparison

| Framework     | Speed           | Memory Peak | Install Size | Dependencies | Success Rate | Production Ready         |
| ------------- | --------------- | ----------- | ------------ | ------------ | ------------ | ------------------------ |
| **Kreuzberg** | **35+ files/s** | **530MB**   | **71MB**     | **20**       | **95%+**     | ✅ **Yes**               |
| Unstructured  | ~12 files/s     | ~1GB        | 146MB        | 54           | 88%+         | ⚠️ Memory intensive      |
| MarkItDown    | ~15 files/s     | ~1.5GB      | 251MB        | 25           | 80%          | ⚠️ Fails on complex docs |
| Docling       | 0.017 files/s   | ~5GB        | **1,032MB**  | 88           | **45%**      | ❌ **Not viable**        |

## 🚀 Performance Advantages

### Speed Leadership

- **2-3x faster** than closest competitor
- **2000x faster** than IBM Docling
- Async processing delivers **up to 4.5x speedup** on batch workloads
- Intelligent multi-threading optimizes CPU utilization

### Memory Efficiency

- **Lowest memory footprint** of any framework
- **14x smaller** install size than alternatives
- Streaming processing prevents memory bloat on large documents
- Smart caching reduces redundant processing

### Resource Optimization

- **Minimal CPU usage** through optimized algorithms
- **Fewest dependencies** (20 vs 88 for competitors)
- **Cold start optimized** for serverless environments
- **No GPU requirements** - runs anywhere

## 🔬 Technical Deep Dive

### Why Kreuzberg is Faster

1. **Engineer-Built Architecture**: Designed by software engineers, not data scientists

    - Optimal Python patterns and algorithms
    - Efficient memory management
    - Minimal overhead and abstractions

1. **Async-First Design**: True async/await throughout the stack

    - Non-blocking I/O operations
    - Concurrent document processing
    - Intelligent work scheduling

1. **Smart Extraction Logic**: Intelligent fallback strategies

    - Fast path for searchable PDFs
    - OCR only when necessary
    - Cached results for repeated processing

1. **Optimized Dependencies**: Curated, minimal dependency tree

    - No bloated ML frameworks unless needed
    - Lean core with optional extras
    - Fast import times

### Benchmark Methodology

Our benchmarks are **completely transparent and reproducible**:

```bash
# Run benchmarks yourself
git clone https://github.com/Goldziher/python-text-extraction-libs-benchmarks
cd python-text-extraction-libs-benchmarks
python benchmark.py --all-frameworks
```

**Test Environment:**

- AWS EC2 c5.2xlarge (8 vCPU, 16GB RAM)
- Python 3.11, latest versions of all frameworks
- Same document corpus for all tests
- Multiple runs averaged for statistical significance

## 🎯 Real-World Performance

### Batch Processing Scenarios

| Document Count | Kreuzberg (Async) | Kreuzberg (Sync) | Unstructured | Time Savings   |
| -------------- | ----------------- | ---------------- | ------------ | -------------- |
| 10 PDFs        | **8.5s**          | 12.3s            | 24.7s        | **65% faster** |
| 100 PDFs       | **1m 25s**        | 2m 45s           | 6m 12s       | **77% faster** |
| 1000 PDFs      | **14m 10s**       | 27m 30s          | 62m 5s       | **77% faster** |

### Memory Usage Under Load

| Concurrent Jobs | Kreuzberg | Unstructured | Memory Savings |
| --------------- | --------- | ------------ | -------------- |
| 1 document      | 530MB     | 1.1GB        | **52% less**   |
| 10 concurrent   | 680MB     | 2.8GB        | **76% less**   |
| 50 concurrent   | 1.2GB     | 8.5GB        | **86% less**   |

## 💰 Cost Impact

### Infrastructure Savings

The performance advantages translate directly to cost savings:

#### Cloud Functions (AWS Lambda)

- **Execution time**: 65-77% reduction = 65-77% cost savings
- **Memory allocation**: Can use smaller instances = additional 50% savings
- **Cold starts**: 14x smaller package = faster cold starts

#### Container Deployments

- **Smaller images**: 71MB vs 1GB+ = faster deployments, less storage
- **Memory efficiency**: Can run more containers per host
- **CPU optimization**: Better resource utilization

#### Development Velocity

- **Faster tests**: 95%+ test coverage runs in seconds, not minutes
- **Quick feedback**: Local development doesn't require powerful machines
- **Simple debugging**: Clean codebase and excellent error messages

## 🔍 Quality & Reliability

### Test Coverage

- **95%+ code coverage** across all modules
- **1,100+ automated tests** covering edge cases
- **Property-based testing** for algorithm validation
- **Integration tests** with real documents

### Production Reliability

- **Battle-tested** in production environments
- **Graceful error handling** with detailed context
- **Comprehensive logging** for debugging
- **Health checks** and monitoring ready

### Quality Metrics

- **Type safety**: 100% type coverage with mypy
- **Code quality**: Consistent formatting with ruff
- **Security**: No known vulnerabilities
- **Maintenance**: Active development and quick issue resolution

## 🚀 Getting Maximum Performance

### Async Best Practices

```python
import asyncio
from kreuzberg import batch_extract_files

async def process_documents():
    # Batch processing for maximum throughput
    files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    results = await batch_extract_files(files)
    return results

# Up to 4.5x faster than sync processing
asyncio.run(process_documents())
```

### Configuration Tuning

```python
from kreuzberg import ExtractionConfig, extract_file

# Optimize for speed
fast_config = ExtractionConfig(
    force_ocr=False,  # Use searchable text when available
    quality_processing=False,  # Skip cleanup for raw speed
)

result = await extract_file("document.pdf", config=fast_config)
```

### Memory Optimization

```python
# For high-volume processing
efficient_config = ExtractionConfig(
    chunk_content=True,  # Enable chunking for large docs
    chunk_size=1000,  # Smaller chunks for memory efficiency
)
```

## 🌱 Environmental Impact & Sustainability

### Green Computing Choice

Kreuzberg is the **environmentally responsible choice** for document processing:

#### CPU-Only Processing

- **No GPU required** - runs efficiently on standard CPU-only machines
- **Lower power consumption** compared to GPU-accelerated alternatives
- **Reduced hardware costs** - no expensive GPU instances needed
- **Better hardware utilization** of existing infrastructure

#### Energy Efficiency

- **14x smaller footprint** means less storage and bandwidth usage
- **Faster processing** = shorter execution times = less energy consumption
- **Efficient algorithms** minimize CPU cycles per document
- **Smart caching** reduces redundant processing

### Sustainable Infrastructure

| Resource Type | Kreuzberg Impact                    | Environmental Benefit             |
| ------------- | ----------------------------------- | --------------------------------- |
| **Compute**   | CPU-only, 65% faster execution      | **65% less energy** per job       |
| **Storage**   | 71MB vs 1GB+ packages               | **93% less** storage footprint    |
| **Memory**    | 530MB vs 5GB peak usage             | **89% less** memory requirements  |
| **Network**   | Smaller containers, fewer downloads | **Reduced bandwidth** consumption |

### Carbon Footprint Reduction

**Cloud Deployment Benefits:**

- **Shorter execution times** = lower cloud compute costs and energy usage
- **Smaller instance sizes** = reduced datacenter resource requirements
- **Less data transfer** = lower network infrastructure load
- **Efficient scaling** = better resource utilization during peak loads

**On-Premise Benefits:**

- **Longer hardware lifespan** - no need for expensive GPU upgrades
- **Lower cooling requirements** - CPU-only processing generates less heat
- **Reduced e-waste** - maximizes utility of existing hardware
- **Energy cost savings** - significant reduction in electricity usage

### Responsible AI Development

Unlike competitors that rely on massive GPU clusters for processing:

- ✅ **Kreuzberg**: Efficient CPU algorithms, minimal resource usage
- ❌ **GPU-based solutions**: Require expensive, power-hungry hardware
- ❌ **Cloud API services**: Hidden environmental costs in remote datacenters
- ❌ **Bloated frameworks**: Wasteful resource consumption

**Choose Kreuzberg** for faster performance AND environmental responsibility.

______________________________________________________________________

**Ready to experience the fastest document extraction?** [Get started now](getting-started/installation.md) and see the performance difference for yourself.
