#!/usr/bin/env bash
set -euo pipefail

cd crates/kreuzberg-wasm
pnpm biome check typescript
