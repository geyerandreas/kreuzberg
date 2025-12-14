#!/usr/bin/env bash
set -euo pipefail

base="${RUSTFLAGS:-"-D warnings -A unpredictable-function-pointer-comparisons"}"

check_output=""
if ! check_output="$(printf 'fn main() {}\n' | RUSTC_COLOR=never rustc -W fn_ptr_eq - 2>&1)"; then
	:
fi
if grep -qi "unknown lint" <<<"$check_output"; then
	echo "fn_ptr_eq lint unavailable on $(rustc -V); skipping flag"
else
	base+=" -A fn_ptr_eq --cfg has_fn_ptr_eq_lint"
	echo "Detected fn_ptr_eq lint support; appended suppression flags"
fi

echo "RUSTFLAGS=$base" >>"$GITHUB_ENV"
