#!/usr/bin/env bash
set -euo pipefail

ruby_arch="$(ruby -e "require 'rbconfig'; print RbConfig::CONFIG['arch']")"
stage_dir="tmp/${ruby_arch}/stage"
mkdir -p pkg

if [ ! -f "${stage_dir}/kreuzberg.gemspec" ]; then
	echo "Stage directory ${stage_dir} missing" >&2
	exit 1
fi

(cd "${stage_dir}" && gem build kreuzberg.gemspec)
mv "${stage_dir}"/kreuzberg-*.gem pkg/

gem_file="$(find pkg -name "kreuzberg-*.gem" -type f | head -n 1)"
echo "gem-path=${GITHUB_WORKSPACE}/packages/ruby/$gem_file" >>"$GITHUB_OUTPUT"
