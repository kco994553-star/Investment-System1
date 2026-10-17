#!/usr/bin/env bash
# Builds the fixture public dir, serves it with the frontend, runs the browser test, stops the server.
# Needs python3, node and playwright (NODE_PATH pointing at a node_modules with playwright).
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
dir="$(mktemp -d)"
port="${FRONTEND_PORT:-8994}"
node "$here/tools/fixture_public_dir.js" "$dir/public" --ledger active
python3 "$here/tools/dev_server.py" --data "$dir/public" --port "$port" >"$dir/server.log" 2>&1 &
server=$!
trap 'kill "$server" 2>/dev/null || true; rm -rf "$dir"' EXIT
for _ in $(seq 1 50); do
  if python3 -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:$port/app/', timeout=1)" 2>/dev/null; then break; fi
  python3 -c "import time; time.sleep(0.2)"
done
FRONTEND_URL="http://127.0.0.1:$port/app/" node "$here/tests/browser_test.cjs"
