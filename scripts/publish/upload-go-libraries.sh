#!/usr/bin/env bash

# Upload Go FFI libraries to GitHub Release
#
# Uploads all Go FFI library artifacts (go-ffi-*.tar.gz) to the specified release.
# Uses gh release upload with --clobber for idempotent uploads.
#
# Environment Variables:
#   - GH_TOKEN: GitHub API token (required for gh command)
#
# Arguments:
#   $1: Release tag (e.g., v4.0.0-rc.1)
#   $2: Directory containing Go FFI artifacts (default: dist/go)

set -euo pipefail

tag="${1:?Release tag argument required}"
artifacts_dir="${2:-dist/go}"

if [ ! -d "$artifacts_dir" ]; then
	echo "Error: Artifacts directory not found: $artifacts_dir" >&2
	exit 1
fi

found_files=0
existing_assets="$(mktemp)"
trap 'rm -f "$existing_assets"' EXIT

gh release view "$tag" --json assets | jq -r '.assets[].name' >"$existing_assets" 2>/dev/null || true

for file in "$artifacts_dir"/go-ffi-*.tar.gz; do
	if [ -f "$file" ]; then
		base="$(basename "$file")"
		if grep -Fxq "$base" "$existing_assets"; then
			echo "⏭️  Skipping $base (already uploaded)"
		else
			gh release upload "$tag" "$file"
			echo "✅ Uploaded $base"
		fi
		found_files=$((found_files + 1))
	fi
done

if [ $found_files -eq 0 ]; then
	echo "❌ Error: No Go FFI artifacts found in $artifacts_dir" >&2
	exit 1
fi

echo "✅ Go FFI libraries uploaded to $tag ($found_files files)"
