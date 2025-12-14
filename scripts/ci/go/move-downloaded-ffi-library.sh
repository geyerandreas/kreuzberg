#!/usr/bin/env bash
set -euo pipefail

mkdir -p target/release
mkdir -p target/x86_64-pc-windows-gnu/release

find ffi-download -type f \( -name "libkreuzberg_ffi.*" -o -name "kreuzberg_ffi.*" \) | while read -r file; do
	filename="$(basename "$file")"
	if [[ "$file" == *"x86_64-pc-windows-gnu"* ]]; then
		cp "$file" target/x86_64-pc-windows-gnu/release/
		echo "Copied $filename to target/x86_64-pc-windows-gnu/release/"
	else
		cp "$file" target/release/
		echo "Copied $filename to target/release/"
	fi
done

rm -rf ffi-download
