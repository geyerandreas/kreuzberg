#!/usr/bin/env bash
set -euo pipefail

pkg_dir="crates/kreuzberg-wasm/pkg"

echo "Checking for generated type definitions..."

required_files=(
	"$pkg_dir/kreuzberg_wasm.d.ts"
	"$pkg_dir/index.d.ts"
)

for file in "${required_files[@]}"; do
	if [ ! -f "$file" ]; then
		echo "ERROR: Type definition file not found: $file"
		exit 1
	fi
	echo "Found: $file"
done

echo ""
echo "Type definitions validation passed!"
