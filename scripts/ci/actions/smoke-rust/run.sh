#!/usr/bin/env bash
set -euo pipefail

source_path="${1:-}"
python scripts/smoke_rust.py --workspace "${GITHUB_WORKSPACE}" --source-path "${source_path}"
