#!/usr/bin/env bash
set -euo pipefail

bash scripts/ci/validate/show-disk-space.sh "Before shfmt installation"

if [[ "${RUNNER_OS:-}" == "Linux" ]]; then
	curl -sSL "https://github.com/mvdan/sh/releases/download/v3.8.0/shfmt_v3.8.0_linux_amd64" -o /usr/local/bin/shfmt
	chmod +x /usr/local/bin/shfmt
elif [[ "${RUNNER_OS:-}" == "macOS" ]]; then
	brew install shfmt
fi

bash scripts/ci/validate/show-disk-space.sh "After shfmt installation"
