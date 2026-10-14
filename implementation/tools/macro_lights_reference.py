#!/usr/bin/env python3
"""Build tests/fixtures/macro_lights_v1_vectors.json: SYNTHETIC vectors for the macro lights v1 (PLAYBOOK_V1 13-5).

Every unemployment rate, CPI index, Treasury yield and ETF close below is generated (fixed LCG / fixed numbers), not
market or government data. The Python reference (investment_system.macro.macro_lights_v1) writes the expected
outputs; tools/macro_lights_node_test.js checks that web_assets/macro-lights.js returns the same values.
Usage: python tools/macro_lights_reference.py [--check]
"""
from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.macro import macro_lights_v1 as ml  # noqa: E402

OUT = ROOT / 'tests/fixtures/macro_lights_v1_vectors.json'
NOTE = 'SYNTHETIC test vectors: every rate, index, yield and close below is generated, not market or government data.'
FUNCTIONS = {'employment_light': ml.employment_light, 'inflation_light': ml.inflation_light, 'curve_light': ml.curve_light,
             'market_light': ml.market_light, 'credit_light': ml.credit_light, 'macro_state': ml.macro_state}


class Lcg:
    def __init__(self, seed):
        self.state = seed

    def unit(self):
        self.state = (self.state * 1103515245 + 12345) % 2147483648
        return self.state / 2147483648


def weekdays(start, count):
    out, day = [], date.fromisoformat(start)
    while len(out) < count:
        if day.weekday() < 5:
            out.append(day.isoformat())
        day += timedelta(days=1)
    return out


def months(start, count):
    y, m = int(start[:4]), int(start[5:7])
    out = []
    for _ in range(count):
        out.append('%04d-%02d' % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def walk(days, seed, vol, start=100.0, shocks=None):
    """Synthetic closes: multiplicative LCG walk; shocks = {index_from: (daily_drift, vol)}."""
    rng, value, out, drift, sigma = Lcg(seed), start, [], 0.0002, vol
    for i, d in enumerate(days):
        if shocks and i in shocks:
            drift, sigma = shocks[i]
        value = value * (1 + drift + sigma * (rng.unit() * 2 - 1))
        out.append([d, round(value, 4)])
    return out


def monthly(values, start='2029-01'):
    return [[p, v] for p, v in zip(months(start, len(values)), values)]


def cases():
    c = []

    def add(case_id, fn, *args):
        c.append({'id': case_id, 'fn': fn, 'args': list(args)})

    # employment: 3-month mean − lowest of the 12 months ending at the latest month ≥ 0.5 %p
    flat = [4.0] * 15
    add('employment-flat-not-lit', 'employment_light', monthly(flat))
    add('employment-rising-lit', 'employment_light', monthly([4.0] * 12 + [4.5, 4.6, 4.7]))
    add('employment-boundary-exactly-half-point-lit', 'employment_light', monthly([3.6] * 12 + [4.1, 4.1, 4.1]))
    add('employment-just-below-not-lit', 'employment_light', monthly([3.6] * 12 + [4.0, 4.1, 4.1]))
    add('employment-low-is-in-window-only', 'employment_light', monthly([2.0, 2.0, 2.0] + [4.0] * 12 + [4.3, 4.3, 4.4]))
    holes = monthly([4.0] * 12 + [4.4, 4.5, 4.6]); holes[6][1] = None
    add('employment-unpublished-month-skipped-not-filled', 'employment_light', holes)
    gap = monthly([4.0] * 12 + [4.4, 4.5, 4.6]); gap[13][1] = None
    add('employment-avg-window-incomplete', 'employment_light', gap)
    add('employment-short-history', 'employment_light', monthly([4.0, 4.6, 4.7, 4.8]))
    add('employment-empty', 'employment_light', [])
    add('employment-conflicting-duplicate', 'employment_light', monthly(flat) + [['2029-03', 4.2]])
    add('employment-invalid-period', 'employment_light', [['2029-13', 4.0]])
    add('employment-zero-is-a-value-negative-is-missing', 'employment_light', monthly([0.0] * 12 + [0.0, 0.0, -1.0]))
    # inflation: CPI YoY > 5 %
    add('inflation-3pct-not-lit', 'inflation_light', monthly([100.0] + [101.0] * 11 + [103.0]))
    add('inflation-6pct-lit', 'inflation_light', monthly([100.0] + [102.0] * 11 + [106.0]))
    add('inflation-exactly-5pct-not-lit', 'inflation_light', monthly([100.0] + [102.0] * 11 + [105.0]))
    add('inflation-9pct-lit', 'inflation_light', monthly([200.0] + [210.0] * 11 + [218.0]))
    add('inflation-base-month-missing', 'inflation_light', monthly([None] + [102.0] * 11 + [106.0]))
    add('inflation-latest-unpublished-uses-previous', 'inflation_light', monthly([100.0, 100.0] + [102.0] * 11 + [None]))
    add('inflation-no-data', 'inflation_light', monthly([None, None]))
    # curve: 10 Y − 3 M < 0 for ≥ 20 consecutive published days
    days = weekdays('2031-01-02', 40)

    def curve(spreads):
        return [[d, 4.0, None if s is None else round(4.0 + s, 2)] for d, s in zip(days, spreads)]

    add('curve-inverted-25-days-lit', 'curve_light', curve([0.3] * 15 + [-0.2] * 25))
    add('curve-inverted-19-days-not-lit', 'curve_light', curve([0.3] * 21 + [-0.1] * 19))
    add('curve-inverted-20-days-lit', 'curve_light', curve([0.3] * 20 + [-0.01] * 20))
    add('curve-latest-positive-not-lit', 'curve_light', curve([-0.5] * 39 + [0.05]))
    add('curve-zero-spread-is-not-inverted', 'curve_light', curve([-0.2] * 30 + [0.0] + [-0.2] * 9))
    add('curve-all-negative-short-history', 'curve_light', curve([-0.2] * 10)[:10])
    add('curve-missing-day-inside-run', 'curve_light', curve([-0.2] * 30 + [None] + [-0.2] * 9))
    add('curve-missing-day-after-20', 'curve_light', curve([0.2] * 5 + [None] + [-0.2] * 34))
    add('curve-latest-missing', 'curve_light', curve([-0.2] * 39 + [None]))
    add('curve-unordered-input-is-sorted', 'curve_light', list(reversed(curve([0.3] * 15 + [-0.2] * 25))))
    # market: SPY ≤ −20 % from the 52-week high OR 20-session realized vol in the top 5 % of 3 years
    long = weekdays('2027-01-04', 820)
    add('market-calm-not-lit', 'market_light', walk(long, 7, 0.01, shocks={790: (0.0005, 0.002)}))
    add('market-crash-drawdown-lit', 'market_light', walk(long, 11, 0.008, shocks={780: (-0.008, 0.004)}))
    add('market-vol-spike-lit', 'market_light', walk(long, 13, 0.006, shocks={799: (0.0, 0.05)}))
    short = weekdays('2029-06-01', 400)
    add('market-1y-history-crash-lit-by-drawdown-only', 'market_light', walk(short, 17, 0.008, shocks={360: (-0.01, 0.003)}))
    add('market-1y-history-calm-no-data', 'market_light', walk(short, 19, 0.008))
    add('market-60-days-no-data', 'market_light', walk(weekdays('2030-01-01', 60), 23, 0.01))
    holed = walk(long, 29, 0.01, shocks={790: (0.0005, 0.002)}); holed[-5][1] = None
    add('market-recent-gap-no-data', 'market_light', holed)
    add('market-empty', 'market_light', [])
    # credit: HYG ÷ IEF over 20 joint sessions ≤ −5 % (estimate)
    cd = weekdays('2031-03-03', 30)
    ief = [[d, 100.0] for d in cd]
    add('credit-calm-not-lit', 'credit_light', [[d, round(80 - 0.05 * i, 4)] for i, d in enumerate(cd)], ief)
    add('credit-stress-lit', 'credit_light', [[d, round(80 * (1 - 0.004 * i), 4)] for i, d in enumerate(cd)], ief)
    add('credit-ief-up-hyg-flat-lit', 'credit_light', [[d, 80.0] for d in cd], [[d, round(100 * (1 + 0.003 * i), 4)] for i, d in enumerate(cd)])
    add('credit-boundary-exactly-5pct-lit', 'credit_light', [[d, 100.0] for d in cd[:10]] + [[d, 95.0] for d in cd[10:]], [[d, 100.0] for d in cd])
    ief_hole = [[d, 100.0] for d in cd]; ief_hole[25][1] = None
    add('credit-missing-day-skipped-in-joint-calendar', 'credit_light', [[d, round(80 * (1 - 0.004 * i), 4)] for i, d in enumerate(cd)], ief_hole)
    add('credit-short-history', 'credit_light', [[d, 80.0] for d in cd[:15]], [[d, 100.0] for d in cd[:15]])
    add('credit-no-numerator', 'credit_light', [], ief)
    # state
    L = lambda **kw: {n: kw.get(n) for n in ml.LIGHTS}
    add('state-all-off-normal', 'macro_state', L(employment=False, inflation=False, curve=False, market=False, credit=False), 0.02, 0.02)
    add('state-one-lit-normal', 'macro_state', L(employment=True, inflation=False, curve=False, market=False, credit=False), 0.02, 0.02)
    add('state-two-lit-warning', 'macro_state', L(employment=True, inflation=False, curve=True, market=False, credit=False), 0.02, 0.02)
    add('state-three-lit-crisis', 'macro_state', L(employment=True, inflation=False, curve=True, market=True, credit=False), 0.02, 0.02)
    add('state-market-and-credit-crisis', 'macro_state', L(employment=False, inflation=False, curve=False, market=True, credit=True), 0.02, 0.02)
    add('state-inflation-over-8-crisis', 'macro_state', L(employment=False, inflation=True, curve=False, market=False, credit=False), 0.09, 0.03)
    add('state-stagflation-warning', 'macro_state', L(employment=False, inflation=True, curve=False, market=False, credit=False), 0.06, -0.01)
    add('state-inflation-6-growth-positive-normal', 'macro_state', L(employment=False, inflation=True, curve=False, market=False, credit=False), 0.06, 0.01)
    add('state-inflation-exactly-5-growth-negative-normal', 'macro_state', L(employment=False, inflation=False, curve=False, market=False, credit=False), 0.05, -0.01)
    add('state-growth-missing-no-stagflation-rule', 'macro_state', L(employment=False, inflation=True, curve=False, market=None, credit=None), 0.06, None)
    add('state-no-data-is-normal-low-confidence', 'macro_state', L(), None, None)
    add('state-two-available-low-confidence', 'macro_state', L(employment=True, inflation=True), 0.06, 0.02)
    add('state-three-available-one-lit', 'macro_state', L(employment=True, inflation=False, curve=False), 0.02, 0.02)
    add('state-light-rows-and-invalid-numbers', 'macro_state', {'employment': {'lit': True, 'reason': 'LIT'}, 'inflation': {'lit': None, 'reason': 'NO_DATA'},
                                                                'curve': {'lit': True}, 'market': 'yes', 'credit': 1}, '0.09', float(1e300))
    add('state-market-alone-with-credit-blocked', 'macro_state', L(employment=False, inflation=False, curve=False, market=True, credit=None), 0.02, 0.02)
    return c


def build():
    out = []
    for case in cases():
        args = json.loads(json.dumps(case['args']))
        expected = FUNCTIONS[case['fn']](*args)
        out.append({**case, 'synthetic': True, 'expected_json': json.dumps(expected, sort_keys=True, allow_nan=False)})
    return {'note': NOTE, 'config_id': ml.CONFIG['id'], 'config_version': ml.CONFIG['version'], 'cases': out}


def main(argv):
    text = json.dumps(build(), ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n'
    if '--check' in argv:
        if OUT.read_text(encoding='utf-8') != text:
            print('MACRO_LIGHTS_VECTORS_STALE')
            return 1
        print('MACRO_LIGHTS_VECTORS_OK cases=%d' % len(json.loads(text)['cases']))
        return 0
    OUT.write_text(text, encoding='utf-8')
    print('MACRO_LIGHTS_VECTORS_WRITTEN cases=%d' % len(json.loads(text)['cases']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
