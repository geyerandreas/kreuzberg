#!/usr/bin/env bash
set -euo pipefail

target="${1:-<not set>}"

set -eo pipefail
echo "=== CLI Build Diagnostics ==="
echo "Target: ${target}"
echo "Rust toolchain:"
rustc --version --verbose
echo "Cargo version:"
cargo --version
echo "PDFium environment:"
echo "  KREUZBERG_PDFIUM_PREBUILT=${KREUZBERG_PDFIUM_PREBUILT:-not set}"
if [ -n "${KREUZBERG_PDFIUM_PREBUILT:-}" ] && [ -d "${KREUZBERG_PDFIUM_PREBUILT}" ]; then
	echo "  PDFium directory exists"
	find "${KREUZBERG_PDFIUM_PREBUILT}" -maxdepth 1 -ls | head -10
fi
echo "Disk space (before build):"
df -h . || du -h . 2>/dev/null | head -1
echo "=== End diagnostics ==="
