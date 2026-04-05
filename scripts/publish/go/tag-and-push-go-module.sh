#!/usr/bin/env bash
set -euo pipefail

tag="${1:?Release tag argument required (e.g. v4.0.0-rc.7)}"

version="${tag#v}"
# Extract major version for the Go module subdirectory path.
# Go module at packages/go/v4 requires tags of the form packages/go/v4/vX.Y.Z
major="${version%%.*}"
module_tag="packages/go/v${major}/${tag}"

if git rev-parse "$module_tag" >/dev/null 2>&1; then
  echo "::notice::Go module tag $module_tag already exists locally; skipping."
  exit 0
fi

# Check if tag exists on remote
if git ls-remote --tags origin | grep -q "refs/tags/${module_tag}$"; then
  echo "::notice::Go module tag $module_tag already exists on remote; skipping."
  exit 0
fi

# Resolve the commit SHA the release tag points to
sha=$(git rev-parse "$tag^{commit}")

# Create tag locally
git tag "$module_tag" "$tag"

# Push via the GitHub API to avoid the GITHUB_TOKEN 'workflows' permission
# restriction that blocks `git push` when the repo contains workflow files.
repo="${GITHUB_REPOSITORY:-kreuzberg-dev/kreuzberg}"
gh api "repos/${repo}/git/refs" \
  -f "ref=refs/tags/${module_tag}" \
  -f "sha=${sha}" \
  --silent

echo "✅ Go module tag created: $module_tag (sha: ${sha:0:12})"
