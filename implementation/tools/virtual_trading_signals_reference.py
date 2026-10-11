"""Build tests/fixtures/virtual_trading_signals_v1.json: SYNTHETIC runner-level vectors for D-5, V history and rehearsal.

Every close, FX rate, V value and valuation input below is generated (fixed LCG / fixed numbers), not market data.
Worker-shaped 2y daily histories (326 weekday sessions) go through the runner assembly (qgv/virtual_trading_inputs.py),
the engine (qgv/virtual_trading.py) and the signal helpers (qgv/virtual_trading_signals.py):
- msft (D-22 XLK, 326 aligned closes) falls sharply against XLK over its last sessions → ▼ RECHECK_ABNORMAL_DROP;
- googl (XLK) has exactly 273 closes (the D-5 minimum) and a rising stored V history → basis usable, V slope READY;
- nvda (SMH) has 272 closes → RECHECK_BASIS_NOT_AVAILABLE (HISTORY_INSUFFICIENT), V slope unused;
- amzn (XLY) gets a Worker error for XLY → the engine falls back to S&P 500 and the report labels it.
Usage: python tools/virtual_trading_signals_reference.py [--check]
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from investment_system.qgv import virtual_trading as vt  # noqa: E402
from investment_system.qgv import virtual_trading_inputs as vi  # noqa: E402
from investment_system.qgv import virtual_trading_signals as vs  # noqa: E402
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters  # noqa: E402
import virtual_trading_inputs_reference as base  # noqa: E402

OUT = ROOT / 'tests/fixtures/virtual_trading_signals_v1.json'
NOTE = 'SYNTHETIC test vectors: every close, FX rate, V value and valuation input below is generated, not market data.'
READ_AT = '2026-12-01T01:00:00Z'
DAYS = base.weekdays('2025-09-01', '2026-11-30')
FOCUS = ('amzn', 'googl', 'msft', 'nvda')


def bars(values, zone, hour):
    return [{'timestamp': base.stamp(d, zone, hour), 'close': p, 'session_status': 'COMPLETE'} for d, p in values]


def walk(seed, start, amplitude, days=DAYS, shock=None):
    r, p, out = base.Lcg(seed), start, []
    for i, d in enumerate(days):
        step = (r.next() - 0.5) * amplitude
        if shock:
            step += shock(i, len(days))
        p = round(p * (1 + step), 4)
        out.append((d, p))
    return out


def body(symbol, currency, zone, values, hour=15):
    return {'schema': 'private-history/1', 'provider': 'Yahoo Finance(비공식)', 'symbol': symbol, 'range': '2y', 'currency': currency,
            'exchange': 'SYNTHETIC', 'timezone': zone, 'interval': '1d', 'basis': 'RAW_CLOSE', 'delay_status': 'UNKNOWN',
            'read_at': READ_AT, 'bars': bars(values, zone, hour)}


def histories():
    ny = 'America/New_York'
    xlk = walk(41, 200.0, 0.012)
    msft_noise = walk(43, 1.0, 0.012)
    # msft = XLK × own noise, then −4 % per session over the last 12 sessions (a sharp, company-specific fall).
    msft = []
    for i, ((d, b), (_, n)) in enumerate(zip(xlk, msft_noise)):
        fall = 0.96 ** max(0, i - (len(DAYS) - 13))
        msft.append((d, round(b * n * 2.0 * fall, 4)))
    out = {
        'SPY': body('SPY', 'USD', ny, walk(7, 500.0, 0.01)),
        'KRW=X': body('KRW=X', 'KRW', 'Europe/London', walk(11, 1380.0, 0.006), hour=0),
        'MSFT': body('MSFT', 'USD', ny, msft),
        'GOOGL': body('GOOGL', 'USD', ny, walk(47, 150.0, 0.014)[-273:]),
        'NVDA': body('NVDA', 'USD', ny, walk(53, 120.0, 0.02)[-272:]),
        'AMZN': body('AMZN', 'USD', ny, walk(59, 180.0, 0.014)),
        'XLK': body('XLK', 'USD', ny, xlk),
        'SMH': body('SMH', 'USD', ny, walk(61, 250.0, 0.016)),
        'XLY': {'error': 'REQUEST_INVALID'},
    }
    return out


def forward_ledger(days):
    records = []
    for d in days:
        companies = {cid: {'state': 'LIVE', 'Q': {'score': 50 + j, 'coverage': 'READY', 'missing_factor_count': 0},
                           'G': {'score': 60 - j * 0.5, 'coverage': 'READY', 'missing_factor_count': 0}}
                     for j, cid in enumerate(vi.IDS)}
        records.append({'date': d, 'state': 'RECORDED', 'reason_codes': [], 'companies': companies})
    return {'kind': 'FORWARD_VALIDATION_LEDGER', 'versions': {vi.FORWARD_VERSION: records}}


def v_store(days):
    """Stored device V from 2026-10-19: googl rises 0.75 per session (+15 over 20), msft flat, nvda flat."""
    out = {}
    for i, d in enumerate(x for x in days if x >= '2026-10-19'):
        out[d] = {'googl': round(40 + 0.75 * i, 2), 'msft': 55.0, 'nvda': 48.5}
    return out


def valuation():
    """Price-free synthetic valuation rows (public sec-valuation-inputs.json shape) for four companies."""
    def row(fcfe, currency='USD', eps=4.0, revenue=5000.0, revenue_prev=4600.0, cagr=0.08):
        fcfe_block = ({'state': 'NOT_AVAILABLE', 'reason_codes': ['SEC_INPUT_NOT_AVAILABLE'], 'fcfe_per_share': None, 'currency': None}
                      if fcfe is None else {'state': 'LIVE', 'reason_codes': [], 'fcfe_per_share': fcfe, 'currency': currency})
        return {'state': 'LIVE', 'fcfe': fcfe_block,
                'v_inputs': {'state': 'LIVE', 'reason_codes': [], 'eps': eps, 'revenue': revenue, 'revenue_prev': revenue_prev,
                             'revenue_cagr_3y': cagr, 'currency': currency}}
    return {'kind': 'SEC_VALUATION_INPUTS', 'data': {'companies': {
        'msft': row(13.0, eps=11.0), 'googl': row(7.25, eps=6.5, cagr=0.12), 'nvda': row(4.0, eps=4.5, cagr=0.31),
        'amzn': row(None, eps=8.0),            # no FCFE: DCF, reverse DCF and margin of safety NOT_AVAILABLE, EPS branch only
        'asml': row(4.25, currency='EUR')}}}   # EUR filer, no ASML close in these histories → no V


def qg_rows():
    """Today's public Q·G screen rows (synthetic) for the rehearsal snapshot fill."""
    return {'msft': {'q': 61.5, 'g': 58.0, 'partial': False}, 'googl': {'q': 64.0, 'g': 66.5, 'partial': True},
            'nvda': {'q': 70.0, 'g': None, 'partial': True}, 'amzn': {'q': 55.0, 'g': 57.25, 'partial': False},
            'unknown_co': {'q': 1, 'g': 1, 'partial': False}}


def scenarios():
    inputs = {'config': {'start_date': '2026-10-19'}, 'catalog': base.catalog(), 'forward_ledger': forward_ledger([d for d in DAYS if d >= '2026-10-19']),
              'classification': base.classification(), 'histories': histories(), 'holdings': None, 'set_b': None,
              'v_store': v_store(DAYS), 'flags': []}
    out = [{'name': 'recording_d5_v_slope', 'inputs': inputs, 'rehearsal': False}]
    s = copy.deepcopy(inputs)
    s['forward_ledger'] = None          # before the start date nothing is published: today's public Q·G fills the window
    s['v_store'] = {}
    out.append({'name': 'rehearsal_window_qg_fill', 'inputs': s, 'rehearsal': True})
    s = copy.deepcopy(inputs)
    s['histories'] = {'SPY': {'error': 'REQUEST_INVALID'}}
    out.append({'name': 'rehearsal_without_spy', 'inputs': s, 'rehearsal': True})
    return out


def project(result):
    days = result['days']
    return {'state': result['state'], 'reason_codes': result['reason_codes'],
            'sessions': [d['date'] for d in days],
            'mains': {d['date']: {cid: d['judgements'][cid]['main'] for cid in FOCUS if cid in d['judgements']} for d in days},
            'last': {cid: {k: days[-1]['judgements'][cid][k] for k in ('main', 'aux_levels', 'aux', 'reason_codes')}
                     for cid in FOCUS if days and cid in days[-1]['judgements']},
            'trade_count': len(result['trades'])}


def build():
    cfg, params, vectors = vt.load_config(), load_default_dcf_parameters(), []
    for sc in scenarios():
        inputs = sc['inputs']
        run_cfg = vs.rehearsal_config(inputs['histories'], cfg) if sc['rehearsal'] else cfg | {'start_date': inputs['config']['start_date']}
        assembled = vi.assemble(**(inputs | {'config': {'start_date': run_cfg['start_date']}}))
        filled = []
        if sc['rehearsal']:
            assembled, filled = vs.apply_rehearsal_snapshots(assembled, qg_rows())
        plan = vs.capture_plan(assembled)
        v_now, v_raw = vs.v_scores_for(plan, valuation(), params)
        entry = assembled['ledgers']['SET_A']
        engine = project(vt.run_ledger(run_cfg, copy.deepcopy(entry['input']))) if entry['state'] == 'READY' else None
        vectors.append({'name': sc['name'], 'rehearsal': sc['rehearsal'], 'inputs': inputs,
                        'expected': {'run_start_date': run_cfg['start_date'],
                                     'rehearsal_start': vs.rehearsal_start(inputs['histories']) if sc['rehearsal'] else None,
                                     'state': assembled['state'], 'reason_codes': assembled['reason_codes'],
                                     'sessions': entry['input']['sessions'] if entry['state'] == 'READY' else None,
                                     'sector_keys': {cid: c['sector_benchmark'] for cid, c in entry['input']['companies'].items()} if entry['state'] == 'READY' else None,
                                     'benchmark_keys': sorted(entry['input']['benchmarks']) if entry['state'] == 'READY' else None,
                                     'qg_filled': filled,
                                     'signals': vs.report_signals(assembled, 'SET_A', run_cfg, inputs['v_store']),
                                     'capture_date': plan['date'] if plan else None,
                                     'v_scores': v_now, 'v_raw': v_raw,
                                     'engine': engine}})
    return {'schema_version': 1, 'note': NOTE, 'synthetic': True, 'qg_rows': qg_rows(), 'valuation': valuation(), 'vectors': vectors}


def text():
    return json.dumps(build(), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'


def main(argv):
    if '--check' in argv:
        print('VIRTUAL_TRADING_SIGNALS_REFERENCE_OK' if OUT.read_text(encoding='utf-8') == text() else 'VIRTUAL_TRADING_SIGNALS_REFERENCE_STALE')
        return 0
    OUT.write_text(text(), encoding='utf-8')
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
