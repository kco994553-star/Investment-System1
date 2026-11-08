#!/usr/bin/env python3
"""Main's synthetic I1-shaped Q/G partial comparison (owner 2026-11-07 「#505 실자료 부분 비교 계약 추가 인수」).

Codex's shared synthetic comparison (docs/research/sector_qgv/partial-synthetic-comparison.json) is a D1 case (settings only).
The screen also needs the other kind, INPUT_CLASSIFICATION (I1: classification addendum and peer expansion, same settings).
This file is Codex's own engine output for it, never written by hand: preview_qgv on Codex's partial-synthetic-snapshot.json with
one company unclassified (before) and as published (after), default config on both sides, then
research.sector_qgv_partial.compare_axes(..., input_treatment=True). Synthetic only; no real company.
Run: PYTHONPATH=implementation/src python implementation/tools/sector_qgv_axis_main_variants.py [--check]
"""
import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.research.sector_qgv import default_config, preview_qgv  # noqa: E402
from investment_system.research.sector_qgv_partial import compare_axes  # noqa: E402

SNAPSHOT = ROOT / 'docs/research/sector_qgv/partial-synthetic-snapshot.json'
OUT = ROOT / 'tests/fixtures/sector_qgv_axis_i1_synthetic.json'


def build():
    after = json.loads(SNAPSHOT.read_text())
    before = copy.deepcopy(after)
    before['snapshot_id'] = after['snapshot_id'] + '-before-addendum'
    before['input_version'] = 'synthetic-input/0'
    before['rows'][-1]['sector_id'] = None
    before['rows'][-1]['accounting_template'] = None
    c = default_config()
    return compare_axes(preview_qgv(c, before, 'SYNTHETIC-I1:before'), preview_qgv(c, after, 'SYNTHETIC-I1'), c, c,
                        'SYNTHETIC-I1', input_treatment=True)


def text(v):
    return json.dumps(v, ensure_ascii=False, allow_nan=False, indent=1, sort_keys=True) + '\n'


def main():
    a = argparse.ArgumentParser(); a.add_argument('--check', action='store_true'); ns = a.parse_args()
    want = text(build())
    if ns.check:
        same = OUT.exists() and OUT.read_text() == want
        print(json.dumps({'status': 'SAME' if same else 'DIFFERENT'})); return 0 if same else 1
    OUT.write_text(want); print(json.dumps({'status': 'WRITTEN'})); return 0


if __name__ == '__main__':
    raise SystemExit(main())
