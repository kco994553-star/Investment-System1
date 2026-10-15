#!/usr/bin/env bash
# Daily SEC workflow, verify job: run one verification command and, when it fails, record the failure as one fixed token
#   DAILY_VERIFY_FAILED test=<test file name from the manifest, or the given label> exit=<code>
# The token carries a file name and an exit code only: no values, prices, URLs or secrets.
# Usage: daily_verify_step.sh <label> <command> [args...]
set -uo pipefail
label="$1"; shift
log="$(mktemp)"
trap 'rm -f "$log"' EXIT
"$@" 2>&1 | tee "$log"
code=${PIPESTATUS[0]}
[ "$code" -eq 0 ] && exit 0
# run_js_tests.sh names the failing manifest entry as "CI_TEST_FAILED <name> exit=<status>".
name="$(grep -o 'CI_TEST_FAILED [A-Za-z0-9_.-]* exit=' "$log" | tail -n 1 | cut -d' ' -f2)"
[[ "$name" =~ ^[A-Za-z0-9_.-]+$ ]] || name="$label"
[[ "$name" =~ ^[A-Za-z0-9_.-]+$ ]] || name="UNNAMED"
echo "DAILY_VERIFY_FAILED test=$name exit=$code"
echo "::error title=DAILY_VERIFY_FAILED::DAILY_VERIFY_FAILED test=$name exit=$code"
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then echo "DAILY_VERIFY_FAILED test=$name exit=$code" >> "$GITHUB_STEP_SUMMARY"; fi
exit "$code"
