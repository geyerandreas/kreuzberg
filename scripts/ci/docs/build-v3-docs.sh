#!/usr/bin/env bash
set -euo pipefail

echo "Building v3 docs from v3/ subdirectory..."

cp mkdocs.yaml mkdocs-v3.yaml
sed -i 's|paths: \\[packages/python\\]|paths: [v3]|g' mkdocs-v3.yaml

echo "Building v3 docs..."
uv run mike deploy --config-file mkdocs-v3.yaml 3.0 v3

echo "Cleaning up temporary config..."
rm -f mkdocs-v3.yaml
