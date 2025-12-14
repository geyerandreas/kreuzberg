#!/usr/bin/env bash
set -euo pipefail

bundle config set --local path 'vendor/bundle'
bundle install --jobs 4 --retry 3
