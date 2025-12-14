#!/usr/bin/env bash
set -euo pipefail

gem_path="${1:-}"

tmp="$(mktemp -d)"
cp -R e2e/smoke/ruby/. "$tmp"/
pushd "$tmp" >/dev/null

bundle config set --local path vendor/bundle

if [[ -n "$gem_path" ]]; then
	if [[ "$gem_path" != /* ]]; then
		gem_path="${GITHUB_WORKSPACE}/${gem_path}"
	fi
	echo "Looking for gems in: $gem_path"
	if [[ -d "$gem_path" ]]; then
		gem_file="$(find "$gem_path" -name "*.gem" -type f | head -n 1)"
	else
		gem_file="$gem_path"
	fi

	if [[ -z "${gem_file:-}" || ! -f "$gem_file" ]]; then
		echo "No gem found at $gem_path" >&2
		ls -la "$gem_path" >&2 || true
		exit 1
	fi

	echo "Using gem: $gem_file"
	gem install rb_sys --no-document
	gem install "$gem_file" --local --no-document
fi

bundle install
bundle exec ruby app.rb
popd >/dev/null
echo "✓ Ruby gem smoke test passed"
