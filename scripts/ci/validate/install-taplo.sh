#!/usr/bin/env bash
set -euo pipefail

bash scripts/ci/validate/show-disk-space.sh "Before taplo installation"

if ! command -v taplo >/dev/null 2>&1; then
	cargo install taplo-cli --locked
fi

rm -rf ~/.cargo/registry/cache/* ~/.cargo/git/db/* 2>/dev/null || true

bash scripts/ci/validate/show-disk-space.sh "After taplo installation and cleanup"
