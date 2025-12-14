#!/usr/bin/env bash
set -euo pipefail

cd crates/kreuzberg-wasm
pnpm pack

wasm_pkg_path="$(pwd)/$(ls kreuzberg-wasm-*.tgz)"
echo "WASM_PKG_PATH=$wasm_pkg_path" >>"$GITHUB_ENV"
