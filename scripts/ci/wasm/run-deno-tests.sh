#!/usr/bin/env bash
set -euo pipefail

cd e2e/wasm-deno
deno task test
