#!/usr/bin/env bash
set -euo pipefail

source scripts/lib/tessdata.sh
setup_tessdata

task e2e:go:test
