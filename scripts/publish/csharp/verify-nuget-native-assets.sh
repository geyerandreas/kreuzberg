#!/usr/bin/env bash

set -euo pipefail

pkg="$(find artifacts/csharp -maxdepth 1 -name '*.nupkg' -print | sort | head -n 1)"
if [ -z "$pkg" ]; then
	echo "No .nupkg found under artifacts/csharp" >&2
	exit 1
fi

for rid in linux-x64 osx-arm64 win-x64; do
	unzip -l "$pkg" | grep -E "runtimes/${rid}/native/.*kreuzberg_ffi\\.(dll|so|dylib)" >/dev/null || {
		echo "Missing kreuzberg_ffi binary for $rid in $pkg" >&2
		exit 1
	}
	unzip -l "$pkg" | grep -E "runtimes/${rid}/native/.*onnxruntime" >/dev/null || {
		echo "Missing ONNX Runtime library for $rid in $pkg" >&2
		exit 1
	}
done
