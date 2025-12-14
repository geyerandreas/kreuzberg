#!/usr/bin/env bash
set -euo pipefail

version="${1:?version required}"

task_bin_dir="${HOME}/.local/bin"
mkdir -p "$task_bin_dir"

if ! command -v task >/dev/null 2>&1 || [[ "$(task --version 2>/dev/null || echo '')" != *"$version"* ]]; then
	sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b "$task_bin_dir"
fi

echo "$task_bin_dir" >>"$GITHUB_PATH"
