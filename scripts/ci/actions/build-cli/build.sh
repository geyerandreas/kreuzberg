#!/usr/bin/env bash
set -euo pipefail

target="${1:?target required}"
use_cross="${2:-false}"

if [[ "$use_cross" == "true" ]]; then
	cross build --release --target "$target" --package kreuzberg-cli
else
	cargo build --release --target "$target" --package kreuzberg-cli
fi
