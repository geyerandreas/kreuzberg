#!/usr/bin/env bash

# Update Homebrew formula with bottle blocks
#
# Updates the Homebrew formula in the tap repository with pre-built bottle SHA256 hashes.
# This script:
# 1. Clones/updates the homebrew-tap repository
# 2. Extracts SHA256 hashes from bottle artifacts
# 3. Updates the formula with bottle block DSL
# 4. Creates a commit and push (if not dry-run)
#
# Environment Variables:
#   - TAG: Release tag (e.g., v4.0.0-rc.1)
#   - VERSION: Version number (e.g., 4.0.0-rc.1)
#   - DRY_RUN: Skip git operations if 'true'
#   - GITHUB_TOKEN: Required for pushing to tap (unless DRY_RUN)
#
# Arguments:
#   $1: Path to directory containing bottle artifacts
#   $2: Path to Homebrew tap repository (default: homebrew-tap)

set -euo pipefail

artifacts_dir="${1:?Artifacts directory argument required}"
tap_dir="${2:-homebrew-tap}"
tag="${TAG:?TAG not set}"
version="${VERSION:?VERSION not set}"
dry_run="${DRY_RUN:-false}"

if [ ! -d "$artifacts_dir" ]; then
	echo "Error: Artifacts directory not found: $artifacts_dir" >&2
	exit 1
fi

echo "=== Updating Homebrew formula with bottles ==="
echo "Tag: $tag"
echo "Version: $version"
echo "Artifacts: $artifacts_dir"

# Collect bottle hashes
declare -A bottle_hashes
declare -a bottle_tags

for bottle in "$artifacts_dir"/kreuzberg--*.bottle.tar.gz; do
	if [ -f "$bottle" ]; then
		filename="$(basename "$bottle")"
		# Extract bottle tag from filename (e.g., arm64_sequoia, ventura)
		# Format: kreuzberg--VERSION.BOTTLE_TAG.bottle.tar.gz
		without_suffix="${filename%.bottle.tar.gz}"
		bottle_tag="${without_suffix##*.}"
		sha256=$(shasum -a 256 "$bottle" | cut -d' ' -f1)

		bottle_hashes[$bottle_tag]=$sha256
		bottle_tags+=("$bottle_tag")
		echo "  $bottle_tag: $sha256"
	fi
done

if [ ${#bottle_hashes[@]} -eq 0 ]; then
	echo "Warning: No bottle artifacts found" >&2
	exit 1
fi

# Ensure tap directory exists
if [ ! -d "$tap_dir" ]; then
	echo "Cloning homebrew-tap..."
	git clone https://github.com/kreuzberg-dev/homebrew-tap.git "$tap_dir"
fi

formula_path="$tap_dir/Formula/kreuzberg.rb"

if [ ! -f "$formula_path" ]; then
	echo "Error: Formula not found at $formula_path" >&2
	exit 1
fi

# Read current formula
formula_content=$(<"$formula_path")

# Generate bottle block
bottle_block="  bottle do"
bottle_block+=$'\n'"    root_url \"https://github.com/kreuzberg-dev/kreuzberg/releases/download/$tag\""

for bottle_tag in "${bottle_tags[@]}"; do
	sha256=${bottle_hashes[$bottle_tag]}
	bottle_block+=$'\n'"    sha256 cellar: :any_skip_relocation, $bottle_tag: \"$sha256\""
done

bottle_block+=$'\n'"  end"

# Update the formula
# 1. Update the version, URL, and SHA256 of the source tarball
# 2. Uncomment and update the bottle block

new_formula=$(echo "$formula_content" | sed \
	-e "s/url \"https:\/\/github.com\/kreuzberg-dev\/kreuzberg\/archive\/.*\.tar\.gz\"/url \"https:\/\/github.com\/kreuzberg-dev\/kreuzberg\/archive\/$tag.tar.gz\"/" \
	-e "s/version \"[^\"]*\"/version \"$version\"/")

# Replace the commented bottle block with the new one
# First, find and remove the old commented/blank bottle block
new_formula=$(echo "$new_formula" | sed '/# bottle do/,/# end/d')

# Add the new bottle block before the first dependency
new_formula=$(echo "$new_formula" | sed "/^  depends_on/i\\
$bottle_block
")

# Write back the formula
echo "$new_formula" >"$formula_path"

# Display the changes
echo ""
echo "=== Updated formula ==="
head -30 "$formula_path"
echo "..."

# Git operations
if [ "$dry_run" = "true" ]; then
	echo ""
	echo "Dry run mode: skipping git operations"
	echo "Formula would be updated at: $formula_path"
	exit 0
fi

# Setup git
cd "$tap_dir"
git config user.name "kreuzberg-bot"
git config user.email "bot@kreuzberg.dev"

# Check if there are actual changes
if git diff --quiet Formula/kreuzberg.rb; then
	echo "No changes to formula"
	exit 0
fi

# Commit and push
git add Formula/kreuzberg.rb
git commit -m "chore(homebrew): update kreuzberg to $version

Auto-update from release $tag

Includes pre-built bottles for macOS"

echo "Pushing to homebrew-tap..."
git push origin main

echo "Formula updated successfully"
