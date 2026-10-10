#!/usr/bin/env bash
# Runs every test listed in a manifest (one tools/ file name per line, # comments allowed).
# Fails on the first failing test and when the manifest lists nothing.
set -euo pipefail
manifest="$1"; count=0
while IFS= read -r line || [ -n "$line" ]; do
  name="${line%%#*}"; name="$(echo "$name" | xargs)"
  [ -z "$name" ] && continue
  case "$name" in */*|..*) echo "INVALID_TEST_NAME $name"; exit 1;; esac
  echo "RUN $name"
  node "implementation/tools/$name"
  count=$((count+1))
done < "$manifest"
[ "$count" -gt 0 ] || { echo "EMPTY_TEST_MANIFEST"; exit 1; }
echo "MANIFEST_OK tests=$count"
