#!/usr/bin/env bash
set -euo pipefail

cd packages/python
uv run maturin sdist --out ../../target/wheels
