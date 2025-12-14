#!/usr/bin/env bash
set -euo pipefail

ruby_arch="$(ruby -e "require 'rbconfig'; print RbConfig::CONFIG['arch']")"
bundle exec rake "native:kreuzberg:${ruby_arch}"
