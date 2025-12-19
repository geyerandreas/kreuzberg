#!/usr/bin/env bash
set -euo pipefail

# Install only doc dependencies without building the Rust workspace/project
# This avoids unnecessary Rust compilation for documentation builds
uv sync --group doc --no-editable --no-install-workspace --no-install-project
