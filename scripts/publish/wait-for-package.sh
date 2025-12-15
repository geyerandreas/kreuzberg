#!/bin/bash
set -euo pipefail

# wait-for-package.sh - Securely wait for package availability on various registries
#
# Usage: wait-for-package.sh <registry> <package> <version> [max_attempts]
#
# Registries: npm, pypi, cratesio, maven, rubygems
# Example: wait-for-package.sh npm @kreuzberg/core 4.0.0 10

registry="$1"
package="$2"
version="$3"
max_attempts="${4:-10}"

# Strict parameter validation to prevent shell injection

# Validate version format (semantic versioning with optional pre-release/build)
# Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
if ! [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$ ]]; then
	echo "Invalid version format: $version" >&2
	echo "Expected semantic version format: X.Y.Z[-PRERELEASE][+BUILD]" >&2
	exit 1
fi

# Validate package name
# Allowed: alphanumeric, @, /, -, _, . (covers npm scoped packages and most registries)
if ! [[ "$package" =~ ^(@?[a-zA-Z0-9._/-]+)$ ]]; then
	echo "Invalid package name: $package" >&2
	echo "Package names must contain only alphanumeric characters, @, /, -, _, ." >&2
	exit 1
fi

# Validate max_attempts is numeric and positive
if ! [[ "$max_attempts" =~ ^[0-9]+$ ]] || [ "$max_attempts" -le 0 ]; then
	echo "Invalid max_attempts: $max_attempts" >&2
	echo "max_attempts must be a positive integer" >&2
	exit 1
fi

# Check package availability on the specified registry
# Uses direct command execution instead of eval() to prevent shell injection
check_package() {
	case "$registry" in
	npm)
		# Use npm view to check package version availability
		# The --json flag ensures we get machine-readable output
		npm view "${package}@${version}" version >/dev/null 2>&1
		return $?
		;;
	pypi)
		# Use pip index versions to check for package version
		# grep -qF uses fixed string matching (not regex) for safety
		pip index versions "$package" 2>/dev/null | grep -qF "$version"
		return $?
		;;
	cratesio)
		PKG="$package" VER="$version" python3 - <<'PY'
import json
import os
import sys
import urllib.request

crate = os.environ["PKG"]
version = os.environ["VER"].lstrip("v")

def index_path(crate_name: str) -> str:
    normalized = crate_name.lower()
    n = len(normalized)
    if n == 1:
        return f"1/{normalized}"
    if n == 2:
        return f"2/{normalized}"
    if n == 3:
        return f"3/{normalized[0]}/{normalized}"
    return f"{normalized[0:2]}/{normalized[2:4]}/{normalized}"

url = f"https://index.crates.io/{index_path(crate)}"
with urllib.request.urlopen(url, timeout=20) as resp:
    body = resp.read().decode("utf-8", errors="replace")

existing_versions: set[str] = set()
for line in body.splitlines():
    line = line.strip()
    if not line:
        continue
    try:
        entry = json.loads(line)
    except json.JSONDecodeError:
        continue
    if isinstance(entry, dict):
        vers = entry.get("vers")
        if isinstance(vers, str):
            existing_versions.add(vers)

sys.exit(0 if version in existing_versions else 1)
PY
		return $?
		;;
	maven)
		# Query Maven Central using straightforward HTTP call
		# Safe URL construction with direct variable substitution
		if command -v curl >/dev/null 2>&1; then
			curl -s "https://central.maven.org/search/solrsearch/select" \
				--get \
				--data-urlencode "q=g:${package}%20AND%20v:${version}" \
				--data-urlencode "rows=1" \
				--data-urlencode "wt=json" 2>/dev/null | grep -qF "\"numFound\":1" || return 1
			return 0
		else
			echo "curl is required for Maven registry check" >&2
			return 1
		fi
		;;
	rubygems)
		if command -v curl >/dev/null 2>&1; then
			PKG="$package" VER="$version" python3 - <<'PY'
import json
import os
import sys
import urllib.request

package = os.environ["PKG"]
version = os.environ["VER"].lstrip("v")

def normalize_rubygems_version(v: str) -> str:
    if "-" not in v:
        return v
    base, prerelease = v.split("-", 1)
    return f"{base}.pre.{prerelease.replace('-', '.')}"

candidates = [version]
normalized = normalize_rubygems_version(version)
if normalized != version:
    candidates.append(normalized)

url = f"https://rubygems.org/api/v1/versions/{package}.json"
with urllib.request.urlopen(url, timeout=20) as resp:
    data = json.load(resp)
existing = {entry.get("number") for entry in data if isinstance(entry, dict)}
sys.exit(0 if any(c in existing for c in candidates) else 1)
PY
			return $?
		fi

		echo "curl is required for RubyGems registry check" >&2
		return 1
		;;
	*)
		echo "Unknown registry: $registry" >&2
		echo "Supported registries: npm, pypi, cratesio, maven, rubygems" >&2
		exit 1
		;;
	esac
}

# Exponential backoff with cap at 64 seconds
# Prevents overwhelming the registry APIs while being responsive
attempt=1
while [ "$attempt" -le "$max_attempts" ]; do
	if check_package; then
		echo "✓ Package ${package}@${version} available on $registry"
		exit 0
	fi

	# Calculate exponential backoff: 2^attempt seconds, capped at 64
	sleep_time=$((2 ** attempt))
	if [ $sleep_time -gt 64 ]; then
		sleep_time=64
	fi

	# Only show waiting message if not on final attempt
	if [ "$attempt" -lt "$max_attempts" ]; then
		echo "⏳ Attempt $attempt/$max_attempts: Package not yet indexed, waiting ${sleep_time}s..."
	fi

	sleep $sleep_time
	attempt=$((attempt + 1))
done

# Timeout reached
echo "❌ Timeout: Package ${package}@${version} not indexed after $max_attempts attempts on $registry" >&2
exit 1
