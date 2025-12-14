#!/usr/bin/env bash
set -euo pipefail

target="${1:?target required}"
use_cross="${2:-false}"

pnpm install

if [[ "$use_cross" == "true" ]]; then
	pnpm run build --target "$target" --use-cross
else
	pnpm run build --target "$target"
fi

binding="$(find . -name "*.node" -type f | head -n 1)"
if [[ -z "$binding" ]]; then
	echo "No .node binding file found" >&2
	exit 1
fi

echo "binding-path=${GITHUB_WORKSPACE}/crates/kreuzberg-node/$binding" >>"$GITHUB_OUTPUT"
