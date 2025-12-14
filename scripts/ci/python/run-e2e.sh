#!/usr/bin/env bash
set -euo pipefail

if [[ "${RUNNER_OS:-}" == "Windows" ]]; then
	task e2e:python:test -- -m "not slow and not windows_slow" --timeout=60
else
	task e2e:python:test -- -m "not slow" --timeout=60
fi
