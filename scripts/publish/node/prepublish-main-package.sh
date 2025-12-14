#!/usr/bin/env bash
set -euo pipefail

pkg_dir="${1:-crates/kreuzberg-node}"

if [ ! -d "$pkg_dir" ]; then
	echo "Package directory not found: $pkg_dir" >&2
	exit 1
fi

# `npm publish` is invoked with `--ignore-scripts` in CI for safety, so we run
# the prepublish step explicitly to ensure `optionalDependencies` for the
# platform packages are present in the published manifest.
pnpm -C "$pkg_dir" run prepublishOnly
