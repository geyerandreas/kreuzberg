#!/usr/bin/env bash
set -euo pipefail

coverage="${1:-false}"

source scripts/lib/library-paths.sh
setup_all_library_paths

if [[ "$coverage" == "true" ]]; then
	pnpm vitest run --root e2e/typescript --config vitest.config.ts --coverage
else
	pnpm vitest run --root e2e/typescript --config vitest.config.ts
fi
