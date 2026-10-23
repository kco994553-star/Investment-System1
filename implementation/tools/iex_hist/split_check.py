"""U8 split-consistency check (owner request 2026-10-23): does rule SPLIT still pair correctly with raw IEX month-end prices?

ebit_per_share_history (sec-qgv2.json, v2_factors) is on the LATEST share basis (split-adjusted). IEX HIST trades are as traded
(split-unadjusted). For a company that split by R (post/pre share count) after fiscal year k, the V4 past yield E_k / P_k is then
too small by R. This check computes, per stock with a verified split inside its history window, the pre/post jump

    J = median(E_k / P_k, k before the split) / median(E_k / P_k, k after the split)

with the raw IEX prices and again with the basis factor F_k (product of the R of every verified split after month-end k and up to
the latest share basis): E_k * F_k / P_k. Decision per split: raw J nearest (log distance, among 1/R, 1, R) to 1/R -> MISMATCH
(the jump is the split); adjusted J nearest to 1 -> CONSISTENT. Both -> RAW_MISMATCH_FIXED_BY_F; raw J nearest 1 ->
RAW_CONSISTENT (the prices are already on the latest basis, F must not be applied); else UNEXPECTED. Overall: >= 3 testable
stocks and every split RAW_MISMATCH_FIXED_BY_F -> the history needs F_k with raw IEX prices; every split RAW_CONSISTENT -> rule
SPLIT applies as is; otherwise MIXED. Output: only these dimensionless jump factors and verdicts; never a price, a yield level or a per-stock hash.

    python split_check.py check --stamp YYYYMMDD --shards 6 [--qgv2 URL|PATH] [--plan-b64-env PLAN_B64]   # reads private shards
    python split_check.py derive SEC_RAW.tar.gz ...    # re-derive VERIFIED_SPLITS from the private raw SEC archives (no prices)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src'))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from investment_system.qgv.v2_factors import SPLIT_RATIO_CONCEPTS  # noqa: E402
from monthend_plan import QGV2, load_json  # noqa: E402

COVER_CONCEPT = 'EntityCommonStockSharesOutstanding'  # dei cover share count (point in time, one per filing)
MATCH_TOLERANCE = 0.05  # cover-count ratio vs reported split ratio (a quarter of buybacks/issuance stays well inside)
MIN_RATIO = 1.2  # ignore ratio facts closer to 1 (not a split the check can see)

# Splits verified 2026-10-23 from the private raw SEC archives (sec-universe-raw-2026-10-17-all-shard0..6) with `derive`:
# ratio = a us-gaap StockholdersEquityNoteStockSplitConversionRatio(1) fact; the split date lies in (low, high], the dei cover
# share-count dates whose ratio matches it within MATCH_TOLERANCE (a day inside a bracket is excluded, never guessed). The request's
# examples all match (NVDA 4:1 2021-07 and 10:1 2024-06, AMZN 20:1 2022-06, WMT 3:1 2024-02, CMG 50:1 2024-06, AVGO 10:1 2024-07,
# LRCX 10:1 2024-10, DECK 6:1 2024-09, CTAS 4:1 2024-09, ORLY 15:1 2025-06) except GOOGL 20:1 2022-07: no single-class cover
# series, so it is not verified here (its history starts 2022-12, after the split, so it is not testable anyway).
VERIFIED_SPLIT_ROWS = (  # (code, ratio post/pre count, low, high, split-ratio fact accession)
    ('NASDAQ:AMZN', 20.0, '2022-04-20', '2022-07-20', '0001018724-22-000019'),
    ('NASDAQ:AVGO', 10.0, '2024-05-31', '2024-08-30', '0001730168-24-000099'),
    ('NASDAQ:COO', 4.0, '2023-12-01', '2024-02-23', '0000711404-24-000043'),
    ('NASDAQ:CPRT', 2.0, '2022-09-26', '2022-11-17', '0000900075-22-000065'),
    ('NASDAQ:CPRT', 2.0, '2023-05-24', '2023-09-27', '0000900075-22-000065'),
    ('NASDAQ:CRWD', 4.0, '2026-05-28', '2026-08-20', '0001535527-26-000031'),
    ('NASDAQ:CSGP', 10.0, '2021-04-23', '2021-07-23', '0001057352-21-000082'),
    ('NASDAQ:CSX', 3.0, '2021-03-31', '2021-06-30', '0000277948-21-000041'),
    ('NASDAQ:CTAS', 4.0, '2024-06-30', '2024-09-30', '0000723254-24-000036'),
    ('NASDAQ:DXCM', 4.0, '2022-04-21', '2022-07-21', '0001093557-22-000146'),
    ('NASDAQ:FAST', 2.0, '2025-04-10', '2025-07-11', '0001193125-12-172121'),
    ('NASDAQ:FTNT', 5.0, '2022-05-03', '2022-07-29', '0001262039-22-000029'),
    ('NASDAQ:HON', 0.5, '2026-03-31', '2026-06-30', '0000773840-26-000124'),
    ('NASDAQ:ISRG', 3.0, '2021-07-15', '2021-10-14', '0001035267-17-000147'),
    ('NASDAQ:LRCX', 10.0, '2024-08-22', '2024-10-24', '0000707549-25-000014'),
    ('NASDAQ:MCHP', 2.0, '2021-07-28', '2021-10-28', '0000827054-21-000280'),
    ('NASDAQ:MNST', 2.0, '2023-02-16', '2023-04-28', '0001104659-12-014573'),
    ('NASDAQ:NDAQ', 3.0, '2022-07-26', '2022-10-25', '0001120193-22-000020'),
    ('NASDAQ:NFLX', 10.0, '2025-09-30', '2025-12-31', '0001065280-26-000034'),
    ('NASDAQ:NVDA', 4.0, '2021-05-21', '2021-08-13', '0001045810-21-000131'),
    ('NASDAQ:NVDA', 10.0, '2024-05-24', '2024-08-23', '0001045810-24-000264'),
    ('NASDAQ:ODFL', 2.0, '2024-02-21', '2024-05-03', '0000950170-24-054284'),
    ('NASDAQ:ORLY', 15.0, '2025-05-05', '2025-08-04', '0000898173-25-000057'),
    ('NASDAQ:PANW', 2.0, '2024-11-13', '2025-02-07', '0001327567-25-000010'),
    ('NASDAQ:PANW', 3.0, '2022-08-22', '2022-11-10', '0001327567-22-000038'),
    ('NASDAQ:SMCI', 10.0, '2024-04-30', '2025-01-31', '0001375365-25-000005'),
    ('NASDAQ:TECH', 4.0, '2022-11-02', '2023-02-01', '0001558370-23-000979'),
    ('NASDAQ:TSCO', 5.0, '2024-10-26', '2025-01-25', '0000916365-25-000076'),
    ('NASDAQ:TSLA', 3.0, '2022-07-19', '2022-10-18', '0000950170-22-019867'),
    ('NASDAQ:WMT', 3.0, '2023-11-28', '2024-03-13', '0000104169-24-000105'),
    ('NYSE:ANET', 4.0, '2021-10-27', '2022-02-08', '0001596532-22-000026'),
    ('NYSE:ANET', 4.0, '2024-11-04', '2025-02-12', '0001596532-22-000026'),
    ('NYSE:APH', 2.0, '2021-01-31', '2021-04-27', '0001104659-15-012575'),
    ('NYSE:APH', 2.0, '2024-04-23', '2024-07-23', '0001104659-15-012575'),
    ('NYSE:CMG', 50.0, '2024-04-22', '2024-07-22', '0001058090-24-000032'),
    ('NYSE:DD', 0.333, '2026-05-01', '2026-07-31', '0001666700-26-000053'),
    ('NYSE:DECK', 6.0, '2024-07-11', '2024-10-11', '0000910521-24-000059'),
    ('NYSE:ETR', 2.0, '2024-09-30', '2025-01-31', '0000065984-25-000012'),
    ('NYSE:GE', 0.125, '2021-06-30', '2021-09-30', '0000040545-21-000064'),
    ('NYSE:NEE', 4.0, '2020-09-30', '2021-01-31', '0000753308-20-000186'),
    ('NYSE:NOW', 5.0, '2025-09-30', '2026-01-23', '0001373715-26-000007'),
    ('NYSE:RJF', 1.5, '2021-08-04', '2021-11-18', '0000720005-21-000106'),
    ('NYSE:ROL', 1.5, '2020-10-16', '2021-01-31', '0001047469-13-001764'),
    ('NYSE:SHW', 3.0, '2021-01-31', '2021-03-31', '0000089800-21-000016'),
    ('NYSE:SRE', 2.0, '2023-07-31', '2023-10-31', '0001032208-23-000057'),
    ('NYSE:TPL', 3.0, '2024-02-14', '2024-04-30', '0001811074-24-000031'),
    ('NYSE:TPL', 3.0, '2025-10-31', '2026-02-09', '0001811074-24-000031'),
    ('NYSE:WRB', 1.4999, '2024-04-29', '2024-07-29', '0000011544-20-000016'),
    ('NYSE:WRB', 1.5, '2022-02-17', '2022-05-02', '0000011544-22-000016'),
    ('NYSE:WSM', 2.0, '2024-05-19', '2024-08-18', '0001628280-24-038362'),
)
VERIFIED_SPLITS: dict[str, tuple[dict, ...]] = {}
for _c, _r, _lo, _hi, _accn in VERIFIED_SPLIT_ROWS:
    VERIFIED_SPLITS[_c] = VERIFIED_SPLITS.get(_c, ()) + ({'ratio': _r, 'low': _lo, 'high': _hi, 'ratio_fact_accn': _accn},)


def _cover_series(facts: dict) -> list[tuple[str, float]]:
    rows = (((facts.get('dei') or {}).get(COVER_CONCEPT) or {}).get('units') or {}).get('shares') or []
    by_end: dict[str, set] = {}
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get('end'), str) and isinstance(r.get('val'), (int, float)) and r['val'] > 0:
            by_end.setdefault(r['end'], set()).add(float(r['val']))
    return [(end, next(iter(v))) for end, v in sorted(by_end.items()) if len(v) == 1]  # several classes on one date: skip


def _ratio_facts(facts: dict) -> list[tuple[float, str, str]]:
    out = []
    for group in (facts or {}).values():
        for concept in SPLIT_RATIO_CONCEPTS:
            for rows in ((group or {}).get(concept) or {}).get('units', {}).values():
                for r in rows if isinstance(rows, list) else ():
                    v = r.get('val') if isinstance(r, dict) else None
                    if isinstance(v, (int, float)) and v > 0 and max(v, 1 / v) >= MIN_RATIO:
                        out.append((float(v), str(r.get('filed')), str(r.get('accn'))))
    return out


def derive_events(companyfacts: dict, *, since: str = '2021-01-01', tolerance: float = MATCH_TOLERANCE) -> list[dict]:
    """Splits confirmed by both a split-ratio fact and a matching jump of consecutive dei cover share counts."""
    facts = companyfacts.get('facts') if isinstance(companyfacts, dict) else None
    ratios = _ratio_facts(facts or {})
    series = _cover_series(facts or {})
    events = []
    for (low, a), (high, b) in zip(series, series[1:]):
        if high < since:
            continue
        r = b / a
        cands = [(abs(math.log(r / c)), filed, accn, c) for v, filed, accn in ratios for c in (v, 1 / v)
                 if abs(r / c - 1) <= tolerance]
        if cands:
            _, filed, accn, c = min(cands)
            events.append({'ratio': round(c, 4), 'low': low, 'high': high, 'ratio_fact_accn': accn, 'ratio_fact_filed': filed})
    return events


def factor(day: str, events, basis: str | None):
    """F for a month-end trading day (YYYY-MM-DD): product of the ratios of verified splits after it and up to the latest
    share basis date. None when a split bracket contains the day or the basis date (the side is not determined)."""
    f = 1.0
    for e in events:
        if e['low'] < day < e['high'] or (basis and e['low'] < basis < e['high']):
            return None
        if day <= e['low'] and (basis is None or e['high'] <= basis):
            f *= e['ratio']
    return f


def _nearest(j: float, r: float) -> str:
    """Which of 1/R (pre-split basis left in), 1 (consistent), R (adjusted twice) a jump is closest to, in log distance."""
    return min((abs(math.log(j * r)), 'INV_RATIO'), (abs(math.log(j)), 'ONE'), (abs(math.log(j / r)), 'RATIO'))[1]


def check_stock(history, prices: dict, events, basis: str | None) -> list[dict]:
    """history: [{fiscal_year_end, value}] (latest basis). prices: {YYYY-MM: (YYYY-MM-DD trading day, price)}.
    One dimensionless result per split event with >= 1 usable year on each side."""
    points = []
    for h in history:
        m = h.get('fiscal_year_end', '')[:7]
        if m in prices and isinstance(h.get('value'), (int, float)) and h['value'] > 0 and prices[m][1] > 0:
            day, px = prices[m]
            points.append((day, h['value'] / px, factor(day, events, basis)))
    out = []
    for i, e in enumerate(events):
        lo = events[i - 1]['high'] if i else ''
        hi = events[i + 1]['low'] if i + 1 < len(events) else '9999'
        pre = [(y, f) for d, y, f in points if lo <= d <= e['low'] and f is not None]
        post = [(y, f) for d, y, f in points if e['high'] <= d <= hi and f is not None]
        res = {'ratio': e['ratio'], 'low': e['low'], 'high': e['high'], 'pre': len(pre), 'post': len(post)}
        if not pre or not post:
            res['verdict'] = 'NOT_TESTABLE'
            out.append(res)
            continue
        raw = statistics.median(y for y, _ in pre) / statistics.median(y for y, _ in post)
        adj = statistics.median(y * f for y, f in pre) / statistics.median(y * f for y, f in post)
        r = e['ratio']
        res.update({'raw_jump': raw, 'raw_jump_x_ratio': raw * r, 'adjusted_jump': adj,
                    'raw': {'INV_RATIO': 'MISMATCH', 'ONE': 'NO_JUMP', 'RATIO': 'INVERSE_JUMP'}[_nearest(raw, r)],
                    'adjusted': 'CONSISTENT' if _nearest(adj, r) == 'ONE' else 'MISMATCH'})
        res['verdict'] = ('RAW_MISMATCH_FIXED_BY_F' if (res['raw'], res['adjusted']) == ('MISMATCH', 'CONSISTENT') else
                          'RAW_CONSISTENT' if res['raw'] == 'NO_JUMP' else 'UNEXPECTED')
        out.append(res)
    return out


def overall(results: dict) -> dict:
    tested = {c: [r for r in rs if r['verdict'] != 'NOT_TESTABLE'] for c, rs in results.items()}
    tested = {c: rs for c, rs in tested.items() if rs}
    verdicts = [r['verdict'] for rs in tested.values() for r in rs]
    fixed = sum(v == 'RAW_MISMATCH_FIXED_BY_F' for v in verdicts)
    if len(tested) < 3:
        decision = 'INSUFFICIENT (fewer than 3 testable stocks)'
    elif fixed == len(verdicts):
        decision = 'SPLIT_RULE_NEEDS_BASIS_FACTOR (raw IEX + latest-basis history mismatches by the split ratio; F_k restores it)'
    elif all(v == 'RAW_CONSISTENT' for v in verdicts):
        decision = 'SPLIT_RULE_APPLIES_AS_IS'
    else:
        decision = 'MIXED (review the per-stock lines)'
    return {'stocks_tested': len(tested), 'events_tested': len(verdicts), 'fixed_by_f': fixed,
            'raw_consistent': sum(v == 'RAW_CONSISTENT' for v in verdicts),
            'unexpected': sum(v == 'UNEXPECTED' for v in verdicts), 'decision': decision}


def _sig(x: float) -> str:
    return f'{x:.2g}' if x < 1 else f'{x:.3g}'


def report_line(code: str, r: dict) -> str:
    head = f"{code} split {_sig(r['ratio'])}:1 in ({r['low']}, {r['high']}] pre/post years {r['pre']}/{r['post']}"
    if r['verdict'] == 'NOT_TESTABLE':
        return head + ' -> NOT_TESTABLE'
    return (head + f" raw pre/post median ratio {_sig(r['raw_jump'])} (x ratio {_sig(r['raw_jump_x_ratio'])}) -> {r['raw']};"
            f" after F {_sig(r['adjusted_jump'])} -> {r['adjusted']} [{r['verdict']}]")


def prices_from_shards(shards, code_symbols) -> dict:
    """{code: {YYYY-MM: (YYYY-MM-DD, price)}} from shard payloads (ROUND, else ODD_ONLY; NO_TRADE skipped). RAM only."""
    out: dict[str, dict] = {}
    for body in shards:
        for month, m in body['months'].items():
            d = m['date']
            day = f'{d[:4]}-{d[4:6]}-{d[6:]}'
            for code, sym in m.get('codes', {}).items():
                if code not in code_symbols:
                    continue
                row = m['symbols'].get(sym) or {}
                if row.get('status') in ('ROUND', 'ODD_ONLY') and isinstance(row.get('price_e4'), int) and row['price_e4'] > 0:
                    out.setdefault(code, {})[month] = (day, row['price_e4'] / 1e4)
    return out


def run_check(qgv2: dict, shards, splits=None) -> tuple[dict, dict]:
    splits = VERIFIED_SPLITS if splits is None else splits
    records = qgv2['records']
    prices = prices_from_shards(shards, set(splits))
    results = {}
    for code, events in sorted(splits.items()):
        v = (records.get(code) or {}).get('v_inputs_v2') or {}
        basis = (v.get('diluted_shares') or {}).get('period_end')
        results[code] = check_stock(v.get('ebit_per_share_history') or [], prices.get(code, {}),
                                    sorted(events, key=lambda e: e['low']), basis)
    return results, overall(results)


def coverage(plan: dict, shards) -> dict:
    got = {m: body['months'][m] for body in shards for m in body['months']}
    want = {m['month']: m for m in plan['months']}
    complete = sum(1 for m, p in want.items() if m in got and set(got[m]['symbols']) == set(p['symbols']))
    return {'plan_months': len(want), 'shard_months': len(got), 'complete_months': complete,
            'missing_months': sorted(set(want) - set(got)), 'extra_months': sorted(set(got) - set(want))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check')
    c.add_argument('--stamp', required=True)
    c.add_argument('--shards', type=int, required=True)
    c.add_argument('--qgv2', default=QGV2)
    c.add_argument('--plan', help='plan JSON file (else env PLAN_B64) for the coverage count')
    d = sub.add_parser('derive')
    d.add_argument('archives', nargs='+')
    a = ap.parse_args(argv)
    if a.cmd == 'derive':
        found = {}
        for path in a.archives:
            with tarfile.open(path) as t:
                for m in t:
                    if m.isfile() and m.name.endswith('/companyfacts.json'):
                        events = derive_events(json.load(t.extractfile(m)))
                        if events:
                            found[m.name.split('/')[-2]] = events
        print(json.dumps(found, indent=1, sort_keys=True))
        return 0
    from monthend_backfill import BackfillError, load_plan, read_shard, tag_for  # noqa: PLC0415
    try:
        shards = [read_shard(tag_for(a.stamp, i)) for i in range(a.shards)]
    except BackfillError as error:
        print(f'IEX_V4_SPLIT_CHECK FAILED code={error}')
        return 1
    rc = 0
    try:
        if a.plan or os.environ.get('PLAN_B64'):
            cov = coverage(load_plan(a.plan, os.environ.get('PLAN_B64')), shards)
            print('coverage ' + json.dumps(cov, sort_keys=True))
            rc = 0 if cov['complete_months'] == cov['plan_months'] and not cov['extra_months'] else 1
        results, summary = run_check(load_json(a.qgv2), shards)
    except Exception as error:  # noqa: BLE001 - type name only (a message could carry a value)
        print(f'IEX_V4_SPLIT_CHECK FAILED code={type(error).__name__}')
        return 1
    del shards
    for code, rs in results.items():
        for r in rs:
            print(report_line(code, r))
    print('IEX_V4_SPLIT_CHECK ' + json.dumps(summary, sort_keys=True))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
