#!/usr/bin/env bash
set -euo pipefail

lang="${1:?missing lang (wasm-deno|wasm-workers)}"

cargo run -p kreuzberg-e2e-generator -- generate --lang "$lang" --fixtures fixtures --output e2e
