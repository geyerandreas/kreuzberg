#!/usr/bin/env bash
set -euo pipefail

mode="${1:-check}"

root="$(git rev-parse --show-toplevel)"

# Ruby directories to lint, with their configuration
#   packages/ruby       - main binding (has .rubocop.yml, Steepfile, own Gemfile)
#   e2e/ruby            - generated e2e tests (has own .rubocop.yaml, own Gemfile)

failed=0

# ── Helper: find .rb files, skipping vendor dirs ──────────────────────
has_ruby_files() {
  local dir="$1"
  find "$dir" -name '*.rb' -not -path '*/vendor/*' -print -quit 2>/dev/null | grep -q .
}

# ── 1. packages/ruby ─────────────────────────────────────────────────
pkg_dir="$root/packages/ruby"
if [ -d "$pkg_dir" ] && has_ruby_files "$pkg_dir"; then
  echo "==> Linting packages/ruby"
  case "$mode" in
  fix)
    (cd "$pkg_dir" && bundle exec rubocop --config .rubocop.yml --autocorrect-all .) || failed=1
    ;;
  check)
    (cd "$pkg_dir" && bundle exec rubocop --config .rubocop.yml .) || failed=1
    ;;
  *)
    echo "Usage: $0 [fix|check]" >&2
    exit 2
    ;;
  esac

  # Steep type checking (only packages/ruby has a Steepfile)
  if [ -f "$pkg_dir/Steepfile" ]; then
    echo "==> Running steep in packages/ruby"
    (cd "$pkg_dir" && bundle exec steep check) || failed=1
  fi
fi

# ── 2. tests/test_apps/ruby ──────────────────────────────────────────
test_dir="$root/tests/test_apps/ruby"
if [ -d "$test_dir" ] && has_ruby_files "$test_dir"; then
  echo "==> Linting tests/test_apps/ruby"
  # This directory has no rubocop in its Gemfile, so we use the packages/ruby
  # Gemfile (which pulls in rubocop + plugins) and the packages/ruby config.
  config="$root/packages/ruby/.rubocop.yml"
  case "$mode" in
  fix)
    (cd "$test_dir" && BUNDLE_GEMFILE="$root/packages/ruby/Gemfile" bundle exec rubocop --config "$config" --autocorrect-all .) || failed=1
    ;;
  check)
    (cd "$test_dir" && BUNDLE_GEMFILE="$root/packages/ruby/Gemfile" bundle exec rubocop --config "$config" .) || failed=1
    ;;
  esac
fi

# ── 3. e2e/ruby ──────────────────────────────────────────────────────
e2e_dir="$root/e2e/ruby"
if [ -d "$e2e_dir" ] && has_ruby_files "$e2e_dir"; then
  echo "==> Linting e2e/ruby"
  # e2e/ruby has its own .rubocop.yaml (inherits from packages/ruby) and its
  # own Gemfile with rubocop dependencies.
  config="$e2e_dir/.rubocop.yaml"
  case "$mode" in
  fix)
    (cd "$e2e_dir" && bundle exec rubocop --config "$config" --autocorrect-all .) || failed=1
    ;;
  check)
    (cd "$e2e_dir" && bundle exec rubocop --config "$config" .) || failed=1
    ;;
  esac
fi

# ── Summary ───────────────────────────────────────────────────────────
if [ "$failed" -ne 0 ]; then
  echo ""
  echo "Ruby lint: FAILED (see errors above)"
else
  echo ""
  echo "Ruby lint: OK"
fi

exit $failed
