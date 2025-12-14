#!/usr/bin/env bash
set -euo pipefail

# Install packages only if not already present
brew list openssl@3 &>/dev/null || brew install openssl@3
brew list pkg-config &>/dev/null || brew install pkg-config
