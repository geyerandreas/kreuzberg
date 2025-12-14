#!/usr/bin/env bash
set -euo pipefail

target_sha="${1:?target sha required}"

# Validate SHA format (40 hex chars for full SHA-1, or 7-40 for abbreviated)
if ! [[ "$target_sha" =~ ^[0-9a-fA-F]{7,40}$ ]]; then
	echo "ERROR: Invalid commit SHA format: $target_sha" >&2
	echo "Expected: 7-40 hexadecimal characters" >&2
	exit 1
fi

echo "Ensuring target commit: $target_sha"

# Verify the commit exists before checking it out
if ! git cat-file -t "$target_sha" >/dev/null 2>&1; then
	echo "ERROR: Commit SHA not found in repository: $target_sha" >&2
	exit 1
fi

git checkout --progress --force "$target_sha"

# Verify we checked out the intended commit
current_sha="$(git rev-parse HEAD)"
if [[ ! "$current_sha" =~ ^$target_sha ]]; then
	echo "ERROR: Checkout verification failed. Expected commit starting with $target_sha, got $current_sha" >&2
	exit 1
fi

echo "Successfully checked out commit: $current_sha"
