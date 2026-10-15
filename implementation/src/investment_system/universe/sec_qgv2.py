"""Public price-free QGV v2 Q·G file `sec-qgv2.json` (Universe504 + TARGET). PROVISIONAL, UNCALIBRATED.

User decision 2026-10-13: QGV v2 is the provisional default (decision record GSQ-022 pending approval).
Method: docs/qgv_scoring_standard/QGV_V2_QG_METHOD.md; spec QGV_V2_CANDIDATE.md; weights are the
candidate defaults exactly (no tuning, no Holdout). v1 files/methodology are unchanged.

Producers (no extra SEC request anywhere):
- the daily Universe shard (tools/sec_universe_shares.py) computes rows from the SAME companyfacts and
  submissions bytes it already fetched; rows merge into the previous Pages copy like
  sec-universe-shares.json (own acquired_at, a new row without data never erases a kept one, STALE after
  the shared v0 window);
- the TARGET daily pipeline (tools/public_screens_pipeline.py --live) stages TARGET rows from its own SEC
  bytes into the same file; the shard step then carries them into the published copy.
Scores are recomputed at every publication over all current LIVE/STALE Universe rows (qgv.v2_scoring),
so the published factor/axis scores are reproducible from the published raw metrics; the strict
validators (Python here, JS web_assets/sec-qgv2.js) recompute and compare them.

Never: prices, price-derived values, market caps, ranks or 0-filled missing values.
"""
from __future__ import annotations

from datetime import date, timedelta, timezone
import hashlib
import json
import math
import re

from ..qgv import v2_factors as vf
from ..qgv import v2_scoring as vs
from .sec_universe_shares import _clock, _hash, _iso, load_config, universe_codes

FILENAME = 'sec-qgv2.json'
KIND = 'SEC_QGV2'
MAX_BYTES = 2 * 1024 * 1024
STANDARD = 'QGV_V2'
STANDARD_STATUS = 'PROVISIONAL_DEFAULT_UNCALIBRATED'
DECISION_REF = 'GSQ-022'
STATES = ('LIVE', 'STALE', 'NOT_AVAILABLE')
REASONS = ('NOT_COLLECTED', 'CIK_UNRESOLVED', 'INVALID_INPUT', 'NO_ANNUAL_SEC_FINANCIALS', 'NON_SEC_ISSUER', 'STALE_INPUT')
TOP_REASONS = ('STALE_INPUT', 'NO_ELIGIBLE_INPUT')
METHOD = {
    'weights': {'Q': dict(vs.Q_WEIGHTS_V2), 'G': dict(vs.G_WEIGHTS_V2)},
    'min_peers': vs.MIN_PEERS,
    'axis_coverage_min_percent': vs.AXIS_COVERAGE_MIN,
    'percentile': 'AVERAGE_RANK_0_100',
    'industry_groups': 'sic_industry_groups/v0',
    'financial_sic_range': list(vf.FINANCIAL_SIC_RANGE),
    'cross_section': 'UNIVERSE504_LIVE_STALE_ONE_POINT_PER_CIK',
    'submetric_fallback': 'GROUP_VALUES_BELOW_MIN_PEERS_RANK_IN_GENERAL_UNIVERSE',
    'earnings_surprise': 'OMITTED_NO_FREE_SOURCE',
}
ROW_KEYS = ('cik', 'acquired_at', 'source_sha256', 'state', 'reason_codes', 'sic', 'industry_group', 'profile',
            'fiscal_year_end', 'currency', 'metrics', 'factors', 'axes', 'v_inputs_v2')
AXIS_KEYS = ('score', 'factors_available', 'available_weight', 'peer_basis', 'peer_count', 'submetric_fallbacks', 'reason_codes')
TOP_KEYS = ('schema_version', 'kind', 'as_of', 'standard', 'standard_status', 'decision_ref', 'method', 'config_version',
            'config_status', 'freshness_basis', 'stale_after_seconds', 'shard_count', 'last_shard_index', 'registry_sha256',
            'code_count', 'cross_section_size', 'cross_section_by_profile', 'state', 'reason_codes', 'records', 'target')
METRIC_LIMIT = 1e12
FLOW_V_KEYS = ('ebit', 'fcf', 'revenue')
INSTANT_V_KEYS = ('total_debt', 'cash_and_equivalents', 'diluted_shares')
GROWTH_V_KEYS = ('revenue_cagr_3y', 'eps_cagr_3y', 'fcf_per_share_cagr_3y', 'revenue_ttm_growth')
_ERRORS = (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError, ZeroDivisionError)


def target_ids():
    from ..qgv.portfolio import OFFICIAL_V11_TARGETS
    return tuple(OFFICIAL_V11_TARGETS)


def target_cik(company_id):
    from ..markets.us import US_LISTINGS
    listing = US_LISTINGS.get(company_id)
    return listing['cik'] if listing else None


def _sic_config():
    from ..qgv.sic_industry import load_sic_config
    return load_sic_config()


def _need(condition):
    if not condition:
        raise ValueError('SEC_QGV2_INVALID')


def _finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _cik_ok(value):
    return type(value) is str and re.fullmatch(r'[0-9]{10}', value) is not None and value != '0000000000'


def _date(value):
    _need(type(value) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is not None)
    return date.fromisoformat(value)


def empty_record(*, cik=None, reasons=('NOT_COLLECTED',)):
    return {'cik': cik, 'acquired_at': None, 'source_sha256': {'companyfacts': None, 'submissions': None},
            'state': 'NOT_AVAILABLE', 'reason_codes': list(reasons), 'sic': None, 'industry_group': None, 'profile': None,
            'fiscal_year_end': None, 'currency': None, 'metrics': {},
            'factors': dict.fromkeys(vs.FACTOR_IDS), 'axes': {axis: vs._empty_axis('ROW_NOT_AVAILABLE') for axis in vs.AXES},
            'v_inputs_v2': vf.empty_v_inputs()}


def _has_data(record):
    return record['fiscal_year_end'] is not None


def _parse(body):
    from ..product.public_engine_screens import parse_json as parse_sec
    return parse_sec(body)


def build_row(*, cik, companyfacts_body, submissions_body, acquired_at, sic_config=None):
    """One issuer's row (raw metrics + v_inputs_v2, scores filled at publication). Untrusted content -> fixed reason."""
    if not _cik_ok(cik):
        return empty_record(reasons=('INVALID_INPUT',))
    record = empty_record(cik=cik, reasons=('INVALID_INPUT',))
    if type(companyfacts_body) is not bytes or type(submissions_body) is not bytes or getattr(acquired_at, 'utcoffset', lambda: None)() is None:
        return record
    record.update(acquired_at=_iso(acquired_at), source_sha256={'companyfacts': hashlib.sha256(companyfacts_body).hexdigest(),
                                                                 'submissions': hashlib.sha256(submissions_body).hexdigest()})
    try:
        facts, subs = _parse(companyfacts_body), _parse(submissions_body)
        if not isinstance(facts, dict) or not isinstance(subs, dict):
            return record
        if str(facts.get('cik')).zfill(10) != cik or str(subs.get('cik')).zfill(10) != cik:
            return record
        from ..qgv.sic_industry import classify_sic
        industry = classify_sic(subs.get('sic'), sic_config or _sic_config())
        profile, fy_end, currency, metrics, v_inputs = vf.compute(
            facts, sic=industry['sic'], cutoff=acquired_at.astimezone(timezone.utc).date())
    except _ERRORS + (UnicodeError,):
        return record
    record.update(sic=industry['sic'], industry_group=industry['group'])
    if fy_end is None:
        record['reason_codes'] = ['NO_ANNUAL_SEC_FINANCIALS']
        return record
    # Sparse: an absent metric key is NOT_AVAILABLE (never 0).
    record.update(profile=profile, fiscal_year_end=fy_end, currency=currency,
                  metrics={k: v for k, v in metrics.items() if v is not None}, v_inputs_v2=v_inputs,
                  state='LIVE', reason_codes=[])
    return record


def build_issuer_records(*, codes, cik, companyfacts_body, submissions_body, acquired_at, sic_config=None):
    """Every Universe code of one issuer carries the issuer's row."""
    row = build_row(cik=cik, companyfacts_body=companyfacts_body, submissions_body=submissions_body,
                    acquired_at=acquired_at, sic_config=sic_config)
    return {code: json.loads(json.dumps(row)) for code in codes}


def build_target_rows(entries, *, sic_config=None):
    """TARGET rows from the TARGET pipeline bytes: entries = [(company_id, companyfacts_body, submissions_body, acquired_at)].

    Only US SEC issuers of the TARGET; the CIK comes from the TARGET listing table (bytes must match it)."""
    rows = {}
    for company_id, facts, subs, acquired in entries:
        cik = target_cik(company_id)
        if company_id not in target_ids() or cik is None:
            continue
        rows[company_id] = build_row(cik=cik, companyfacts_body=facts, submissions_body=subs, acquired_at=acquired,
                                     sic_config=sic_config)
    return rows


def restate(record, as_of, stale_after):
    """Freshness from the row's own acquisition time; values never change (scores are recomputed by publish)."""
    out = json.loads(json.dumps(record))
    reasons = [r for r in out['reason_codes'] if r != 'STALE_INPUT']
    if not _has_data(out):
        out['state'] = 'NOT_AVAILABLE'
        out['reason_codes'] = reasons or ['NO_ANNUAL_SEC_FINANCIALS']
        return out
    fresh = as_of.astimezone(timezone.utc) - _clock(out['acquired_at']) <= stale_after
    out['state'] = 'LIVE' if fresh else 'STALE'
    out['reason_codes'] = [] if fresh else ['STALE_INPUT']
    return out


def _pick(old, new, as_of, stale_after, cut, sic_cfg, *, target_id=None):
    """A valid new row replaces the kept one unless it has no data and the kept one has."""
    if new is not None:
        try:
            _row(restate(new, as_of, stale_after), cut, stale_after, sic_cfg, target_id=target_id)
        except _ERRORS:
            cik = new.get('cik') if type(new) is dict else None
            new = empty_record(cik=cik if _cik_ok(cik) else None, reasons=('INVALID_INPUT',))
    if new is not None and not (not _has_data(new) and _has_data(old)):
        return new
    return old


def _target_empty(company_id):
    cik = target_cik(company_id)
    return empty_record(cik=None, reasons=('NON_SEC_ISSUER',)) if cik is None else empty_record(cik=None)


def merge(previous, updates, *, as_of, shard_index, registry_sha256=None, unresolved=(), config=None, target_updates=None):
    """Previous published rows + this run's Universe/TARGET rows, then publication-time scoring."""
    cfg = config or load_config()
    sic_cfg = _sic_config()
    stale_after = timedelta(days=cfg['stale_after_days'])
    cut = _clock(_iso(as_of))
    kept = previous['records'] if previous is not None else {}
    records = {}
    for code in universe_codes():
        old = kept.get(code) or empty_record()
        new = updates.get(code)
        chosen = _pick(old, new, as_of, stale_after, cut, sic_cfg)
        if new is None and code in unresolved and not _has_data(chosen):
            chosen = empty_record(reasons=('CIK_UNRESOLVED',))
        records[code] = restate(chosen, as_of, stale_after)
    kept_target = (previous or {}).get('target') or {}
    target = {}
    for company_id in target_ids():
        if target_cik(company_id) is None:
            target[company_id] = _target_empty(company_id)
            continue
        old = kept_target.get(company_id) or _target_empty(company_id)
        chosen = _pick(old, (target_updates or {}).get(company_id), as_of, stale_after, cut, sic_cfg, target_id=company_id)
        target[company_id] = restate(chosen, as_of, stale_after)
    payload = publish(records, target, as_of=as_of, cfg=cfg, stale_after=stale_after, shard_index=shard_index,
                      registry_sha256=registry_sha256 if registry_sha256 is not None else (previous or {}).get('registry_sha256'))
    require_qgv2(payload)
    return payload


def publish(records, target, *, as_of, cfg, stale_after, shard_index, registry_sha256):
    scores, summary = vs.score_rows(records, target)
    volatility = vs.volatility_rank_rows(records, target)
    for role, rows in (('universe', records), ('target', target)):
        for key, row in rows.items():
            row['factors'] = scores[(role, key)]['factors']
            row['axes'] = scores[(role, key)]['axes']
            rank = volatility[(role, key)]
            if rank is None:
                row['metrics'].pop('revenue_volatility_5y_rank_pct', None)
            else:
                row['metrics']['revenue_volatility_5y_rank_pct'] = rank
    states = [r['state'] for r in records.values()] + [r['state'] for r in target.values()]
    state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
    return {'schema_version': 1, 'kind': KIND, 'as_of': _iso(as_of), 'standard': STANDARD, 'standard_status': STANDARD_STATUS,
            'decision_ref': DECISION_REF, 'method': json.loads(json.dumps(METHOD)), 'config_version': cfg['config_version'],
            'config_status': cfg['config_status'], 'freshness_basis': 'SOURCE_ACQUISITION',
            'stale_after_seconds': int(stale_after.total_seconds()), 'shard_count': cfg['shard_count'],
            'last_shard_index': shard_index, 'registry_sha256': registry_sha256, 'code_count': len(records),
            'cross_section_size': summary['cross_section_size'], 'cross_section_by_profile': summary['cross_section_by_profile'],
            'state': state, 'reason_codes': [] if state == 'LIVE' else ['STALE_INPUT'] if state == 'STALE' else ['NO_ELIGIBLE_INPUT'],
            'records': records, 'target': target}


# ---------------- strict validator ----------------
def _metric_ok(key, value):
    if key == 'moat_return_years':
        return type(value) is int and 3 <= value <= vf.HISTORY_YEARS
    if key == 'ebit_estimated_years':  # FY0..FY-5 substitute-EBIT count, published only when >= 1
        return type(value) is int and 1 <= value <= vf.HISTORY_YEARS + 1
    # JSON numbers: an integral float may arrive as an int (JS has one number type); bool is never a number.
    valid = type(value) in (int, float) and math.isfinite(value) and abs(value) <= METRIC_LIMIT
    if key == 'revenue_growth_std_5y':
        return valid and value >= 0
    if key == 'revenue_volatility_5y_rank_pct':
        return valid and 0 <= value <= 100
    return valid


def _v_inputs(v, cut_day, has_data):
    _need(type(v) is dict and set(v) in (set(vf.V_KEYS), set(vf.LEGACY_V_KEYS)))
    if not has_data:
        _need(v == {k: x for k, x in vf.empty_v_inputs().items() if k in v})
        return
    _need(type(v['currency']) is str and re.fullmatch(r'[A-Z]{3}', v['currency']) is not None)
    _need(v['taxonomy'] in ('us-gaap', 'ifrs-full'))
    _need(_date(v['fiscal_year_end']) <= cut_day)
    for key in FLOW_V_KEYS:
        f = v.get(key)
        if f is None:
            continue
        _need(type(f) is dict and set(f) == set(vf.V_FLOW_KEYS))
        for value_key, end_key in (('fy_value', 'fy_end'), ('ttm_value', 'ttm_end')):
            _need((f[value_key] is None) == (f[end_key] is None))
            if f[value_key] is not None:
                _need(_finite(f[value_key]) and type(f[value_key]) is not bool and _date(f[end_key]) <= cut_day)
        _need(f['fy_value'] is not None or f['ttm_value'] is not None)
        if f['fy_end'] is not None and f['ttm_end'] is not None:
            _need(_date(f['ttm_end']) >= _date(f['fy_end']))
    for key in INSTANT_V_KEYS:
        i = v[key]
        if i is None:
            continue
        _need(type(i) is dict and set(i) == {'value', 'period_end'} and _finite(i['value']) and type(i['value']) is not bool)
        _need(_date(i['period_end']) <= cut_day)
        if key == 'diluted_shares':
            _need(i['value'] > 0)
    for key in ('ebit_per_share_history', 'fcf_per_share_history', 'operating_margin_history'):
        history = v.get(key, [])
        _need(type(history) is list and len(history) <= vf.HISTORY_YEARS)
        ends = []
        for h in history:
            _need(type(h) is dict and set(h) == {'fiscal_year_end', 'value'} and _finite(h['value']) and type(h['value']) is not bool)
            ends.append(_date(h['fiscal_year_end']))
            _need(ends[-1] <= cut_day)
        _need(all(a < b for a, b in zip(ends, ends[1:])))
    for key in GROWTH_V_KEYS:
        _need(v[key] is None or type(v[key]) in (int, float) and math.isfinite(v[key]) and abs(v[key]) <= METRIC_LIMIT)


def _row(r, cut, ttl, sic_cfg, *, target_id=None):
    _need(type(r) is dict and set(r) == set(ROW_KEYS))
    _need(r['cik'] is None or _cik_ok(r['cik']))
    if target_id is not None and r['cik'] is not None:
        _need(r['cik'] == target_cik(target_id))
    h = r['source_sha256']
    _need(type(h) is dict and set(h) == {'companyfacts', 'submissions'} and all(v is None or _hash(v) for v in h.values()))
    if r['acquired_at'] is None:
        _need(h['companyfacts'] is None and h['submissions'] is None)
    else:
        _need(_clock(r['acquired_at']) <= cut and r['cik'] is not None and h['companyfacts'] and h['submissions'])
    _need(r['state'] in STATES)
    reasons = r['reason_codes']
    _need(type(reasons) is list and len(reasons) == len(set(reasons)) <= 3 and all(x in REASONS for x in reasons))
    from ..qgv.sic_industry import classify_sic
    _need(r['sic'] is None or type(r['sic']) is str and re.fullmatch(r'[0-9]{4}', r['sic']) is not None and r['sic'] != '0000')
    if r['sic'] is None:
        _need(r['industry_group'] is None)
    else:
        _need(r['acquired_at'] is not None and r['industry_group'] == classify_sic(r['sic'], sic_cfg)['group'])
    metrics = r['metrics']
    _need(type(metrics) is dict and set(metrics) <= set(vf.METRIC_KEYS) | set(vf.EXTRA_METRIC_KEYS)
          and all(_metric_ok(k, v) for k, v in metrics.items()))
    has_data = r['fiscal_year_end'] is not None
    if has_data:
        _need(r['acquired_at'] is not None and _date(r['fiscal_year_end']) <= cut.date())
        _need(r['profile'] == vf.profile_for_sic(r['sic']))
        _need(type(r['currency']) is str and re.fullmatch(r'[A-Z]{3}', r['currency']) is not None)
        allowed = {m for specs in vs.SUBMETRICS[r['profile']].values() for m, _ in specs} | vf.DESCRIPTIVE_METRICS | {'dilution_3y'}
        allowed |= {k for k, profiles in vf.EXTRA_METRIC_PROFILES.items() if r['profile'] in profiles}
        _need(set(metrics) <= allowed)
        fresh = cut - _clock(r['acquired_at']) <= ttl
        _need(r['state'] == ('LIVE' if fresh else 'STALE') and reasons == ([] if fresh else ['STALE_INPUT']))
        _need(r['v_inputs_v2']['currency'] == r['currency'] and r['v_inputs_v2']['fiscal_year_end'] == r['fiscal_year_end'])
    else:
        _need(r['profile'] is None and r['currency'] is None and metrics == {})
        _need(r['state'] == 'NOT_AVAILABLE' and reasons and 'STALE_INPUT' not in reasons)
        if target_id is not None and target_cik(target_id) is None:
            _need(reasons == ['NON_SEC_ISSUER'] and r['cik'] is None and r['acquired_at'] is None)
        else:
            _need('NON_SEC_ISSUER' not in reasons)
    _v_inputs(r['v_inputs_v2'], cut.date(), has_data)
    _need(type(r['factors']) is dict and set(r['factors']) == set(vs.FACTOR_IDS))
    _need(type(r['axes']) is dict and set(r['axes']) == set(vs.AXES) and all(type(a) is dict and set(a) == set(AXIS_KEYS) for a in r['axes'].values()))
    return r['state']


def _same_number(a, b):
    if a is None or b is None:
        return a is None and b is None
    return _finite(a) and type(a) is not bool and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def _scores_match(row, expected):
    _need(all(_same_number(row['factors'][f], expected['factors'][f]) for f in vs.FACTOR_IDS))
    for axis in vs.AXES:
        got, want = row['axes'][axis], expected['axes'][axis]
        _need(_same_number(got['score'], want['score']))
        _need(all(type(got[k]) is type(want[k]) and got[k] == want[k] for k in AXIS_KEYS if k != 'score'))


def require_qgv2(payload):
    """Strict public validator (also the Pages guard). Recomputes every score from the published metrics."""
    try:
        _need(type(payload) is dict and set(payload) == set(TOP_KEYS))
        cfg = load_config()
        _need(type(payload['schema_version']) is int and payload['schema_version'] == 1 and payload['kind'] == KIND)
        _need(payload['standard'] == STANDARD and payload['standard_status'] == STANDARD_STATUS and payload['decision_ref'] in (DECISION_REF, 'GSQ-022_PENDING_APPROVAL'))
        _need(payload['method'] == METHOD and json.dumps(payload['method'], sort_keys=True) == json.dumps(METHOD, sort_keys=True))
        cut = _clock(payload['as_of'])
        _need(payload['config_version'] == cfg['config_version'] and payload['config_status'] == cfg['config_status'])
        _need(payload['freshness_basis'] == 'SOURCE_ACQUISITION')
        ttl = payload['stale_after_seconds']
        _need(type(ttl) is int and 0 < ttl <= 366 * 86400)
        _need(type(payload['shard_count']) is int and 1 <= payload['shard_count'] <= 366)
        index = payload['last_shard_index']
        _need(index is None or type(index) is int and 0 <= index < payload['shard_count'])
        _need(payload['registry_sha256'] is None or _hash(payload['registry_sha256']))
        records, target = payload['records'], payload['target']
        codes, ids = universe_codes(), target_ids()
        _need(type(records) is dict and set(records) == set(codes) and type(payload['code_count']) is int and payload['code_count'] == len(codes))
        _need(type(target) is dict and set(target) == set(ids))
        sic_cfg, window = _sic_config(), timedelta(seconds=ttl)
        states = [_row(records[code], cut, window, sic_cfg) for code in codes]
        states += [_row(target[cid], cut, window, sic_cfg, target_id=cid) for cid in ids]
        state = 'LIVE' if 'LIVE' in states else 'STALE' if 'STALE' in states else 'NOT_AVAILABLE'
        _need(payload['state'] == state)
        top = payload['reason_codes']
        _need(type(top) is list and all(x in TOP_REASONS for x in top) and len(top) == len(set(top)))
        _need(top == ([] if state == 'LIVE' else ['STALE_INPUT'] if state == 'STALE' else ['NO_ELIGIBLE_INPUT']))
        expected, summary = vs.score_rows(records, target)
        volatility = vs.volatility_rank_rows(records, target)
        for role, rows in (('universe', records), ('target', target)):
            for key, r in rows.items():
                rank = r['metrics'].get('revenue_volatility_5y_rank_pct')
                want = volatility[(role, key)]
                _need((rank is None and want is None) or rank is not None and want is not None and abs(rank - want) < 1e-9)
        _need(type(payload['cross_section_size']) is int and payload['cross_section_size'] == summary['cross_section_size'])
        _need(payload['cross_section_by_profile'] == summary['cross_section_by_profile']
              and all(type(v) is int for v in payload['cross_section_by_profile'].values()))
        # Issuer codes of one CIK carry one identical row (one cross-section point).
        by_cik = {}
        for code in codes:
            r = records[code]
            if r['state'] != 'NOT_AVAILABLE':
                _need(by_cik.setdefault(r['cik'], json.dumps(r, sort_keys=True)) == json.dumps(r, sort_keys=True))
            _scores_match(r, expected[('universe', code)])
        for cid in ids:
            _scores_match(target[cid], expected[('target', cid)])
        return payload
    except _ERRORS:
        raise ValueError('SEC_QGV2_INVALID') from None


def parse_json(body):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('SEC_QGV2_INVALID')
            out[key] = value
        return out

    def constant(_):
        raise ValueError('SEC_QGV2_INVALID')
    try:
        if type(body) is not bytes or len(body) > MAX_BYTES:
            raise ValueError
        return json.loads(body.decode('utf-8', errors='strict'), object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError('SEC_QGV2_INVALID') from None


def encode(payload):
    require_qgv2(payload)
    body = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()
    _need(len(body) <= MAX_BYTES)
    return body


def target_updates_from(payload):
    """TARGET rows with data from a staged/previous payload (used to carry the TARGET stage into the shard publish)."""
    return {cid: row for cid, row in payload['target'].items() if _has_data(row)}


def summary_line(payload, *, prefix):
    rows = list(payload['records'].values())
    count = lambda value: sum(1 for r in rows if r['state'] == value)
    q_scored = sum(1 for r in rows if r['axes']['Q']['score'] is not None)
    g_scored = sum(1 for r in rows if r['axes']['G']['score'] is not None)
    target = list(payload['target'].values())
    t_live = sum(1 for r in target if r['state'] == 'LIVE')
    t_q = sum(1 for r in target if r['axes']['Q']['score'] is not None)
    t_g = sum(1 for r in target if r['axes']['G']['score'] is not None)
    return (f"{prefix} live={count('LIVE')} stale={count('STALE')} not_available={count('NOT_AVAILABLE')} "
            f"cross_section={payload['cross_section_size']} q_scored={q_scored} g_scored={g_scored} "
            f"target_live={t_live} target_q_scored={t_q} target_g_scored={t_g}")
