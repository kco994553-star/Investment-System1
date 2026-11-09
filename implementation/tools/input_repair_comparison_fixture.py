#!/usr/bin/env python3
"""Main's consumer fixture for Codex #527 sector-qgv-input-repair-comparison/1 (owner 2026-11-09 QGV coverage instruction §4).

Runs Codex's own functions as they are — research.sector_qgv.preview_qgv with the pinned default configuration and
research.sector_qgv_held_repair.comparison — on Codex's public synthetic input (docs/research/sector_qgv/synthetic-input.json).
Each case states the "before" input as the synthetic input with some observations absent (the state an input connection repair
fixes) and the "after" input as the synthetic input itself; the same rows, date, universe and configuration on both sides. A case
the producer refuses records its refusal code. Main's reader test reads this file. Synthetic only: no real company, nothing fetched,
nothing computed beyond Codex's functions; the case edits below only remove or relabel synthetic observations.

  python implementation/tools/input_repair_comparison_fixture.py          # write
  python implementation/tools/input_repair_comparison_fixture.py --check  # the stored file equals a fresh run
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'implementation' / 'src'))
from investment_system.research.sector_qgv import default_config, preset, preview_qgv  # noqa: E402
from investment_system.research.sector_qgv_held_repair import comparison  # noqa: E402

SRC = ROOT / 'implementation' / 'docs' / 'research' / 'sector_qgv' / 'synthetic-input.json'
OUT = ROOT / 'implementation' / 'tests' / 'fixtures' / 'input_repair_comparison' / 'outputs.json'


def _widen(snapshot, extra):
    """Synthetic copies of the first rows under new ids (both sides alike), so a peer pool can stay above the minimum."""
    rows = snapshot['rows']
    for i in range(extra):
        r = deepcopy(rows[i])
        r['company_id'] = 'company-x%02d' % i
        r['issuer_id'] = 'issuer-x%d' % i
        r['security_id'] = 'security-x%d' % i
        for o in r['observations'].values():
            o['issuer_id'], o['security_id'] = r['issuer_id'], r['security_id']
        rows.append(r)
    snapshot['members'] = sorted([r['company_id'] for r in rows])
    return snapshot


def _drop(snapshot, variant, count):
    for r in snapshot['rows'][:count]:
        r['observations'].pop(variant, None)
    return snapshot


def _relabel(snapshot, sector, count):
    for r in snapshot['rows'][-count:]:
        r['sector_id'] = sector
    return snapshot


def cases():
    base = json.loads(SRC.read_text())
    # (id, what it shows, before builder, after builder, configuration change)
    yield ('peer_minimum', '관측 4개가 빠져 비교 표본이 최소 아래 → 연결 뒤 같은 설정으로 Q·총점 산출',
           lambda s: _drop(s, 'operating_margin_ttm', 4), lambda s: s, False)
    yield ('peer_shift', '비교 표본이 최소 이상인 채 관측 3개 추가 → 기존 상대점수 변화(실적 개선 아님)',
           lambda s: _drop(_widen(s, 4), 'operating_margin_ttm', 3), lambda s: _widen(s, 4), False)
    yield ('small_group', '3행 섹터 그룹(최소 20 미만) · 구조적 표본 부족은 입력 연결로 풀리지 않음',
           lambda s: _drop(_relabel(s, 'ENERGY', 3), 'debt_assets', 2), lambda s: _relabel(s, 'ENERGY', 3), False)
    yield ('no_change', '입력 변화 없음', lambda s: s, lambda s: s, False)
    yield ('config_changed', '설정이 바뀌면 생산자가 비교를 거부', lambda s: s, lambda s: s, True)


def build() -> dict:
    base = json.loads(SRC.read_text())
    out = []
    for cid, note, before_fn, after_fn, config_change in cases():
        before = before_fn(deepcopy(base))
        after = after_fn(deepcopy(base))
        cfg = default_config()
        a = preview_qgv(cfg, before, 'before')
        cfg2 = default_config()
        if config_change:
            # A setting change (axis weights of one scope), which an input connection repair never is.
            p = preset(cfg2, 'INFORMATION_TECHNOLOGY', 'GENERAL')
            p['axis_weights'] = {'Q': 4000, 'G': 3000, 'V': 3000}
            cfg2['scoped_overrides']['INFORMATION_TECHNOLOGY|GENERAL'] = p
        b = preview_qgv(cfg2, after, 'after')
        try:
            out.append({'id': cid, 'note': note, 'output': comparison(a, b)})
        except ValueError as e:
            out.append({'id': cid, 'note': note, 'error': str(e)})
    return {'schema_version': 'main-input-repair-comparison-fixture/1', 'data_kind': 'SYNTHETIC',
            'producer': {'pr': 527, 'functions': ['sector_qgv.preview_qgv(default_config())', 'sector_qgv_held_repair.comparison'],
                         'input': 'implementation/docs/research/sector_qgv/synthetic-input.json'},
            'cases': out}


def encode(doc) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True, allow_nan=False) + '\n'


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args(argv)
    text = encode(build())
    if args.check:
        if not OUT.exists() or OUT.read_text() != text:
            print('input repair comparison fixture differs from a fresh run of Codex comparison()')
            return 1
        print('input repair comparison fixture = fresh Codex comparison() run')
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
