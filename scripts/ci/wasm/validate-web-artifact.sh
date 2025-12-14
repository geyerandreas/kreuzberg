#!/usr/bin/env bash
set -euo pipefail

pkg_dir="crates/kreuzberg-wasm/pkg"
if [ ! -f "$pkg_dir/kreuzberg_wasm_bg.wasm" ]; then
	echo "ERROR: Web WASM artifact not found"
	exit 1
fi

echo "Web WASM artifact validated: $pkg_dir/kreuzberg_wasm_bg.wasm"
