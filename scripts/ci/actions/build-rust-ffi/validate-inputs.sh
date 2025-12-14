#!/usr/bin/env bash
set -euo pipefail

crate_name="${CRATE_NAME:?CRATE_NAME required}"
features="${FEATURES:-}"
target="${TARGET:-}"
build_profile="${BUILD_PROFILE:-release}"
verbose="${VERBOSE:-true}"
additional_flags="${ADDITIONAL_FLAGS:-}"

echo "=== Rust FFI Build Configuration ==="
echo "Crate: ${crate_name}"
echo "Features: ${features:-default}"
echo "Target: ${target:-host}"
echo "Profile: ${build_profile}"
echo "Verbose: ${verbose}"
echo "Additional flags: ${additional_flags:-none}"
echo ""

if [ ! -f "crates/${crate_name}/Cargo.toml" ]; then
	if [ ! -f "packages/ruby/ext/kreuzberg_rb/native/Cargo.toml" ] || [ "$crate_name" != "kreuzberg-rb" ]; then
		echo "Error: Crate '${crate_name}' not found in crates/ or packages/ruby/ext/kreuzberg_rb/native/" >&2
		exit 1
	fi
fi

echo "✓ Crate validation passed"
