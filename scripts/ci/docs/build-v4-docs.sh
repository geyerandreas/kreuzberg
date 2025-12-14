#!/usr/bin/env bash
set -euo pipefail

uv run mike deploy --update-aliases 4.0 latest
uv run mike set-default latest
