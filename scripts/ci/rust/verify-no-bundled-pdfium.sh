#!/usr/bin/env bash
set -euo pipefail

lib_path="target/debug/libkreuzberg.a"
if [ ! -f "${lib_path}" ]; then
	lib_path="target/debug/libkreuzberg.so"
fi
if [ ! -f "${lib_path}" ]; then
	lib_path="target/debug/libkreuzberg.dylib"
fi

if [ -f "${lib_path}" ]; then
	echo "Checking for bundled pdfium symbols..."
	if nm "${lib_path}" 2>/dev/null | grep -q "FPDF_GetDocument"; then
		echo "Warning: Found PDFium symbols in library (expected with pdf feature)"
	fi
fi
