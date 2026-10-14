#!/usr/bin/env python3
"""Synthetic Python reference vectors for QGV v2 device scoring (web_assets/qgv-v2.js == qgv/qgv_v2.py).

Usage: qgv_v2_reference.py --write   (regenerates tests/fixtures/qgv_v2_vectors_v1.json)
       qgv_v2_reference.py --check   (exit 1 when the committed fixture differs from a fresh run)
Synthetic codes, prices and fundamentals only (SYN tickers); never a public or live-data serializer.
"""
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
FIXTURE = Path(__file__).resolve().parents[1] / 'tests/fixtures/qgv_v2_vectors_v1.json'
Q_IDS = ('q_profitability', 'q_moat_proxy', 'q_earnings_quality', 'q_financial_safety', 'q_capital_allocation')
G_IDS = ('g_revenue_growth', 'g_per_share_growth', 'g_growth_efficiency', 'g_consistency', 'g_recent_acceleration')


def _company(n, group, *, profile='GENERAL', q=60.0, g=50.0, missing=(), ebit=None, fcf=None, debt=200.0, cash=100.0,
             shares=100.0, cagr=0.06, memberships=None, history=True, currency='USD', v=True):
    """Synthetic company n (1..): fundamentals in synthetic units, scores 0..100."""
    factors = {}
    for i, k in enumerate(Q_IDS):
        factors[k] = None if k in missing else round(q + (i - 2) * 3.0 + n * 0.5, 4)
    for i, k in enumerate(G_IDS):
        factors[k] = None if k in missing else round(g + (2 - i) * 2.0 + n * 0.25, 4)
    ebit = 50.0 + n * 7.0 if ebit is None else ebit
    fcf = 30.0 + n * 5.0 if fcf is None else fcf
    hist = [{'period_end': f'{2020 + y}-12-31', 'value': round(ebit / shares * (0.7 + 0.08 * y), 6)} for y in range(5)] if history else []
    vin = {'currency': currency, 'ebit': ebit, 'fcf': fcf, 'total_debt': debt, 'cash': cash, 'diluted_shares': shares,
           'ebit_per_share_history': hist, 'revenue_cagr_3y': cagr} if v else None
    return {'industry_group': group, 'profile': profile, 'factors': factors, 'v_inputs': vin, 'memberships': memberships}


def _month_closes(base):
    """Synthetic month-end closes {YYYY-MM: close} (device Prices tab shape) around each fiscal year end 2020..2024."""
    out = {}
    for y in range(5):
        out[f'{2020 + y}-12'] = round(base * (1.4 - 0.15 * y), 4)
        out[f'{2020 + y}-11'] = round(base * (0.55 + 0.1 * y), 4)
    out['2021-12'] = None  # a missing month stays missing (never 0)
    return out


def universe():
    c = {}
    # Group A: 9 companies (>= 8 peers -> INDUSTRY basis).
    for n in range(1, 10):
        c[f'NYSE:SYNA{n}'] = _company(n, 'synthetic_group_a', q=40.0 + n * 4.0, g=45.0 + (n % 4) * 6.0)
    # Group B: 3 companies (< 8 peers -> UNIVERSE_FALLBACK).
    for n in range(1, 4):
        c[f'NASDAQ:SYNB{n}'] = _company(n + 10, 'synthetic_group_b', q=55.0 + n, g=60.0 - n)
    c['NASDAQ:SYNB1']['memberships'] = {'growth': 0.9, 'quality': 0.4, 'value': None, 'dividend': None}
    c['NASDAQ:SYNB2']['memberships'] = {'growth': 0.1, 'quality': 0.2}
    c['NYSE:SYNA9']['memberships'] = {'quality': 1.0}
    # Edge cases.
    c['NYSE:SYNF1'] = _company(20, 'synthetic_group_fin', profile='FINANCIAL', q=70.0, g=40.0)
    c['NYSE:SYNN1'] = _company(21, None, q=50.0, g=50.0)                        # no SIC group
    c['NYSE:SYNC1'] = _company(22, 'synthetic_group_a', cash=1.0e6, q=65.0)       # EV <= 0
    c['NYSE:SYNX1'] = _company(23, 'synthetic_group_a', fcf=-40.0, q=52.0)        # negative FCF -> reverse DCF NA
    c['NYSE:SYNP1'] = _company(24, 'synthetic_group_a', q=58.0, missing=('q_profitability', 'q_moat_proxy', 'q_earnings_quality'))  # Q axis NA
    c['NYSE:SYNG1'] = _company(25, 'synthetic_group_b', missing=('g_revenue_growth', 'g_per_share_growth'), q=61.0)  # G partial
    c['NYSE:SYNE1'] = _company(26, 'synthetic_group_b', currency='EUR')          # currency basis
    c['NYSE:SYNV1'] = _company(27, 'synthetic_group_a', v=False)                  # no v_inputs
    c['NYSE:SYNR1'] = _company(28, 'synthetic_group_a', cagr=None)                # realized growth missing
    c['TARGET:synt'] = dict(_company(29, 'synthetic_group_a', q=45.0), in_cross_section=False)  # TARGET-only row: ranked, not pooled
    # Cyclical type (PLAYBOOK_V1 §13-2): EBIT-based yield on revenue × 5-year mean operating margin; < 5 margins -> NA.
    c['NYSE:SYNY1'] = _company(30, 'synthetic_group_a', memberships={'cyclical': 0.9})
    c['NYSE:SYNY1']['v_inputs'].update(revenue=900.0, operating_margin_history=[{'period_end': f'{2020 + y}-12-31', 'value': 0.08 + 0.02 * y} for y in range(6)])
    c['NYSE:SYNY2'] = _company(31, 'synthetic_group_a', memberships={'cyclical': 0.9})
    c['NYSE:SYNY2']['v_inputs'].update(revenue=900.0, operating_margin_history=[{'period_end': f'{2022 + y}-12-31', 'value': 0.1} for y in range(3)])
    c['NYSE:SYNA1.B'] = dict(c['NYSE:SYNA1'], in_cross_section=False)            # second listing of one issuer
    return c


def published(companies):
    """Same universe with published Q/G axis scores (sec-qgv2 axes) instead of recomputation."""
    out = copy.deepcopy(companies)
    for n, (k, v) in enumerate(sorted(out.items())):
        v['qg_axes'] = {'Q': {'score': None if n % 7 == 3 else 30.0 + (n * 13) % 60}, 'G': {'score': 40.0 + (n * 7) % 50}}
    return out


def market(companies, *, skip=(), history_for=('NYSE:SYNA3', 'NASDAQ:SYNB2')):
    out = {}
    for k in sorted(companies):
        if k in skip:
            continue
        idx = sum(ord(ch) for ch in k) % 37
        price = 8.0 + idx * 0.9
        out[k] = {'price': price, 'currency': 'USD'}
        if k in history_for:
            out[k]['month_closes'] = _month_closes(price)
    out.pop('NYSE:SYNQ0', None)
    return out


def unit_cases():
    from investment_system.qgv import qgv_v2 as m
    from investment_system.qgv.type_config import load_official_type_config
    cfg = load_official_type_config().to_dict()
    pops = [[5.0, 1.0, 3.0], [2.0, 2.0, 2.0, 1.0], [7.0], [-0.5, 0.25, 0.25, 4.0, 9.0]]
    percentile = [{'value': v, 'population': p, 'expected': m.percentile(v, p)} for p in pops for v in sorted(set(p))]
    axis = []
    for scores in ({'q_profitability': 80, 'q_moat_proxy': 60, 'q_earnings_quality': 40, 'q_financial_safety': 20, 'q_capital_allocation': 0},
                   {'q_profitability': 80, 'q_moat_proxy': None, 'q_earnings_quality': 40, 'q_financial_safety': None, 'q_capital_allocation': 0},
                   {'q_profitability': 80, 'q_moat_proxy': None, 'q_earnings_quality': None, 'q_financial_safety': None, 'q_capital_allocation': 0},
                   {}):
        axis.append({'axis': 'Q', 'scores': scores, 'expected': m.axis_score(scores, 'Q')})
    types = []
    for mem in (None, {}, {'growth': 0.9}, {'growth': 0.5, 'quality': 0.5}, {'cyclical': 0.8, 'defensive': 0.9, 'growth': 0.2},
                {'growth': 1.0, 'quality': 0.6, 'dividend': 0.4, 'leader': 0.3}, {'theme': 1.0}):
        types.append({'memberships': mem, 'expected': list(m.type_axis_weights(mem, cfg))})
    composite = []
    fallback = {p: float(cfg['fallback']['weights'][p]) for p in m.PILLARS}
    for preset in m.PRESETS:
        for tw in ({'Q': 34.0, 'G': 33.0, 'V': 33.0}, {'Q': 30.0, 'G': 50.0, 'V': 20.0}):
            composite.append({'preset': preset, 'type_weights': tw, 'expected': m.composite_weights(m.PRESETS[preset]['weights'], tw, fallback)})
    return {'percentile': percentile, 'axis': axis, 'type_weights': types, 'composite': composite}


def cases():
    from investment_system.qgv import qgv_v2 as m
    from investment_system.qgv.dcf_parameters import load_default_dcf_parameters
    from investment_system.qgv.type_config import load_official_type_config
    cfg = load_official_type_config().to_dict()
    params = load_default_dcf_parameters()
    u = universe()
    full = market(u, skip=('NYSE:SYNN1',))
    small = {k: v for k, v in list(full.items())[:5]}
    spec = [
        ('balanced-default', u, full, 'balanced', None),
        ('value-gate-off', u, full, 'value', False),
        ('quality-gate-on', u, full, 'quality', True),
        ('growth-default', u, full, 'growth', None),
        ('small-cross-section', u, small, 'balanced', None),
        ('no-device-prices', u, {}, 'balanced', None),
        ('published-axes', published(u), full, 'balanced', None),
    ]
    out = []
    for cid, comps, mk, preset, gate in spec:
        result = m.score_universe(copy.deepcopy(comps), copy.deepcopy(mk), type_config=cfg, parameters=params, preset=preset, gate=gate)
        out.append({'id': cid, 'input': {'companies': comps, 'synthetic_market': mk, 'preset': preset, 'gate': gate}, 'expected': result})
    return out


def payload():
    from investment_system.qgv import qgv_v2 as m
    return {'schema_version': 1, 'kind': 'QGV_V2_REFERENCE_VECTORS', 'synthetic': True, 'version': m.VERSION, 'status': m.STATUS,
            'config': {'weights': m.WEIGHTS, 'presets': m.PRESETS, 'default_preset': m.DEFAULT_PRESET, 'gate_default': m.GATE_DEFAULT,
                       'gate_percentile': m.GATE_PERCENTILE, 'min_peers': m.MIN_PEERS, 'min_universe': m.MIN_UNIVERSE,
                       'min_axis_weight': m.MIN_AXIS_WEIGHT, 'min_history': m.MIN_HISTORY},
            'units': unit_cases(), 'cases': cases()}


def main(argv):
    text = json.dumps(payload(), ensure_ascii=False, indent=1, sort_keys=True) + '\n'
    if '--write' in argv:
        FIXTURE.write_text(text, encoding='utf-8')
        print('WROTE ' + str(FIXTURE.name))
        return 0
    if '--check' in argv:
        same = FIXTURE.exists() and FIXTURE.read_text(encoding='utf-8') == text
        print('FIXTURE_' + ('OK' if same else 'STALE'))
        return 0 if same else 1
    sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
