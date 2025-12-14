#!/usr/bin/env bash
set -euo pipefail

case "$RUNNER_OS" in
Linux)
	echo "platform=Linux" >>"$GITHUB_OUTPUT"
	;;
macOS)
	echo "platform=macOS" >>"$GITHUB_OUTPUT"
	;;
Windows)
	echo "platform=Windows" >>"$GITHUB_OUTPUT"
	;;
*)
	echo "platform=unknown" >>"$GITHUB_OUTPUT"
	;;
esac
