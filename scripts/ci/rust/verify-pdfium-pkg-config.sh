#!/usr/bin/env bash
set -euo pipefail

if [ "${RUNNER_OS:-}" = "macOS" ]; then
	export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
fi

pkg-config --modversion pdfium
pkg-config --cflags --libs pdfium
