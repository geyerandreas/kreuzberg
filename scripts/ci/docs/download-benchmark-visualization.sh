#!/usr/bin/env bash
set -euo pipefail

run_id="${1:?Usage: $0 <benchmark-run-id>}"

gh run download "$run_id" --name benchmark-visualization-html --dir benchmark-viz-temp

mkdir -p docs/benchmarks/charts
cp -r benchmark-viz-temp/* docs/benchmarks/charts/

echo "Benchmark visualization downloaded and deployed"
