#!/usr/bin/env bash

set -euo pipefail

target="${TARGET:?TARGET not set}"

mkdir -p crates/kreuzberg-node/artifacts
pnpm --filter @kreuzberg/node exec napi artifacts --output-dir ./artifacts
if [ ! -d crates/kreuzberg-node/npm ]; then
	echo "npm artifact directory missing" >&2
	exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
	echo "jq is required to package Node runtime dependencies" >&2
	exit 1
fi

case "$target" in
aarch64-apple-darwin)
	platform_dir="darwin-arm64"
	node_file="kreuzberg-node.darwin-arm64.node"
	pdfium_file="libpdfium.dylib"
	;;
x86_64-apple-darwin)
	platform_dir="darwin-x64"
	node_file="kreuzberg-node.darwin-x64.node"
	pdfium_file="libpdfium.dylib"
	;;
x86_64-pc-windows-msvc)
	platform_dir="win32-x64-msvc"
	node_file="kreuzberg-node.win32-x64-msvc.node"
	pdfium_file="pdfium.dll"
	;;
aarch64-pc-windows-msvc)
	platform_dir="win32-arm64-msvc"
	node_file="kreuzberg-node.win32-arm64-msvc.node"
	pdfium_file="pdfium.dll"
	;;
x86_64-unknown-linux-gnu)
	platform_dir="linux-x64-gnu"
	node_file="kreuzberg-node.linux-x64-gnu.node"
	pdfium_file="libpdfium.so"
	;;
aarch64-unknown-linux-gnu)
	platform_dir="linux-arm64-gnu"
	node_file="kreuzberg-node.linux-arm64-gnu.node"
	pdfium_file="libpdfium.so"
	;;
armv7-unknown-linux-gnueabihf)
	platform_dir="linux-arm-gnueabihf"
	node_file="kreuzberg-node.linux-arm-gnueabihf.node"
	pdfium_file="libpdfium.so"
	;;
*)
	echo "Unsupported NAPI target: $target" >&2
	exit 1
	;;
esac

dest="crates/kreuzberg-node/npm/${platform_dir}/${node_file}"
src=""

echo "Looking for NAPI binary: ${node_file} (platform: ${platform_dir}, target: ${target})"

for candidate in "crates/kreuzberg-node/artifacts/${node_file}" "crates/kreuzberg-node/${node_file}"; do
	echo "Checking: $candidate"
	if [ -f "$candidate" ]; then
		src="$candidate"
		echo "Found: $src"
		break
	fi
done

if [ -z "$src" ]; then
	echo "::error::Missing built NAPI binary: expected ${node_file}" >&2
	echo "Expected locations:" >&2
	echo "  - crates/kreuzberg-node/artifacts/${node_file}" >&2
	echo "  - crates/kreuzberg-node/${node_file}" >&2
	echo "Available .node files:" >&2
	find crates/kreuzberg-node -maxdepth 3 -type f -name "*.node" -print 2>/dev/null || echo "  (none found)"
	echo "npm directory structure:" >&2
	find crates/kreuzberg-node/npm -type d 2>/dev/null | head -20 || echo "  (npm directory not created)"
	exit 1
fi

mkdir -p "$(dirname "$dest")"
echo "Copying $src -> $dest"
cp -f "$src" "$dest"
echo "Result:"
ls -la "$(dirname "$dest")"

if [ "${INCLUDE_PDFIUM_RUNTIME:-0}" = "1" ]; then
	pdfium_src=""
	for candidate in \
		"crates/kreuzberg-node/${pdfium_file}" \
		"target/release/${pdfium_file}" \
		"target/${target}/release/${pdfium_file}"; do
		if [ -f "$candidate" ]; then
			pdfium_src="$candidate"
			break
		fi
	done

	if [ -z "$pdfium_src" ]; then
		echo "INCLUDE_PDFIUM_RUNTIME=1 but ${pdfium_file} not found; skipping." >&2
	else
		cp -f "$pdfium_src" "crates/kreuzberg-node/npm/${platform_dir}/${pdfium_file}"

		platform_pkg_json="crates/kreuzberg-node/npm/${platform_dir}/package.json"
		tmp_pkg_json="$(mktemp)"
		trap 'rm -f "$tmp_pkg_json"' EXIT
		jq --arg f "$pdfium_file" '.files |= ((. + [$f]) | unique)' "$platform_pkg_json" >"$tmp_pkg_json"
		mv "$tmp_pkg_json" "$platform_pkg_json"
	fi
fi

tar -czf "node-bindings-${target}.tar.gz" -C crates/kreuzberg-node npm
