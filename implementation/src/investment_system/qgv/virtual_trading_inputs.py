"""Virtual trading runner v1: assembly of the engine's ledger inputs from device-side sources (pure function).

Python reference for the pure part of web_assets/virtual-trading-runner.js (vectors:
tests/fixtures/virtual_trading_inputs_v1.json). The device fetches daily history through the existing private
history Worker and keeps it in RAM; this module only shows, for the same Worker-shaped inputs, which ledger input
the device must build. Nothing here fetches, stores or publishes prices, FX rates, ledgers or holdings.

Rules (ENGINE_V1.md, VIRTUAL_TRADING_V1_PROPOSAL.md):
- A close or FX rate is used only when its bar is COMPLETE, or UNKNOWN on a local date before the payload's read_at
  date. IN_PROGRESS bars, null closes and dates that occur twice are left out, never filled.
- Bar dates are the listing's local session date (bar.session_date, else the timestamp in the payload timezone),
  the same rule as private-history.js / forward-validation.js.
- Sessions are the SPY (S&P 500 proxy) session dates on or after start_date. No SPY → no ledger (NOT_AVAILABLE).
- Q·G snapshots come only from the public forward ledger's RECORDED records. V scores come only from values stored
  on the device per date; nothing is invented.
- A symbol the client or Worker rejected keeps its error code and is absent from the input (NOT_AVAILABLE).
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import math
import re
from zoneinfo import ZoneInfo

from .sector_basis import sector_benchmark

SCHEMA = 'virtual-trading-inputs/1'
IDS = ('asml', 'lrcx', 'klac', 'tokyo_electron', 'hanmi', 'nvda', 'amd', 'avgo', 'qcom', 'intc', 'msft', 'googl',
       'amzn', 'rtx', 'stry', 'etn', 'hubb', 'gev', 'rok')
TARGETS = {'asml': 'ASML', 'lrcx': 'LRCX', 'klac': 'KLAC', 'tokyo_electron': '8035.T', 'hanmi': '042700.KS',
           'nvda': 'NVDA', 'amd': 'AMD', 'avgo': 'AVGO', 'qcom': 'QCOM', 'intc': 'INTC', 'msft': 'MSFT',
           'googl': 'GOOGL', 'amzn': 'AMZN', 'rtx': 'RTX', 'stry': 'SYK', 'etn': 'ETN', 'hubb': 'HUBB', 'gev': 'GEV',
           'rok': 'ROK'}
# Set members other than the 19 TARGET companies: the ETFs on the client history allowlist (GoogleSheetQuotes.HISTORY_SYMBOLS
# minus the FX pairs). Any wider symbol needs a Worker allowlist change first. Priced in USD, no public Q·G.
ETF_MEMBERS = {'spy': 'SPY', 'smh': 'SMH', 'xlk': 'XLK', 'xlv': 'XLV', 'xle': 'XLE', 'xlb': 'XLB', 'xlp': 'XLP', 'xly': 'XLY',
               'xlc': 'XLC', 'xlu': 'XLU', 'xlre': 'XLRE', 'xlf': 'XLF', 'xli': 'XLI', 'vug': 'VUG', 'qual': 'QUAL'}
MEMBERS = {**TARGETS, **ETF_MEMBERS}
USER_SETS = ('SET_B', 'SET_C', 'SET_D')
KINDS = ('SET_A', 'SET_B', 'SET_C', 'SET_D', 'SHADOW')
COMPOSITION = re.compile(r'[a-z][a-z0-9_]{0,63}(?:\+[a-z][a-z0-9_]{0,63}){0,15}')
SP500_SYMBOL = 'SPY'
FX_SYMBOLS = {'USD': 'KRW=X', 'JPY': 'JPYKRW=X'}
# S17 ⑬ relative-index dashboard ETFs (VIRTUAL_TRADING_V1_PROPOSAL table ⑬): always requested, even when no company maps
# to them. Their closes (with SPY and KRW=X) are passed through as `indices` for qgv/report_benchmarks.py.
DASHBOARD_ETFS = ('XLK', 'VUG', 'QUAL', 'XLY', 'XLP')
CURRENCIES = ('USD', 'KRW', 'JPY')
STATUSES = ('COMPLETE', 'IN_PROGRESS', 'UNKNOWN')
FLAG_KINDS = ('HOLD', 'EXCLUDE', 'CONFIRMED_TEMPORARY', 'CONFIRMED_STRUCTURAL', 'CLEAR')
FORWARD_VERSION = 'forward_validation/v1'
FORWARD_V2_VERSION = 'forward_validation/v2'
MAX_BARS = 1500
MAX_TIMESTAMP = 4102444800  # 2100-01-01T00:00:00Z
CODE = re.compile(r'[A-Z][A-Z0-9_]{0,63}')
DAY = re.compile(r'\d{4}-\d{2}-\d{2}')
CLOCK = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})')
ZONE = re.compile(r'[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+){0,2}')


class _Invalid(ValueError):
    pass


def _need(ok):
    if not ok:
        raise _Invalid()


def _num(v):
    return type(v) in (int, float) and math.isfinite(v)


def _day(v):
    if not (isinstance(v, str) and DAY.fullmatch(v)):
        return False
    m, d = int(v[5:7]), int(v[8:])
    return 1 <= m <= 12 and 1 <= d <= 31


def _zone(tz):
    _need(isinstance(tz, str) and ZONE.fullmatch(tz) is not None)
    try:
        return ZoneInfo(tz)
    except Exception:
        raise _Invalid() from None


def _instant(text):
    _need(isinstance(text, str) and CLOCK.fullmatch(text) is not None)
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        raise _Invalid() from None


def local_date(seconds, tz):
    return datetime.fromtimestamp(seconds, ZoneInfo(tz) if isinstance(tz, str) else tz).strftime('%Y-%m-%d')


def catalog_targets(catalog):
    """TARGET v0 rows of the public actual-catalog.json → [{cid, symbol, currency, weight}] (weight in %)."""
    try:
        _need(isinstance(catalog, dict) and catalog.get('total_units') == 10000)
        rows = catalog.get('instruments')
        _need(isinstance(rows, list) and len(rows) == len(IDS))
        out = []
        for i, (cid, row) in enumerate(zip(IDS, rows)):
            _need(isinstance(row, dict) and row.get('row_index') == i)
            _need(row.get('ticker') == TARGETS[cid].split('.')[0] and row.get('currency') in CURRENCIES)
            units = row.get('target_units')
            _need(type(units) is int and 0 <= units <= 10000)
            out.append({'cid': cid, 'symbol': TARGETS[cid], 'currency': row['currency'], 'weight': units / 100})
        _need(sum(r['weight'] for r in out) <= 100 + 1e-9)
        return out
    except _Invalid:
        return None


def _classification_row(classification, cid):
    try:
        return classification['data']['companies'][cid]
    except (TypeError, KeyError):
        return None


def sector_for(classification, cid):
    """D-22 sector benchmark ETF from the public classification (SIC + theme v0 'semiconductors' membership)."""
    row = _classification_row(classification, cid)
    sic = semis = None
    if isinstance(row, dict):
        industry, themes = row.get('industry'), row.get('themes')
        if isinstance(industry, dict) and isinstance(industry.get('sic'), str):
            sic = industry['sic']
        if isinstance(themes, dict) and isinstance(themes.get('memberships'), dict):
            member = themes['memberships'].get('semiconductors')
            if isinstance(member, dict) and member.get('member') in (True, False):
                semis = member['member']
    return sector_benchmark(sic, semis)


def _benchmark_key(etf):
    return 'SP500' if etf == SP500_SYMBOL else etf


def _weights_of(v):
    return v['target_weights'] if isinstance(v, dict) and isinstance(v.get('target_weights'), dict) else {}


def _sets_of(sets, set_b):
    """User set definitions {SET_B, SET_C, SET_D: {target_weights} | None}; legacy callers pass set_b alone."""
    return {k: (sets[k] if isinstance(sets, dict) and k in sets else (set_b if k == 'SET_B' else None)) for k in USER_SETS}


def _universe(targets, holdings, set_b, sets=None, user_target=None):
    cids = [t['cid'] for t in targets]
    every = _sets_of(sets, set_b)
    positions = holdings.get('positions') if isinstance(holdings, dict) else None
    lists = [positions if isinstance(positions, dict) else {}] + [_weights_of(every[k]) for k in USER_SETS] + \
        [_weights_of(sets.get('SET_A') if isinstance(sets, dict) else None), user_target if isinstance(user_target, dict) else {}]
    for extra in lists:
        cids += sorted(c for c in extra if c in MEMBERS and c not in cids)
    return cids


def _listing(targets):
    out = {t['cid']: t['currency'] for t in targets}
    out.update({c: 'USD' for c in ETF_MEMBERS})
    return out


def required_symbols(*, catalog, classification=None, holdings=None, set_b=None, sets=None, user_target=None):
    """Symbols to request, in request order: SPY first (sessions), then FX, members, sector ETFs and the remaining ⑬
    ETFs (each once)."""
    targets = catalog_targets(catalog)
    if targets is None:
        return []
    currency = _listing(targets)
    cids = _universe(targets, holdings, set_b, sets, user_target)
    fx = [FX_SYMBOLS[c] for c in ('USD', 'JPY') if c in {currency[cid] for cid in cids}]
    etfs = sorted({sector_for(classification, cid)['etf'] for cid in cids} - {SP500_SYMBOL})
    out = []
    for symbol in [SP500_SYMBOL] + fx + [MEMBERS[cid] for cid in cids] + etfs + sorted(set(DASHBOARD_ETFS) - set(etfs)):
        if symbol not in out:
            out.append(symbol)
    return out


def series_from_history(entry, symbol, currency):
    """Worker private-history/1 payload (or {'error': code}) → (closes {date: close}, None) or ({}, code)."""
    if entry is None:
        return {}, 'NOT_REQUESTED'
    if isinstance(entry, dict) and set(entry) == {'error'}:
        code = entry['error']
        return {}, code if isinstance(code, str) and CODE.fullmatch(code) else 'HISTORY_UNAVAILABLE'
    try:
        _need(isinstance(entry, dict) and entry.get('schema') == 'private-history/1' and entry.get('symbol') == symbol)
        _need(entry.get('interval') == '1d')
        tz = _zone(entry.get('timezone'))
        read_day = _instant(entry.get('read_at')).astimezone(tz).strftime('%Y-%m-%d')
        bars = entry.get('bars')
        _need(isinstance(bars, list) and len(bars) <= MAX_BARS)
        rows, previous = [], 0
        for bar in bars:
            _need(isinstance(bar, dict))
            ts, status, close = bar.get('timestamp'), bar.get('session_status'), bar.get('close')
            _need(type(ts) is int and previous < ts <= MAX_TIMESTAMP and status in STATUSES)
            _need(close is None or (_num(close) and type(close) is not bool))
            previous = ts
            session_date = bar.get('session_date')
            _need(session_date is None or _day(session_date))
            rows.append((session_date or local_date(ts, tz), status, close))
    except _Invalid:
        return {}, 'HISTORY_FORMAT_INVALID'
    if entry.get('currency') != currency:
        return {}, 'CURRENCY_MISMATCH'
    seen = Counter(d for d, _, _ in rows)
    closes = {}
    for d, status, close in rows:
        if seen[d] != 1 or close is None or not close > 0:
            continue
        if status == 'COMPLETE' or (status == 'UNKNOWN' and d < read_day):
            closes[d] = close
    if not closes:
        return {}, 'HISTORY_UNAVAILABLE'
    return dict(sorted(closes.items())), None


def coverage(row):
    """Forward-ledger company row → engine coverage (READY / PARTIAL / BLOCKED)."""
    if row.get('state') == 'NOT_AVAILABLE':
        return 'BLOCKED'
    axes = (row['Q']['coverage'], row['G']['coverage'])
    if 'BLOCKED' in axes:
        return 'BLOCKED'
    if row.get('state') == 'STALE' or 'PARTIAL' in axes:
        return 'PARTIAL'
    return 'READY'


def snapshots_from_ledger(forward):
    """Q·G per NYSE session date from RECORDED records of the public forward ledger (no V, no prices)."""
    out = {}
    try:
        records = forward['versions'][FORWARD_V2_VERSION if forward.get('schema_version') == 2 else FORWARD_VERSION]
    except (TypeError, KeyError):
        return out
    for r in records if isinstance(records, list) else []:
        if not (isinstance(r, dict) and r.get('state') == 'RECORDED' and _day(r.get('date')) and isinstance(r.get('companies'), dict)):
            continue
        out[r['date']] = {cid: {'q': row['Q']['score'], 'g': row['G']['score'], 'coverage': coverage(row)}
                          for cid, row in sorted(r['companies'].items())}
    return out


def v_composition_from_store(store):
    """V factor composition per date and company (V history /2): the V slope compares only equal compositions."""
    out = {}
    if not isinstance(store, dict):
        return out
    for d, row in sorted(store.items()):
        if not (_day(d) and isinstance(row, dict)):
            continue
        kept = {cid: v for cid, v in sorted(row.items()) if isinstance(v, str) and COMPOSITION.fullmatch(v)}
        if kept:
            out[d] = kept
    return out


def v_scores_from_store(store):
    """Device V scores stored per date: only finite values within 0..100 are kept; nothing is filled."""
    out = {}
    if not isinstance(store, dict):
        return out
    for d, row in sorted(store.items()):
        if not (_day(d) and isinstance(row, dict)):
            continue
        kept = {cid: v for cid, v in sorted(row.items()) if isinstance(cid, str) and _num(v) and type(v) is not bool and 0 <= v <= 100}
        if kept:
            out[d] = kept
    return out


def flags_from_store(flags):
    if not isinstance(flags, list):
        return []
    return [{'date': f['date'], 'kind': f['kind'], 'company': f['company']} for f in flags
            if isinstance(f, dict) and _day(f.get('date')) and f.get('kind') in FLAG_KINDS and isinstance(f.get('company'), str)]


def eastern_date(text):
    return _instant(text).astimezone(ZoneInfo('America/New_York')).strftime('%Y-%m-%d')


def _rate_on_or_before(series, d):
    best = None
    for k in series:
        if k <= d and (best is None or k > best):
            best = k
    return None if best is None else series[best]


def _unavailable(codes):
    return {'state': 'NOT_AVAILABLE', 'reason_codes': list(codes), 'input': None}


def assemble(*, config, catalog, forward_ledger=None, classification=None, histories=None, holdings=None,
             set_b=None, sets=None, user_target=None, v_store=None, v_composition=None, flags=None):
    """Same inputs → same ledger inputs for SET_A, SET_B, SET_C, SET_D and SHADOW (see module docstring). The shadow
    ledger's target is the user's own target only (decision 2026-10-11): without it the shadow ledger is
    TARGET_NOT_AVAILABLE; TARGET v0 is never substituted."""
    histories = histories or {}
    start = config.get('start_date')
    out = {'schema': SCHEMA, 'state': 'READY', 'reason_codes': [], 'sources': {}, 'sector': {}, 'ledgers': {}, 'indices': {},
           'snapshot_basis': 'v2' if isinstance(forward_ledger, dict) and forward_ledger.get('schema_version') == 2 else 'v1'}
    targets = catalog_targets(catalog)
    if targets is None:
        out.update(state='NOT_AVAILABLE', reason_codes=['TARGET_CATALOG_INVALID'])
        out['ledgers'] = {k: _unavailable(['TARGET_CATALOG_INVALID']) for k in KINDS}
        return out
    listing = _listing(targets)
    cids = _universe(targets, holdings, set_b, sets, user_target)
    series, sector = {}, {}

    def source(symbol, currency):
        closes, code = series_from_history(histories.get(symbol), symbol, currency)
        out['sources'][symbol] = {'state': 'OK' if code is None else 'NOT_REQUESTED' if code == 'NOT_REQUESTED' else 'NOT_AVAILABLE',
                                  'code': code, 'sessions': len(closes)}
        if code is None:
            series[symbol] = closes
        return closes if code is None else None

    spy = source(SP500_SYMBOL, 'USD')
    fx = {}
    for ccy in ('USD', 'JPY'):
        if ccy in {listing[c] for c in cids}:
            rates = source(FX_SYMBOLS[ccy], 'KRW')
            if rates is not None:
                fx[ccy] = rates
    for cid in cids:
        if MEMBERS[cid] not in out['sources']:
            source(MEMBERS[cid], listing[cid])
        sector[cid] = sector_for(classification, cid)
    etfs = sorted({s['etf'] for s in sector.values()} - {SP500_SYMBOL})
    for etf in etfs + sorted(set(DASHBOARD_ETFS) - set(etfs)):
        if etf not in out['sources']:
            source(etf, 'USD')
    out['sector'] = sector
    out['indices'] = {sym: series[sym] for sym in (SP500_SYMBOL, *DASHBOARD_ETFS, FX_SYMBOLS['USD']) if sym in series}
    if spy is None:
        out.update(state='NOT_AVAILABLE', reason_codes=['SESSIONS_NOT_AVAILABLE'])
        out['ledgers'] = {k: _unavailable(['SESSIONS_NOT_AVAILABLE']) for k in KINDS}
        return out
    v2_rows = forward_ledger['versions'].get(FORWARD_V2_VERSION, []) if isinstance(forward_ledger, dict) and forward_ledger.get('schema_version') == 2 else None
    ready_date = next((r['date'] for r in v2_rows if r.get('state') == 'RECORDED' and any(_finite(c['Q']['score']) and _finite(c['G']['score']) for c in (r.get('companies') or {}).values())), None) if v2_rows is not None else None
    sessions = [d for d in spy if start is not None and d >= start and (v2_rows is None or ready_date is not None and d >= ready_date)]
    snapshots = snapshots_from_ledger(forward_ledger)
    v2_basis = isinstance(forward_ledger, dict) and forward_ledger.get('schema_version') == 2
    v_scores = {} if v2_basis else v_scores_from_store(v_store)
    v_comp = {} if v2_basis else v_composition_from_store(v_composition)
    flag_rows = flags_from_store(flags)

    # Every ledger carries every priced member (a stored set definition is then derived from any ledger input); the
    # engine judges only its own target weights and positions.
    def ledger(ledger_id, kind, weights, ledger_sessions, initial):
        companies, bench = {}, {'SP500': spy}
        for cid in sorted(cids):
            key = _benchmark_key(sector[cid]['etf'])
            companies[cid] = {'currency': listing[cid], 'closes': series.get(MEMBERS[cid], {}), 'sector_benchmark': key}
            if key != 'SP500' and sector[cid]['etf'] in series:
                bench[key] = series[sector[cid]['etf']]
        return {'state': 'READY', 'reason_codes': [], 'input': {
            'id': ledger_id, 'kind': kind, 'sessions': ledger_sessions, 'target_weights': weights,
            'companies': companies, 'benchmarks': bench, 'fx': dict(fx), 'initial': initial,
            'snapshots': snapshots, 'v_scores': v_scores, 'v_composition': v_comp, 'flags': flag_rows, 'events': {}}}

    target_weights = {t['cid']: t['weight'] for t in targets}
    out['ledgers']['SET_A'] = ledger('set_a', 'SET_A', target_weights, sessions, {'cash': 0, 'positions': {}})
    every = _sets_of(sets, set_b)
    for kind in USER_SETS:
        w = every[kind].get('target_weights') if isinstance(every[kind], dict) else None
        legacy = kind == 'SET_B'
        if w is None:
            out['ledgers'][kind] = _unavailable(['SET_B_NOT_DEFINED' if legacy else 'SET_NOT_DEFINED'])
        elif not _weights_valid(w, listing):
            out['ledgers'][kind] = _unavailable(['SET_B_INVALID' if legacy else 'SET_INVALID'])
        else:
            out['ledgers'][kind] = ledger(kind.lower(), kind, dict(w), sessions, {'cash': 0, 'positions': {}})
    if user_target is None:
        out['ledgers']['SHADOW'] = _unavailable(['TARGET_NOT_AVAILABLE'])
    elif not _weights_valid(user_target, listing):
        out['ledgers']['SHADOW'] = _unavailable(['WEIGHT_INVALID'])
    else:
        out['ledgers']['SHADOW'] = _shadow(holdings, dict(user_target), sessions, fx, ledger, listing)
    return out


def _weights_valid(w, listing):
    if not (isinstance(w, dict) and w and all(c in MEMBERS and c in listing and _num(v) and type(v) is not bool and 0 <= v <= 100 for c, v in w.items())):
        return False
    total = 0
    for k in sorted(w):
        total += w[k]
    return total <= 100 + 1e-9


def _shadow(holdings, target_weights, sessions, fx, ledger, listing):
    positions = holdings.get('positions') if isinstance(holdings, dict) else None
    positions = positions if isinstance(positions, dict) else {}
    held = {cid: p for cid, p in sorted(positions.items())
            if cid in TARGETS and cid in listing and isinstance(p, dict) and _num(p.get('quantity')) and p['quantity'] > 0}
    if not held:
        return _unavailable(['NO_ACTUAL'])
    if any(not (_num(p.get('average_cost')) and p['average_cost'] >= 0 and p.get('currency') in CURRENCIES) for p in held.values()):
        return _unavailable(['ACTUAL_INVALID'])
    try:
        begin = eastern_date(holdings.get('effective_at'))
    except _Invalid:
        return _unavailable(['ACTUAL_INVALID'])
    own = [d for d in sessions if d >= begin]
    initial = {'cash': 0, 'positions': {}}
    if own:
        for cid, p in held.items():
            rate = 1 if p['currency'] == 'KRW' else _rate_on_or_before(fx.get(p['currency'], {}), own[0])
            if rate is None:
                return _unavailable(['INITIAL_COST_FX_MISSING'])
            initial['positions'][cid] = {'quantity': p['quantity'], 'cost': p['quantity'] * p['average_cost'] * rate}
    return ledger('shadow-' + begin, 'SHADOW', target_weights, own, initial)
