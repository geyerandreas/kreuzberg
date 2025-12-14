#!/usr/bin/env bash
set -euo pipefail

echo "Verifying system PDFium linking on Linux..."
ldd /usr/local/lib/libpdfium.so | head -20
pkg-config --list-all | grep pdfium
