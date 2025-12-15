#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

source scripts/lib/library-paths.sh
setup_all_library_paths "$repo_root"

cd packages/typescript && pnpm install && cd - >/dev/null
task e2e:ts:test
