#!/usr/bin/env bash
set -euo pipefail

target="${1:?missing target (web|bundler|nodejs|deno)}"

cd crates/kreuzberg-wasm
pnpm run "build:wasm:${target}"
