#!/usr/bin/env bash
set -euo pipefail

target="${1:?target required}"
stage="cli-${target}"

rm -rf "$stage"
mkdir -p "$stage"
cp "target/${target}/release/kreuzberg" "$stage/"
cp LICENSE "$stage/"
cp README.md "$stage/"
tar -czf "${stage}.tar.gz" "$stage"
rm -rf "$stage"

echo "archive-path=${GITHUB_WORKSPACE}/${stage}.tar.gz" >>"$GITHUB_OUTPUT"
