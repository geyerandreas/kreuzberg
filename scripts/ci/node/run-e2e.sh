#!/usr/bin/env bash
set -euo pipefail

source scripts/lib/library-paths.sh
setup_all_library_paths

cd packages/typescript && pnpm install && cd - >/dev/null
task e2e:ts:test
