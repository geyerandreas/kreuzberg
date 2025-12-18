#!/usr/bin/env bash

# Prepare Node package artifacts for publishing
#
# Unpacks Node binding tarballs and organizes npm packages.
# Merges TypeScript definitions if available.
#
# Arguments:
#   $1: Node artifacts source directory (default: node-artifacts)
#   $2: TypeScript defs source directory (default: typescript-defs)
#   $3: Destination directory (default: crates/kreuzberg-node)

set -euo pipefail

artifacts_dir="${1:-node-artifacts}"
typescript_defs_dir="${2:-typescript-defs}"
dest_dir="${3:-crates/kreuzberg-node}"

if [ ! -d "$artifacts_dir" ]; then
	echo "Error: Artifacts directory not found: $artifacts_dir" >&2
	exit 1
fi

# Clean and prepare destination
rm -rf "$dest_dir/npm"
mkdir -p "$dest_dir/npm"

shopt -s nullglob
for pkg in "$artifacts_dir"/*.tar.gz; do
	echo "Unpacking $pkg"
	tmpdir=$(mktemp -d)
	tar -xzf "$pkg" -C "$tmpdir"

	# Tarballs now contain platform directories directly (darwin-arm64/, linux-x64-gnu/, etc)
	# Find all platform directories and copy them
	echo "Contents of $tmpdir:"
	find "$tmpdir" -maxdepth 2 -type d

	# Copy all platform directories found at top level
	while IFS= read -r -d '' platform_dir; do
		dir_name=$(basename "$platform_dir")
		echo "Processing platform directory: $dir_name"

		dest="$dest_dir/npm/$dir_name"
		echo "  Destination: $dest"

		# Verify directory contains files before copying
		if [ -z "$(find "$platform_dir" -maxdepth 1 -type f -print -quit)" ]; then
			echo "  ⚠ Warning: $dir_name appears to be empty, skipping"
			continue
		fi

		# Remove existing to avoid conflicts, then copy
		rm -rf "$dest"
		cp -R "$platform_dir" "$dest"

		# Verify copy succeeded
		if [ -d "$dest" ]; then
			file_count=$(find "$dest" -type f | wc -l)
			echo "  ✓ Copied successfully ($file_count files)"
		else
			echo "  ✗ ERROR: Copy failed!"
		fi
	done < <(find "$tmpdir" -mindepth 1 -maxdepth 1 -type d -print0)

	rm -rf "$tmpdir"
done

echo ""
echo "=== Final npm directory structure ==="
find "$dest_dir/npm" -type f | sort

# Merge TypeScript definitions if available
if [ -d "$typescript_defs_dir" ]; then
	cp "$typescript_defs_dir"/index.js "$typescript_defs_dir"/index.d.ts "$dest_dir/" || true
	echo "TypeScript definitions merged"
fi

echo "Node artifacts prepared successfully"
