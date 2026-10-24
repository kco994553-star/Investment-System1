"""Direction guard: stop superseded directions from coming back into current docs and code comments.

Rules live in docs/SPEC/direction_rules.json (one regex per superseded direction, see docs/SPEC/DIRECTION_CHANGES.md).
A line that matches a rule fails unless it also carries one of that rule's exempt words (a line that explains the
change, e.g. "... 이 결정으로 바뀐다"). History, superseded and vendor files are skipped. Read-only; no network.

    python implementation/tools/spec_direction_guard.py            # exit 1 on any hit
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / 'docs' / 'SPEC' / 'direction_rules.json'
SUFFIXES = {'.md', '.js', '.py', '.html', '.yml', '.yaml'}
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'fixtures', 'handoff'}
SKIP_FILES = {
    'docs/SPEC/DIRECTION_CHANGES.md',
    'docs/SPEC/direction_rules.json',
    'implementation/tools/spec_direction_guard.py',
    'implementation/tests/test_spec_direction_guard.py',
}
SKIP_NAME_PARTS = ('HISTORY', 'lightweight-charts')
SUPERSEDED_MARK = 'SUPERSEDED'


def load_rules(path: Path = RULES):
    data = json.loads(path.read_text(encoding='utf-8'))
    out = []
    for r in data['rules']:
        flags = re.IGNORECASE if 'i' in r.get('flags', '') else 0
        out.append((r['id'], re.compile(r['pattern'], flags), [w.lower() for w in r.get('exempt', [])]))
    return out


def candidate_files(root: Path = ROOT):
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.suffix not in SUFFIXES:
            continue
        rel = p.relative_to(root).as_posix()
        if rel in SKIP_FILES or any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if any(s in p.name for s in SKIP_NAME_PARTS):
            continue
        yield p, rel


def scan_text(text: str, rules):
    hits = []
    if SUPERSEDED_MARK in text[:200]:
        return hits
    for n, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        for rid, rx, exempt in rules:
            if rx.search(line) and not any(w in low for w in exempt):
                hits.append((rid, n, line.strip()[:160]))
    return hits


def scan(root: Path = ROOT, rules=None):
    rules = rules or load_rules()
    found = []
    for p, rel in candidate_files(root):
        try:
            text = p.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue
        found += [(rel, *h) for h in scan_text(text, rules)]
    return found


def main() -> int:
    hits = scan()
    for rel, rid, n, line in hits:
        print(f'{rid} {rel}:{n}: {line}')
    if hits:
        print(f'{len(hits)} superseded-direction line(s). See docs/SPEC/DIRECTION_CHANGES.md', file=sys.stderr)
        return 1
    print('direction guard: 0 hits')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
