#!/usr/bin/env python3
"""JS parity vectors for the qgv-official/1 reader (web_assets/qgv-official.js, PR-D, owner decision D8 (b)).

Synthetic only: the publication is built by the production publisher (qgv/qgv_official.build) from the tests/test_qgv_official.py
builders (synthetic sec-qgv2 vector base, made-up prices that never leave RAM), then cut to a mini form and re-derived with the
production helpers (assign_ranks, coverage, pooled_digest). Every hash the validator checks for format only (engine, publisher,
registry, inputs, publication_id) is replaced by a fixed synthetic hex, so the fixture does not follow engine or publisher source
bytes. Lives in tests/ (not tools/): it imports the IEX adapters, which tools/ may not name (tests/test_qgv_official_guards.py).

Fixture tests/fixtures/qgv_official_vectors_v1.json:
- base_text: the mini publication as Python's canonical bytes (qgv_official._canonical), verified_at set;
- cases: JSON ops on the parsed base + the verdict of Python require_qgv_official (`max_bytes` patches qgv_official.MAX_BYTES);
  `js_stricter` = Python accepts, the JS reader must reject (verified_at null);
- bodies: byte edits of base_text + the verdict of Python parse(); `divergence` = a documented byte-spelling difference the JS
  reader does not mirror (the Pages guard runs the Python validator on every deploy);
- digest_cases / canonical_length_cases / constants.
`--write` regenerates the fixture; without it the fixture is compared (QGV_OFFICIAL_VECTORS_OK / _STALE).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _p in (ROOT, ROOT / 'src'):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from investment_system.providers import iex_hist, iex_monthend  # noqa: E402
from investment_system.qgv import qgv_official as qo  # noqa: E402
from investment_system.qgv import qgv_v2  # noqa: E402
from investment_system.qgv import v2_factors as vf  # noqa: E402
from tests.test_qgv_official import base_payload, build, synthetic_day, without_price_free_v  # noqa: E402

FIXTURE = HERE / 'fixtures' / 'qgv_official_vectors_v1.json'
NO_V = ('NYSE:ARE', 'NYSE:MMM')                 # GENERAL rows without a price-free V (Q·G reference rows)
CHEAP = 'NASDAQ:ALGN'                           # synthetic price near 0: price-dependent V reasons (public label)
TARGETS = ('TARGET:amd', 'TARGET:asml', 'TARGET:googl', 'TARGET:hanmi', 'TARGET:msft', 'TARGET:nvda')
VERIFIED_AT = '2026-10-13T22:46:00Z'
SYN = 7.25                                      # synthetic free value smuggled into typed fields (never a price)


def hexof(label):
    return hashlib.sha256(('qgv-official-vectors/' + label).encode()).hexdigest()


def derive(o):
    """Re-derive ranks, counts, digest and coverage after rows changed (production helpers only)."""
    rows = o['rows']
    for r in rows.values():
        r['rank'] = r['qg_reference_order'] = r['rank_row'] = None
    qo.assign_ranks(rows)
    pop = o['population']
    pop.update(row_count=len(rows), pooled_count=sum(1 for r in rows.values() if r['in_cross_section']),
               pooled_digest=qo.pooled_digest(rows), universe_code_count=sum(1 for k in rows if not k.startswith(qo.TARGET_PREFIX)))
    rejected = {}
    for k in sorted(rows):
        if not k.startswith(qo.TARGET_PREFIX) and rows[k]['price_status'] != iex_hist.SUPPLIED:
            rejected[rows[k]['price_status']] = rejected.get(rows[k]['price_status'], 0) + 1
    o['price_source']['rejected'] = rejected
    o['price_source']['supplied'] = sum(1 for k, r in rows.items() if not k.startswith(qo.TARGET_PREFIX) and r['price_status'] == iex_hist.SUPPLIED)
    o['coverage'] = qo.coverage(rows)
    return o


def mini():
    payload = without_price_free_v(base_payload(), NO_V)
    full, _ = build(payload, synthetic_day(payload, drop=list(NO_V), price_of={CHEAP: 1e-9}))
    rows = full['rows']
    data = [k for k, r in rows.items() if not k.startswith(qo.TARGET_PREFIX) and (r['state'] != 'NOT_AVAILABLE' or r['cik'])]
    empty = [k for k, r in sorted(rows.items()) if not k.startswith(qo.TARGET_PREFIX) and k not in data][:3]
    o = copy.deepcopy(full)
    o['rows'] = {k: rows[k] for k in sorted(set(data) | set(empty) | set(TARGETS))}
    # D-CV8: a TARGET row with data stands for its Universe issuer (synthetic CIKs aligned); D-CV9: a second share class of one
    # CIK outside the cross-section points to its primary row.
    o['rows']['TARGET:amd']['cik'] = o['rows']['NASDAQ:AMD']['cik']
    o['rows']['NASDAQ:GOOG'].update(cik=o['rows']['NASDAQ:GOOGL']['cik'], in_cross_section=False)
    o['rows'][empty[0]]['price_status'] = 'ODD_LOT_ONLY'
    derive(o)
    o['publication_id'] = 'qgvpub-' + hexof('publication')
    o['engine'].update(python_sha256=hexof('engine-python'), js_sha256=hexof('engine-js'), publisher_sha256=hexof('publisher'))
    o['population']['registry_sha256'] = hexof('registry')
    o['inputs'][0]['sha256'] = hexof('inputs')
    o['times']['verified_at'] = VERIFIED_AT
    qo.require_qgv_official(o)
    assert o['rows']['NASDAQ:AMD']['rank_row'] == 'TARGET:amd' and o['rows']['NASDAQ:GOOG']['rank_row'] == 'NASDAQ:GOOGL'
    assert o['coverage']['reasons'] and o['price_source']['rejected'] and any(r['rank'] for r in o['rows'].values())
    return o


def verdict(p, max_bytes=None):
    old = qo.MAX_BYTES
    try:
        if max_bytes is not None:
            qo.MAX_BYTES = max_bytes
        qo.require_qgv_official(p)
        return True, None
    except ValueError as e:
        return False, e.args[0]
    finally:
        qo.MAX_BYTES = old


def body_verdict(body, max_bytes=None):
    old = qo.MAX_BYTES
    try:
        if max_bytes is not None:
            qo.MAX_BYTES = max_bytes
        qo.parse(body)
        return True, None
    except ValueError as e:
        return False, e.args[0]
    finally:
        qo.MAX_BYTES = old


def intify(v):
    """What JSON.parse sees: a whole-number float is just a number (5.0 and 5 are one value)."""
    if isinstance(v, dict):
        return {k: intify(x) for k, x in v.items()}
    if isinstance(v, list):
        return [intify(x) for x in v]
    if type(v) is float and math.isfinite(v) and v.is_integer():
        return int(v)
    return v


def _same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def diff(a, b, path=()):
    """JSON ops turning a into b: {'path': [...], 'value': v} or {'path': [...], 'delete': true}; lists are replaced whole."""
    if type(a) is dict and type(b) is dict:
        ops = [{'path': [*path, k], 'delete': True} for k in a if k not in b]
        for k in b:
            ops += [{'path': [*path, k], 'value': b[k]}] if k not in a else diff(a[k], b[k], (*path, k))
        return ops
    return [] if _same(a, b) else [{'path': list(path), 'value': b}]


def apply(p, ops):
    p = copy.deepcopy(p)
    for op in ops:
        *head, last = op['path']
        t = p
        for k in head:
            t = t[k]
        if op.get('delete'):
            del t[last]
        else:
            t[last] = copy.deepcopy(op['value'])
    return p


def _integer_like_keys(v):
    if isinstance(v, dict):
        return any(k.isdigit() or _integer_like_keys(x) for k, x in v.items())
    return isinstance(v, list) and any(_integer_like_keys(x) for x in v)


# ---- case helpers (operate on a parsed copy of the base) ---------------------------------------------------------------
def ranked(o):
    return [k for _, k in sorted((r['rank'], k) for k, r in o['rows'].items() if r['rank'] is not None)]


def first(o):
    return o['rows'][sorted(o['rows'])[0]]


def empty_rows(o):
    return [k for k, r in sorted(o['rows'].items()) if r['cik'] is None and r['rank_row'] is None and not k.startswith(qo.TARGET_PREFIX)]


def unplaced_target(o):
    return next(k for k, r in sorted(o['rows'].items()) if k.startswith(qo.TARGET_PREFIX) and r['total'] is None and r['rank_row'] is None)


def nest(n):
    v = []
    for _ in range(n):
        v = [v]
    return v


def scored_row(o):
    return o['rows'][ranked(o)[0]]


def flip_cross(o, digest=True, count=True):
    k = empty_rows(o)[1]
    o['rows'][k]['in_cross_section'] = True
    if count:
        o['population']['pooled_count'] += 1
    if digest:
        o['population']['pooled_digest'] = qo.pooled_digest(o['rows'])


def swap(o, a, b):
    o['rows'][a]['rank'], o['rows'][b]['rank'] = o['rows'][b]['rank'], o['rows'][a]['rank']


def tie_rows(o):
    """Ties broken by ticker ('.' -> '-' in every position, then the key): copies of the two best rows under new codes / CIKs."""
    one, two = ranked(o)[:2]
    for code, src, cik in (('NYSE:AB.C', one, '0000003001'), ('NYSE:AB-D', one, '0000003002'), ('NYSE:Q.R.S', two, '0000003003'),
                           ('NYSE:Q.R-T', two, '0000003004')):
        o['rows'][code] = copy.deepcopy(o['rows'][src]) | {'cik': cik, 'in_cross_section': True}
    derive(o)
    assert [k for k in ranked(o)][:3] == ['NYSE:AB.C', 'NYSE:AB-D', one]
    assert ranked(o).index('NYSE:Q.R.S') + 1 == ranked(o).index('NYSE:Q.R-T')


def target_for_two_classes(o):
    """D-CV8 with a second share class: TARGET:googl (data, the GOOGL/GOOG CIK) stands for both codes in the publication (rank_row);
    GOOG keeps its own, higher scores (a copy of the best row), GOOGL its own. The TARGET v1 adapter maps like the device path."""
    cik = o['rows']['NASDAQ:GOOGL']['cik']
    o['rows']['TARGET:googl'] = copy.deepcopy(o['rows']['TARGET:amd']) | {'cik': cik}
    o['rows']['NASDAQ:GOOG'] = copy.deepcopy(scored_row(o)) | {'cik': cik, 'in_cross_section': False}
    derive(o)
    assert o['rows']['NASDAQ:GOOG']['rank_row'] == o['rows']['NASDAQ:GOOGL']['rank_row'] == 'TARGET:googl'
    assert o['rows']['NASDAQ:GOOG']['total'] > o['rows']['TARGET:googl']['total'] > o['rows']['NASDAQ:GOOGL']['total']


def target_live_unplaced(o):
    """TARGET:amd LIVE but with no total (axes below the weight rule): the issuer gets no rank, no rank_row on NASDAQ:AMD."""
    t = o['rows']['TARGET:amd']
    for a in ('Q', 'G', 'V'):
        t['axes'][a] = {'score': None, 'state': 'NOT_AVAILABLE', 'weight_available': 0.0, 'factors_available': 0, 'reason': 'AXIS_WEIGHT_INSUFFICIENT'}
    for f in t['factors']:
        t['factors'][f] = {'score': None, 'reason': 'SEC_FACTOR_NOT_AVAILABLE', 'basis': None}
    t.update(total=None, total_reason='AXIS_WEIGHT_INSUFFICIENT', value_trap_gate=False, v_excluded=None, q_industry_percentile=None)
    derive(o)
    assert t['state'] == 'LIVE' and t['rank_row'] is None and o['rows']['NASDAQ:AMD']['rank_row'] is None


def target_calc_mismatch(o):
    """TARGET:amd of another calc_version (7-day shard rotation): an NA row, not the CIK representative; NASDAQ:AMD ranks itself."""
    t = o['rows']['TARGET:amd']
    t.update(factors=qo._na_factors('CALC_VERSION_MISMATCH'), axes=qo._na_axes('CALC_VERSION_MISMATCH'), weights=None, type_weights=None,
             type_reason=None, selected_types=[], q_industry_percentile=None, value_trap_gate=False, v_excluded=None,
             flags=['CALC_VERSION_MISMATCH'], total=None, total_reason='CALC_VERSION_MISMATCH')
    derive(o)
    assert t['state'] == 'LIVE' and o['rows']['NASDAQ:AMD']['rank_row'] == 'NASDAQ:AMD'


def calc(o, value):
    o['calc_version'] = value
    o['inputs'][0]['calc_version'] = value


# Last-trade time (owner decision 2026-10-31, docs/qgv_official/LAST_TRADE_TIME_20261031.md). The base price basis day 2026-10-13 is
# on New York daylight time (UTC-4): 09:30 = 13:30Z, 13:00 = 17:00Z, 16:00 = 20:00Z. Synthetic times only.
CLOSE = '2026-10-13T20:00:00Z'
EARLY_CLOSE = '2026-10-13T17:00:00Z'
# Per V row, in key order: under 30 minutes before the close, exactly 30, at the open, then 15 minutes before for the rest.
TRADE_TIMES = ('2026-10-13T19:59:59Z', '2026-10-13T19:30:00Z', '2026-10-13T13:30:00Z')


def v_rows(o):
    """Keys of the rows with a V (finite V axis score, SUPPLIED): the only rows that may carry v_last_trade_at."""
    return [k for k, r in sorted(o['rows'].items()) if r['axes']['V']['score'] is not None and r['price_status'] == iex_hist.SUPPLIED]


def last_trades(o, close=CLOSE, times=TRADE_TIMES, rest='2026-10-13T19:45:00Z', only=None):
    o['times']['price_session_close_at'] = close
    for i, k in enumerate(v_rows(o)[:only]):
        o['rows'][k]['v_last_trade_at'] = times[i] if i < len(times) else rest


def one_trade(o, value, key=None, close=CLOSE):
    if close is not None:
        o['times']['price_session_close_at'] = close
    o['rows'][key or v_rows(o)[0]]['v_last_trade_at'] = value


def winter_day(o, close, trade):
    """The basis day moved to 2026-11-27 (New York standard time, UTC-5; the NYSE-scheduled early close): 13:00 = 18:00Z."""
    o['price_source'].update(basis_date='2026-11-27', requested_basis_date='2026-11-27')
    o['times']['price_basis_date'] = '2026-11-27'
    o['times']['price_session_close_at'] = close
    o['rows'][v_rows(o)[0]]['v_last_trade_at'] = trade


# (id, mutate, expected Python verdict (True or the error code), flags)
INVALID, FORBIDDEN, LARGE = 'OFFICIAL_INVALID', 'OFFICIAL_FORBIDDEN_KEY', 'OFFICIAL_TOO_LARGE'
CASES = [
    ('base_valid', lambda o: None, True, {}),
    # ported from tests/test_qgv_official.py test_validator_rejects (nan -> bodies)
    ('extra_top_key', lambda o: o.update(note='x'), INVALID, {}),
    ('price_key_nested', lambda o: first(o)['factors']['q_profitability'].update(price=1.0), FORBIDDEN, {}),
    ('detail_field', lambda o: first(o).update(detail={}), FORBIDDEN, {}),
    ('month_closes_anywhere', lambda o: o['coverage'].update(month_closes={}), FORBIDDEN, {}),
    ('row_extra_key', lambda o: first(o).update(ev=None), FORBIDDEN, {}),
    ('total_changed', lambda o: scored_row(o).update(total=scored_row(o)['total'] - 1e-9), INVALID, {}),
    ('v_axis_changed', lambda o: scored_row(o)['axes']['V'].update(score=1.0), INVALID, {}),
    ('rank_order', lambda o: swap(o, *ranked(o)[:2]), INVALID, {}),
    ('rank_gap', lambda o: o['rows'][ranked(o)[-1]].update(rank=999), INVALID, {}),
    ('coverage_changed', lambda o: o['coverage']['v'].update(full=o['coverage']['v']['full'] + 1), INVALID, {}),
    ('attribution_changed', lambda o: o['attribution'].update(text='IEX'), INVALID, {}),
    ('price_status_unknown', lambda o: first(o).update(price_status='CLOSE'), INVALID, {}),
    ('supply_not_met', lambda o: o['price_source']['supply'].update(met=False), INVALID, {}),
    ('basis_after_requested', lambda o: (o['price_source'].update(basis_date='2026-10-14'), o['times'].update(price_basis_date='2026-10-14')), INVALID, {}),
    # ported from test_validator_types_every_scalar (a synthetic free value instead of the canary)
    ('inputs_as_of_value', lambda o: o['inputs'][0].update(as_of=SYN), INVALID, {}),
    ('inputs_acquired_newest_value', lambda o: o['inputs'][0].update(acquired_newest=SYN), INVALID, {}),
    ('inputs_acquired_oldest_text', lambda o: o['inputs'][0].update(acquired_oldest=str(SYN)), INVALID, {}),
    ('inputs_calc_version_other', lambda o: o['inputs'][0].update(calc_version='qgv2-calc/2026-10-23.2'), INVALID, {}),
    ('times_inputs_as_of_value', lambda o: o['times'].update(inputs_as_of=SYN), INVALID, {}),
    ('times_inputs_as_of_other_clock', lambda o: o['times'].update(inputs_as_of='2026-10-13T00:00:00Z'), INVALID, {}),
    ('supply_eligible_value', lambda o: o['price_source']['supply'].update(eligible=SYN), INVALID, {}),
    ('supply_supplied_text', lambda o: o['price_source']['supply'].update(supplied='x'), INVALID, {}),
    ('supply_one_of_eligible_met', lambda o: o['price_source']['supply'].update(supplied=1, met=True), INVALID, {}),
    ('supply_eligible_zero', lambda o: o['price_source']['supply'].update(eligible=0, supplied=0), INVALID, {}),
    ('supply_supplied_over_eligible', lambda o: o['price_source']['supply'].update(supplied=o['price_source']['supply']['eligible'] + 1), INVALID, {}),
    ('supply_eligible_over_rows', lambda o: o['price_source']['supply'].update(eligible=400, supplied=400), INVALID, {}),
    ('supply_minimum_other', lambda o: o['price_source']['supply'].update(minimum_share=0.5), INVALID, {}),
    ('supply_bool_count', lambda o: o['price_source']['supply'].update(eligible=True), INVALID, {}),
    ('month_end_months_value', lambda o: o['price_source']['month_end'].update(months=SYN), INVALID, {}),
    ('month_end_months_negative', lambda o: o['price_source']['month_end'].update(months=-5), INVALID, {}),
    ('month_end_months_bool', lambda o: o['price_source']['month_end'].update(months=True), INVALID, {}),
    ('month_end_stamp_list', lambda o: o['price_source']['month_end'].update(stamp=[SYN, SYN]), INVALID, {}),
    ('month_end_stamp_short', lambda o: o['price_source']['month_end'].update(stamp='2026102'), INVALID, {}),
    ('month_end_store_other', lambda o: o['price_source']['month_end'].update(store='iex-monthend/2'), INVALID, {}),
    ('month_end_basis_other', lambda o: o['price_source']['month_end'].update(basis='ANYTHING'), INVALID, {}),
    ('currency_other', lambda o: o['price_source'].update(currency='EUR'), INVALID, {}),
    ('feed_other', lambda o: o['price_source'].update(feed='X'), INVALID, {}),
    ('price_source_supplied_value', lambda o: o['price_source'].update(supplied=SYN), INVALID, {}),
    ('engine_status_value', lambda o: o['engine'].update(status=SYN), INVALID, {}),
    ('weights_version_value', lambda o: o['weights'].update(weights_version=SYN), INVALID, {}),
    ('weights_profile_other', lambda o: o['weights'].update(profile_id='qgv-v2/balanced/gate-off'), INVALID, {}),
    ('weights_type_weights_value', lambda o: o['weights'].update(type_weights=SYN), INVALID, {}),
    ('config_type_config_value', lambda o: o['config_versions'].update(type_config=SYN), INVALID, {}),
    ('config_dcf_other', lambda o: o['config_versions'].update(dcf_parameters='dcf_parameters/v1-default'), INVALID, {}),
    ('type_scope_other', lambda o: o.update(type_scope=SYN), INVALID, {}),
    ('population_registry_value', lambda o: o['population'].update(registry_sha256=SYN), INVALID, {}),
    ('population_version_other', lambda o: o['population'].update(version=str(SYN)), INVALID, {}),
    ('population_pooled_digest_other', lambda o: o['population'].update(pooled_digest='0' * 64), INVALID, {}),
    ('calc_version_value', lambda o: calc(o, str(SYN)), INVALID, {}),
    ('calc_version_before_u7', lambda o: calc(o, 'qgv2-calc/2026-10-17.1'), INVALID, {}),
    ('row_acquired_at_text', lambda o: first(o).update(acquired_at=str(SYN)), INVALID, {}),
    ('row_selected_type_value', lambda o: first(o).update(selected_types=[str(SYN)]), INVALID, {}),
    # JS traps: forbidden keys (case-insensitive like Python str.lower) and the walk order
    ('top_key_price_is_a_key_set_error', lambda o: o.update(price=1), INVALID, {}),
    ('forbidden_mixed_case_nested', lambda o: scored_row(o)['factors']['v_fcf_yield'].update(Price=None), FORBIDDEN, {}),
    ('forbidden_upper_in_coverage', lambda o: o['coverage'].update(EV=0), FORBIDDEN, {}),
    ('forbidden_kelvin_sign', lambda o: first(o).update({'MARKET_CAP': None}), FORBIDDEN, {}),
    ('forbidden_hmac_in_engine', lambda o: o['engine'].update(Price_HMAC='x'), FORBIDDEN, {}),
    ('list_nested_too_deep', lambda o: first(o).update(flags=nest(40)), INVALID, {}),
    ('deep_list_before_forbidden_key', lambda o: first(o).update(flags=[nest(40), {'price': 1}]), INVALID, {}),
    ('forbidden_key_before_deep_list', lambda o: first(o).update(flags=[{'price': 1}, nest(40)]), FORBIDDEN, {}),
    # identity and clock formats (regex only, text order, like Python)
    ('cik_unicode_digits', lambda o: o['rows'][empty_rows(o)[0]].update(cik='٠' * 9 + '١'), INVALID, {}),
    ('cik_fullwidth_digits', lambda o: o['rows'][empty_rows(o)[0]].update(cik='０' * 10), INVALID, {}),
    ('cik_all_zero_valid', lambda o: o['rows'][empty_rows(o)[0]].update(cik='0000000000'), True, {}),
    ('cik_nine_digits', lambda o: o['rows'][empty_rows(o)[0]].update(cik='000000001'), INVALID, {}),
    ('fiscal_year_end_calendar_free_valid', lambda o: first(o).update(fiscal_year_end='2025-02-30'), True, {}),
    ('acquired_at_calendar_free_valid', lambda o: first(o).update(acquired_at='2026-99-99T99:99:99Z'), True, {}),
    ('inputs_as_of_offset', lambda o: (o['inputs'][0].update(as_of='2026-10-13T22:30:00+00:00'), o['times'].update(inputs_as_of='2026-10-13T22:30:00+00:00')), INVALID, {}),
    ('generated_at_offset', lambda o: o['times'].update(generated_at='2026-10-13T22:40:00+00:00'), INVALID, {}),
    ('clock_seven_fraction_digits', lambda o: o['times'].update(price_collected_to='2026-10-13T22:45:00.1234567Z'), INVALID, {}),
    ('clock_fraction_valid', lambda o: o['times'].update(price_collected_to='2026-10-13T22:45:00.123456Z'), True, {}),
    ('acquired_text_order_reversed', lambda o: o['inputs'][0].update(acquired_oldest='2026-10-13T22:30:00Z', acquired_newest='2026-10-13T22:30:00.5Z'), INVALID, {}),
    ('acquired_text_order_valid', lambda o: o['inputs'][0].update(acquired_oldest='2026-10-13T22:30:00.5Z', acquired_newest='2026-10-13T22:30:00Z'), True, {}),
    ('acquired_one_null', lambda o: o['inputs'][0].update(acquired_oldest=None), INVALID, {}),
    ('acquired_both_null_valid', lambda o: o['inputs'][0].update(acquired_oldest=None, acquired_newest=None), True, {}),
    # raw price-dependent engine codes: allowed in flags / basis / type_reason, refused as a reason (D-CV2 label)
    ('raw_price_code_in_flags_valid', lambda o: first(o).update(flags=['EV_NON_POSITIVE']), True, {}),
    ('raw_price_code_in_basis_valid', lambda o: scored_row(o)['factors']['v_fcf_yield'].update(basis='ROOT_NOT_CONVERGED'), True, {}),
    ('raw_price_code_in_type_reason_valid', lambda o: first(o).update(type_reason='NUMERIC_OVERFLOW'), True, {}),
    ('raw_price_code_in_factor_reason', lambda o: o['rows'][CHEAP]['factors']['v_earnings_yield'].update(reason='EV_NON_POSITIVE'), INVALID, {}),
    ('raw_price_code_in_axis_reason', lambda o: o['rows'][CHEAP]['axes']['V'].update(reason='ROOT_NOT_BRACKETED'), INVALID, {}),
    ('raw_price_code_in_total_reason', lambda o: o['rows'][unplaced_target(o)].update(total_reason='EV_NON_POSITIVE'), INVALID, {}),
    ('raw_price_code_in_source_reasons', lambda o: first(o).update(source_reason_codes=['NUMERIC_OVERFLOW']), INVALID, {}),
    ('empty_source_reason', lambda o: first(o).update(source_reason_codes=['']), INVALID, {}),
    ('factor_score_with_reason', lambda o: scored_row(o)['factors']['q_profitability'].update(reason='X'), INVALID, {}),
    ('score_over_100', lambda o: scored_row(o).update(q_industry_percentile=100.5), INVALID, {}),
    ('weight_available_over_1', lambda o: scored_row(o)['axes']['Q'].update(weight_available=1.5), INVALID, {}),
    ('factors_available_6', lambda o: scored_row(o)['axes']['Q'].update(factors_available=6), INVALID, {}),
    # verified_at: Python accepts null (the publisher sets it before writing); the JS reader only reads a verified file
    ('verified_at_null', lambda o: o['times'].update(verified_at=None), True, {'js_stricter': INVALID}),
    ('verified_at_other_clock_valid', lambda o: o['times'].update(verified_at='2026-10-14T00:00:00Z'), True, {}),
    # pooled population and its SHA-256 digest
    ('cross_section_flip_recounted_valid', lambda o: flip_cross(o), True, {}),
    ('cross_section_flip_stale_digest', lambda o: flip_cross(o, digest=False), INVALID, {}),
    ('cross_section_flip_stale_count', lambda o: flip_cross(o, count=False), INVALID, {}),
    ('universe_code_count_other', lambda o: o['population'].update(universe_code_count=o['population']['universe_code_count'] + 1), INVALID, {}),
    ('row_count_other', lambda o: o['population'].update(row_count=o['population']['row_count'] - 1), INVALID, {}),
    # ranks, rank_row (D-CV8 / D-CV9 / D11)
    ('rank_row_to_unplaced_row', lambda o: o['rows'][empty_rows(o)[0]].update(rank_row=empty_rows(o)[1]), INVALID, {}),
    ('rank_row_missing_on_placed', lambda o: scored_row(o).update(rank_row=None), INVALID, {}),
    ('rank_row_other_cik', lambda o: o['rows']['NASDAQ:GOOG'].update(rank_row=ranked(o)[0]), INVALID, {}),
    ('rank_row_unknown_key', lambda o: o['rows']['NASDAQ:GOOG'].update(rank_row='NYSE:ZZZZ'), INVALID, {}),
    ('rank_on_a_qg_only_row', lambda o: o['rows'][next(k for k, r in sorted(o['rows'].items()) if r['qg_reference_order'] == 1)].update(rank=len(ranked(o)) + 1, qg_reference_order=None), INVALID, {}),
    ('target_rank_row_valid_as_published', lambda o: None, True, {}),
    # TARGET rows the TARGET v1 adapter must map like the device path (target_v1_builder_node_test.js), all valid publications
    ('target_for_two_share_classes_valid', target_for_two_classes, True, {}),
    ('target_live_unplaced_valid', target_live_unplaced, True, {}),
    ('target_calc_mismatch_valid', target_calc_mismatch, True, {}),
    ('tie_dot_symbols_valid', tie_rows, True, {}),
    ('tie_dot_symbols_swapped', lambda o: (tie_rows(o), swap(o, 'NYSE:AB.C', 'NYSE:AB-D')), INVALID, {}),
    ('tie_every_dot_replaced_swapped', lambda o: (tie_rows(o), swap(o, 'NYSE:Q.R.S', 'NYSE:Q.R-T')), INVALID, {}),
    # recompute rules: exact equality, stop reasons skip it
    ('total_one_ulp_up', lambda o: scored_row(o).update(total=math.nextafter(scored_row(o)['total'], math.inf)), INVALID, {}),
    ('v_axis_state_changed', lambda o: scored_row(o)['axes']['V'].update(state='PARTIAL' if scored_row(o)['axes']['V']['state'] == 'READY' else 'READY'), INVALID, {}),
    ('row_weights_null', lambda o: scored_row(o).update(weights=None), INVALID, {}),
    ('row_gate_inconsistent', lambda o: scored_row(o).update(value_trap_gate=not scored_row(o)['value_trap_gate']), INVALID, {}),
    ('stop_reason_skips_recompute_valid', lambda o: o['rows'][unplaced_target(o)].update(total_reason='PRICE_IDENTITY_CONFLICT', value_trap_gate=True, weights=None), True, {}),
    ('calc_mismatch_skips_recompute_valid', lambda o: o['rows'][unplaced_target(o)].update(total_reason='CALC_VERSION_MISMATCH'), True, {}),
    ('stop_reason_with_v_score', lambda o: o['rows'][CHEAP]['axes']['V'].update(score=50.0) or o['rows'][CHEAP].update(total=None, total_reason='PRICE_IDENTITY_CONFLICT'), INVALID, {}),
    # calc_version: pattern and >= 2026-10-23.1 (calendar date)
    ('calc_version_later_day_valid', lambda o: calc(o, 'qgv2-calc/2026-11-01.1'), True, {}),
    ('calc_version_same_day_n2_valid', lambda o: calc(o, 'qgv2-calc/2026-10-23.2'), True, {}),
    ('calc_version_same_day_n0', lambda o: calc(o, 'qgv2-calc/2026-10-23.0'), INVALID, {}),
    ('calc_version_day_before', lambda o: calc(o, 'qgv2-calc/2026-10-22.9'), INVALID, {}),
    ('calc_version_not_a_date', lambda o: calc(o, 'qgv2-calc/2027-02-30.1'), INVALID, {}),
    ('calc_version_five_digit_n', lambda o: calc(o, 'qgv2-calc/2026-10-23.12345'), INVALID, {}),
    ('calc_version_leap_day_valid', lambda o: calc(o, 'qgv2-calc/2028-02-29.1'), True, {}),
    ('schema_other', lambda o: o.update(schema='qgv-official/2'), INVALID, {}),
    ('state_other', lambda o: o.update(state='DRAFT'), INVALID, {}),
    ('publication_id_upper_hex', lambda o: o.update(publication_id=o['publication_id'].upper().replace('QGVPUB', 'qgvpub')), INVALID, {}),
    ('rows_empty', lambda o: o.update(rows={}), INVALID, {}),
    ('row_key_lower_case', lambda o: o['rows'].update({'nyse:zzz': o['rows'].pop(empty_rows(o)[0])}), INVALID, {}),
    ('rejected_lists_supplied', lambda o: o['price_source']['rejected'].update(SUPPLIED=1), INVALID, {}),
    ('rejected_count_other', lambda o: o['price_source']['rejected'].update(NO_IEX_TRADE=o['price_source']['rejected']['NO_IEX_TRADE'] + 1), INVALID, {}),
    ('coverage_bool_as_int', lambda o: o['coverage']['target'].update(met=1 if o['coverage']['target']['met'] else 0), INVALID, {}),
    ('coverage_reasons_order', lambda o: o['coverage'].update(reasons=list(reversed(o['coverage']['reasons']))), INVALID, {}),
    ('attribution_extra_key', lambda o: o['attribution'].update(note='x'), INVALID, {}),
    ('label_ko_other', lambda o: o['attribution'].update(label_ko='IEX'), INVALID, {}),
    # last-trade time: two optional keys, exactly these (owner decision 2026-10-31); a file without them is the base above
    ('last_trade_session_close_only_valid', lambda o: o['times'].update(price_session_close_at=CLOSE), True, {}),
    ('last_trade_every_v_row_valid', last_trades, True, {}),
    ('last_trade_one_v_row_valid', lambda o: last_trades(o, only=1), True, {}),
    ('last_trade_early_close_valid', lambda o: last_trades(o, close=EARLY_CLOSE, times=('2026-10-13T16:59:59Z', '2026-10-13T16:30:00Z'), rest='2026-10-13T13:30:00Z'), True, {}),
    ('last_trade_winter_early_close_valid', lambda o: winter_day(o, '2026-11-27T18:00:00Z', '2026-11-27T17:59:59Z'), True, {}),
    ('last_trade_winter_regular_close_valid', lambda o: winter_day(o, '2026-11-27T21:00:00Z', '2026-11-27T14:30:00Z'), True, {}),
    ('last_trade_without_session_close', lambda o: one_trade(o, '2026-10-13T19:00:00Z', close=None), INVALID, {}),
    ('last_trade_on_a_supplied_row_without_v', lambda o: one_trade(o, '2026-10-13T19:00:00Z', key='NASDAQ:AAPL'), INVALID, {}),
    ('last_trade_on_a_no_trade_row', lambda o: one_trade(o, '2026-10-13T19:00:00Z', key='NYSE:ARE'), INVALID, {}),
    ('last_trade_null', lambda o: one_trade(o, None), INVALID, {}),
    ('last_trade_number', lambda o: one_trade(o, SYN), INVALID, {}),
    ('last_trade_fraction', lambda o: one_trade(o, '2026-10-13T19:00:00.5Z'), INVALID, {}),
    ('last_trade_offset', lambda o: one_trade(o, '2026-10-13T15:00:00-04:00'), INVALID, {}),
    ('last_trade_before_open', lambda o: one_trade(o, '2026-10-13T13:29:59Z'), INVALID, {}),
    ('last_trade_at_close', lambda o: one_trade(o, CLOSE), INVALID, {}),
    ('last_trade_after_close', lambda o: one_trade(o, '2026-10-13T20:30:00Z'), INVALID, {}),
    ('last_trade_after_early_close', lambda o: one_trade(o, '2026-10-13T17:30:00Z', close=EARLY_CLOSE), INVALID, {}),
    ('last_trade_other_day', lambda o: one_trade(o, '2026-10-12T19:00:00Z'), INVALID, {}),
    ('last_trade_hour_24', lambda o: one_trade(o, '2026-10-13T24:00:00Z'), INVALID, {}),
    ('last_trade_second_60', lambda o: one_trade(o, '2026-10-13T19:59:60Z'), INVALID, {}),
    ('last_trade_other_spelling', lambda o: scored_row(o).update(v_last_trade='2026-10-13T19:00:00Z') or o['times'].update(price_session_close_at=CLOSE), INVALID, {}),
    ('session_close_null', lambda o: o['times'].update(price_session_close_at=None), INVALID, {}),
    ('session_close_number', lambda o: o['times'].update(price_session_close_at=SYN), INVALID, {}),
    ('session_close_15h', lambda o: o['times'].update(price_session_close_at='2026-10-13T19:00:00Z'), INVALID, {}),
    ('session_close_with_seconds', lambda o: o['times'].update(price_session_close_at='2026-10-13T20:00:01Z'), INVALID, {}),
    ('session_close_fraction', lambda o: o['times'].update(price_session_close_at='2026-10-13T20:00:00.0Z'), INVALID, {}),
    ('session_close_standard_time_on_a_daylight_day', lambda o: o['times'].update(price_session_close_at='2026-10-13T21:00:00Z'), INVALID, {}),
    ('session_close_other_day', lambda o: o['times'].update(price_session_close_at='2026-10-12T20:00:00Z'), INVALID, {}),
    ('session_close_winter_daylight_spelling', lambda o: winter_day(o, '2026-11-27T17:00:00Z', '2026-11-27T16:00:00Z'), INVALID, {}),
    ('times_unknown_key', lambda o: o['times'].update(price_session_open_at='2026-10-13T13:30:00Z'), INVALID, {}),
]


def cases(base, base_len, estimate):
    out = []
    for cid, fn, expected, flags in CASES:
        p = copy.deepcopy(base)
        fn(p)
        ops = diff(base, p)
        assert _same(apply(base, ops), p), cid
        assert not any(_integer_like_keys(op.get('value')) for op in ops), cid      # JS lists integer-like keys first
        valid, code = verdict(p)
        assert (valid if expected is True else code == expected), (cid, valid, code)
        assert verdict(intify(p)) == (valid, code), cid                           # the verdict does not hang on 5 vs 5.0
        case = {'id': cid, 'ops': ops, 'valid': valid, 'code': code}
        if 'js_stricter' in flags:
            assert valid
            case['js_stricter'] = flags['js_stricter']
        out.append(case)
    # size: Python's canonical length L; the JS reader counts whole floats as ints, so its estimate E <= L is a lower bound
    for cid, max_bytes, expected in (('size_cap_at_canonical_length_valid', base_len, True),
                                     ('size_cap_below_estimate', estimate - 1, LARGE)):
        valid, code = verdict(copy.deepcopy(base), max_bytes)
        assert (valid if expected is True else code == expected), cid
        out.append({'id': cid, 'ops': [], 'max_bytes': max_bytes, 'valid': valid, 'code': code})
    bad = copy.deepcopy(base)
    bad['state'] = 'DRAFT'
    assert verdict(bad, estimate - 1) == (False, INVALID)                      # every other rule comes before the size
    out.append({'id': 'size_and_invalid_is_invalid', 'ops': diff(base, bad), 'max_bytes': estimate - 1, 'valid': False, 'code': INVALID})
    return out


def bodies(base_text):
    label = json.dumps(iex_hist.LABEL_KO)                                     # as it appears in base_text (\u escapes)
    assert label in base_text and '"months":' in base_text and '"cik":"0000001000"' in base_text
    months = '"months":%d' % json.loads(base_text)['price_source']['month_end']['months']
    specs = [
        ('base_body_valid', {}, True, None),
        ('trailing_whitespace_valid', {'suffix': '\n \t\r\n'}, True, None),
        ('leading_whitespace_valid', {'prefix_hex': '200a'}, True, None),
        ('raw_utf8_label_valid', {'find': label, 'replace_hex': ('"' + iex_hist.LABEL_KO + '"').encode().hex()}, True, None),
        ('utf8_bom_prefix', {'prefix_hex': 'efbbbf'}, INVALID, None),
        ('invalid_utf8_byte', {'find': label, 'replace_hex': '22ff22'}, INVALID, None),
        ('overlong_utf8', {'find': label, 'replace_hex': '22c0af22'}, INVALID, None),
        ('utf8_surrogate', {'find': label, 'replace_hex': '22eda08022'}, INVALID, None),
        ('duplicate_top_key', {'find': '{"attribution":', 'replace': '{"kind":"QGV_OFFICIAL","attribution":'}, INVALID, None),
        ('duplicate_row_key', {'find': '"cik":"0000001000"', 'replace': '"cik":"0000001000","cik":"0000001000"'}, INVALID, None),
        ('duplicate_key_by_escape', {'find': '{"attribution":', 'replace': '{"\\u006bind":"QGV_OFFICIAL","attribution":'}, INVALID, None),
        ('nan_literal', {'find': months, 'replace': '"months":NaN'}, INVALID, None),
        ('infinity_literal', {'find': months, 'replace': '"months":Infinity'}, INVALID, None),
        ('overflow_exponent', {'find': months, 'replace': '"months":1e400'}, INVALID, None),
        ('trailing_comma', {'find': months, 'replace': months + ','}, INVALID, None),
        ('single_quotes', {'find': months, 'replace': "'months':5"}, INVALID, None),
        ('empty_body', {'whole': ''}, INVALID, None),
        ('null_body', {'whole': 'null'}, INVALID, None),
        ('array_body', {'whole': '[]'}, INVALID, None),
        ('two_documents', {'suffix': '{}'}, INVALID, None),
        ('share_exponent_spelling_valid', {'find': '"share":0.9}', 'replace': '"share":9e-1}'}, True, None),
        ('weight_int_spelling_valid', {'find': '"weight_available":1.0', 'replace': '"weight_available":1'}, True, None),
        ('months_float_spelling', {'find': months, 'replace': months + '.0'}, INVALID, 'INT_FLOAT_SPELLING'),
        ('pad_over_cap', {'pad_to': qo.MAX_BYTES + 1}, INVALID, None),
    ]
    out = []
    raw = base_text.encode()
    for bid, edit, expected, divergence in specs:
        body = make_body(raw, edit)
        valid, code = body_verdict(body)
        assert (valid if expected is True else code == expected), (bid, valid, code)
        out.append(dict(edit, id=bid, valid=valid, code=code, **({'divergence': divergence} if divergence else {})))
    for bid, max_bytes in (('body_cap_equal_length_valid', len(raw)), ('body_cap_one_below', len(raw) - 1)):
        valid, code = body_verdict(raw, max_bytes)
        out.append({'id': bid, 'max_bytes': max_bytes, 'valid': valid, 'code': code})
    assert out[-2]['valid'] and out[-1]['code'] == INVALID                       # an oversized body is INVALID, not TOO_LARGE
    return out


def make_body(raw, edit):
    if 'whole' in edit:
        return edit['whole'].encode()
    body = raw
    if 'find' in edit:
        find = edit['find'].encode()
        i = body.index(find)
        rep = bytes.fromhex(edit['replace_hex']) if 'replace_hex' in edit else edit['replace'].encode()
        body = body[:i] + rep + body[i + len(find):]
    if 'prefix_hex' in edit:
        body = bytes.fromhex(edit['prefix_hex']) + body
    if 'suffix' in edit:
        body = body + edit['suffix'].encode()
    if 'pad_to' in edit:
        body = body + b' ' * (edit['pad_to'] - len(body))
    return body


def constants():
    return {
        'schema': qo.SCHEMA, 'kind': qo.KIND, 'filename': qo.FILENAME, 'max_bytes': qo.MAX_BYTES, 'target_prefix': qo.TARGET_PREFIX,
        'top_keys': list(qo.TOP_KEYS), 'row_keys': list(qo.ROW_KEYS), 'factor_keys': list(qo.FACTOR_KEYS),
        'axis_keys': list(qo.AXIS_KEYS), 'forbidden_keys': sorted(qo.FORBIDDEN_KEYS), 'price_dependent': sorted(qo.PRICE_DEPENDENT),
        'price_dependent_public': qo.PRICE_DEPENDENT_PUBLIC, 'stop_reasons': list(qo.STOP_REASONS),
        'target_tickers': dict(sorted(qo.TARGET_TICKERS.items())), 'status_codes': list(iex_hist.STATUS_CODES), 'supplied': iex_hist.SUPPLIED,
        'attribution': qo.attribution(),
        'price_source': {'provider': iex_hist.PROVIDER, 'feed': ' '.join(iex_hist.FEED), 'basis_kind': iex_hist.BASIS_KIND,
                         'adjustment_basis': iex_hist.ADJUSTMENT_BASIS, 'currency': iex_hist.CURRENCY},
        'month_end': {'store': iex_monthend.SCHEMA, 'basis': qo.MONTHEND_BASIS}, 'max_months': qo.MAX_MONTHS,
        'supply_min': qo.SUPPLY_MIN, 'v_target_share': qo.V_TARGET_SHARE, 'population_version': qo.population_version(),
        'weights': qo.weights_block(), 'config_versions': qo.config_versions_block(), 'type_scope': qgv_v2.TYPE_SCOPE,
        'engine': {'version': qgv_v2.VERSION, 'status': qgv_v2.STATUS}, 'calc_version_pattern': vf.CALC_VERSION_PATTERN,
        'share_basis_since': [vf.SHARE_BASIS_FACTOR_SINCE[0].isoformat(), vf.SHARE_BASIS_FACTOR_SINCE[1]],
        'inputs_file': qo.qi.FILE, 'factors': list(qgv_v2.FACTORS), 'pillars': list(qgv_v2.PILLARS),
        'v_factors': list(qgv_v2.WEIGHTS['V']), 'min_axis_weight': qgv_v2.MIN_AXIS_WEIGHT,
        'times_keys': list(qo.TIMES_KEYS), 'times_optional_keys': list(qo.TIMES_OPTIONAL_KEYS), 'row_optional_keys': list(qo.ROW_OPTIONAL_KEYS),
        'session_open_minutes': qo.SESSION_OPEN_NY[0] * 60 + qo.SESSION_OPEN_NY[1],
        'session_close_minutes': [h * 60 + m for h, m in qo.SESSION_CLOSES_NY], 'last_trade_note_minutes': qo.LAST_TRADE_NOTE_MINUTES,
    }


DIGEST_KEYS = ([], ['NYSE:A'], ['NYSE:B', 'NYSE:A', 'TARGET:amd'], ['NASDAQ:BRK.B', 'NASDAQ:BRK-A'])
LENGTH_VALUES = (1e-05, 1.5e-07, 0.0001, 0.5, 123.456, 1.5e16, 1.2345e100, -2.5e-07, 0.1, 1 / 3, -1 / 7, 12345678901234.5,
                 'IEX 마지막 체결가 기준(공식 종가 아님)', 'a"b\\c\n\t\r\x08\x0c', '\x00\x1f\x7f~ ', '\U0001F600', '',
                 {'k': [1, 2, None, True, False], 'x': {'y': -1}, '"': 0.25}, [], {})


def build_vectors():
    base = mini()
    text = qo._canonical(base).decode()
    assert text.isascii()
    parsed = json.loads(text)
    assert _same(parsed, base) and qo.parse(text.encode())['publication_id'] == base['publication_id']
    base_len, estimate = len(text), len(qo._canonical(intify(parsed)))
    assert estimate <= base_len
    return {
        'schema': 'qgv-official-vectors/1', 'synthetic': True,
        'note': 'Synthetic publication (made-up prices never written); hashes are fixed synthetic hex (format-only fields).',
        'base_text': text, 'base_canonical_length': base_len, 'base_estimate_length': estimate,
        'delete_marker': {'delete': True},
        'cases': cases(parsed, base_len, estimate),
        'bodies': bodies(text),
        'digest_cases': [{'keys': k, 'sha256': hashlib.sha256('\n'.join(sorted(k)).encode()).hexdigest()} for k in DIGEST_KEYS],
        'canonical_length_cases': [{'value': v, 'length': len(qo._canonical(v))} for v in LENGTH_VALUES],
        'constants': constants(),
    }


def render(vectors=None) -> str:
    return json.dumps(vectors or build_vectors(), indent=1, sort_keys=True, ensure_ascii=True) + '\n'


def main(argv):
    text = render()
    if '--write' in argv:
        FIXTURE.write_text(text)
        print('QGV_OFFICIAL_VECTORS_WRITTEN cases=%d' % text.count('"id":'))
        return 0
    ok = FIXTURE.is_file() and FIXTURE.read_text() == text
    print('QGV_OFFICIAL_VECTORS_OK' if ok else 'QGV_OFFICIAL_VECTORS_STALE')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
