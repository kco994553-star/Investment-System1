#!/usr/bin/env bash
# Runs a browser test manifest with "now" moved forward by DAYS days (clock_shift_preload.js), minus the listed
# exclusions. Unlike run_js_tests.sh it keeps going after a failure, so one run names every failing test.
# Usage: run_js_tests_date_shift.sh <manifest> <exclude list> <days>
set -euo pipefail
manifest="$1"; exclude="$2"; days="$3"
case "$days" in ''|*[!0-9]*|0) echo "INVALID_SHIFT_DAYS $days"; exit 1;; esac
names() { while IFS= read -r line || [ -n "$line" ]; do n="${line%%#*}"; n="$(echo "$n" | xargs)"; [ -n "$n" ] && echo "$n"; done < "$1"; }
mapfile -t tests < <(names "$manifest"); mapfile -t skip < <(names "$exclude")
for s in "${skip[@]}"; do printf '%s\n' "${tests[@]}" | grep -qxF "$s" || { echo "STALE_EXCLUSION $s"; exit 1; }; done
preload="$(cd "$(dirname "$0")" && pwd)/clock_shift_preload.js"
count=0; failed=()
for name in "${tests[@]}"; do
  case "$name" in */*|..*) echo "INVALID_TEST_NAME $name"; exit 1;; esac
  if printf '%s\n' "${skip[@]}" | grep -qxF "$name"; then echo "DATE_SHIFT_EXCLUDED $name"; continue; fi
  echo "RUN $name (+${days}d)"
  evidence="$(mktemp -d)"
  if PAGES_COCKPIT_EVIDENCE_DIR="$evidence" TEST_CLOCK_SHIFT_DAYS="$days" NODE_OPTIONS="--require $preload" node "implementation/tools/$name"; then
    count=$((count+1))
  else
    status=$?; failed+=("$name")
    printf '::error file=implementation/tools/%s,title=DATE_SHIFT_TEST_FAILED::DATE_SHIFT_TEST_FAILED %s shift=+%sd exit=%s\n' "$name" "$name" "$days" "$status"
    # Where it failed: the error and stack a test wrote to its evidence file (code locations only, no page data).
    find "$evidence" -name '*.json' -print0 | xargs -0 -r node -e 'for (const f of process.argv.slice(1)) { try { const j = JSON.parse(require("fs").readFileSync(f, "utf8")); if (j && typeof j.stack === "string") console.log("DATE_SHIFT_STACK " + j.stack.split("\n").filter((l) => /^\s*at .*implementation\/tools\//.test(l) || /Error/.test(l)).slice(0, 8).join(" | ")); } catch (e) {} }'
  fi
  rm -rf "$evidence"
done
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  { echo "### 날짜 +${days}일 브라우저 시험"; echo "- 통과 ${count} · 실패 ${#failed[@]} · 제외 ${#skip[@]}"; for f in "${failed[@]}"; do echo "- 실패: \`$f\`"; done; } >> "$GITHUB_STEP_SUMMARY"
fi
[ "${#failed[@]}" -eq 0 ] || { echo "DATE_SHIFT_FAILED shift=+${days}d failed=${#failed[@]} passed=$count"; exit 1; }
[ "$count" -gt 0 ] || { echo "EMPTY_TEST_MANIFEST"; exit 1; }
echo "DATE_SHIFT_OK shift=+${days}d tests=$count excluded=${#skip[@]}"
