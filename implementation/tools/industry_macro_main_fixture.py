#!/usr/bin/env python3
"""Main's consumer fixture for Codex #525 company-industry-macro-query/1 (owner 2026-11-09 queue item 5).

Runs Codex's own query (research/common_classification/macro_evidence.query_industry_evidence, used as is) on Codex's public synthetic
inputs (tests/fixtures/macro_industry_evidence: view, mappings, cache) for the base case and each case of cases.json (the changes
written there, applied as written), and records each output or the producer's refusal code. Main's reader test reads this file.
Synthetic only; nothing is fetched or computed beyond Codex's function.

  python implementation/tools/industry_macro_main_fixture.py          # write
  python implementation/tools/industry_macro_main_fixture.py --check  # the stored file equals a fresh run
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'implementation' / 'src'))
from investment_system.research.common_classification.macro_evidence import query_industry_evidence  # noqa: E402

SRC = ROOT / 'implementation' / 'tests' / 'fixtures' / 'macro_industry_evidence'
OUT = ROOT / 'implementation' / 'tests' / 'fixtures' / 'industry_macro_main' / 'outputs.json'


def _walk(doc, path):
    parts = re.findall(r'[^.\[\]]+|\[\d+\]', path)
    for p in parts[:-1]:
        doc = doc[int(p[1:-1])] if p.startswith('[') else doc[p]
    last = parts[-1]
    return doc, (int(last[1:-1]) if last.startswith('[') else last)


def apply(inputs, change):
    root, _, rest = change['path'].partition('.')
    holder, key = _walk(inputs[root], rest)
    op = change.get('operation')
    if op is None:
        holder[key] = deepcopy(change['value'])
    elif op == 'keep_first':
        holder[key] = holder[key][:1]
    elif op == 'set_unknown_with_no_targets':
        m = holder[key]
        m.update(status='UNKNOWN', relation='UNKNOWN', targets=[], unknown_reasons=[change['reason']])
    else:
        raise ValueError('UNKNOWN_OPERATION:' + op)


def build() -> dict:
    base = {'view': json.loads((SRC / 'view.json').read_text()), 'mappings': json.loads((SRC / 'mappings.json').read_text()),
            'cache': json.loads((SRC / 'cache.json').read_text())}
    cases = json.loads((SRC / 'cases.json').read_text())['cases']
    out = []
    for case in [{'id': 'base', 'changes': [], 'expected': None}] + cases:
        inputs = deepcopy(base)
        for change in case['changes']:
            apply(inputs, change)
        try:
            result, error = query_industry_evidence(inputs['view'], inputs['mappings'], inputs['cache']), None
        except ValueError as exc:
            result, error = None, str(exc)
        out.append({'id': case['id'], 'codex_expected': case['expected'], 'output': result, 'error': error})
    return {'schema_version': 'industry-macro-main-fixture/1', 'data_kind': 'SYNTHETIC',
            'producer': 'research/common_classification/macro_evidence.py (Codex #525 731e4682)', 'cases': out}


def encode(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1) + '\n'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    text = encode(build())
    if args.check:
        if not OUT.is_file() or OUT.read_text() != text:
            print('INDUSTRY_MACRO_MAIN_FIXTURE stale')
            return 1
        print('INDUSTRY_MACRO_MAIN_FIXTURE ok')
        return 0
    OUT.write_text(text)
    print('INDUSTRY_MACRO_MAIN_FIXTURE written cases=' + str(len(json.loads(text)['cases'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
