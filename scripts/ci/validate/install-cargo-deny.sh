#!/usr/bin/env bash
set -euo pipefail

bash scripts/ci/validate/show-disk-space.sh "Before cargo-deny installation"

cargo install cargo-deny --locked

rm -rf ~/.cargo/registry/cache/* ~/.cargo/git/db/* 2>/dev/null || true

bash scripts/ci/validate/show-disk-space.sh "After cargo-deny installation and cleanup"
