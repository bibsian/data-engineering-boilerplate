#!/usr/bin/env bash
# scripts/test_wt_sanitize.sh — unit tests for wt_sanitize
set -euo pipefail

# Extract just the wt_sanitize function from scripts/wt
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

wt_sanitize() {
  local branch="$1"
  printf '%s' "$branch" \
    | tr '[:upper:]' '[:lower:]' \
    | tr '/_ ' '-' \
    | tr -cd 'a-z0-9-' \
    | sed -E 's/-{2,}/-/g' \
    | sed -E 's/^-+//;s/-+$//'
}

pass=0; fail=0
assert_eq() {
  local got="$1" expected="$2" desc="$3"
  if [[ "$got" == "$expected" ]]; then
    echo "PASS: $desc"; (( pass++ )) || true
  else
    echo "FAIL: $desc — expected '$expected', got '$got'" >&2; (( fail++ )) || true
  fi
}

assert_eq "$(wt_sanitize 'earl/FIB-123')"            "earl-fib-123"       "slash + uppercase"
assert_eq "$(wt_sanitize 'my_feature')"              "my-feature"         "underscore"
assert_eq "$(wt_sanitize 'UPPER-CASE')"              "upper-case"         "uppercase only"
assert_eq "$(wt_sanitize 'a--b')"                    "a-b"                "collapse dashes"
assert_eq "$(wt_sanitize '-leading-trailing-')"      "leading-trailing"   "strip leading/trailing dashes"
assert_eq "$(wt_sanitize 'team/PROJ-999/my-thing')"  "team-proj-999-my-thing" "multiple slashes"
assert_eq "$(wt_sanitize 'simple')"                  "simple"             "passthrough"

echo ""
echo "Results: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]]
