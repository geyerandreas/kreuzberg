#!/usr/bin/env bash

# Extract SHA256 hashes from Homebrew bottles
#
# Extracts the SHA256 hash from each bottle file by running shasum -a 256
# and outputs them as GitHub Actions outputs for use in formula updates.
#
# Environment Variables:
#   - GITHUB_OUTPUT: GitHub Actions output file path
#
# Arguments:
#   $1: Directory containing bottle artifacts

set -euo pipefail

artifacts_dir="${1:?Artifacts directory argument required}"

if [ ! -d "$artifacts_dir" ]; then
	echo "Error: Artifacts directory not found: $artifacts_dir" >&2
	exit 1
fi

echo "Extracting bottle hashes from: $artifacts_dir"

# Extract SHA256 for each bottle
for bottle in "$artifacts_dir"/kreuzberg--*.bottle.tar.gz; do
	if [ -f "$bottle" ]; then
		filename="$(basename "$bottle")"

		# Extract bottle tag (e.g., arm64_sequoia, ventura) from filename
		# Format: kreuzberg--VERSION.BOTTLE_TAG.bottle.tar.gz
		without_suffix="${filename%.bottle.tar.gz}"
		bottle_tag="${without_suffix##*.}"

		# Calculate SHA256
		sha256=$(shasum -a 256 "$bottle" | cut -d' ' -f1)

		# Add to GitHub output
		echo "${bottle_tag}=${sha256}" >>"${GITHUB_OUTPUT:?GITHUB_OUTPUT not set}"

		echo "  $bottle_tag: $sha256"
	fi
done

echo "Bottle hashes extracted"
