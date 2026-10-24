"""Official central QGV publication `qgv-official.json` (qgv-official/1) and its status file (GSQ-024, design
docs/qgv_scoring_standard/CENTRAL_V_PUBLICATION_DESIGN_20261018.md §4-§7). PROVISIONAL engine, unchanged.

One publication = the WHOLE Universe (+ TARGET rows) of one `sec-qgv2.json` scored by `qgv_v2.score_universe` (official
default: balanced preset, value-trap gate on, type weights on) with ONE IEX day of last regular-session trades (RAM only) and the
private IEX month-end store for V4. Public fields: scores, ranks, reasons, coverage counts and basis times only. Never published:
prices, month-end prices, EV, market caps, yields, implied growth, expectation gaps, realized-growth detail, DCF reference ranges,
per-code price hashes. Owner decisions applied:
- calc_version: the ONE `sec-qgv2.json` calc_version (no separate v_calc_version);
- D-CV2: price-dependent reasons EV_NON_POSITIVE / ROOT_NOT_BRACKETED / ROOT_NOT_CONVERGED / NUMERIC_OVERFLOW are published
  as PRICE_DEPENDENT_NOT_COMPUTABLE (scores and rules unchanged; the engine codes stay in RAM);
- D-CV5: a new publication needs >= 95% of the price-independent V-eligible Universe rows supplied on the same IEX day;
- D-CV8/D-CV9: one official rank per CIK (the TARGET row of a Universe issuer stands for it, else its cross-section code);
  D11: only rows with a total AND a V score are ranked; a Q·G-only total gets `qg_reference_order` instead;
- V4 month-end prices: raw / share_basis_factor (F_k from the raw sec-qgv2 history item; missing -> month left out, public
  reason = its fixed share_basis_factor_reason or SHARE_BASIS_FACTOR_NOT_AVAILABLE); NASDAQ:PSKY pre-merger months left out
  (MERGER_PRE_BASIS_UNCONFIRMED);
- owner decisions 2026-10-24 (CENTRAL_V_DC02_PLAN_20261024.md section 4): D3 the IEX day is the latest TOPS day <= the run's New
  York day (usually the previous trading day; requested_basis_date and basis_date both published); D4 SUPPLY_MIN 95%; D6 (a) the
  current-price split check reads the F_k evidence of calc_version 2026-10-23.1 (`split_after_share_count`); D7 a foreign private
  issuer (20-F / 40-F filer) is ADR_RATIO_UNCONFIRMED whatever its taxonomy (`adr_unconfirmed`); the publication needs a
  sec-qgv2.json of calc_version 2026-10-23.1 or later (the one bump that covers these rules, D-CV7 (b)).
Verify without prices: `require_qgv_official` (exact key sets, forbidden keys anywhere, V axis = weighted factors, total = axes and
weights, ranks = total order, coverage = row counts, size <= 2 MiB).
"""
from __future__ import annotations

import copy
import datetime as _dt
import hashlib
import hmac
import json
import math
import re
from pathlib import Path

from . import qgv2_inputs as qi
from . import qgv_v2
from . import v2_factors as vf
from ..providers import iex_hist, iex_monthend

SCHEMA = 'qgv-official/1'
KIND = 'QGV_OFFICIAL'
FILENAME = 'qgv-official.json'
STATUS_FILENAME = 'qgv-official-status.json'
STATUS_SCHEMA = 'qgv-official-status/1'
STATUS_KIND = 'QGV_OFFICIAL_STATUS'
MAX_BYTES = 2 * 1024 * 1024
PRESET = qgv_v2.DEFAULT_PRESET
GATE = True
SUPPLY_MIN = 0.95                  # D-CV5; owner decision D4 2026-10-24
PRICE_DEPENDENT = frozenset({'EV_NON_POSITIVE', 'ROOT_NOT_BRACKETED', 'ROOT_NOT_CONVERGED', 'NUMERIC_OVERFLOW'})
PRICE_DEPENDENT_PUBLIC = 'PRICE_DEPENDENT_NOT_COMPUTABLE'
V4 = 'v_vs_own_history'
V4_HISTORY_REASONS = ('HISTORY_TOO_SHORT', 'PRICE_HISTORY_NOT_AVAILABLE')
TARGET_PREFIX = 'TARGET:'
ATTEMPT_STATES = ('OK', 'SUPPLY_FAILED', 'VERIFY_FAILED', 'NOT_RUN', 'NO_OFFICIAL_YET')
# D7 (owner decision 2026-10-24; D-CV10 conservative): a foreign private issuer's row gets no price (ADR_RATIO_UNCONFIRMED, V NA)
# whether it reports ifrs-full or us-gaap, until its listed security / ADS ratio is confirmed. sec-qgv2.json carries no form type
# (only v_inputs_v2.taxonomy), so next to the ifrs-full rule the known 20-F / 40-F filers of the fixed Universe504 are listed by
# CIK from existing public data only (never inferred). Source: docs/qgv_scoring_standard/DCV_OPEN_ITEMS_20261019.md D-CV10
# (SEC submissions, latest annual form of the 498 Universe CIKs: 10-K 482, 10-K/A 14, 10-KT 1, 20-F 1 = ASML, 40-F 0) and its
# section 5-8 (20-F FY2025, accession 0001628280-26-011378). A new 20-F / 40-F filer in the Universe must be added here.
FOREIGN_ANNUAL_FILERS: dict[str, tuple[str, str, str]] = {
    '0000937966': ('NASDAQ:ASML', '20-F', 'DCV_OPEN_ITEMS_20261019.md D-CV10 + 5-8: 20-F FY2025 accession 0001628280-26-011378'),
}
V_TARGET_SHARE = 0.9
# Device ticker of each TARGET company (web_assets/watchlist.js IDS; US ones = markets.us US_LISTINGS).
TARGET_TICKERS = {'asml': 'ASML', 'lrcx': 'LRCX', 'klac': 'KLAC', 'tokyo_electron': '8035', 'hanmi': '042700', 'nvda': 'NVDA',
                  'amd': 'AMD', 'avgo': 'AVGO', 'qcom': 'QCOM', 'intc': 'INTC', 'msft': 'MSFT', 'googl': 'GOOGL', 'amzn': 'AMZN',
                  'rtx': 'RTX', 'stry': 'SYK', 'etn': 'ETN', 'hubb': 'HUBB', 'gev': 'GEV', 'rok': 'ROK'}
FORBIDDEN_KEYS = frozenset({'price', 'prices', 'close', 'closes', 'month_closes', 'quote', 'quotes', 'price_e4', 'ev',
                            'enterprise_value', 'market_cap', 'marketcap', 'mcap', 'ebit_yield', 'fcf_yield', 'implied_growth',
                            'expectation_gap', 'realized_growth', 'detail', 'reference_range', 'hmac', 'price_hmac', 'yield'})
_HERE = Path(__file__).resolve().parent
ENGINE_PY = _HERE / 'qgv_v2.py'
ENGINE_JS = _HERE.parent / 'product' / 'web_assets' / 'qgv-v2.js'
PUBLISHER_SOURCES = (Path(__file__).resolve(), Path(iex_hist.__file__).resolve(), Path(iex_monthend.__file__).resolve(),
                     Path(qi.__file__).resolve())

TOP_KEYS = ('schema', 'kind', 'publication_id', 'state', 'calc_version', 'engine', 'population', 'weights', 'type_scope',
            'config_versions', 'price_source', 'attribution', 'inputs', 'times', 'coverage', 'rows')
ROW_KEYS = ('cik', 'profile', 'industry_group', 'in_cross_section', 'state', 'source_reason_codes', 'acquired_at',
            'fiscal_year_end', 'factors', 'axes', 'weights', 'type_weights', 'type_reason', 'selected_types',
            'q_industry_percentile', 'value_trap_gate', 'v_excluded', 'flags', 'total', 'total_reason', 'price_status', 'rank',
            'qg_reference_order', 'rank_row')
FACTOR_KEYS = ('score', 'reason', 'basis')
AXIS_KEYS = ('score', 'state', 'weight_available', 'factors_available', 'reason')
STOP_REASONS = ('PRICE_IDENTITY_CONFLICT', 'CALC_VERSION_MISMATCH', 'SOURCE_NOT_AVAILABLE')
_REASON = re.compile(r'[A-Z][A-Z0-9_]{0,63}', re.ASCII)
_CODE = re.compile(r'(?:[A-Z]{2,8}:[A-Z0-9][A-Z0-9.\-]{0,15}|TARGET:[a-z][a-z0-9_]{0,63})', re.ASCII)
_HEX = re.compile(r'[0-9a-f]{64}', re.ASCII)
_DAY = re.compile(r'\d{4}-\d{2}-\d{2}', re.ASCII)
_CLOCK = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', re.ASCII)


class OfficialError(RuntimeError):
    """(attempt_state, fixed reason code): never a value."""

    def __init__(self, state, code):
        super().__init__(f'{state}:{code}')
        self.state, self.code = state, code


def _need(cond, code='OFFICIAL_INVALID'):
    if not cond:
        raise ValueError(code)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


def iso(moment) -> str:
    return moment.astimezone(_dt.timezone.utc).isoformat().replace('+00:00', 'Z')


# ---- inputs -------------------------------------------------------------------------------------------------------------
def target_identities(inputs) -> list[dict]:
    return [{'company_id': k[len(TARGET_PREFIX):], 'ticker': TARGET_TICKERS[k[len(TARGET_PREFIX):]]}
            for k in sorted(inputs['records']) if k.startswith(TARGET_PREFIX) and k[len(TARGET_PREFIX):] in TARGET_TICKERS]


def listing_code(key: str):
    """The Universe-style listing code ('EXCH:TICKER') whose IEX price a row uses; None for a TARGET outside the US track."""
    if not key.startswith(TARGET_PREFIX):
        return key
    from ..markets.us import US_LISTINGS
    listing = US_LISTINGS.get(key[len(TARGET_PREFIX):])
    return f"{listing['exchange']}:{listing['yahoo']}" if listing else None


def raw_row(payload, key):
    return payload['target'].get(key[len(TARGET_PREFIX):]) if key.startswith(TARGET_PREFIX) else payload['records'].get(key)


def _raw_v(payload, key):
    r = raw_row(payload, key)
    return r.get('v_inputs_v2') if isinstance(r, dict) and isinstance(r.get('v_inputs_v2'), dict) else None


def prepare(payload, now):
    """sec-qgv2.json payload (already require_qgv2-valid) -> context: converted inputs, identities, engine companies (no price)."""
    try:
        inputs = qi.from_published(payload, now)
    except ValueError:
        raise OfficialError('VERIFY_FAILED', 'SEC_QGV2_INVALID') from None
    targets = target_identities(inputs)
    identities = qi.page_identities(inputs, targets)
    companies, _ = qi.engine_inputs(inputs, {}, identities=identities)
    blocked = qi.blocked_codes(inputs, identities)
    return {'payload': payload, 'inputs': inputs, 'identities': identities, 'companies': companies, 'blocked': blocked,
            'keys': {k: listing_code(k) for k in sorted(inputs['records'])}}


def adr_unconfirmed(rec, v) -> bool:
    """D7: an ifrs-full row or a known 20-F / 40-F filer (FOREIGN_ANNUAL_FILERS, by CIK; a TARGET row shares its issuer's CIK)."""
    return bool(v and v.get('taxonomy') == 'ifrs-full') or rec.get('cik') in FOREIGN_ANNUAL_FILERS


def split_after_share_count(code, v, basis_day) -> bool:
    """D-CV11 / D6 (a): True when a split may have taken effect after the diluted-share period end, up to the basis day.

    Evidence, no new source: (1) the F_k chain of calc_version 2026-10-23.1 (V-PRICE-BASIS): an ebit_per_share_history item at or
    after the share-count period end (the count is that annual filing's) with share_basis_factor null and reason
    SPLIT_TIMING_UNCONFIRMED = a split-ratio fact or a cover share-count jump dated between that fiscal-year-end month-end and the
    annual filing, i.e. after the count's period end; (2) the verified split windows of iex_hist.SPLITS (empty: no verified source
    is connected, see its comment). The window after the count's own filing up to the basis day has no SEC evidence in
    sec-qgv2.json (iex_hist.SPLITS comment), so a split there is not seen until the next periodic filing restates the count."""
    shares = v.get('diluted_shares') if isinstance(v, dict) else None
    period_end = shares.get('period_end') if isinstance(shares, dict) else None
    if not isinstance(period_end, str):
        return False
    for h in v.get('ebit_per_share_history') or []:
        if isinstance(h, dict) and h.get('share_basis_factor', 0) is None and \
                h.get('share_basis_factor_reason') == vf.SPLIT_TIMING_UNCONFIRMED and str(h.get('fiscal_year_end')) >= period_end:
            return True
    return iex_hist.split_after(code, period_end, basis_day)


def price_status(ctx, day) -> dict:
    """{key: price status} (iex_hist module doc): identity rules, then ADR (D7) / split (D6 (a)) rules, then the IEX day's."""
    out = {}
    for key, rec in ctx['inputs']['records'].items():
        v = _raw_v(ctx['payload'], key)
        code = ctx['keys'][key]
        if rec.get('identity_withdrawn') is True:
            out[key] = 'IDENTITY_CONFLICT_WITHDRAWN'
        elif key in ctx['blocked']:
            out[key] = 'PRICE_IDENTITY_CONFLICT'
        elif code is None:
            out[key] = 'PRICE_SYMBOL_UNMAPPED'
        elif adr_unconfirmed(rec, v):
            out[key] = 'ADR_RATIO_UNCONFIRMED'
        elif split_after_share_count(code, v, day.day):
            out[key] = 'SPLIT_AFTER_SHARE_COUNT'
        else:
            out[key] = day.status.get(key, 'PRICE_SYMBOL_UNMAPPED')
    return out


def engine_quotes(ctx, day, status, months) -> tuple[dict, dict]:
    """({key: {price, currency, month_closes}} for SUPPLIED keys, {key: [(month, reason)] left out}). RAM only."""
    quotes, left = {}, {}
    for key, st in status.items():
        if st != iex_hist.SUPPLIED or key not in day.quotes:
            continue
        q = dict(day.quotes[key])
        v = _raw_v(ctx['payload'], key)
        closes, out = iex_monthend.month_closes(ctx['keys'][key], v.get('ebit_per_share_history') if v else [], months)
        if closes:
            q['month_closes'] = closes
        if out:
            left[key] = out
        quotes[key] = q
    return quotes, left


def supply_check(ctx, status) -> dict:
    """D-CV5 counts over the price-independent V-eligible Universe rows (cross-section, GENERAL, V inputs, USD, not ADR/split)."""
    eligible = supplied = 0
    for key, rec in ctx['inputs']['records'].items():
        if key.startswith(TARGET_PREFIX) or rec.get('in_cross_section') is not True or rec.get('published_profile') != 'GENERAL':
            continue
        v = rec.get('v_inputs')
        if not isinstance(v, dict) or v.get('currency') != iex_hist.CURRENCY or status[key] in ('ADR_RATIO_UNCONFIRMED', 'SPLIT_AFTER_SHARE_COUNT'):
            continue
        eligible += 1
        supplied += status[key] == iex_hist.SUPPLIED
    return {'eligible': eligible, 'supplied': supplied, 'minimum_share': SUPPLY_MIN,
            'met': eligible > 0 and supplied >= math.ceil(SUPPLY_MIN * eligible - 1e-9)}


def score(ctx, quotes):
    priced = qi.priced_quotes(quotes, ctx['blocked'])
    from .dcf_parameters import load_default_dcf_parameters
    from .type_config import load_official_type_config
    return qgv_v2.score_universe(copy.deepcopy(ctx['companies']), priced, type_config=load_official_type_config().to_dict(),
                                 parameters=load_default_dcf_parameters(), preset=PRESET, gate=GATE)


# ---- public projection ----------------------------------------------------------------------------------------------
def projection(result) -> dict:
    """The engine fields both twins must agree on (JS cross-check), with engine reason codes (before public mapping)."""
    return {'factors': {k: {f: result['factors'][k][f] for f in FACTOR_KEYS} for k in qgv_v2.FACTORS},
            'axes': {a: {f: result['axes'][a].get(f) for f in AXIS_KEYS} for a in qgv_v2.PILLARS},
            'weights': result['weights'], 'type_weights': result['type_weights'], 'type_reason': result['type_reason'],
            'selected_types': list(result['selected_types']), 'q_industry_percentile': result['q_industry_percentile'],
            'value_trap_gate': result['value_trap_gate'], 'v_excluded': result['v_excluded'], 'flags': list(result['flags']),
            'total': result['total'], 'total_reason': result['total_reason']}


def public_reason(reason):
    return PRICE_DEPENDENT_PUBLIC if reason in PRICE_DEPENDENT else reason


def _na_factors(reason):
    return {k: {'score': None, 'reason': reason, 'basis': None} for k in qgv_v2.FACTORS}


def _na_axes(reason):
    return {a: {'score': None, 'state': 'NOT_AVAILABLE', 'weight_available': 0, 'factors_available': 0, 'reason': reason}
            for a in qgv_v2.PILLARS}


def public_row(key, rec, result, status, left):
    base = {'cik': rec.get('cik'), 'profile': rec.get('published_profile'), 'industry_group': rec.get('industry_group'),
            'in_cross_section': rec.get('in_cross_section') is True, 'state': rec.get('state'),
            'source_reason_codes': list(rec.get('na_reasons') or []), 'acquired_at': rec.get('acquired_at'),
            'fiscal_year_end': rec.get('fiscal_year_end'), 'price_status': status, 'rank': None, 'qg_reference_order': None,
            'rank_row': None}
    if result is None:   # calc_version mismatch: outside every population (Qgv2Inputs / QgvScores rule)
        return dict(base, factors=_na_factors('CALC_VERSION_MISMATCH'), axes=_na_axes('CALC_VERSION_MISMATCH'), weights=None,
                    type_weights=None, type_reason=None, selected_types=[], q_industry_percentile=None, value_trap_gate=False,
                    v_excluded=None, flags=['CALC_VERSION_MISMATCH'], total=None, total_reason='CALC_VERSION_MISMATCH')
    p = projection(result)
    for k, f in p['factors'].items():
        f['reason'] = public_reason(f['reason'])
    v4 = p['factors'][V4]
    if v4['score'] is None and result['factors'][V4]['reason'] in V4_HISTORY_REASONS and left:
        v4['reason'] = iex_monthend.public_v4_reason(left) or v4['reason']
    if status == 'PRICE_IDENTITY_CONFLICT':   # QgvScores.compute stop: no V, no total
        for k in qgv_v2.WEIGHTS['V']:
            p['factors'][k] = {'score': None, 'reason': 'PRICE_IDENTITY_CONFLICT', 'basis': None}
        p['axes']['V'] = _na_axes('PRICE_IDENTITY_CONFLICT')['V']
        p['total'], p['total_reason'] = None, 'PRICE_IDENTITY_CONFLICT'
        if 'PRICE_IDENTITY_CONFLICT' not in p['flags']:
            p['flags'].append('PRICE_IDENTITY_CONFLICT')
    elif (rec.get('state') == 'NOT_AVAILABLE' or rec.get('identity_withdrawn') is True) and p['total'] is None:
        p['total_reason'] = 'SOURCE_NOT_AVAILABLE'
    return dict(base, **p)


def _symbol(key):
    return TARGET_TICKERS.get(key[len(TARGET_PREFIX):], key) if key.startswith(TARGET_PREFIX) else qi.symbol_of(key)


def assign_ranks(rows) -> None:
    """D-CV8/D-CV9 + D11: one row per CIK (a TARGET row with data of a Universe issuer, else its cross-section code); ranked
    = total and V score, else qg_reference_order = total only. Ties: ticker, then key. Other rows of the CIK point to it."""
    universe_ciks = {r['cik'] for k, r in rows.items() if not k.startswith(TARGET_PREFIX) and r['cik']}
    rep = {}
    for k in sorted(rows):
        r = rows[k]
        if k.startswith(TARGET_PREFIX) and r['cik'] in universe_ciks and r['state'] in ('LIVE', 'STALE') \
                and r['total_reason'] != 'CALC_VERSION_MISMATCH':
            rep[r['cik']] = k
    for k in sorted(rows):
        r = rows[k]
        if not k.startswith(TARGET_PREFIX) and r['in_cross_section'] and r['cik'] and r['cik'] not in rep:
            rep[r['cik']] = k
    reps = [rows[k] | {'_key': k} for k in rep.values()]

    def order(xs):
        return sorted(xs, key=lambda r: (-r['total'], _symbol(r['_key']), r['_key']))
    ranked = order([r for r in reps if _finite(r['total']) and _finite(r['axes']['V']['score'])])
    qg = order([r for r in reps if _finite(r['total']) and not _finite(r['axes']['V']['score'])])
    for i, r in enumerate(ranked):
        rows[r['_key']]['rank'] = i + 1
    for i, r in enumerate(qg):
        rows[r['_key']]['qg_reference_order'] = i + 1
    for k, r in rows.items():
        target = rep.get(r['cik']) if r['cik'] else None
        if target and (rows[target]['rank'] is not None or rows[target]['qg_reference_order'] is not None):
            r['rank_row'] = target


def _finite(v):
    return type(v) in (int, float) and math.isfinite(v)


def _bump(m, k):
    m[k] = m.get(k, 0) + 1


def v_reason(row):
    """Public V reason of a row without a V score: its price status unless SUPPLIED, else the first V factor reason."""
    if row['price_status'] != iex_hist.SUPPLIED:
        return row['price_status']
    for k in qgv_v2.WEIGHTS['V']:
        if row['factors'][k]['score'] is None and row['factors'][k]['reason']:
            return row['factors'][k]['reason']
    return row['axes']['V']['reason'] or 'V_INPUTS_NOT_AVAILABLE'


def coverage(rows) -> dict:
    """Counts only, from the public rows (Universe codes; QgvScores.vCoverage vocabulary). Recomputed by the validator."""
    pop = {'total': 0, 'general': 0, 'financial': 0, 'unknown': 0, 'stopped': 0}
    v, qgv = {'full': 0, 'general': 0}, {'full': 0, 'general': 0}
    qg_only = {'full': 0, 'general': 0, 'financial': 0, 'no_v': 0, 'gate': 0}
    status, reasons, factor_reasons = {}, {}, {}
    missing = 0
    for key in sorted(rows):
        if key.startswith(TARGET_PREFIX):
            continue
        r = rows[key]
        cls = 'stopped' if r['state'] == 'WITHDRAWN' else 'general' if r['profile'] == 'GENERAL' else \
            'financial' if r['profile'] == 'FINANCIAL' else 'unknown'
        pop['total'] += 1
        pop[cls] += 1
        _bump(status, r['price_status'])
        has_v = _finite(r['axes']['V']['score'])
        gen = cls == 'general'
        if has_v:
            v['full'] += 1
            v['general'] += gen
            if _finite(r['axes']['Q']['score']) and _finite(r['axes']['G']['score']):
                qgv['full'] += 1
                qgv['general'] += gen
        if _finite(r['total']) and not has_v:
            qg_only['full'] += 1
            qg_only['general'] += gen
            qg_only['financial' if cls == 'financial' else 'no_v'] += 1
        if _finite(r['total']) and has_v and r['v_excluded']:
            qg_only['gate'] += 1
        if gen and not has_v:
            missing += 1
            _bump(reasons, v_reason(r))
            for f in sorted({r['factors'][k]['reason'] for k in qgv_v2.WEIGHTS['V'] if r['factors'][k]['score'] is None and r['factors'][k]['reason']}):
                _bump(factor_reasons, f)

    def listed(m):
        return [[k, n] for k, n in sorted(m.items(), key=lambda x: (-x[1], x[0]))]
    n = math.ceil(V_TARGET_SHARE * pop['general'] - 1e-9)
    return {'basis': 'UNIVERSE_CODES', 'population': pop, 'v': v, 'qgv': qgv, 'qg_only_total': qg_only,
            'ranked': sum(1 for r in rows.values() if r['rank'] is not None),
            'qg_reference': sum(1 for r in rows.values() if r['qg_reference_order'] is not None),
            'price_status': dict(sorted(status.items())), 'not_computed': missing, 'reasons': listed(reasons),
            'factor_reasons': listed(factor_reasons),
            'target': {'share': V_TARGET_SHARE, 'n': n, 'met': v['general'] >= n, 'observation_only': True}}


# ---- publication ----------------------------------------------------------------------------------------------------
def price_hmac(key: bytes, quotes: dict, status: dict) -> str:
    """Keyed fingerprint of the whole price set (D-CV design §3-3): never published, only inside publication_id."""
    body = _canonical({'quotes': {k: {'price': q['price'], 'month_closes': q.get('month_closes', {})} for k, q in sorted(quotes.items())},
                       'status': status})
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def engine_block():
    return {'version': qgv_v2.VERSION, 'status': qgv_v2.STATUS, 'python_sha256': sha256_bytes(ENGINE_PY.read_bytes()),
            'js_sha256': sha256_bytes(ENGINE_JS.read_bytes()),
            'publisher_sha256': sha256_bytes(b''.join(sha256_bytes(p.read_bytes()).encode() for p in PUBLISHER_SOURCES))}


def publication_id(manifest) -> str:
    return 'qgvpub-' + sha256_bytes(_canonical(manifest))


def attribution():
    return {'text': iex_hist.ATTRIBUTION, 'terms_url': iex_hist.TERMS_URL, 'label_ko': iex_hist.LABEL_KO}


def require_rule_version(payload) -> None:
    """The publication rules (U7) ride on the one calc_version bump 2026-10-23.1 (D-CV7 (b), owner decision D1 (ii)): a
    sec-qgv2.json of an earlier calc_version (no F_k on its rows) is not published from (NOT_RUN, the last good copy stays)."""
    if not vf.carries_share_basis(payload.get('calc_version') if isinstance(payload, dict) else None):
        raise OfficialError('NOT_RUN', 'SEC_QGV2_CALC_VERSION_BEFORE_U7')


def build(payload, payload_sha256, *, now, day, months, monthend_stamp, hmac_key, generated_at):
    """The publication (state OFFICIAL, times.verified_at None until verified) or OfficialError. RAM only."""
    from .dcf_parameters import CONFIG_VERSION as DCF_VERSION
    from .type_config import load_official_type_config
    from ..universe.sec_universe_shares import load_config
    if not isinstance(hmac_key, bytes) or len(hmac_key) < 16:
        raise OfficialError('NOT_RUN', 'HMAC_KEY_MISSING')
    require_rule_version(payload)
    ctx = prepare(payload, now)
    status = price_status(ctx, day)
    supply = supply_check(ctx, status)
    if not supply['met']:
        raise OfficialError('SUPPLY_FAILED', 'SUPPLY_BELOW_THRESHOLD')
    quotes, left = engine_quotes(ctx, day, status, months)
    results = score(ctx, quotes)
    rows = {key: public_row(key, rec, results.get(key), status[key], left.get(key)) for key, rec in sorted(ctx['inputs']['records'].items())}
    assign_ranks(rows)
    pooled = sorted(k for k, r in rows.items() if r['in_cross_section'])
    rejected = {}
    for k in sorted(status):
        if not k.startswith(TARGET_PREFIX) and status[k] != iex_hist.SUPPLIED:
            _bump(rejected, status[k])
    acquired = sorted(r['acquired_at'] for r in list(payload['records'].values()) + list(payload['target'].values())
                      if isinstance(r, dict) and isinstance(r.get('acquired_at'), str))
    type_cfg = load_official_type_config().to_dict()
    population = {'version': load_config()['config_version'], 'universe_code_count': payload['code_count'],
                  'registry_sha256': payload['registry_sha256'], 'row_count': len(rows), 'pooled_count': len(pooled),
                  'pooled_digest': sha256_bytes('\n'.join(pooled).encode())}
    weights = {'default_preset': PRESET, 'gate': GATE, 'type_weights': True, 'profile_id': f'{qgv_v2.VERSION}/{PRESET}/gate-on',
               'weights_version': qgv_v2.weights_id(qgv_v2.official_weights(PRESET))}
    config_versions = {'type_config': type_cfg['config_version'], 'dcf_parameters': DCF_VERSION}
    engine = engine_block()
    price_source = {'provider': iex_hist.PROVIDER, 'feed': ' '.join(iex_hist.FEED), 'basis_kind': iex_hist.BASIS_KIND,
                    'adjustment_basis': iex_hist.ADJUSTMENT_BASIS, 'currency': iex_hist.CURRENCY, 'basis_date': day.day,
                    'requested_basis_date': day.basis_date,
                    'supplied': sum(1 for k, s in status.items() if not k.startswith(TARGET_PREFIX) and s == iex_hist.SUPPLIED),
                    'rejected': rejected, 'supply': supply,
                    'month_end': {'store': iex_monthend.SCHEMA, 'stamp': monthend_stamp, 'months': len(months),
                                  'basis': 'RAW_DIVIDED_BY_SHARE_BASIS_FACTOR'}}
    manifest = {'calc_version': payload.get('calc_version'), 'inputs_sha256': payload_sha256, 'provider': iex_hist.PROVIDER,
                'feed': price_source['feed'], 'basis_date': day.day, 'adjustment_basis': iex_hist.ADJUSTMENT_BASIS,
                'price_hmac': price_hmac(hmac_key, quotes, status), 'population': population, 'weights': weights,
                'type_scope': qgv_v2.TYPE_SCOPE, 'config_versions': config_versions, 'engine': engine,
                'month_end': price_source['month_end']}
    official = {
        'schema': SCHEMA, 'kind': KIND, 'publication_id': publication_id(manifest), 'state': 'OFFICIAL',
        'calc_version': payload.get('calc_version'), 'engine': engine, 'population': population, 'weights': weights,
        'type_scope': qgv_v2.TYPE_SCOPE, 'config_versions': config_versions, 'price_source': price_source,
        'attribution': attribution(),
        'inputs': [{'file': qi.FILE, 'sha256': payload_sha256, 'as_of': payload['as_of'], 'calc_version': payload.get('calc_version'),
                    'acquired_oldest': acquired[0] if acquired else None, 'acquired_newest': acquired[-1] if acquired else None}],
        'times': {'price_basis_date': day.day, 'price_collected_from': iso(day.collected_from), 'price_collected_to': iso(day.collected_to),
                  'inputs_as_of': payload['as_of'], 'generated_at': iso(generated_at), 'verified_at': None},
        'coverage': coverage(rows), 'rows': rows}
    return official, {'ctx': ctx, 'quotes': quotes, 'results': results}


def encode(official) -> bytes:
    require_qgv_official(official)
    body = _canonical(official)
    _need(len(body) <= MAX_BYTES, 'OFFICIAL_TOO_LARGE')
    return body


# ---- strict validator (no prices needed) -----------------------------------------------------------------------------
def _walk_forbidden(value, depth=0):
    _need(depth <= 32)
    if isinstance(value, dict):
        for k, v in value.items():
            _need(isinstance(k, str) and k.lower() not in FORBIDDEN_KEYS, 'OFFICIAL_FORBIDDEN_KEY')
            _walk_forbidden(v, depth + 1)
    elif isinstance(value, list):
        for v in value:
            _walk_forbidden(v, depth + 1)
    elif isinstance(value, float):
        _need(math.isfinite(value))


def _keys(d, keys):
    _need(type(d) is dict and set(d) == set(keys))


def _score_ok(v):
    return v is None or (type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 100)


def _reason_ok(v):
    return v is None or (type(v) is str and _REASON.fullmatch(v) is not None and v not in PRICE_DEPENDENT)


def _str_or_none(v, rx=None):
    return v is None or (type(v) is str and (rx is None or rx.fullmatch(v) is not None))


def _row_ok(key, r):
    _keys(r, ROW_KEYS)
    _need(_CODE.fullmatch(key) is not None)
    _need(_str_or_none(r['cik'], re.compile(r'\d{10}')) and r['profile'] in (None, 'GENERAL', 'FINANCIAL'))
    _need(_str_or_none(r['industry_group'], re.compile(r'[a-z][a-z0-9_]{0,63}')) and type(r['in_cross_section']) is bool)
    _need(r['state'] in ('LIVE', 'STALE', 'NOT_AVAILABLE', 'WITHDRAWN'))
    _need(type(r['source_reason_codes']) is list and all(_reason_ok(x) and x for x in r['source_reason_codes']))
    _need(_str_or_none(r['acquired_at']) and _str_or_none(r['fiscal_year_end'], _DAY))
    _need(r['price_status'] in iex_hist.STATUS_CODES)
    _keys(r['factors'], qgv_v2.FACTORS)
    for f in r['factors'].values():
        _keys(f, FACTOR_KEYS)
        _need(_score_ok(f['score']) and _reason_ok(f['reason']) and _str_or_none(f['basis'], _REASON))
        _need(f['score'] is None or f['reason'] is None)
    _keys(r['axes'], qgv_v2.PILLARS)
    for a in r['axes'].values():
        _keys(a, AXIS_KEYS)
        _need(_score_ok(a['score']) and _reason_ok(a['reason']) and a['state'] in ('READY', 'PARTIAL', 'NOT_AVAILABLE'))
        _need(type(a['weight_available']) in (int, float) and 0 <= a['weight_available'] <= 1)
        _need(type(a['factors_available']) is int and 0 <= a['factors_available'] <= 5)
    for name in ('weights', 'type_weights'):
        w = r[name]
        _need(w is None or (type(w) is dict and set(w) == set(qgv_v2.PILLARS) and all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in w.values())))
    _need(_str_or_none(r['type_reason'], _REASON) and type(r['selected_types']) is list and all(type(x) is str for x in r['selected_types']))
    _need(_score_ok(r['q_industry_percentile']) and type(r['value_trap_gate']) is bool and r['v_excluded'] in (None, 'VALUE_TRAP_GATE'))
    _need(type(r['flags']) is list and all(type(x) is str and _REASON.fullmatch(x) for x in r['flags']))
    _need(_score_ok(r['total']) and _reason_ok(r['total_reason']) and (r['total'] is None) == (r['total_reason'] is not None))
    for name in ('rank', 'qg_reference_order'):
        _need(r[name] is None or (type(r[name]) is int and r[name] >= 1))
    _need(_str_or_none(r['rank_row'], _CODE))
    # Self-consistency: V axis = the engine's weighted mean of the published V factors; total = axes x weights (gate).
    if r['total_reason'] in ('PRICE_IDENTITY_CONFLICT', 'CALC_VERSION_MISMATCH'):
        _need(r['total'] is None and r['axes']['V']['score'] is None)
        return
    v = qgv_v2.axis_score({k: r['factors'][k]['score'] for k in qgv_v2.WEIGHTS['V']}, 'V')
    _need(v['score'] == r['axes']['V']['score'] and v['state'] == r['axes']['V']['state'])
    _need(r['weights'] is not None)
    axes, w = r['axes'], r['weights']
    data = 0.0
    for p in qgv_v2.PILLARS:
        if axes[p]['score'] is not None:
            data += w[p]
    included = [p for p in qgv_v2.PILLARS if axes[p]['score'] is not None and not (p == 'V' and r['value_trap_gate'])]
    if data / 100.0 < qgv_v2.MIN_AXIS_WEIGHT or not included:
        _need(r['total'] is None)
    else:
        acc = used = 0.0
        for p in included:
            acc += w[p] * axes[p]['score']
            used += w[p]
        _need(r['total'] == acc / used)
    _need(r['value_trap_gate'] == (r['v_excluded'] == 'VALUE_TRAP_GATE'))


def _ranks_ok(rows):
    for name in ('rank', 'qg_reference_order'):
        got = sorted((r[name], k) for k, r in rows.items() if r[name] is not None)
        _need([n for n, _ in got] == list(range(1, len(got) + 1)))
        for (_, ka), (_, kb) in zip(got, got[1:]):
            a, b = rows[ka], rows[kb]
            _need(_finite(a['total']) and _finite(b['total']) and a['total'] >= b['total'])
            _need(a['total'] > b['total'] or (_symbol(ka), ka) < (_symbol(kb), kb))   # ties: ticker, then key (assign_ranks)
        for _, k in got:
            r = rows[k]
            _need(_finite(r['total']) and _finite(r['axes']['V']['score']) == (name == 'rank'))
    ciks = [r['cik'] for r in rows.values() if r['rank'] is not None or r['qg_reference_order'] is not None]
    _need(len(ciks) == len(set(ciks)) and None not in ciks)   # one place per CIK
    for k, r in rows.items():
        if r['rank_row'] is not None:
            t = rows.get(r['rank_row'])
            _need(t is not None and t['cik'] == r['cik'] and (t['rank'] is not None or t['qg_reference_order'] is not None))
        if r['rank'] is not None or r['qg_reference_order'] is not None:
            _need(r['rank_row'] == k)


def require_qgv_official(payload) -> None:
    """Strict public validator (also the verify job and the Pages guard file validator, tools/pages_artifact_guard.py). ValueError
    fixed codes."""
    try:
        _keys(payload, TOP_KEYS)
        _walk_forbidden(payload)
        _need(payload['schema'] == SCHEMA and payload['kind'] == KIND and payload['state'] == 'OFFICIAL')
        _need(type(payload['publication_id']) is str and re.fullmatch(r'qgvpub-[0-9a-f]{64}', payload['publication_id']))
        _need(_str_or_none(payload['calc_version']))
        _keys(payload['engine'], ('version', 'status', 'python_sha256', 'js_sha256', 'publisher_sha256'))
        _need(payload['engine']['version'] == qgv_v2.VERSION and all(_HEX.fullmatch(payload['engine'][k]) for k in ('python_sha256', 'js_sha256', 'publisher_sha256')))
        _keys(payload['population'], ('version', 'universe_code_count', 'registry_sha256', 'row_count', 'pooled_count', 'pooled_digest'))
        _keys(payload['weights'], ('default_preset', 'gate', 'type_weights', 'profile_id', 'weights_version'))
        _need(payload['weights']['default_preset'] == PRESET and payload['weights']['gate'] is GATE)
        _keys(payload['config_versions'], ('type_config', 'dcf_parameters'))
        ps = payload['price_source']
        _keys(ps, ('provider', 'feed', 'basis_kind', 'adjustment_basis', 'currency', 'basis_date', 'requested_basis_date', 'supplied',
                   'rejected', 'supply', 'month_end'))
        _need(ps['provider'] == iex_hist.PROVIDER and ps['basis_kind'] == iex_hist.BASIS_KIND and ps['adjustment_basis'] == iex_hist.ADJUSTMENT_BASIS)
        _need(_DAY.fullmatch(ps['basis_date']) and _DAY.fullmatch(ps['requested_basis_date']) and ps['basis_date'] <= ps['requested_basis_date'])
        _need(type(ps['rejected']) is dict and all(k in iex_hist.STATUS_CODES and k != iex_hist.SUPPLIED and type(n) is int and n > 0 for k, n in ps['rejected'].items()))
        _keys(ps['supply'], ('eligible', 'supplied', 'minimum_share', 'met'))
        _need(ps['supply']['met'] is True and ps['supply']['minimum_share'] == SUPPLY_MIN)
        _keys(ps['month_end'], ('store', 'stamp', 'months', 'basis'))
        _need(payload['attribution'] == attribution())
        _need(type(payload['inputs']) is list and len(payload['inputs']) == 1)
        _keys(payload['inputs'][0], ('file', 'sha256', 'as_of', 'calc_version', 'acquired_oldest', 'acquired_newest'))
        _need(payload['inputs'][0]['file'] == qi.FILE and _HEX.fullmatch(payload['inputs'][0]['sha256']))
        t = payload['times']
        _keys(t, ('price_basis_date', 'price_collected_from', 'price_collected_to', 'inputs_as_of', 'generated_at', 'verified_at'))
        _need(t['price_basis_date'] == ps['basis_date'] and all(_CLOCK.fullmatch(t[k]) for k in ('price_collected_from', 'price_collected_to', 'generated_at')))
        _need(t['verified_at'] is None or _CLOCK.fullmatch(t['verified_at']))
        rows = payload['rows']
        _need(type(rows) is dict and 0 < len(rows) <= 2048)
        for k, r in rows.items():
            _row_ok(k, r)
        _ranks_ok(rows)
        _need(payload['population']['row_count'] == len(rows))
        _need(payload['population']['pooled_count'] == sum(1 for r in rows.values() if r['in_cross_section']))
        _need(payload['population']['universe_code_count'] == sum(1 for k in rows if not k.startswith(TARGET_PREFIX)))
        rejected = {}
        for k in sorted(rows):
            if not k.startswith(TARGET_PREFIX) and rows[k]['price_status'] != iex_hist.SUPPLIED:
                _bump(rejected, rows[k]['price_status'])
        _need(ps['rejected'] == rejected and ps['supplied'] == sum(1 for k, r in rows.items() if not k.startswith(TARGET_PREFIX) and r['price_status'] == iex_hist.SUPPLIED))
        _need(json.dumps(payload['coverage'], sort_keys=True) == json.dumps(coverage(rows), sort_keys=True))
        _need(len(_canonical(payload)) <= MAX_BYTES, 'OFFICIAL_TOO_LARGE')
    except ValueError as e:
        raise ValueError(e.args[0] if e.args and str(e.args[0]).startswith('OFFICIAL_') else 'OFFICIAL_INVALID') from None
    except (TypeError, KeyError, AttributeError, OverflowError, RecursionError, ZeroDivisionError):
        raise ValueError('OFFICIAL_INVALID') from None


def parse(body: bytes):
    """Strict JSON (no duplicate keys, no NaN) of at most MAX_BYTES, then require_qgv_official."""
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('OFFICIAL_INVALID')
            out[k] = v
        return out

    def constant(_):
        raise ValueError('OFFICIAL_INVALID')
    if type(body) is not bytes or len(body) > MAX_BYTES:
        raise ValueError('OFFICIAL_INVALID')
    try:
        payload = json.loads(body.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise ValueError('OFFICIAL_INVALID') from None
    require_qgv_official(payload)
    return payload


# ---- status file ----------------------------------------------------------------------------------------------------
STATUS_KEYS = ('schema', 'kind', 'last_attempt_at', 'attempt_state', 'reason_code', 'official_publication_id',
               'official_price_basis_date', 'official_verified_at', 'latest_inputs', 'attribution')


def status_payload(*, attempt_at, state, reason, official, inputs_sha256, inputs_as_of):
    """Attempt record: no values, no code lists, no prices. `official` = the publication now in the artifact (or None).
    A failed attempt without any official publication is NO_OFFICIAL_YET (its reason = the failure code)."""
    if state not in ATTEMPT_STATES or (state == 'OK') != (reason is None) or (state == 'OK' and official is None):
        raise ValueError('OFFICIAL_STATUS_INVALID')
    return {'schema': STATUS_SCHEMA, 'kind': STATUS_KIND, 'last_attempt_at': iso(attempt_at),
            'attempt_state': state if official is not None else 'NO_OFFICIAL_YET', 'reason_code': reason,
            'official_publication_id': official['publication_id'] if official else None,
            'official_price_basis_date': official['times']['price_basis_date'] if official else None,
            'official_verified_at': official['times']['verified_at'] if official else None,
            'latest_inputs': {'sha256': inputs_sha256, 'as_of': inputs_as_of}, 'attribution': attribution()}


def require_status(payload) -> None:
    try:
        _keys(payload, STATUS_KEYS)
        _walk_forbidden(payload)
        _need(payload['schema'] == STATUS_SCHEMA and payload['kind'] == STATUS_KIND and payload['attempt_state'] in ATTEMPT_STATES)
        _need(_CLOCK.fullmatch(payload['last_attempt_at']) and _reason_ok(payload['reason_code']))
        _need((payload['reason_code'] is None) == (payload['attempt_state'] == 'OK'))
        has = payload['official_publication_id'] is not None
        _need(not has or re.fullmatch(r'qgvpub-[0-9a-f]{64}', payload['official_publication_id']))
        _need(has == (payload['official_price_basis_date'] is not None) and _str_or_none(payload['official_price_basis_date'], _DAY))
        _need(_str_or_none(payload['official_verified_at'], _CLOCK) and (payload['attempt_state'] != 'NO_OFFICIAL_YET' or not has))
        _keys(payload['latest_inputs'], ('sha256', 'as_of'))
        _need(_str_or_none(payload['latest_inputs']['sha256'], _HEX) and _str_or_none(payload['latest_inputs']['as_of']))
        _need(payload['attribution'] == attribution())
    except ValueError:
        raise ValueError('OFFICIAL_STATUS_INVALID') from None
    except (TypeError, KeyError, AttributeError):
        raise ValueError('OFFICIAL_STATUS_INVALID') from None
