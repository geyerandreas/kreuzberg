#!/usr/bin/env bash
set -euo pipefail

echo "Verifying system PDFium linking on macOS..."
otool -L /usr/local/lib/libpdfium.dylib | head -20
export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
pkg-config --list-all | grep pdfium
