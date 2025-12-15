#!/usr/bin/env bash
set -euo pipefail

coverage="${1:-false}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

source scripts/lib/library-paths.sh
setup_all_library_paths "$repo_root"

if [[ "$coverage" == "true" ]]; then
	pnpm vitest run --root e2e/typescript --config vitest.config.ts --coverage
else
	pnpm vitest run --root e2e/typescript --config vitest.config.ts
fi
