#!/usr/bin/env bash
set -euo pipefail

pkg_dir="crates/kreuzberg-wasm/pkg"
wasm_file="$pkg_dir/kreuzberg_wasm_bg.wasm"

if [ ! -f "$wasm_file" ]; then
	echo "ERROR: WASM file not found at $wasm_file"
	exit 1
fi

wasm_size=$(wc -c <"$wasm_file")
wasm_size_mb=$(echo "scale=2; $wasm_size / 1048576" | bc)
echo "WASM size (uncompressed): ${wasm_size_mb}MB (${wasm_size} bytes)"

limit_uncompressed=13631488
if [ "$wasm_size" -gt "$limit_uncompressed" ]; then
	echo "ERROR: WASM bundle exceeds 13MB limit: ${wasm_size_mb}MB"
	exit 1
fi

gzip -c "$wasm_file" >"$wasm_file.gz"
gzip_size=$(wc -c <"$wasm_file.gz")
gzip_size_mb=$(echo "scale=2; $gzip_size / 1048576" | bc)
echo "WASM size (gzipped): ${gzip_size_mb}MB (${gzip_size} bytes)"

limit_gzipped=6291456
if [ "$gzip_size" -gt "$limit_gzipped" ]; then
	echo "ERROR: Gzipped WASM exceeds 6MB limit: ${gzip_size_mb}MB"
	exit 1
fi

echo ""
echo "Bundle size check passed!"
echo "- Uncompressed: ${wasm_size_mb}MB / 13MB"
echo "- Gzipped: ${gzip_size_mb}MB / 6MB"
