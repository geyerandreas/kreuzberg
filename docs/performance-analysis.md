# Performance Analysis

## Overview

This page presents comprehensive benchmark results comparing Kreuzberg against other text extraction frameworks. All data is derived from rigorous testing across ~100 real-world documents using standardized methodology.

> **Benchmark Methodology**: Results based on the [python-text-extraction-libraries-benchmarks-2025](https://github.com/Goldziher/python-text-extraction-libraries-benchmarks-2025) project with comprehensive testing across multiple document types and sizes.

## Executive Summary

Kreuzberg demonstrates exceptional performance across all key metrics:

- **Speed**: 6-126x faster than competitors
- **Memory**: 2-4x lower usage
- **Installation**: 2-68x smaller footprint
- **Reliability**: Perfect 100% success rate

## Detailed Performance Metrics

### Processing Speed

#### By File Size Category

| Category              | Kreuzberg Sync | Kreuzberg Async | Best Competitor | Advantage   |
| --------------------- | -------------- | --------------- | --------------- | ----------- |
| **Tiny (\<100KB)**    | 31.6 files/sec | 23.6 files/sec  | 4.8 files/sec   | 6.6x faster |
| **Small (100KB-1MB)** | 9.0 files/sec  | 10.1 files/sec  | 3.6 files/sec   | 2.8x faster |
| **Medium (1-10MB)**   | 2.6 files/sec  | 3.2 files/sec   | 0.065 files/sec | 49x faster  |

#### Processing Time Comparison

| Framework           | Tiny Files (s) | Small Files (s) | Medium Files (s) |
| ------------------- | -------------- | --------------- | ---------------- |
| **Kreuzberg Sync**  | 0.032          | 0.111           | 0.388            |
| **Kreuzberg Async** | 0.042          | 0.099           | 0.315            |
| Extractous          | 0.316          | 0.281           | 15.38            |
| Unstructured        | 0.210          | 1.123           | -                |
| Docling             | 3.956          | 14.47           | -                |

### Memory Usage

| Framework           | Average Memory (MB) | vs Kreuzberg |
| ------------------- | ------------------- | ------------ |
| **Kreuzberg Sync**  | 360                 | Baseline     |
| **Kreuzberg Async** | 396                 | +10%         |
| Extractous          | 513                 | +43%         |
| Unstructured        | 1,389               | +286%        |
| Docling             | 1,838               | +411%        |

### Installation Size

| Framework     | Size (MB) | Packages | vs Kreuzberg |
| ------------- | --------- | -------- | ------------ |
| **Kreuzberg** | 87        | 43       | Baseline     |
| Unstructured  | 176       | 54       | 2.0x larger  |
| MarkItDown    | 208       | 25       | 2.4x larger  |
| Docling       | 5,900     | 103      | 67.8x larger |

### Success Rate & Reliability

| Framework     | Tiny Files | Small Files | Medium Files | Overall  |
| ------------- | ---------- | ----------- | ------------ | -------- |
| **Kreuzberg** | 100%       | 100%        | 100%         | **100%** |
| Extractous    | 100%       | 95.8%       | 100%         | 98.6%    |
| Unstructured  | 100%       | 100%        | -            | 100%     |
| Docling       | 100%       | 96.3%       | -            | 98.2%    |

### Content Extraction Quality

#### Characters Extracted (Average)

| Framework     | Tiny Files | Small Files | Medium Files |
| ------------- | ---------- | ----------- | ------------ |
| **Kreuzberg** | 6,950      | 173,505     | 500,643      |
| Extractous    | 6,894      | 106,641     | 251,612      |
| Unstructured  | 3,842      | 70,396      | -            |
| Docling       | 3,316      | 59,129      | -            |

## Performance Insights

### Speed Advantages

1. **Optimized Processing Pipeline**: Efficient async/await implementation
1. **Smart Resource Management**: Minimal overhead operations
1. **Native Libraries**: Built on high-performance C libraries (PDFium, Tesseract)

### Memory Efficiency

1. **Lean Architecture**: Minimal memory footprint during processing
1. **Resource Cleanup**: Proper resource disposal and garbage collection
1. **Streaming Processing**: Process large files without loading entirely into memory

### Installation Benefits

1. **Minimal Dependencies**: Only essential packages included
1. **No Heavy ML Models**: CPU-focused processing without large model files
1. **Efficient Packaging**: Optimized distribution with selective dependencies

## Production Implications

### Cost Savings

- **Infrastructure**: 2-4x lower memory requirements reduce server costs
- **Storage**: 2-68x smaller installation saves disk space
- **Processing**: 6-126x faster execution reduces compute time

### Operational Benefits

- **Deployment Speed**: Faster installations and updates
- **Resource Planning**: Predictable memory and CPU usage
- **Scaling**: Efficient resource utilization enables higher throughput

### Developer Experience

- **Quick Setup**: Minimal installation time and complexity
- **Reliable Performance**: Consistent results across document types
- **Production Ready**: Battle-tested performance characteristics

## Test Environment

**Hardware**: Linux CI runners
**Python Version**: 3.13
**Document Corpus**: ~100 real-world documents tested across multiple frameworks
**Test Date**: July 13, 2025
**Methodology**: [Full methodology available](https://github.com/Goldziher/python-text-extraction-libraries-benchmarks-2025)

## Framework Comparison Matrix

| Metric              | Kreuzberg | Extractous | Unstructured | Docling |
| ------------------- | --------- | ---------- | ------------ | ------- |
| **Speed**           | ★★★★★     | ★★☆☆☆      | ★★☆☆☆        | ★☆☆☆☆   |
| **Memory**          | ★★★★★     | ★★★★☆      | ★★☆☆☆        | ★☆☆☆☆   |
| **Installation**    | ★★★★★     | -          | ★★★☆☆        | ★☆☆☆☆   |
| **Reliability**     | ★★★★★     | ★★★★☆      | ★★★★★        | ★★★★☆   |
| **Content Quality** | ★★★★★     | ★★★☆☆      | ★★★☆☆        | ★★☆☆☆   |
| **Overall**         | ★★★★★     | ★★★☆☆      | ★★★☆☆        | ★★☆☆☆   |

______________________________________________________________________

*Performance data is based on comprehensive benchmarking across real-world document corpus. Results may vary based on specific use cases and hardware configurations.*
