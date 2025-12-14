#!/usr/bin/env bash
set -euo pipefail

variant="${1:?missing variant}"

echo "=== Running Docker feature tests (${variant}) ==="
./scripts/test_docker.sh --skip-build --image "kreuzberg:${variant}" --variant "${variant}" --verbose
