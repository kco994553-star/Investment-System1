"""Deterministic SYNTHETIC multi-run macro-evidence.json for the offline tests and the browser test.

Every value and date below is invented (not agency data). Eight runs: a baseline, then seven daily runs that each add
releases or revisions so the payload carries first releases, revisions, real-time events with both release-time bases,
a 3-month condition that is recorded only at the third observation (E01), a revision that clears a condition (E13) and
a revision that establishes one (E36). `python tests/macro_evidence_fixture.py` rewrites the committed JSON.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.macro import evidence_lines as el  # noqa: E402

FIXTURE = ROOT / 'tests/fixtures/macro_evidence/browser_payload.json'
T0 = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)


def months(start: str, count: int):
    y, m = int(start[:4]), int(start[5:7])
    for _ in range(count):
        yield '%04d-%02d' % (y, m)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def quarters(start: str, count: int):
    y, q = int(start[:4]), int(start[5])
    for _ in range(count):
        yield '%04dQ%d' % (y, q)
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)


def grow(start: str, count: int, base: float, rates):
    out, value = {}, base
    for i, period in enumerate(months(start, count)):
        value = round(value * (1 + rates(i, period)), 4)
        out[period] = value
    return out


def base_rows():
    rows = {
        'TREASURY:BC_10YEAR-BC_3MONTH:MONTHLY_MEAN': {p: 0.6 for p in months('2024-11', 22)},
        'BLS:LNS14000000': {p: 4.0 for p in months('2025-01', 19)},
        'BLS:CES6056132001': {p: 2600.0 + i for i, p in enumerate(months('2023-01', 44))},
        'BLS:CES3000000007': {p: 40.5 for p in months('2023-01', 44)},
        'BLS:CUSR0000SA0L1E': grow('2023-01', 42, 300.0, lambda i, p: 0.003 if p < '2026-01' else 0.002),
        'BEA:NIPA:DPCCRG:M': grow('2023-01', 44, 120.0, lambda i, p: 0.0025),
        'FED:G17:IP.B50001.S': {p: round(100 + 0.1 * i, 4) for i, p in enumerate(months('2023-01', 44))},
        'FED:SLOOS:SUBLPDCILS_N.Q': {p: (-3.0 if i % 2 else -6.0) for i, p in enumerate(quarters('2019Q1', 30))},
        'BEA:NIPA:A191RL:Q': {p: (2.0 if p != '2025Q1' else -0.5) for p in quarters('2022Q1', 18)},
        'BTS:TSI:FREIGHT': {p: round(130 + 0.2 * i, 4) for i, p in enumerate(months('2023-01', 41))},
        'DOL:ETA539:INITIAL_CLAIMS_SA': {'2026-09-%02d' % d: 220000.0 for d in (5, 12, 19, 26)},
        'FED:FOMC:TARGET_RANGE': {'2024-09-19': 5.0, '2024-11-08': 4.75, '2024-12-19': 4.5, '2025-09-18': 4.25,
                                  '2025-10-30': 4.0, '2025-12-11': 3.75},
    }
    return rows


def capture(rows, at, posted=None, release_date=None):
    return {'rows': dict(rows), 'acquired_at': at, 'release': {'at': posted, 'date': release_date}}


def runs():
    rows = base_rows()
    reasons = {sid: {'reason': 'SOURCE_KEY_NOT_CONFIGURED'} for sid in ('CENSUS:M3:NXA:NO:SA', 'CENSUS:RESCONST:APERMITS:TOTAL:SA')}
    fomc = [('2026-10-02', 3.5), ('2026-10-03', 3.25), ('2026-10-04', 3.5), ('2026-10-05', 3.75), ('2026-10-06', 3.5),
            ('2026-10-07', 3.25), ('2026-10-08', 3.0)]
    steps = {
        1: lambda r: None,
        2: lambda r: r['BLS:LNS14000000'].update({'2026-08': 5.6}),                       # Sahm condition met
        3: lambda r: (r['FED:G17:IP.B50001.S'].update({'2026-06': 104.0, '2026-09': 104.2}),  # revision + new month
                      r['BTS:TSI:FREIGHT'].update({'2026-06': 137.5})),                    # 1st decline
        4: lambda r: (r['TREASURY:BC_10YEAR-BC_3MONTH:MONTHLY_MEAN'].update({'2026-09': -0.1}),
                      r['BTS:TSI:FREIGHT'].update({'2026-07': 137.0}),                     # 2nd decline
                      r['BLS:CUSR0000SA0L1E'].update({'2026-07': round(r['BLS:CUSR0000SA0L1E']['2026-06'] * 1.006, 4)})),
        5: lambda r: (r['BTS:TSI:FREIGHT'].update({'2026-08': 136.4}),                     # 3rd decline -> E01 down
                      r['BLS:CUSR0000SA0L1E'].update({'2026-08': round(r['BLS:CUSR0000SA0L1E']['2026-07'] * 1.006, 4)})),
        6: lambda r: (r['FED:SLOOS:SUBLPDCILS_N.Q'].update({'2026Q3': 5.0}),
                      r['BLS:CUSR0000SA0L1E'].update({'2026-09': round(r['BLS:CUSR0000SA0L1E']['2026-08'] * 1.006, 4)})),
        7: lambda r: (r['BLS:LNS14000000'].update({'2026-08': 4.9}),                       # revision clears Sahm
                      r['FED:SLOOS:SUBLPDCILS_N.Q'].update({'2026Q3': -2.0})),             # revision flips E36
    }
    payload, previous_state = None, 'NO_LIVE'
    out = []
    for k in range(8):
        at = T0 + timedelta(days=k)
        if k:
            steps[k](rows)
            rows['FED:FOMC:TARGET_RANGE'][fomc[k - 1][0]] = fomc[k - 1][1]
        captures = dict(reasons)
        for sid, values in rows.items():
            posted = at - timedelta(hours=2) if sid in ('BTS:TSI:FREIGHT', 'BEA:NIPA:DPCCRG:M') or (sid == 'FED:FOMC:TARGET_RANGE' and k % 2) else None
            captures[sid] = capture(values, at, posted, '2026-10-01' if sid == 'FED:G17:IP.B50001.S' else None)
        payload = el.build(captures, previous=payload, previous_state=previous_state, now=at)
        previous_state = 'LOADED'
        out.append(payload)
    return out


def browser_payload():
    return runs()[-1]


def encoded():
    return json.dumps(browser_payload(), ensure_ascii=False, sort_keys=True, indent=1) + '\n'


if __name__ == '__main__':
    FIXTURE.write_text(encoded(), encoding='utf-8')
    print('wrote', FIXTURE.relative_to(ROOT))
