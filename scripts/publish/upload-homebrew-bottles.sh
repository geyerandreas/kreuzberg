#!/usr/bin/env bash

# Upload Homebrew bottles to GitHub Release
#
# Uploads all Homebrew bottle artifacts to the specified release.
# Uses gh release upload with --clobber for idempotent uploads.
#
# Environment Variables:
#   - GH_TOKEN: GitHub API token (required for gh command)
#
# Arguments:
#   $1: Release tag (e.g., v4.0.0-rc.1)
#   $2: Directory containing bottle artifacts (default: dist/homebrew)

set -euo pipefail

tag="${1:?Release tag argument required}"
artifacts_dir="${2:-dist/homebrew}"

if [ ! -d "$artifacts_dir" ]; then
	echo "Error: Artifacts directory not found: $artifacts_dir" >&2
	exit 1
fi

existing_assets="$(mktemp)"
trap 'rm -f "$existing_assets"' EXIT

gh release view "$tag" --json assets | jq -r '.assets[].name' >"$existing_assets" 2>/dev/null || true

bottle_count=0
for file in "$artifacts_dir"/kreuzberg--*.bottle.tar.gz; do
	if [ -f "$file" ]; then
		base="$(basename "$file")"
		if grep -Fxq "$base" "$existing_assets"; then
			echo "Skipping $base (already uploaded)"
		else
			gh release upload "$tag" "$file"
			echo "Uploaded $base"
			((bottle_count++)) || true
		fi
	fi
done

if [ "$bottle_count" -eq 0 ]; then
	echo "Note: No new bottles uploaded (all may already exist in release)"
fi

echo "Homebrew bottles upload complete for $tag"
