"""Python twin of the published `sec-qgv2.json` -> QGV v2 engine-input conversion. Price-free, RAM only.

The device builds the engine input in three JS steps; this module mirrors each one exactly (same rules, same order):

1. `to_inputs`      == web_assets/sec-qgv2.js `SecQgv2.toInputs` (strict reader: `require_qgv2`, then device-time
                       freshness `restate` from each row's own acquired_at);
2. `from_inputs`    == web_assets/qgv2-inputs.js `Qgv2Inputs.fromInputs` / `normalize` (one cross-section point per CIK,
                       TARGET rows scored against it, calc_version mismatch, identity withdrawal, v_inputs FY/TTM flows);
   `light`          == `Qgv2Inputs.light` (the check used when the strict reader is absent);
3. `engine_companies` == web_assets/qgv-scores.js `universeScores` company records, with
   `cyclical_basis` == the `PlaybookEngine.classifyTypesV0` loop of `QgvScores.compute` (Python `playbook.classify_types_v0`
                       / `playbook.sector_for`) and `row_memberships` == `rowMemberships` (`qgv_v2.pricefree_memberships`,
                       TYPE_SCOPE); `blocked_codes` / `priced_quotes` == the PRICE_IDENTITY_CONFLICT quote removal of compute.

The result feeds `qgv_v2.score_universe` unchanged. Nothing here computes a score, changes a formula, a reason code, PIT
or provenance, or reads, stores or logs a price. Values the publisher already withheld (V-STALE-BS debt/cash, V-STALE-SHARES
and V-SHARES-SCALE diluted shares / per-share histories: null or [] in the file) stay missing here, never filled.
Parity with the JS (node) path: tests/test_qgv2_inputs.py and tools/qgv2_inputs_node_test.js.
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone, timedelta

FILE = 'sec-qgv2.json'
KIND = 'SEC_QGV2'
FACTORS = ('q_profitability', 'q_moat_proxy', 'q_earnings_quality', 'q_financial_safety', 'q_capital_allocation',
           'g_revenue_growth', 'g_per_share_growth', 'g_growth_efficiency', 'g_consistency', 'g_recent_acceleration')
WITHDRAWN_REASON = 'IDENTITY_CONFLICT_WITHDRAWN'

# JS regular expressions (no flags: \d is ASCII-only, `$` is the end of the string -> re.ASCII + fullmatch).
_A = re.ASCII
_CODE = re.compile(r'[A-Z]{2,8}:[A-Z0-9][A-Z0-9.\-]{0,15}', _A)
_ID = re.compile(r'[a-z][a-z0-9_]{0,63}', _A)
_DAY = re.compile(r'\d{4}-\d{2}-\d{2}', _A)
_GROUP = _ID
_CURRENCY = re.compile(r'[A-Z]{3}', _A)
_REASON = re.compile(r'[A-Z][A-Z0-9_]{0,63}', _A)
_METRIC_KEY = re.compile(r'[a-z][a-z0-9_]{0,63}', _A)
_SIC = re.compile(r'\d{4}', _A)
_FACTORS_AVAILABLE = re.compile(r'\d/\d', _A)
_PEER_BASIS = re.compile(r'[A-Z][A-Z_]{0,31}', _A)
_CLOCK = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', _A)
_PRICE_LIKE = re.compile(r'"(price|prices|market_?cap|marketcap|ev|enterprise_value|v_score|rank)"\s*:', re.I)
_JS_SAFE = 2 ** 53


# ---- JS value semantics -------------------------------------------------------------------------------------------
def _object(v):
    return isinstance(v, dict)


def _js_number(v):
    """A JSON number as the browser holds it (an IEEE double); None when it is no finite number there."""
    if type(v) is int:
        if abs(v) <= _JS_SAFE:
            return v
        try:
            v = float(v)
        except OverflowError:
            return None
    if type(v) is float and math.isfinite(v):
        return v
    return None


def _finite(v):
    return _js_number(v) is not None


def _is_integer(v):
    n = _js_number(v)
    return n is not None and float(n).is_integer()


def _string(v):
    return type(v) is str


def _match(rx, v):
    return _string(v) and rx.fullmatch(v) is not None


def _truthy(v):
    """JS truthiness of a JSON value (arrays and objects are truthy, unlike Python)."""
    if v is None or v is False:
        return False
    if type(v) in (int, float):
        return v != 0 and not (type(v) is float and math.isnan(v))
    if _string(v):
        return v != ''
    return True


def _set_key(v):
    """Set membership as JS Set (SameValueZero): primitives by value, objects by identity."""
    if v is None or type(v) in (str, bool, int, float):
        return (type(v) is bool, v)
    return ('object', id(v))


def _copy(v):
    return json.loads(json.dumps(v))


def _score(v):
    n = _js_number(v)
    return n if n is not None and 0 <= n <= 100 else None


def _value(x):
    return _js_number(x['value']) if _object(x) and _finite(x.get('value')) else None


# ---- Qgv2Inputs.normalize ----------------------------------------------------------------------------------------
def _flow(x):
    if not _object(x):
        return None, None
    if _finite(x.get('ttm_value')):
        return _js_number(x['ttm_value']), ('TTM ' + x['ttm_end'] if _string(x.get('ttm_end')) else 'TTM')
    if _finite(x.get('fy_value')):
        return _js_number(x['fy_value']), ('FY ' + x['fy_end'] if _string(x.get('fy_end')) else 'FY')
    return None, None


def _history(items):
    out = []
    for h in items if isinstance(items, list) else []:
        pe = h.get('fiscal_year_end') if _object(h) else None
        if _match(_DAY, pe) and _finite(h.get('value')):
            out.append({'period_end': pe, 'value': _js_number(h['value'])})
    return sorted(out, key=lambda h: h['period_end'])   # stable, as Array.prototype.sort


def _v_inputs(v):
    if not _object(v) or not _match(_CURRENCY, v.get('currency')):
        return None, {}
    (ebit, ebit_p), (fcf, fcf_p), (revenue, revenue_p) = _flow(v.get('ebit')), _flow(v.get('fcf')), _flow(v.get('revenue'))
    periods = {}
    if ebit_p:
        periods['ebit'] = ebit_p
    if fcf_p:
        periods['fcf'] = fcf_p
    if revenue_p:
        periods['revenue'] = revenue_p
    for k in ('total_debt', 'cash_and_equivalents', 'diluted_shares'):
        if _object(v.get(k)) and _string(v[k].get('period_end')):
            periods[k] = v[k]['period_end']
    return {'currency': v['currency'], 'ebit': ebit, 'fcf': fcf, 'revenue': revenue,
            'operating_margin_history': _history(v.get('operating_margin_history')),
            'total_debt': _value(v.get('total_debt')), 'cash': _value(v.get('cash_and_equivalents')),
            'diluted_shares': _value(v.get('diluted_shares')),
            'ebit_per_share_history': _history(v.get('ebit_per_share_history')),
            'revenue_cagr_3y': _js_number(v['revenue_cagr_3y']) if _finite(v.get('revenue_cagr_3y')) else None}, periods


def _has_data(r):
    return _object(r) and r.get('state') != 'NOT_AVAILABLE' and r.get('fiscal_year_end') is not None


def version_mismatch(r, file_version):
    """calc_version (QGV_V2_QG_METHOD.md 5): a data row of another rule version than the versioned file's."""
    return _string(file_version) and _has_data(r) and r.get('calc_version') != file_version


def _axis_meta(a):
    if not _object(a):
        return {'score': None}
    out = {'score': _score(a.get('score'))}
    if _match(_FACTORS_AVAILABLE, a.get('factors_available')):
        out['factors_available'] = a['factors_available']
    w = _js_number(a.get('available_weight'))
    if w is not None and 0 <= w <= 100:
        out['available_weight'] = w
    if _match(_PEER_BASIS, a.get('peer_basis')):
        out['peer_basis'] = a['peer_basis']
    for k in ('peer_count', 'submetric_fallbacks'):
        if _is_integer(a.get(k)) and a[k] >= 0:
            out[k] = _js_number(a[k])
    if isinstance(a.get('reason_codes'), list):
        out['reason_codes'] = [x for x in a['reason_codes'] if _match(_REASON, x)]
    return out


def _fiscal_years(r):
    ys = r['metrics'].get('ebit_estimated_fiscal_years') if _object(r) and _object(r.get('metrics')) else None
    if isinstance(ys, list) and all(_is_integer(y) and 1900 <= y <= 2100 for y in ys):
        return {'ebit_estimated_fiscal_years': [_js_number(y) for y in ys]}
    return {}


def normalize(r, pooled):
    """Qgv2Inputs.normalize: one published row -> one device record."""
    obj = _object(r)
    f = r['factors'] if obj and _object(r.get('factors')) else {}
    factors = {k: _score(f.get(k)) for k in FACTORS}
    has = _has_data(r)
    v, periods = _v_inputs(r.get('v_inputs_v2')) if has else (None, {})
    ax = r['axes'] if obj and _object(r.get('axes')) else {}
    na = [x for x in r['reason_codes'] if _match(_REASON, x)] if obj and not has and isinstance(r.get('reason_codes'), list) else []
    metrics = {}
    if obj and _object(r.get('metrics')):
        metrics = {k: _js_number(x) for k, x in r['metrics'].items() if _match(_METRIC_KEY, k) and _finite(x)}
        metrics.update(_fiscal_years(r))
    return {
        'na_reasons': na, 'metrics': metrics,
        'sic': r['sic'] if obj and _match(_SIC, r.get('sic')) else None,
        'cik': r['cik'] if obj and _string(r.get('cik')) else None,
        'industry_group': r['industry_group'] if obj and _match(_GROUP, r.get('industry_group')) else None,
        'profile': 'FINANCIAL' if obj and r.get('profile') == 'FINANCIAL' else 'GENERAL',
        'factors': factors, 'qg_axes': {'Q': _axis_meta(ax.get('Q')), 'G': _axis_meta(ax.get('G'))},
        'v_inputs': v, 'periods': periods,
        'state': r['state'] if obj and r.get('state') in ('LIVE', 'STALE') else 'NOT_AVAILABLE',
        'in_cross_section': pooled,
        'acquired_at': r['acquired_at'] if has and _match(_CLOCK, r.get('acquired_at')) else None,
        'fiscal_year_end': r['fiscal_year_end'] if has and _match(_DAY, r.get('fiscal_year_end')) else None,
        'published_profile': r['profile'] if has and r.get('profile') in ('GENERAL', 'FINANCIAL') else None,
    }


def _withdrawn(r):
    return _object(r) and ('detected_at' in r or isinstance(r.get('reason_codes'), list) and WITHDRAWN_REASON in r['reason_codes'])


def _empty_scores():
    return {'factors': {k: None for k in FACTORS}, 'qg_axes': {'Q': {'score': None}, 'G': {'score': None}}}


def _stopped(rec):
    return dict(rec, state='WITHDRAWN', na_reasons=[WITHDRAWN_REASON], metrics={}, sic=None, industry_group=None,
                acquired_at=None, fiscal_year_end=None, published_profile=None, v_inputs=None, periods={},
                in_cross_section=False, identity_withdrawn=True, **_empty_scores())


def from_inputs(inputs):
    """Qgv2Inputs.fromInputs: a `to_inputs` result (or a `light` payload) -> {as_of, calc_version, target, records, count}.

    Universe codes in sorted order; the first LIVE/STALE same-version code of a CIK is its one cross-section point. A
    withdrawn TARGET issuer stops its TARGET record and every Universe code of its CIK (identity_withdrawn). A data row of
    another calc_version leaves every population (calc_version_mismatch). TARGET rows are never in the cross-section."""
    if not _object(inputs) or not _object(inputs.get('records')):
        raise ValueError('SEC_QGV2_INVALID')
    version = inputs['calc_version'] if _string(inputs.get('calc_version')) else None
    records, seen = {}, set()

    def mark(rec, r):
        if not version_mismatch(r, version):
            return rec
        return dict(rec, v_inputs=None, in_cross_section=False, calc_version_mismatch=True, **_empty_scores())

    targets = inputs['target'] if _object(inputs.get('target')) else {}
    withdrawn_ciks = {r['cik'] for r in targets.values() if _withdrawn(r) and _string(r.get('cik'))}
    for code in sorted(inputs['records']):
        if not _match(_CODE, code):
            raise ValueError('SEC_QGV2_INVALID')
        r = inputs['records'][code]
        cik = r.get('cik') if _object(r) else None
        stop = _withdrawn(r) or (_string(cik) and cik in withdrawn_ciks)
        live = not stop and _object(r) and r.get('state') in ('LIVE', 'STALE')
        mismatch = version_mismatch(r, version)
        pooled = live and not mismatch and not (_truthy(cik) and _set_key(cik) in seen)
        if live and not mismatch and _truthy(cik):
            seen.add(_set_key(cik))
        records[code] = dict(_stopped(normalize(r, False)), universe_withdrawal=_withdrawn(r)) if stop else mark(normalize(r, pooled), r)
    for cid, r in targets.items():
        if not _match(_ID, cid):
            raise ValueError('SEC_QGV2_INVALID')
        records['TARGET:' + cid] = _stopped(normalize(r, False)) if _withdrawn(r) else mark(normalize(r, False), r)
    return {'as_of': inputs['as_of'] if _string(inputs.get('as_of')) else None, 'calc_version': version,
            'target': _copy(targets), 'records': records, 'count': len(records)}


def light(payload):
    """Qgv2Inputs.light: the structural check used only without the strict reader; price-like keys fail closed."""
    text = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    if not _object(payload) or payload.get('kind') != KIND or not _object(payload.get('records')) or _PRICE_LIKE.search(text):
        raise ValueError('SEC_QGV2_INVALID')
    return payload


# ---- SecQgv2.toInputs ---------------------------------------------------------------------------------------------
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _ms(clock):
    """Date.parse of an ISO clock: whole milliseconds since the epoch (sub-millisecond digits dropped); None = NaN."""
    try:
        parsed = clock if isinstance(clock, datetime) else datetime.fromisoformat(clock.replace('Z', '+00:00'))
        if parsed.utcoffset() is None:
            return None
        return (parsed - _EPOCH) // timedelta(milliseconds=1)
    except (TypeError, ValueError, AttributeError, OverflowError):
        return None


def _restate(r, now_ms, ttl):
    """SecQgv2.restate: freshness from the row's own acquired_at; a row without a fiscal year is unchanged."""
    out = _copy(r)
    if out.get('fiscal_year_end') is None and 'fiscal_year_end' in out:
        return out
    acquired = _ms(out.get('acquired_at'))
    fresh = now_ms is not None and acquired is not None and now_ms - acquired <= ttl * 1000
    return dict(out, state='LIVE' if fresh else 'STALE', reason_codes=[] if fresh else ['STALE_INPUT'])


def to_inputs(payload, now):
    """SecQgv2.toInputs: strict validation (universe.sec_qgv2.require_qgv2, the JS reader's twin), then restate every
    row at `now` (ISO clock or aware datetime). Raises ValueError('SEC_QGV2_INVALID') on any rejected file."""
    from ..universe import sec_qgv2
    sec_qgv2.require_qgv2(payload)
    now_ms, ttl = _ms(now), payload['stale_after_seconds']
    records = {code: _restate(r, now_ms, ttl) for code, r in payload['records'].items()}
    target = {cid: _restate(r, now_ms, ttl) for cid, r in payload['target'].items()}
    rows = list(records.values()) + list(target.values())
    state = 'LIVE' if any(r['state'] == 'LIVE' for r in rows) else 'STALE' if any(r['state'] == 'STALE' for r in rows) else 'NOT_AVAILABLE'
    return {'records': records, 'target': target, 'as_of': payload['as_of'], 'standard': payload['standard'],
            'standard_status': payload['standard_status'], 'decision_ref': payload['decision_ref'],
            'calc_version': payload['calc_version'] if _string(payload.get('calc_version')) else None,
            'method': _copy(payload['method']), 'cross_section_size': payload['cross_section_size'],
            'cross_section_by_profile': dict(payload['cross_section_by_profile']), 'state': state}


def from_published(payload, now):
    """The device's load path with the strict reader present: from_inputs(to_inputs(payload, now))."""
    return from_inputs(to_inputs(payload, now))


# ---- QgvScores: identities, price-identity conflicts, cyclical basis, engine companies ------------------------------
def _key(t):
    return str(t if _truthy(t) else '').replace('.', '-').upper()


def symbol_of(code):
    code = str(code)
    return _key(code[code.find(':') + 1:])


def code_index(inputs):
    """QgvScores codeIndex: identity {company_id, ticker} -> its v2 record key (the TARGET row when it has data, else the
    first Universe code of that ticker), or None."""
    codes = {}
    for code in inputs['records'] if inputs else ():
        if not code.startswith('TARGET:') and symbol_of(code) not in codes:
            codes[symbol_of(code)] = code

    def code_for(c):
        t = 'TARGET:' + str(c.get('company_id'))
        r = inputs['records'].get(t) if inputs else None
        if r is not None and r.get('state') != 'NOT_AVAILABLE':
            return t
        return codes.get(_key(c.get('ticker')))
    return code_for


def blocked_codes(inputs, identities):
    """UNI-TARGET (QgvScores conflictedSymbols / priceConflict): TARGET codes whose price symbol is the symbol of a
    withdrawn Universe code. compute() removes their quotes (PRICE_IDENTITY_CONFLICT)."""
    if not inputs or not _object(inputs.get('records')):
        return set()
    symbols = {symbol_of(code) for code, r in inputs['records'].items()
               if not code.startswith('TARGET:') and r and r.get('universe_withdrawal') is True}
    code_for, out = code_index(inputs), set()
    for c in identities:
        code = code_for(c)
        if code and code.startswith('TARGET:') and _key(c.get('ticker')) in symbols and inputs['records'][code].get('identity_withdrawn') is not True:
            out.add(code)
    return out


def priced_quotes(quotes, blocked):
    """compute(): the quotes the engine receives (blocked codes removed). RAM only; never stored or logged."""
    priced = dict(quotes) if _object(quotes) else {}
    for code in blocked:
        priced.pop(code, None)
    return priced


def cyclical_basis(inputs, playbook_cfg, identities=()):
    """QgvScores.compute cyclical basis: {code: bool} from playbook.classify_types_v0 on the record's SIC, its sector
    subgroup (playbook.sector_for on the identity's ticker, else the code's symbol) and its published revenue volatility
    rank (0..1). As in JS, an error stops the loop and keeps the codes classified so far."""
    from . import playbook
    out = {}
    if playbook_cfg is None or not inputs or not _object(inputs.get('records')):
        return out
    try:
        code_for, symbols = code_index(inputs), {}
        for c in identities:
            code = code_for(c)
            if code:
                symbols[code] = c.get('ticker')
        for code, r in inputs['records'].items():
            symbol = symbols.get(code) if _truthy(symbols.get(code)) else symbol_of(code)
            group = playbook.sector_for(playbook_cfg, symbol, None, r.get('sic'))
            rank = (r.get('metrics') or {}).get('revenue_volatility_5y_rank_pct')
            info = {'sic': r.get('sic'), 'sector_subgroup': (group or {}).get('sector'),
                    'revenue_volatility_5y_rank_pct': rank / 100 if _finite(rank) else None}
            out[code] = (playbook.classify_types_v0(playbook_cfg, info).get('cyclical') or {}).get('member') is True
    except Exception:  # noqa: BLE001 - mirrors the JS try/catch around the whole loop
        pass
    return out


def row_memberships(r, type_config):
    """QgvScores rowMemberships (TYPE-SCOPE): pricefree_memberships of the row's own published metrics; None for a row of
    another calc_version."""
    from . import qgv_v2
    return qgv_v2.pricefree_memberships(r.get('metrics'), type_config) if r and r.get('calc_version_mismatch') is not True else None


def engine_companies(inputs, basis, type_config):
    """QgvScores universeScores: {code: engine company} for qgv_v2.score_universe (calc_version mismatch rows left out)."""
    out = {}
    for code, r in inputs['records'].items():
        if r.get('calc_version_mismatch') is True:
            continue
        out[code] = {'cyclical_basis': basis.get(code) is True, 'cik': r.get('cik'), 'industry_group': r.get('industry_group'),
                     'profile': r.get('profile'), 'factors': r.get('factors'), 'v_inputs': r.get('v_inputs'),
                     'qg_axes': r.get('qg_axes'), 'in_cross_section': r.get('in_cross_section') is not False,
                     'memberships': row_memberships(r, type_config)}
    return out


def page_identities(inputs, identities=()):
    """QgvScores.pageResult identities: the given ones, then every Universe code as {company_id: code, ticker: symbol}."""
    ids = [{'company_id': c['company_id'], 'ticker': c['ticker']} for c in identities
           if _object(c) and _string(c.get('company_id')) and _string(c.get('ticker'))]
    seen = {c['company_id'] for c in ids}
    for code in inputs['records']:
        if not code.startswith('TARGET:') and code not in seen:
            ids.append({'company_id': code, 'ticker': symbol_of(code)})
    return ids


def engine_inputs(inputs, quotes=None, *, identities=(), playbook_cfg=None, type_config=None):
    """(companies, priced quotes) exactly as QgvScores.compute hands them to scoreUniverse for these identities."""
    from . import playbook
    from .type_config import load_official_type_config
    playbook_cfg = playbook.load_config() if playbook_cfg is None else playbook_cfg
    type_config = load_official_type_config().to_dict() if type_config is None else type_config
    ids = list(identities)
    basis = cyclical_basis(inputs, playbook_cfg, ids)
    return engine_companies(inputs, basis, type_config), priced_quotes(quotes, blocked_codes(inputs, ids))
