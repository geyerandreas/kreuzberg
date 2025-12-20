#!/usr/bin/env bash
#
# Build Ruby gem
# Used by: ci-ruby.yaml - Build Ruby gem step
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# scripts/ci/ruby lives three levels below repo root
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"

echo "=== Building Ruby gem ==="
cd "$REPO_ROOT/packages/ruby"

echo "=== Ruby Environment ==="
echo "Ruby version: $(ruby --version)"
echo "Bundler version: $(bundle --version)"
echo "Gem version: $(gem --version)"
echo "rb_sys version: $(gem list rb_sys)"
echo "Working directory: $(pwd)"
echo ""

echo "=== Running rake compile (verbose) ==="
bundle exec rake compile --verbose --trace
echo ""

echo "=== Running rake build (verbose) ==="
bundle exec rake build --verbose --trace
echo ""

echo "=== Gem build artifacts ==="
ls -lh pkg/*.gem || echo "No gem files found"
echo ""

echo "Gem build complete"
