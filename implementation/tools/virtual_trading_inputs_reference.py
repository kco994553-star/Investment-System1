"""Build tests/fixtures/virtual_trading_inputs_v1.json: SYNTHETIC Worker-shaped inputs + Python reference assembly.

All prices, FX rates and holdings are synthetic (fixed LCG, no market data). The catalog is the public, price-free
actual-catalog.json. Each vector holds the inputs, the expected ledger inputs (qgv/virtual_trading_inputs.py) and,
for the full scenario, the Python engine result on the assembled SET_A and SHADOW inputs so the device runner and
engine can be checked end to end. Usage: python tools/virtual_trading_inputs_reference.py [--check]
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.qgv import virtual_trading as vt  # noqa: E402
from investment_system.qgv import virtual_trading_inputs as vi  # noqa: E402
from investment_system.product.device_actual_catalog import public_actual_catalog  # noqa: E402

OUT = ROOT / 'tests/fixtures/virtual_trading_inputs_v1.json'
NOTE = 'SYNTHETIC test vectors: every price, FX rate and holding below is generated (LCG), not market data.'
TZ = {'USD': 'America/New_York', 'KRW': 'Asia/Seoul', 'JPY': 'Asia/Tokyo', 'FX': 'Europe/London'}
READ_AT = '2026-10-30T22:00:00Z'
H = 'c' * 64


class Lcg:
    def __init__(self, seed):
        self.s = seed

    def next(self):
        self.s = (self.s * 1103515245 + 12345) % 2147483648
        return self.s / 2147483648


def weekdays(start, end):
    d, out = dt.date.fromisoformat(start), []
    while d <= dt.date.fromisoformat(end):
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


DAYS = weekdays('2026-10-12', '2026-10-30')


def stamp(day, zone, hour):
    local = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(hour), ZoneInfo(zone))
    return int(local.timestamp())


def payload(symbol, currency, zone, seed, start, *, hour=9, kind='quote', mutate=None):
    r, p, bars = Lcg(seed), start, []
    for d in DAYS:
        p = round(p * (1 + (r.next() - 0.5) * 0.04), 4)
        bars.append({'timestamp': stamp(d, zone, 0 if kind == 'fx' else hour), 'close': p, 'session_status': 'COMPLETE'})
    body = {'schema': 'private-history/1', 'provider': 'Yahoo Finance(비공식)', 'symbol': symbol, 'range': '2y',
            'currency': currency, 'exchange': 'SYNTHETIC', 'timezone': zone, 'interval': '1d', 'basis': 'RAW_CLOSE',
            'delay_status': 'UNKNOWN', 'read_at': READ_AT, 'bars': bars}
    if mutate:
        mutate(body)
    return body


def catalog():
    return public_actual_catalog()


def classification():
    sic = {'asml': '3559', 'lrcx': '3559', 'klac': '3827', 'nvda': '3674', 'amd': '3674', 'avgo': '3674', 'qcom': '3674',
           'intc': '3674', 'msft': '7372', 'googl': '7370', 'amzn': '5961', 'rtx': '3720', 'stry': '3841', 'etn': '3640',
           'hubb': '3640', 'gev': '3511', 'rok': '3620', 'tokyo_electron': None, 'hanmi': None}
    semis = {'asml': True, 'lrcx': True, 'klac': None}
    companies = {}
    for cid in vi.IDS:
        companies[cid] = {'industry': {'state': 'LIVE' if sic[cid] else 'NOT_AVAILABLE', 'sic': sic[cid]},
                          'themes': {'memberships': {'semiconductors': {'member': semis.get(cid, False)}}}}
    return {'kind': 'COMPANY_CLASSIFICATION', 'data': {'companies': companies}}


def forward_ledger(days):
    records = []
    for i, d in enumerate(days):
        if i == 2:
            records.append({'date': d, 'state': 'NOT_AVAILABLE', 'reason_codes': ['SEC_QG_FACTORS_MISSING'], 'companies': None})
            continue
        companies = {}
        for j, cid in enumerate(vi.IDS):
            if j % 7 == 3:
                companies[cid] = {'state': 'NOT_AVAILABLE', 'Q': {'score': None, 'coverage': 'BLOCKED', 'missing_factor_count': 7},
                                  'G': {'score': None, 'coverage': 'BLOCKED', 'missing_factor_count': 6}}
            else:
                q_cov = 'PARTIAL' if j % 5 == 1 else 'READY'
                state = 'STALE' if j % 6 == 5 else 'LIVE'
                q = round(50 + j - (8 if (cid == 'msft' and i >= 4) else 0) + 0.25 * i, 4)
                companies[cid] = {'state': state, 'Q': {'score': q, 'coverage': q_cov, 'missing_factor_count': 1 if q_cov == 'PARTIAL' else 0},
                                  'G': {'score': round(60 - j * 0.5, 4), 'coverage': 'READY', 'missing_factor_count': 0}}
        records.append({'date': d, 'state': 'RECORDED', 'reason_codes': [], 'companies': companies})
    return {'kind': 'FORWARD_VALIDATION_LEDGER', 'versions': {vi.FORWARD_VERSION: records}}


def histories(full_etfs=True):
    out = {'SPY': payload('SPY', 'USD', TZ['USD'], 7, 500.0)}

    def fx_gap(body):
        # USD/KRW: last session close missing (null) → the device must leave it absent (EXEC_FX_MISSING downstream).
        body['bars'][-1]['close'] = None

    out['KRW=X'] = payload('KRW=X', 'KRW', TZ['FX'], 11, 1380.0, kind='fx', mutate=fx_gap)
    out['JPYKRW=X'] = payload('JPYKRW=X', 'KRW', TZ['FX'], 13, 9.2, kind='fx')
    cat = {t['cid']: t for t in vi.catalog_targets(catalog())}
    for n, cid in enumerate(vi.IDS):
        ccy = cat[cid]['currency']
        mutate = None
        if cid == 'nvda':
            def mutate(body):
                body['bars'][-1]['session_status'] = 'IN_PROGRESS'           # excluded
                body['bars'][-2]['session_status'] = 'UNKNOWN'               # past date → used
                body['bars'][8]['close'] = None                              # absent, not filled
        elif cid == 'hanmi':
            def mutate(body):
                for bar in body['bars']:
                    bar['session_date'] = dt.datetime.fromtimestamp(bar['timestamp'], ZoneInfo(TZ['KRW'])).date().isoformat()
        elif cid == 'amd':
            def mutate(body):
                body['bars'][-1]['session_status'] = 'UNKNOWN'               # same local date as read_at → excluded
                body['bars'][5]['timestamp'] = body['bars'][4]['timestamp'] + 3600   # two bars on one date → both dropped
        out[vi.TARGETS[cid]] = payload(vi.TARGETS[cid], ccy, TZ[ccy], 100 + n, 50.0 + 10 * n, hour=15 if ccy == 'USD' else 15, mutate=mutate)
    if full_etfs:
        out['SMH'] = payload('SMH', 'USD', TZ['USD'], 31, 250.0)
        out['XLK'] = {'error': 'REQUEST_INVALID'}
        out['XLI'] = payload('XLI', 'USD', TZ['USD'], 37, 130.0)
    return out


def holdings():
    return {'effective_at': '2026-10-21T01:00:00+09:00',
            'positions': {'nvda': {'quantity': 12.5, 'average_cost': 101.25, 'currency': 'USD'},
                          'hanmi': {'quantity': 30, 'average_cost': 70000, 'currency': 'KRW'},
                          'tokyo_electron': {'quantity': 4, 'average_cost': 2500.5, 'currency': 'JPY'},
                          'msft': {'quantity': 0, 'average_cost': 300, 'currency': 'USD'}}}


def v_store():
    return {'2026-10-20': {'nvda': 55.5, 'amd': 101, 'msft': None, 'qcom': True}, 'bad-date': {'nvda': 1},
            '2026-10-21': {'nvda': 'x'}, '2026-10-22': {'nvda': 61.0, 'googl': 0}}


def v_composition():
    # V history /2 composition keys (factor ids present that day); invalid entries are dropped, nothing is invented.
    return {'2026-10-20': {'nvda': 'f_one+f_two', 'amd': 'Bad Key'}, 'bad-date': {'nvda': 'f_one'}, '2026-10-22': {'nvda': 'f_one+f_two', 'googl': 7}}


def user_target():
    return {'nvda': 30, 'hanmi': 20, 'tokyo_electron': 10, 'msft': 20}


def flags():
    return [{'date': '2026-10-22', 'kind': 'HOLD', 'company': 'googl', 'note': 'dropped'},
            {'date': '2026-10-23', 'kind': 'SELL', 'company': 'nvda'}, {'date': 'x', 'kind': 'HOLD', 'company': 'amd'}]


def scenarios():
    days = [d for d in DAYS if d >= '2026-10-19']
    base = {'config': {'start_date': '2026-10-19'}, 'catalog': catalog(), 'forward_ledger': forward_ledger(days),
            'classification': classification(), 'histories': histories(), 'holdings': holdings(), 'set_b': None,
            'sets': None, 'user_target': user_target(), 'v_store': v_store(), 'v_composition': v_composition(), 'flags': flags()}
    out = [{'name': 'full_synthetic', 'inputs': base, 'engine': ['SET_A', 'SHADOW']}]
    s = copy.deepcopy(base)
    s['histories'] = {'SPY': {'error': 'REQUEST_INVALID'}}  # the device stops requesting after SPY fails
    out.append({'name': 'spy_rejected', 'inputs': s})
    s = copy.deepcopy(base)
    s['histories']['KRW=X'] = {'error': 'REQUEST_INVALID'}
    s['histories']['JPYKRW=X'] = {'error': 'not a code'}
    out.append({'name': 'fx_rejected', 'inputs': s, 'engine': ['SET_A']})
    s = copy.deepcopy(base)
    s['catalog']['instruments'][3]['ticker'] = 'XXXX'
    s['histories'] = {}
    out.append({'name': 'catalog_invalid', 'inputs': s})
    s = copy.deepcopy(base)
    s['histories']['MSFT']['currency'] = 'KRW'
    s['histories']['GOOGL']['bars'][3]['timestamp'] = s['histories']['GOOGL']['bars'][2]['timestamp']
    s['histories']['AMZN'] = {'schema': 'private-history/1'}
    del s['histories']['RTX']
    s['classification'] = None
    s['holdings'] = None
    out.append({'name': 'format_currency_missing', 'inputs': s})
    s = copy.deepcopy(base)
    s['set_b'] = {'target_weights': {'nvda': 40, 'msft': 35.5, 'hanmi': 24.5}}
    s['holdings']['effective_at'] = '2026-11-02T10:00:00Z'
    out.append({'name': 'set_b_and_late_shadow', 'inputs': s, 'engine': ['SET_B', 'SHADOW']})
    s = copy.deepcopy(base)
    s['set_b'] = {'target_weights': {'nvda': 80, 'msft': 35}}
    s['config'] = {'start_date': '2026-11-02'}
    out.append({'name': 'set_b_invalid_before_start', 'inputs': s, 'engine': ['SET_A']})
    # User sets B/C/D (decision 2026-10-11): members are TARGET companies or allowlisted ETFs (SMH priced, VUG not
    # requested here → absent closes, never filled); an unknown member makes that set invalid. No user target → the
    # shadow ledger is TARGET_NOT_AVAILABLE (TARGET v0 is not substituted).
    s = copy.deepcopy(base)
    s['sets'] = {'SET_B': {'target_weights': {'nvda': 40, 'msft': 35.5, 'hanmi': 24.5}}, 'SET_C': {'target_weights': {'smh': 30, 'nvda': 20, 'vug': 10}},
                 'SET_D': {'target_weights': {'zzz': 10}}, 'SET_A': {'target_weights': {'xli': 5, 'asml': 50}}}
    s['user_target'] = None
    out.append({'name': 'sets_c_d_etf_members_no_user_target', 'inputs': s, 'engine': ['SET_C']})
    s = copy.deepcopy(base)
    s['user_target'] = {'nvda': 70, 'amd': 40}
    out.append({'name': 'user_target_invalid', 'inputs': s})
    return out


def project(result):
    """Compact engine result for the end-to-end check (the full engine is covered by virtual_trading_reference_v1)."""
    return {'state': result['state'], 'reason_codes': result['reason_codes'], 'summary': result['summary'], 'trades': result['trades'],
            'cancelled': [[d['date'], c['company'], c['cancel_reason']] for d in result['days'] for c in d['cancelled']],
            'mains': {d['date']: {cid: j['main'] for cid, j in sorted(d['judgements'].items())} for d in result['days']}}


def build():
    vectors, cfg = [], vt.load_config()
    for sc in scenarios():
        inputs = sc['inputs']
        expected = vi.assemble(**inputs)
        engine = None
        if sc.get('engine'):
            engine = {}
            for kind in sc['engine']:
                entry = expected['ledgers'][kind]
                run_cfg = cfg | {'start_date': inputs['config']['start_date']}
                engine[kind] = project(vt.run_ledger(run_cfg, copy.deepcopy(entry['input'])))
        vectors.append({'name': sc['name'], 'inputs': inputs,
                        'required_symbols': vi.required_symbols(catalog=inputs['catalog'], classification=inputs['classification'],
                                                                holdings=inputs['holdings'], set_b=inputs['set_b'], sets=inputs['sets'],
                                                                user_target=inputs['user_target']),
                        'expected': expected, 'expected_engine': engine})
    return {'schema_version': 1, 'note': NOTE, 'synthetic': True, 'vectors': vectors}


def text():
    return json.dumps(build(), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'


def main(argv):
    if '--check' in argv:
        print('VIRTUAL_TRADING_INPUTS_REFERENCE_OK' if OUT.read_text(encoding='utf-8') == text() else 'VIRTUAL_TRADING_INPUTS_REFERENCE_STALE')
        return 0
    OUT.write_text(text(), encoding='utf-8')
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
