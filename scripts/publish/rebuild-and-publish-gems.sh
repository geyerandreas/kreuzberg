#!/usr/bin/env bash

# Rebuild and publish Ruby gems to RubyGems
#
# This script:
# 1. Ensures latest RubyGems is installed
# 2. Unpacks each gem and extracts its gemspec
# 3. Rebuilds the gem to ensure consistent structure (fixes corruption from artifact transfer)
# 4. Validates the rebuilt gems
# 5. Publishes using 'gem push'
#
# Environment Variables:
#   - GEM_ARTIFACTS_DIR: Directory containing gem files (default: .)

set -euo pipefail

artifacts_dir="${1:-$(pwd)}"

# Change to artifacts directory
cd "$artifacts_dir" || {
	echo "Error: Cannot change to directory: $artifacts_dir" >&2
	exit 1
}

# Ensure we're using latest RubyGems when possible.
# Hosted runners install RubyGems via apt, which rejects in-place upgrades.
if ! gem update --system; then
	echo "::warning::Skipping RubyGems update; system RubyGems installation does not support self-update (apt-managed runner)." >&2
fi

# Find all gem files
shopt -s nullglob
mapfile -t gems < <(find . -maxdepth 1 -name 'kreuzberg-*.gem' -print | sort)

if [ ${#gems[@]} -eq 0 ]; then
	echo "No gem artifacts found in $artifacts_dir" >&2
	exit 1
fi

# Rebuild each gem to ensure consistent structure
# This fixes any corruption that occurred during artifact download/merge
echo "Rebuilding gems to fix potential corruption from artifact transfer..."
for gem in "${gems[@]}"; do
	echo "Rebuilding ${gem} to ensure consistent structure"

	# Validate gzip integrity before attempting unpack
	echo "Checking gzip integrity of ${gem}..."
	if ! gunzip -t "${gem}" 2>/dev/null; then
		echo "::warning::Gem ${gem} has corrupted gzip structure, attempting repair..." >&2

		# Check if file has gzip magic number (1f 8b)
		if ! xxd -p -l 2 "${gem}" | grep -q "^1f8b"; then
			echo "::error::Gem ${gem} is not a valid gzip file (missing magic number)" >&2
			exit 1
		fi

		# Attempt to repair by decompressing and recompressing
		echo "Attempting gzip repair for ${gem}..."
		temp_dir=$(mktemp -d)
		if gunzip -c "${gem}" >"${temp_dir}/uncompressed" 2>/dev/null; then
			gzip -9 -c "${temp_dir}/uncompressed" >"${gem}.repaired"
			mv "${gem}.repaired" "${gem}"
			echo "Successfully repaired ${gem}"
		else
			echo "::error::Cannot repair ${gem} - gzip structure is too damaged" >&2
			rm -rf "${temp_dir}"
			exit 1
		fi
		rm -rf "${temp_dir}"
	else
		echo "✓ Gzip integrity check passed for ${gem}"
	fi

	# Unpack the gem
	gem unpack "${gem}"
	gem_name=$(basename "${gem}" .gem)

	# Extract gemspec from gem metadata
	gem specification "${gem}" --ruby >"${gem_name}/${gem_name}.gemspec"

	# Rebuild the gem from extracted source
	(cd "${gem_name}" && gem build "${gem_name}.gemspec")

	# Replace original gem with rebuilt one
	mv "${gem_name}/${gem}" "./${gem}"

	# Cleanup
	rm -rf "${gem_name}"

	echo "Rebuilt ${gem} successfully"
done

echo "All gems rebuilt successfully"
echo ""

# Validate rebuilt gem files
echo "Validating rebuilt gem files..."
for gem in "${gems[@]}"; do
	echo "Checking $gem..."

	# Check if file is readable and non-empty
	if [ ! -f "$gem" ] || [ ! -r "$gem" ] || [ ! -s "$gem" ]; then
		echo "::error::Gem file is invalid (missing, unreadable, or empty): $gem" >&2
		exit 1
	fi

	# Check file type (gems should be uncompressed tar archives)
	file_output=$(file "$gem" 2>/dev/null || echo "")
	echo "File type: $file_output"

	# Verify gem is valid using gem spec
	echo "Validating gem with gem spec..."
	if ! gem spec "$gem" >/dev/null 2>&1; then
		echo "::error::Gem file validation failed: $gem" >&2
		echo "File type: $(file "$gem")" >&2
		exit 1
	fi
	echo "✓ Gem file validation passed"
done

echo "All gem files validated successfully"
echo ""

# Publish gems to RubyGems
echo "Publishing gems to RubyGems..."
failed_gems=()
for gem in "${gems[@]}"; do
	echo "Pushing ${gem} to RubyGems"
	publish_log=$(mktemp)
	set +e
	gem push "$gem" 2>&1 | tee "$publish_log"
	status=${PIPESTATUS[0]}
	set -e

	if [ "$status" -ne 0 ]; then
		if grep -qE "Repushing of gem versions is not allowed|already been pushed" "$publish_log"; then
			echo "::notice::Gem $gem version already published on RubyGems; skipping."
			if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
				echo "Gem $(basename "$gem") already published; skipping." >>"$GITHUB_STEP_SUMMARY"
			fi
		else
			failed_gems+=("$gem")
		fi
	fi

	rm -f "$publish_log"
done

if [ ${#failed_gems[@]} -gt 0 ]; then
	echo "::error::Failed to publish the following gems:" >&2
	for gem in "${failed_gems[@]}"; do
		echo "  - $gem" >&2
	done
	exit 1
fi

if [ -n "${GITHUB_STEP_SUMMARY:-}" ] && [ -n "${RUBYGEMS_VERSION:-}" ]; then
	echo "Successfully published kreuzberg version ${RUBYGEMS_VERSION} to RubyGems" >>"$GITHUB_STEP_SUMMARY"
fi

echo "All gems processed"
