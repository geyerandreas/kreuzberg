#!/usr/bin/env bash
set -euo pipefail

if [ -f "Cargo.lock" ]; then
	if command -v sha256sum &>/dev/null; then
		hash="$(sha256sum Cargo.lock | cut -d' ' -f1)"
	elif command -v shasum &>/dev/null; then
		hash="$(shasum -a 256 Cargo.lock | cut -d' ' -f1)"
	else
		hash="$(stat -c %Y Cargo.lock 2>/dev/null || stat -f %m Cargo.lock)"
	fi
else
	hash="$(date +%Y%m%d)"
fi

echo "hash=$hash" >>"$GITHUB_OUTPUT"
echo "Using Cargo.lock hash: $hash"
