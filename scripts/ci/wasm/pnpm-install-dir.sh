#!/usr/bin/env bash
set -euo pipefail

dir="${1:?missing dir}"
cd "$dir"
pnpm install
