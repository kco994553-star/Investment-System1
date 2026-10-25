"""Central QGV publication (qgv/qgv_official.py, tools/qgv_official_publish.py, tools/qgv_official_js_check.js).

End to end on a SYNTHETIC universe: the strict-valid sec-qgv2 vector base (tests/fixtures/sec_qgv2_vectors_v1.json of calc_version
2026-10-23.1, expanded to the 504 Universe codes with empty records) + made-up IEX prices and month-end trades. The F_k
(share_basis_factor, rule V-PRICE-BASIS) values are the fixture's own (1.0 on every item) or set by `with_fk` in the production
shape; every payload goes through the production reader `sec_qgv2.require_qgv2` (no simulated reader). Every price is
synthetic; the canary value must never appear in any output, file or exception.
"""
import builtins
import copy
import datetime as dt
import importlib.util
import json
import math
import re
from pathlib import Path

import pytest

from investment_system.providers import iex_hist, iex_monthend
from investment_system.qgv import qgv_official as qo
from investment_system.qgv import qgv_v2
from investment_system.qgv import v2_factors as vf
from investment_system.universe import sec_qgv2
from investment_system.universe.sec_universe_shares import universe_codes

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('qgv_official_publish', ROOT / 'tools/qgv_official_publish.py')
tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tool)

NOW = dt.datetime(2026, 10, 13, 22, 40, tzinfo=dt.timezone.utc)
KEY = b'test-only-hmac-key-0123456789abcdef'
CANARY = 4321.0987          # synthetic price that must never leak


def base_payload():
    d = json.loads((ROOT / 'tests/fixtures/sec_qgv2_vectors_v1.json').read_text())
    b = d['base']
    b['records'] = {c: b['records'].get(c) or sec_qgv2.empty_record() for c in universe_codes()}
    sec_qgv2.require_qgv2(b)
    return b


def _all_rows(payload):
    return list(payload['records'].items()) + [(qo.TARGET_PREFIX + t, r) for t, r in payload['target'].items()]


def with_fk(payload, factor, reason=None, codes=None, items=None):
    """V-PRICE-BASIS in the production shape (#393, sec_qgv2._share_basis_entry): `share_basis_factor` on every
    ebit_per_share_history item, `share_basis_factor_reason` (one of v2_factors.SHARE_BASIS_REASONS) only when the factor is null.
    `codes`: rows to change (default all); `items`: fiscal_year_end values to change (default all). Checked by require_qgv2."""
    p = copy.deepcopy(payload)
    for code, r in _all_rows(p):
        if codes is not None and code not in codes:
            continue
        for h in (r.get('v_inputs_v2') or {}).get('ebit_per_share_history') or []:
            if items is not None and h['fiscal_year_end'] not in items:
                continue
            h['share_basis_factor'] = factor
            if factor is None:
                h['share_basis_factor_reason'] = reason
            else:
                h.pop('share_basis_factor_reason', None)
    sec_qgv2.require_qgv2(p)
    return p


def pre_u7(payload):
    """The same file as published before #393 (calc_version 2026-10-17.1: rows carry exactly fiscal_year_end, value)."""
    p = copy.deepcopy(payload)
    old = 'qgv2-calc/2026-10-17.1'
    p['calc_version'] = old
    for _, r in _all_rows(p):
        if r.get('calc_version'):
            r['calc_version'] = old
        for h in (r.get('v_inputs_v2') or {}).get('ebit_per_share_history') or []:
            h.pop('share_basis_factor', None)
            h.pop('share_basis_factor_reason', None)
    sec_qgv2.require_qgv2(p)
    return p


def synthetic_day(payload, *, drop=(), canary_key=None, price_of=None):
    ctx = qo.prepare(payload, NOW)
    quotes, status = {}, {}
    for i, (k, code) in enumerate(sorted(ctx['keys'].items())):
        if code is None:
            status[k] = 'PRICE_SYMBOL_UNMAPPED'
        elif k in drop:
            status[k] = 'NO_IEX_TRADE'
        else:
            status[k] = 'SUPPLIED'
            price = CANARY if k == canary_key else (price_of or {}).get(k, 20 + (i * 37) % 300 + 0.25)
            quotes[k] = {'price': price, 'currency': 'USD'}
    t = NOW + dt.timedelta(minutes=1)
    return iex_hist.IexDay('2026-10-13', '2026-10-13', quotes, status, t, t + dt.timedelta(minutes=4), {})


def synthetic_months(payload):
    months = {}
    for code, r in payload['records'].items():
        for j, h in enumerate((r.get('v_inputs_v2') or {}).get('ebit_per_share_history') or []):
            m, sym = h['fiscal_year_end'][:7], code.split(':', 1)[1]
            months.setdefault(m, {'date': m.replace('-', '') + '28', 'codes': {}, 'symbols': {}})
            months[m]['codes'][code] = sym
            months[m]['symbols'][sym] = {'status': 'ROUND', 'price_e4': (30 + 7 * j + len(sym)) * 10000, 'ts_ns': 1, 'n': 1}
    return months


def build(payload, day=None, months=None):
    raw = json.dumps(payload).encode()
    return qo.build(payload, qo.sha256_bytes(raw), now=NOW, day=day or synthetic_day(payload),
                    months=synthetic_months(payload) if months is None else months, monthend_stamp='20261023', hmac_key=KEY,
                    generated_at=NOW)


def _keys_anywhere(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _keys_anywhere(v)
    elif isinstance(value, list):
        for v in value:
            yield from _keys_anywhere(v)


# ---- end to end -----------------------------------------------------------------------------------------------------
def test_fixture_is_the_calc_version_with_share_basis_factor():
    payload = base_payload()
    assert payload['calc_version'] == vf.CALC_VERSION == 'qgv2-calc/2026-10-23.1' and vf.carries_share_basis(payload['calc_version'])
    items = [h for _, r in _all_rows(payload) for h in (r.get('v_inputs_v2') or {}).get('ebit_per_share_history') or []]
    assert items and all(h['share_basis_factor'] == 1.0 and 'share_basis_factor_reason' not in h for h in items)
    # the shapes the cv-core branch once simulated are rejected by the production reader: a reason key next to a factor, a
    # reason outside v2_factors.SHARE_BASIS_REASONS
    for reason_key, factor, reason in (('share_basis_factor_reason', 1.0, None), ('share_basis_factor_reason', None, 'SPLIT_RATIO_UNVERIFIED')):
        bad = copy.deepcopy(payload)
        item = next(h for _, r in _all_rows(bad) for h in (r.get('v_inputs_v2') or {}).get('ebit_per_share_history') or [])
        item['share_basis_factor'], item[reason_key] = factor, reason
        with pytest.raises(ValueError):
            sec_qgv2.require_qgv2(bad)


def test_end_to_end_publication_is_valid_complete_and_price_free():
    payload = base_payload()
    canary_key = 'NYSE:ABT'
    official, internal = build(payload, synthetic_day(payload, canary_key=canary_key))
    qo.require_qgv_official(official)
    official['times']['verified_at'] = qo.iso(NOW)
    body = qo.encode(official)
    assert len(body) <= qo.MAX_BYTES
    assert set(official['rows']) == set(payload['records']) | {'TARGET:' + t for t in payload['target']}
    assert not set(_keys_anywhere(official)) & qo.FORBIDDEN_KEYS
    text = body.decode()
    assert repr(CANARY) not in text and '4321.09' not in text
    assert internal['quotes'][canary_key]['price'] == CANARY            # it was used (RAM), only never published
    assert official['calc_version'] == payload['calc_version'] and 'v_calc_version' not in official
    assert official['attribution'] == {'text': iex_hist.ATTRIBUTION, 'terms_url': iex_hist.TERMS_URL, 'label_ko': 'IEX 마지막 체결가 기준(공식 종가 아님)'}
    assert official['price_source']['basis_date'] == official['times']['price_basis_date'] == '2026-10-13'
    assert official['coverage']['ranked'] > 0
    # V4 with the fixture's F_k = 1.0: month close = raw month-end trade / 1.0, computed where the engine can (non-cyclical
    # GENERAL rows); cyclical rows keep the engine's NORMALIZED_HISTORY_NOT_AVAILABLE; no month is left out for F_k
    months = synthetic_months(payload)
    scored = [k for k, r in official['rows'].items() if r['factors']['v_vs_own_history']['score'] is not None]
    assert scored and all(official['rows'][k]['price_status'] == 'SUPPLIED' for k in scored)
    for k, q in internal['quotes'].items():
        for m, close in q.get('month_closes', {}).items():
            assert close == months[m]['symbols'][qo.listing_code(k).split(':', 1)[1]]['price_e4'] / 10000 / 1.0   # TARGET: its US listing
    v4 = {r['factors']['v_vs_own_history']['reason'] for r in official['rows'].values()
          if r['price_status'] == 'SUPPLIED' and r['profile'] == 'GENERAL' and r['factors']['v_vs_own_history']['score'] is None}
    assert v4 == {'NORMALIZED_HISTORY_NOT_AVAILABLE'}
    # the same inputs give the same id (no clock inside); another price set gives another id
    assert build(payload, synthetic_day(payload, canary_key=canary_key))[0]['publication_id'] == official['publication_id']
    assert build(payload)[0]['publication_id'] != official['publication_id']


def test_share_basis_factor_feeds_v4_raw_divided_by_fk():
    payload = with_fk(base_payload(), 2.0)
    official, internal = build(payload)
    qo.require_qgv_official(official)
    scored = [r for r in official['rows'].values() if r['factors']['v_vs_own_history']['score'] is not None]
    assert scored
    code = next(k for k, q in internal['quotes'].items() if q.get('month_closes') and not k.startswith(qo.TARGET_PREFIX))
    months = synthetic_months(payload)
    for m, close in internal['quotes'][code]['month_closes'].items():
        assert close == months[m]['symbols'][code.split(':', 1)[1]]['price_e4'] / 10000 / 2.0
    # F_k null (the production reasons) on every item: every month left out, V4 NA with the item's reason, never 1.0 or 0
    for reason in vf.SHARE_BASIS_REASONS:
        off0, internal0 = build(with_fk(base_payload(), None, reason))
        qo.require_qgv_official(off0)
        assert not any(q.get('month_closes') for q in internal0['quotes'].values())
        assert all(r['factors']['v_vs_own_history']['score'] is None for r in off0['rows'].values())
        reasons = {r['factors']['v_vs_own_history']['reason'] for r in off0['rows'].values()
                   if r['price_status'] == 'SUPPLIED' and r['profile'] == 'GENERAL'}
        assert reasons == {reason, 'NORMALIZED_HISTORY_NOT_AVAILABLE'}
    # one null item of one row: only that month is left out, the row keeps V4 from the other four
    one = with_fk(base_payload(), None, vf.SPLIT_TIMING_UNCONFIRMED, codes={code}, items={'2021-12-31'})
    off1, internal1 = build(one)
    assert sorted(internal1['quotes'][code]['month_closes']) == ['2022-12', '2023-12', '2024-12', '2025-12']
    assert off1['rows'][code]['factors']['v_vs_own_history']['score'] is not None


def test_a_file_before_calc_version_2026_10_23_1_is_not_published_from():
    """U7 rides on the one calc_version bump (D-CV7 (b), D1 (ii)): a pre-#393 file (no F_k) is NOT_RUN, never a V4-less copy."""
    payload = pre_u7(base_payload())
    with pytest.raises(qo.OfficialError) as e:
        build(payload)
    assert (e.value.state, e.value.code) == ('NOT_RUN', 'SEC_QGV2_CALC_VERSION_BEFORE_U7')
    # the month-end reader itself still leaves an F_k-less month out with the fixed reason (never 1.0)
    hist = payload['records']['NYSE:ABT']['v_inputs_v2']['ebit_per_share_history']
    closes, left = iex_monthend.month_closes('NYSE:ABT', hist, synthetic_months(payload))
    assert closes == {} and {r for _, r in left} == {iex_monthend.FK_MISSING}


def test_price_dependent_reasons_are_grouped_and_rejected_raw():
    payload = base_payload()
    rows = payload['records']
    code = next(c for c, r in sorted(rows.items()) if r['state'] == 'LIVE' and r['profile'] == 'GENERAL'
                and (r['v_inputs_v2'].get('cash_and_equivalents') or {}).get('value', 0) > ((r['v_inputs_v2'].get('total_debt') or {}).get('value') or 0) + 1)
    official, internal = build(payload, synthetic_day(payload, price_of={code: 1e-9}))
    assert internal['results'][code]['factors']['v_earnings_yield']['reason'] == 'EV_NON_POSITIVE'
    assert official['rows'][code]['factors']['v_earnings_yield']['reason'] == qo.PRICE_DEPENDENT_PUBLIC
    text = json.dumps(official)
    for raw in qo.PRICE_DEPENDENT:
        assert raw not in text
    bad = copy.deepcopy(official)
    bad['rows'][code]['factors']['v_earnings_yield']['reason'] = 'EV_NON_POSITIVE'
    with pytest.raises(ValueError, match='OFFICIAL_INVALID'):
        qo.require_qgv_official(bad)


FIXTURE_GENERAL = ('NASDAQ:ABNB', 'NASDAQ:ADBE', 'NASDAQ:AKAM', 'NASDAQ:ALGN', 'NASDAQ:AMD', 'NASDAQ:LNT', 'NYSE:A', 'NYSE:ABBV',
                   'NYSE:ABT', 'NYSE:ACN', 'NYSE:AES', 'NYSE:AFL', 'NYSE:ALB', 'NYSE:ALLE', 'NYSE:AOS', 'NYSE:APD', 'NYSE:ARE', 'NYSE:MMM')


def without_price_free_v(payload, codes):
    """GENERAL rows that keep a USD V-input block but cannot reach 50% of the V weight without a price: cash and FCF null (no
    earnings/FCF yield, no industry factor, no expectation check; own history alone is 15%)."""
    p = copy.deepcopy(payload)
    for code in codes:
        v = p['records'][code]['v_inputs_v2']
        v['cash_and_equivalents'], v['fcf'] = None, None
    sec_qgv2.require_qgv2(p)
    return p


def test_price_dependent_codes_sit_in_fixed_factor_slots_known_residual():
    """KNOWN RESIDUAL (review 2026-10-24, owner decision pending; design section 4-4 note, AUDIT.md section 10-6, PR-B). D-CV2 (b)
    changes the label, not the information: each raw price-dependent code appears only in fixed factor slots, so the public
    slot + PRICE_DEPENDENT_NOT_COMPUTABLE gives the raw code back one to one, and with it a price bound computable from public
    inputs (EV <= 0: price <= (cash - debt) / shares; no reverse-DCF root: price outside the public DCF bracket). The V axis and
    rank vs qg_reference_order show the same fact without any reason. Synthetic prices only."""
    payload = base_payload()
    ctx = qo.prepare(payload, NOW)
    code = next(c for c, r in sorted(payload['records'].items()) if r['state'] == 'LIVE' and r['profile'] == 'GENERAL'
                and (r['v_inputs_v2'].get('cash_and_equivalents') or {}).get('value', 0) > ((r['v_inputs_v2'].get('total_debt') or {}).get('value') or 0) + 1)
    v = ctx['companies'][code]['v_inputs']
    bound = (v['cash'] - v['total_debt']) / v['diluted_shares']           # public inputs only
    slots = {}
    for scale in (1e-6, 0.5, 0.9, 1.1, 2.0, 1e3, 1e9):
        official, internal = build(payload, synthetic_day(payload, price_of={code: scale * bound}))
        for key, res in internal['results'].items():
            for f in qgv_v2.WEIGHTS['V']:
                raw = res['factors'][f]['reason']
                if raw in qo.PRICE_DEPENDENT:
                    slots.setdefault(raw, set()).add(f)
                    assert official['rows'][key]['factors'][f]['reason'] == qo.PRICE_DEPENDENT_PUBLIC
        row = official['rows'][code]
        below = scale * bound <= bound
        assert (row['factors']['v_earnings_yield']['reason'] == qo.PRICE_DEPENDENT_PUBLIC) == below
    assert slots['EV_NON_POSITIVE'] == {'v_earnings_yield', 'v_fcf_yield', 'v_vs_industry'}
    assert set(slots) - {'EV_NON_POSITIVE'} and all(s == {'v_expectation_check'} for k, s in slots.items() if k != 'EV_NON_POSITIVE')


def test_supply_denominator_is_the_price_free_v_reachable_rows_d4():
    """D-CV5 / D4: the 95% is over GENERAL cross-section rows that can reach a V score without a price (V_GENERAL_COVERAGE
    2-2 (b)), not every row with a V-input block."""
    payload = base_payload()
    ctx = qo.prepare(payload, NOW)
    status = qo.price_status(ctx, synthetic_day(payload))
    assert qo.supply_eligible(ctx, status) == sorted(FIXTURE_GENERAL)          # every fixture GENERAL row qualifies
    cut = without_price_free_v(payload, ('NYSE:ARE', 'NYSE:MMM'))
    ctx2 = qo.prepare(cut, NOW)
    assert all(isinstance(ctx2['companies'][k]['v_inputs'], dict) for k in ('NYSE:ARE', 'NYSE:MMM'))   # still has V inputs
    eligible = qo.supply_eligible(ctx2, qo.price_status(ctx2, synthetic_day(cut)))
    assert eligible == sorted(set(FIXTURE_GENERAL) - {'NYSE:ARE', 'NYSE:MMM'})
    # missing prices of rows outside the denominator do not count; their V stays NA whatever the price
    official, _ = build(cut, synthetic_day(cut, drop=['NYSE:ARE', 'NYSE:MMM']))
    assert official['price_source']['supply'] == {'eligible': 16, 'supplied': 16, 'minimum_share': 0.95, 'met': True}
    for price in (1e-6, 25.0, 1e6):
        o, _ = build(cut, synthetic_day(cut, price_of={k: price for k in ('NYSE:ARE', 'NYSE:MMM')}))
        assert all(o['rows'][k]['axes']['V']['score'] is None for k in ('NYSE:ARE', 'NYSE:MMM'))
    # one V-reachable row without a price: 15/16 < ceil(0.95 x 16) = 16 -> SUPPLY_FAILED, the last good copy stays
    with pytest.raises(qo.OfficialError) as e:
        build(cut, synthetic_day(cut, drop=['NYSE:ABT']))
    assert (e.value.state, e.value.code) == ('SUPPLY_FAILED', 'SUPPLY_BELOW_THRESHOLD')


def test_supply_threshold_boundary_and_keeps_last_good():
    payload = base_payload()
    ctx = qo.prepare(payload, NOW)
    status = qo.price_status(ctx, synthetic_day(payload))
    eligible = qo.supply_eligible(ctx, status)
    # exactly ceil(0.95 x N) supplied passes, one fewer fails (N = 18 here: all 18 needed)
    assert qo.supply_needed(len(eligible)) == 18
    assert qo.supply_check(ctx, status)['met'] is True
    assert qo.supply_check(ctx, dict(status, **{eligible[0]: 'NO_IEX_TRADE'}))['met'] is False
    for n, need in ((1, 1), (19, 19), (20, 19), (100, 95), (358, 341), (360, 342), (434, 413)):
        assert qo.supply_needed(n) == need == math.ceil(0.95 * n - 1e-9)
    with pytest.raises(qo.OfficialError) as e:
        build(payload, synthetic_day(payload, drop=eligible[:1]))
    assert (e.value.state, e.value.code) == ('SUPPLY_FAILED', 'SUPPLY_BELOW_THRESHOLD')
    official, _ = build(payload, synthetic_day(payload, drop=['NASDAQ:AAPL']))    # a non-eligible miss is fine
    assert official['price_source']['rejected']['NO_IEX_TRADE'] == 1


def test_price_free_eligibility_is_an_upper_bound_of_the_engine():
    """No row outside supply_eligible gets a V score at any price (prices synthetic, month closes for every history month)."""
    payload = without_price_free_v(base_payload(), ('NYSE:ARE',))
    ctx = qo.prepare(payload, NOW)
    day = synthetic_day(payload)
    eligible = set(qo.supply_eligible(ctx, qo.price_status(ctx, day)))
    general = {k for k, r in ctx['inputs']['records'].items() if not k.startswith(qo.TARGET_PREFIX) and r['in_cross_section']
               and r['published_profile'] == 'GENERAL'}
    seen = set()
    for scale in (1e-4, 0.05, 1.0, 40.0, 1e4):
        quotes = {k: {'price': scale * (20 + i), 'currency': 'USD',
                      'month_closes': {h['period_end'][:7]: scale * (10 + i) for h in (ctx['companies'][k]['v_inputs'] or {}).get('ebit_per_share_history', [])}}
                  for i, k in enumerate(sorted(general)) if ctx['companies'].get(k) and ctx['companies'][k].get('v_inputs')}
        results = qo.score(ctx, quotes)
        scored = {k for k in general if results.get(k) and results[k]['axes']['V']['score'] is not None}
        assert scored <= eligible and 'NYSE:ARE' not in scored
        seen |= scored
    assert seen == eligible and len(eligible) == 17          # tight on the fixture: every eligible row is V-capable at some price


def _count_from_annual_filing(payload, code):
    """The row's latest diluted-share count is the FY0 annual one (period end = the last history item's fiscal_year_end)."""
    p = copy.deepcopy(payload)
    v = p['records'][code]['v_inputs_v2']
    v['diluted_shares']['period_end'] = v['ebit_per_share_history'][-1]['fiscal_year_end']
    sec_qgv2.require_qgv2(p)
    return p


def test_conservative_split_rule_reads_the_fk_evidence_d6a(monkeypatch):
    """D6 (a), conservative only: SPLIT_TIMING_UNCONFIRMED on the history item at/after the share count's period end = a split
    between the count's period end and its annual filing (a count that filing usually restates) -> SPLIT_AFTER_SHARE_COUNT as a
    precaution (no price, V NA, not in the D-CV5 denominator). No new source, no table entry. It is not a current-price split
    check: a split after the count's filing is D6 (b)'s (test_d6b_*), residual without short store steps
    (test_residual_without_short_store_steps_a_split_after_the_count_filing_is_not_detected)."""
    code = 'NYSE:ABT'
    fy0 = base_payload()['records'][code]['v_inputs_v2']['ebit_per_share_history'][-1]['fiscal_year_end']
    annual = _count_from_annual_filing(base_payload(), code)
    flagged = with_fk(annual, None, vf.SPLIT_TIMING_UNCONFIRMED, codes={code}, items={fy0})
    ctx = qo.prepare(flagged, NOW)
    assert qo.price_status(ctx, synthetic_day(flagged))[code] == 'SPLIT_AFTER_SHARE_COUNT'
    official, internal = build(flagged)
    row = official['rows'][code]
    assert row['price_status'] == 'SPLIT_AFTER_SHARE_COUNT' and row['axes']['V']['score'] is None and row['rank'] is None
    assert code not in internal['quotes'] and official['price_source']['rejected']['SPLIT_AFTER_SHARE_COUNT'] == 1
    eligible = qo.supply_check(qo.prepare(base_payload(), NOW), qo.price_status(qo.prepare(base_payload(), NOW), synthetic_day(base_payload())))['eligible']
    assert official['price_source']['supply']['eligible'] == eligible - 1
    # the same evidence when the count is a later 10-Q (period end after FY0): the 10-Q is on the post-split basis -> priced
    later = with_fk(base_payload(), None, vf.SPLIT_TIMING_UNCONFIRMED, codes={code}, items={fy0})
    assert qo.price_status(qo.prepare(later, NOW), synthetic_day(later))[code] == 'SUPPLIED'
    # SHARE_BASIS_UNCONFIRMED (chain not established) is not split evidence; an older item is not after the count either
    for p in (with_fk(annual, None, vf.SHARE_BASIS_UNCONFIRMED, codes={code}, items={fy0}),
              with_fk(annual, None, vf.SPLIT_TIMING_UNCONFIRMED, codes={code}, items={'2021-12-31'})):
        assert qo.price_status(qo.prepare(p, NOW), synthetic_day(p))[code] == 'SUPPLIED'
    # the verified-window hook (iex_hist.SPLITS, empty in production) still works
    assert iex_hist.SPLITS == {}
    monkeypatch.setitem(iex_hist.SPLITS, code, (('2026-07-01', '2026-07-31'),))
    assert qo.price_status(qo.prepare(base_payload(), NOW), synthetic_day(base_payload()))[code] == 'SPLIT_AFTER_SHARE_COUNT'


def test_residual_without_short_store_steps_a_split_after_the_count_filing_is_not_detected():
    """RESIDUAL of D6 (b) (owner decision CV-SPLIT (ii) 2026-10-24; was the KNOWN LIMITATION of the 2026-10-24 review). A split
    after the share count's own filing (NVDA type: Q1 10-Q 2024-05-29, 10:1 split 2024-06-10) leaves no evidence in sec-qgv2.json
    (F_k = 1.0 on every item, no SPLIT fact yet) and iex_hist.SPLITS is empty, so D6 (a) does not see it. D6 (b) sees it only
    where the private store has short steps (<= 45 days) since the count's period end (test_d6b_*). Here the store is like
    the U8 store of stamp 20261023: fiscal-year-end months only (the latest 2025-12, before the 10-Q period end 2026-06-30), so
    the row is unchecked, SUPPLIED and scored: count x today's (post-split) price is off by the split ratio until the next
    10-Q / 10-K restates the count. Synthetic prices: the same row at price p and p / 10 gets two different V scores, and
    nothing in the publication marks it. It stays so until recent month-ends of every Universe code are in the store."""
    code = 'NYSE:ABT'
    payload = base_payload()                     # count period end 2026-06-30 (a 10-Q), F_k 1.0 everywhere
    assert payload['records'][code]['v_inputs_v2']['diluted_shares']['period_end'] > \
        payload['records'][code]['v_inputs_v2']['ebit_per_share_history'][-1]['fiscal_year_end']
    assert iex_hist.SPLITS == {}
    for basis_day in ('2026-07-15', '2026-10-13'):
        assert not qo.split_after_share_count(code, payload['records'][code]['v_inputs_v2'], basis_day)
    ctx = qo.prepare(payload, NOW)
    assert qo.price_status(ctx, synthetic_day(payload))[code] == 'SUPPLIED'
    before, _ = build(payload, synthetic_day(payload, price_of={code: 120.0}))
    after, _ = build(payload, synthetic_day(payload, price_of={code: 12.0}))     # post-split price, pre-split count
    for o in (before, after):
        assert o['rows'][code]['price_status'] == 'SUPPLIED' and o['rows'][code]['axes']['V']['score'] is not None
    assert before['rows'][code]['axes']['V']['score'] != after['rows'][code]['axes']['V']['score']
    status, split = qo.price_status_counts(ctx, synthetic_day(payload, price_of={code: 12.0}), synthetic_months(payload))
    assert status[code] == 'SUPPLIED' and split['checked'] == split['flagged'] == 0      # no short step: unchecked


# ---- D6 (b): supplementary split check on short steps of raw prices (owner decision CV-SPLIT (ii) 2026-10-24) ---------------
SPLIT_CODE = 'NYSE:ABT'
SPLIT_V = {'diluted_shares': {'period_end': '2026-06-30'}}
MONTH_ENDS = ('20260630', '20260731', '20260831', '20260930')


def store(code, points):
    """Synthetic private month-end store months of one code: {YYYY-MM: month} with one trade per point (YYYYMMDD, price[, status
    [, store symbol]]): status ROUND unless given, symbol = the alias table's on that date unless given. Made-up prices."""
    months = {}
    for point in points:
        date, price = point[0], point[1]
        status = point[2] if len(point) > 2 else 'ROUND'
        sym = point[3] if len(point) > 3 else iex_hist.iex_symbol(code, date)
        months[f'{date[:4]}-{date[4:6]}'] = {'date': date, 'codes': {code: sym}, 'symbols': {sym: {
            'status': status, 'price_e4': None if status == 'NO_TRADE' else round(price * 10000), 'ts_ns': 1, 'n': 1}}}
    return months


def split_check(prices, today, *, v=SPLIT_V, code=SPLIT_CODE, basis='2026-10-13', dates=MONTH_ENDS):
    return qo.split_check(code, v, store(code, zip(dates, prices)), today, basis)


def test_d6b_split_bands_are_the_split_factor_list():
    assert qo.SPLIT_FACTORS == (2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 30, 40, 50) and qo.SPLIT_MAX_GAP_DAYS == 45
    assert dict(qo.SPLIT_BANDS) == {**{float(n): math.log(1.25) for n in qo.SPLIT_FACTORS}, 1.5: math.log(1.10)}
    hits = (1 / 2, 0.5 * 1.2, 0.5 / 1.2, 1 / 3, 1 / 4, 1 / 10, 1 / 50, 1 / 60, 2.0, 4.0, 4 * 0.85, 50.0,     # forward / reverse n:1
            1 / 1.5, 1 / 1.5 * 1.08, 1 / 1.5 * 0.92, 1.5, 1.5 * 1.08,                                    # 3:2 within 10%
            0.55, 0.70, 1.40)                                    # genuine moves inside the bands (conservative false positives)
    misses = (1.0, 0.95, 0.80, 0.75, 1.10, 1.30, 1.35, 1 / 1.5 * 1.15,   # moves outside the bands; 3:2 with a +15% move (miss)
              1 / 70, 70.0, 0.0, -0.5, float('nan'), float('inf'), None, True)
    assert [r for r in hits if not qo.split_ratio_hit(r)] == []
    assert [r for r in misses if qo.split_ratio_hit(r)] == []


def test_d6b_split_check_on_month_steps_and_the_basis_day():
    """Period end 2026-06-30, store month-ends 06-30 .. 09-30, today = basis day 2026-10-13 (all synthetic prices)."""
    assert split_check((100, 103, 99, 101), 102) == ('CHECKED', 0, False)
    assert split_check((100, 102, 51.5, 52), 53) == ('FLAGGED', 0, False)            # 2:1 forward inside a month step
    assert split_check((100, 102, 101, 104), 52) == ('FLAGGED', 0, False)            # 2:1 between the last month-end and today
    assert split_check((100, 101, 10.2, 10.4), 10.3) == ('FLAGGED', 0, False)        # 10:1
    assert split_check((5, 5.1, 20.6, 20.4), 20.5) == ('FLAGGED', 0, False)          # reverse 1:4
    assert split_check((90, 90, 90 / 1.5 * 1.08, 65), 65) == ('FLAGGED', 0, False)   # 3:2 with a +8% move (within 10%)
    assert split_check((90, 90, 90 / 1.5 * 0.92, 55), 55) == ('FLAGGED', 0, False)   # 3:2 with a -8% move
    assert split_check((90, 90, 90 / 1.5 * 1.15, 69.5), 70) == ('CHECKED', 0, False)  # 3:2 with a +15% move: MISSED (documented)
    assert split_check((100, 100, 55, 56), 57) == ('FLAGGED', 0, False)              # genuine -45% month: FLAGGED (documented, conservative)
    assert split_check((100, 100, 130, 131), 132) == ('CHECKED', 0, False)           # genuine +30% month: not flagged
    assert split_check((100, 100, 80, 80), 80) == ('CHECKED', 0, False)              # genuine -20% month: not flagged


def test_d6b_long_gaps_are_skipped_and_never_flag():
    # 06-30 -> 08-29 is 60 days (skipped, whatever the ratio); 08-29 -> 10-13 is 45 days (checked)
    assert split_check((100, 50), 51, dates=('20260630', '20260829')) == ('CHECKED', 1, False)
    # 06-30 -> 08-28 is 59 days, 08-28 -> 10-13 is 46 days: nothing checked -> unchecked, never NA because of this rule
    assert split_check((100, 10), 1, dates=('20260630', '20260828')) == ('UNCHECKED', 2, False)
    # the U8 store of stamp 20261023 holds fiscal-year-end months only: a count of the FY 2025 10-K, its FY-end month, today
    assert split_check((100,), 10, v={'diluted_shares': {'period_end': '2025-12-31'}}, dates=('20251231',)) == ('UNCHECKED', 1, False)
    assert split_check((), 10) == ('UNCHECKED', 0, True)                             # today's price alone


def test_d6b_a_checked_row_without_the_period_end_month_counts_its_lead_stretch_unchecked():
    """CHECKED is not split-free since the filing (2026-10-25 review). A September fiscal year-end whose count comes from the
    June 10-Q (period end 2026-06-30, filed early August), under the fiscal-year-end-only store: the store has the code's
    2025-09 and 2026-09 month-ends, not 2026-06. A 10:1 split on 2026-08-20 (after the 10-Q filing) sits between the window
    start and the first point (2026-09-30, already post-split); only 09-30 -> basis day is compared. The row is CHECKED and
    stays SUPPLIED (residual), and the third value says the stretch from the window start to the first point was never
    compared (split_lead_unchecked). Synthetic prices."""
    fy_sep = (('20250930', 900.0), ('20260930', 10.0))
    assert qo.split_check(SPLIT_CODE, SPLIT_V, store(SPLIT_CODE, fy_sep), 10.2, '2026-10-23') == ('CHECKED', 0, True)
    # with the period end's own month-end in the store the lead is covered (06-30 -> 09-30 is a 92-day pair: skipped, counted)
    with_june = (('20260630', 100.0), ('20260930', 10.0))
    assert qo.split_check(SPLIT_CODE, SPLIT_V, store(SPLIT_CODE, with_june), 10.2, '2026-10-23') == ('CHECKED', 1, False)
    # a NO_TRADE period-end month is no point either
    no_trade = (('20260630', 0, 'NO_TRADE'), ('20260731', 100.0), ('20260831', 101.0))
    assert qo.split_check(SPLIT_CODE, SPLIT_V, store(SPLIT_CODE, no_trade), 102.0, '2026-09-15') == ('CHECKED', 0, True)
    # counted over the Universe codes checked, as a subset of split_checked; the row itself is unchanged (SUPPLIED)
    payload = base_payload()
    months = dict(synthetic_months(payload), **store(SPLIT_CODE, fy_sep))
    day = synthetic_day(payload, price_of={SPLIT_CODE: 10.2})
    status, split = qo.price_status_counts(qo.prepare(payload, NOW), day, months)
    assert status[SPLIT_CODE] == 'SUPPLIED'
    assert (split['checked'], split['flagged'], split['lead_unchecked'], split['gap_skipped']) == (1, 0, 1, 0)
    assert qo.SPLIT_COUNT_KEYS[-1] == 'lead_unchecked'


def test_d6b_an_impossible_store_date_is_left_out_never_fatal():
    """An 8-digit store date that is no calendar date (2026-06-31) is a malformed month: raw_series leaves it out like any
    other malformed month, and the split check (run for every SUPPLIED row on every store month) does not raise."""
    months = store(SPLIT_CODE, [('20260631', 100.0), ('20260731', 50.0)])
    assert iex_monthend.raw_series(SPLIT_CODE, months, '2026-06', '2026-08-10') == [('2026-07-31', 50.0)]
    assert qo.split_check(SPLIT_CODE, SPLIT_V, months, 50.0, '2026-08-10') == ('CHECKED', 0, True)
    for bad in ('20260230', '20261301', '20260000'):
        months = store(SPLIT_CODE, [(bad, 100.0), ('20260930', 99.0)])
        assert iex_monthend.raw_series(SPLIT_CODE, months, '2026-01', '2026-10-13') == [('2026-09-30', 99.0)]
    # the whole build goes through (it used to end as VERIFY_FAILED UNEXPECTED_VALUEERROR)
    payload = base_payload()
    months = dict(synthetic_months(payload), **store(SPLIT_CODE, [('20260631', 100.0), ('20260930', 99.0)]))
    official, internal = build(payload, synthetic_day(payload, price_of={SPLIT_CODE: 98.0}), months)
    qo.require_qgv_official(official)
    assert official['rows'][SPLIT_CODE]['price_status'] == 'SUPPLIED' and internal['split']['lead_unchecked'] == 1


def test_d6b_no_period_end_is_not_checked():
    for v in ({'diluted_shares': {'period_end': None}}, {'diluted_shares': {'period_end': '2026-06'}}, {'diluted_shares': None}, {},
              None):
        assert split_check((100, 101, 10.2, 10.4), 10.3, v=v) == ('NO_PERIOD', 0, False)


def test_d6b_window_starts_at_the_period_ends_month_and_ends_at_the_basis_day():
    dates, basis = ('20260430', '20260529', '20260630', '20260731'), '2026-08-14'
    # a 10:1 step before the period end's month is outside the window
    assert split_check((100, 10, 10.1, 10.2), 10.3, dates=dates, basis=basis) == ('CHECKED', 0, False)
    # the period end's own month-end trade is the first point, also for a weekend month-end (2026-05-31: trade 05-29)
    weekend = {'diluted_shares': {'period_end': '2026-05-31'}}
    assert split_check((100, 100, 50, 50.5), 51, dates=dates, basis=basis, v=weekend) == ('FLAGGED', 0, False)
    assert split_check((100, 100, 50, 50.5), 51, dates=dates, basis=basis) == ('CHECKED', 0, False)
    # a store month after the basis day is never read
    assert split_check((100, 101, 102, 10), 103, dates=('20260731', '20260831', '20260930', '20261030')) == ('CHECKED', 0, True)


def test_d6b_symbols_follow_month_closes_alias_and_round_rules():
    psky = 'NASDAQ:PSKY'
    dates = ('20260731', '20260831', '20260930', '20261030')                    # PSKY -> SKYD from 2026-10-06
    v = {'diluted_shares': {'period_end': '2026-06-30'}}

    def run(points, today):
        return qo.split_check(psky, v, store(psky, points), today, '2026-11-13')
    assert run(zip(dates, (20, 20.5, 21, 21.2)), 21.5) == ('CHECKED', 0, True)      # PSKY months, then the SKYD month: one series
    assert store(psky, zip(dates, (20, 20.5, 21, 21.2)))['2026-10']['codes'][psky] == 'SKYD'
    assert run(zip(dates, (20, 20.5, 21, 2.1)), 2.15) == ('FLAGGED', 0, True)       # a 10:1 step into the SKYD month
    # the store lists PSKY after the alias date: that month is left out (month_closes MONTH_END_SYMBOL_MISMATCH), not compared
    points = list(zip(dates[:3], (20, 20.5, 21))) + [(dates[3], 2.1, 'ROUND', 'PSKY')]
    assert run(points, 21.5) == ('CHECKED', 0, True)
    months = store(psky, points)
    series = iex_monthend.raw_series(psky, months, '2026-06', '2026-11-13')
    hist = [{'fiscal_year_end': f'{d[:4]}-{d[4:6]}-{d[6:]}', 'value': 1.0, 'share_basis_factor': 1.0} for d in dates]
    closes, left = iex_monthend.month_closes(psky, hist, months)
    assert {d[:7]: px for d, px in series} == closes and left == [('2026-10', iex_monthend.SYMBOL_MISMATCH)]
    # an alias None (WBD from 2026-10-06) leaves the month out as well
    wbd = store('NASDAQ:WBD', [('20260930', 30.0), ('20261030', 3.0, 'ROUND', 'WBD')])
    assert [d for d, _ in iex_monthend.raw_series('NASDAQ:WBD', wbd, '2026-06', '2026-11-13')] == ['2026-09-30']


def test_d6b_na_is_never_zero():
    # NO_TRADE / odd-lot-only months are left out (never a 0 price); the steps around them are then too long and skipped
    points = [('20260630', 100.0), ('20260731', 0, 'NO_TRADE'), ('20260831', 50.0, 'ODD_ONLY'), ('20260930', 99.0)]
    months = store(SPLIT_CODE, points)
    assert iex_monthend.raw_series(SPLIT_CODE, months, '2026-06', '2026-10-13') == [('2026-06-30', 100.0), ('2026-09-30', 99.0)]
    assert qo.split_check(SPLIT_CODE, SPLIT_V, months, 98.0, '2026-10-13') == ('CHECKED', 1, False)
    # a malformed store price (zero, float, bool) is left out too; a missing / non-positive / non-finite price today is no point
    bad = store(SPLIT_CODE, zip(MONTH_ENDS, (100, 101, 102, 103)))
    for month, px in (('2026-07', 0), ('2026-08', 50.5), ('2026-09', True)):
        bad[month]['symbols']['ABT']['price_e4'] = px
    assert iex_monthend.raw_series(SPLIT_CODE, bad, '2026-06', '2026-10-13') == [('2026-06-30', 100.0)]
    for today in (None, 0, -1.0, float('nan'), float('inf')):
        assert qo.split_check(SPLIT_CODE, SPLIT_V, store(SPLIT_CODE, [('20260930', 100.0)]), today, '2026-10-13') == ('UNCHECKED', 0, True)
        assert split_check((100, 101, 102, 103), today) == ('CHECKED', 0, False)


def _supplied_universe(payload, day):
    status = qo.price_status(qo.prepare(payload, NOW), day)
    return [k for k, s in status.items() if s == 'SUPPLIED' and not k.startswith(qo.TARGET_PREFIX)]


def test_d6b_end_to_end_withholds_the_row_and_counts_only():
    """A 10:1 split after the 10-Q of period end 2026-06-30: the store has the code's month-ends 06-30 .. 09-30 at the
    pre-split price, today's raw price is post-split -> SPLIT_AFTER_SHARE_COUNT: no price, V NA, no rank, out of the D4
    denominator, rejected count; nothing else in the row or the publication changes shape. The JS twin still matches (the
    status is Python's; the row has no quote in either twin). Synthetic prices only."""
    payload = base_payload()
    months = dict(synthetic_months(payload), **store(SPLIT_CODE, zip(MONTH_ENDS, (118.0, 121.0, 119.5, 120.0))))
    day = synthetic_day(payload, price_of={SPLIT_CODE: 12.0})
    official, internal = build(payload, day, months)
    qo.require_qgv_official(official)
    row = official['rows'][SPLIT_CODE]
    assert row['price_status'] == 'SPLIT_AFTER_SHARE_COUNT' and row['axes']['V']['score'] is None and row['rank'] is None
    assert SPLIT_CODE not in internal['quotes'] and official['price_source']['rejected']['SPLIT_AFTER_SHARE_COUNT'] == 1
    base, _ = build(payload, synthetic_day(payload), synthetic_months(payload))
    assert official['price_source']['supply']['eligible'] == base['price_source']['supply']['eligible'] - 1
    assert set(official) == set(base) and set(official['price_source']) == set(base['price_source'])   # no new public field
    supplied = _supplied_universe(payload, day)
    no_period = sum(1 for k in supplied if not ((payload['records'][k].get('v_inputs_v2') or {}).get('diluted_shares') or {}).get('period_end'))
    assert internal['split'] == {'checked': 1, 'flagged': 1, 'unchecked': len(supplied) - 1, 'unchecked_no_period': no_period,
                                 'gap_skipped': 0, 'lead_unchecked': 0}
    assert no_period > 0 and repr(12.0) not in json.dumps(internal['split'])
    tool.js_check(internal['ctx']['companies'], qo.qi.priced_quotes(internal['quotes'], internal['ctx']['blocked']),
                  internal['results'])
    # the same store with today's price on the same basis: SUPPLIED, checked, scored
    ok, internal_ok = build(payload, synthetic_day(payload, price_of={SPLIT_CODE: 120.5}), months)
    assert ok['rows'][SPLIT_CODE]['price_status'] == 'SUPPLIED' and ok['rows'][SPLIT_CODE]['axes']['V']['score'] is not None
    assert (internal_ok['split']['checked'], internal_ok['split']['flagged']) == (1, 0)
    # D6 (a) is unchanged and comes first: its row never reaches D6 (b) (not counted)
    fy0 = payload['records'][SPLIT_CODE]['v_inputs_v2']['ebit_per_share_history'][-1]['fiscal_year_end']
    d6a = with_fk(_count_from_annual_filing(payload, SPLIT_CODE), None, vf.SPLIT_TIMING_UNCONFIRMED, codes={SPLIT_CODE}, items={fy0})
    o_a, internal_a = build(d6a, synthetic_day(d6a, price_of={SPLIT_CODE: 120.5}), months)
    assert o_a['rows'][SPLIT_CODE]['price_status'] == 'SPLIT_AFTER_SHARE_COUNT' and internal_a['split']['checked'] == 0


def test_d6b_counts_reach_the_one_line_result_only(artifact):
    out, payload, parser = artifact
    months = dict(synthetic_months(payload), **store(SPLIT_CODE, zip(MONTH_ENDS, (118.0, 121.0, 119.5, 120.0))))
    s = _run(out, parser, day=synthetic_day(payload, price_of={SPLIT_CODE: 12.0}), months=months)
    assert (s['attempt'], s['published']) == ('OK', 'NEW') and (s['split']['checked'], s['split']['flagged']) == (1, 1)
    line = tool.summary_line(s)
    assert re.fullmatch(r'QGV_OFFICIAL attempt=OK reason=- published=NEW basis=2026-10-13 rows=\d+ ranked=\d+ supplied=\d+/\d+ '
                        r'iex_attempts=1 split_checked=1 split_flagged=1 split_unchecked=\d+ split_unchecked_no_period=\d+ split_gap_skipped=0 '
                        r'split_lead_unchecked=0', line)
    assert 'ABT' not in line and '12.0' not in line
    for name in (qo.FILENAME, qo.STATUS_FILENAME):
        assert not {'split_checked', 'split_flagged', 'gap_skipped', 'unchecked', 'lead_unchecked'} & set(
            re.findall(r'[a-z_]+', (out / name).read_text()))
    # an attempt that never built (no prices read) prints no split counts
    failed = _run(out, parser, fail='MD5_MISMATCH')
    assert failed['split'] is None and 'split_' not in tool.summary_line(failed)


def test_iex_attempts_reach_the_one_line_result_only(artifact):
    """2026-10-25 (rehearsal run 40156760950): the number of full IEX stream attempts (1, or 2 after a whole-pipeline retry)
    is a count in the one stdout line, followed, when the first attempt failed, by its fixed code (iex_first) and for a first
    DOWNLOAD_FAILED curl's exit code (iex_curl_rc); never in qgv-official.json or the status file. Nothing before any stream."""
    out, payload, parser = artifact

    def failing(keys, basis, parser=None, workdir=None):
        err = iex_hist.IexHistError('SIZE_MISMATCH')
        err.attempts, err.first_code, err.first_curl_rc = 2, 'DOWNLOAD_FAILED', 18
        raise err
    s = tool.run(out=out, parser=parser, monthend_stamp='20261023', monthend_shards=6, previous=None, raw_token='t', hmac_key=KEY,
                 now=NOW, workdir=out.parent / 'w', fetch_day=failing, read_store=lambda st, n: {}, clock=lambda: NOW)
    assert tool.summary_line(s) == ('QGV_OFFICIAL attempt=NO_OFFICIAL_YET reason=IEX_SIZE_MISMATCH published=NONE basis=- rows=0 '
                                    'ranked=0 supplied=- iex_attempts=2 iex_first=DOWNLOAD_FAILED iex_curl_rc=18')
    status = (out / qo.STATUS_FILENAME).read_text()
    assert not {'attempts', 'first', 'curl', 'DOWNLOAD_FAILED'} & set(re.findall(r'[A-Za-z_]+', status))
    day = synthetic_day(payload)
    day.attempts, day.first_code = 2, 'GZIP_FAILED'
    ok = _run(out, parser, day=day)
    assert ok['published'] == 'NEW' and ' iex_attempts=2 iex_first=GZIP_FAILED split_checked=' in tool.summary_line(ok)
    for name in (qo.FILENAME, qo.STATUS_FILENAME):
        text = (out / name).read_text()
        assert 'attempts' not in text and 'GZIP_FAILED' not in text and 'curl' not in text
    one = synthetic_day(payload)
    assert ' iex_attempts=1 split_checked=' in tool.summary_line(_run(out, parser, day=one))   # clean first attempt: no iex_first
    assert 'iex_' not in tool.summary_line(_run(out, parser, fail='SOURCE_UNAVAILABLE'))      # before any stream
    assert 'iex_' not in tool.summary_line(_run(out, parser, key=None))
    # only an upper-case fixed code and a small integer ever reach the line
    base = dict(s, iex_attempts=1)
    for first, rc in (('https://x.example/a', 18), ('4242.42', 18), ('DOWNLOAD_FAILED', '18'), ('DOWNLOAD_FAILED', 10**6)):
        line = tool.summary_line(dict(base, iex_first=first, iex_curl_rc=rc))
        assert 'x.example' not in line and '4242' not in line and 'iex_curl_rc' not in line
    md5_line = tool.summary_line(dict(base, iex_first='MD5_MISMATCH', iex_curl_rc=None))
    assert md5_line.endswith(' iex_attempts=1 iex_first=MD5_MISMATCH')


def test_main_gives_the_iex_stream_the_step_deadline(artifact, monkeypatch):
    """The V step runs the publisher under `timeout -k 30s 12m`: main hands the production IEX reader the deadline 12 minutes
    after this process started (iex_hist time budget: curl --max-time per attempt, a second attempt only when it fits)."""
    import functools
    import time
    out, payload, parser = artifact
    seen = {}

    def stub_run(**kw):
        seen.update(kw)
        return {'attempt': 'OK', 'reason': None, 'published': 'NONE', 'basis': '-', 'rows': 0, 'ranked': 0, 'supplied': '-'}
    monkeypatch.setattr(tool, 'run', stub_run)
    assert tool.main(['--out', str(out), '--parser', parser, '--monthend-stamp', '20261023', '--previous', '']) == 0
    fetch = seen['fetch_day']
    assert isinstance(fetch, functools.partial) and fetch.func is iex_hist.fetch_day
    assert fetch.keywords == {'deadline': tool.STARTED + tool.STEP_LIMIT_S} and tool.STEP_LIMIT_S == 12 * 60
    assert tool.STARTED <= time.monotonic()


def test_adr_rule_covers_known_20f_filers_whatever_the_taxonomy_d7(monkeypatch):
    from investment_system.markets.us import US_LISTINGS
    # the one known 20-F filer of Universe504 (DCV_OPEN_ITEMS_20261019.md D-CV10): ASML, by CIK, Universe code and TARGET row
    assert set(qo.FOREIGN_ANNUAL_FILERS) == {'0000937966'}
    code, form, evidence = qo.FOREIGN_ANNUAL_FILERS['0000937966']
    assert code == 'NASDAQ:ASML' and code in universe_codes() and form == '20-F' and '0001628280-26-011378' in evidence
    assert US_LISTINGS['asml']['cik'] == '0000937966'
    # ifrs-full stays NA; a us-gaap row of a listed foreign filer is NA too (D7), and leaves the D-CV5 denominator
    assert qo.adr_unconfirmed({'cik': '0000000001'}, {'taxonomy': 'ifrs-full'})
    assert qo.adr_unconfirmed({'cik': '0000937966'}, {'taxonomy': 'us-gaap'})
    assert not qo.adr_unconfirmed({'cik': '0000000001'}, {'taxonomy': 'us-gaap'})
    payload = base_payload()
    cik = payload['records']['NYSE:ABT']['cik']
    base_eligible = build(payload)[0]['price_source']['supply']['eligible']
    monkeypatch.setitem(qo.FOREIGN_ANNUAL_FILERS, cik, ('NYSE:ABT', '20-F', 'synthetic test entry'))
    official, internal = build(payload)
    assert payload['records']['NYSE:ABT']['v_inputs_v2']['taxonomy'] == 'us-gaap'
    assert official['rows']['NYSE:ABT']['price_status'] == 'ADR_RATIO_UNCONFIRMED' and 'NYSE:ABT' not in internal['quotes']
    assert official['rows']['NYSE:ABT']['axes']['V']['score'] is None
    assert official['price_source']['supply']['eligible'] == base_eligible - 1


def test_js_twin_cross_check_matches_and_catches_a_difference():
    payload = base_payload()
    official, internal = build(payload)
    ctx = internal['ctx']
    priced = qo.qi.priced_quotes(internal['quotes'], ctx['blocked'])
    tool.js_check(ctx['companies'], priced, internal['results'])          # exact, no tolerance
    tampered = copy.deepcopy(internal['results'])
    k = next(k for k, r in tampered.items() if r['total'] is not None)
    tampered[k]['total'] += 1e-12
    with pytest.raises(qo.OfficialError) as e:
        tool.js_check(ctx['companies'], priced, tampered)
    assert e.value.code == 'JS_TWIN_MISMATCH'


def test_build_writes_nothing(monkeypatch):
    payload = base_payload()
    day, months = synthetic_day(payload), synthetic_months(payload)
    real_open = builtins.open

    def no_write(file, mode='r', *a, **kw):
        if any(c in mode for c in 'wax+'):
            raise AssertionError('write attempted')
        return real_open(file, mode, *a, **kw)
    monkeypatch.setattr(builtins, 'open', no_write)
    for name in ('write_text', 'write_bytes', 'mkdir', 'touch'):
        monkeypatch.setattr(Path, name, lambda *a, **k: (_ for _ in ()).throw(AssertionError('write attempted')))
    official, _ = qo.build(payload, 'a' * 64, now=NOW, day=day, months=months, monthend_stamp='20261023', hmac_key=KEY, generated_at=NOW)
    assert official['state'] == 'OFFICIAL'


# ---- validator ------------------------------------------------------------------------------------------------------
@pytest.fixture(scope='module')
def official():
    return build(base_payload())[0]


def _tamper(official, fn):
    bad = copy.deepcopy(official)
    fn(bad)
    with pytest.raises(ValueError):
        qo.require_qgv_official(bad)


def _ranked(o):
    return sorted((r['rank'], k) for k, r in o['rows'].items() if r['rank'] is not None)


@pytest.mark.parametrize('name,fn', [
    ('extra_top_key', lambda o: o.update(note='x')),
    ('price_key_nested', lambda o: next(iter(o['rows'].values()))['factors']['q_profitability'].update(price=1.0)),
    ('detail_field', lambda o: next(iter(o['rows'].values())).update(detail={})),
    ('month_closes_anywhere', lambda o: o['coverage'].update(month_closes={})),
    ('row_extra_key', lambda o: next(iter(o['rows'].values())).update(ev=None)),
    ('total_changed', lambda o: o['rows'][_ranked(o)[0][1]].update(total=o['rows'][_ranked(o)[0][1]]['total'] - 1e-9)),
    ('v_axis_changed', lambda o: o['rows'][_ranked(o)[0][1]]['axes']['V'].update(score=1.0)),
    ('rank_order', lambda o: (lambda a, b: (o['rows'][a].update(rank=2), o['rows'][b].update(rank=1)))(_ranked(o)[0][1], _ranked(o)[1][1])),
    ('rank_gap', lambda o: o['rows'][_ranked(o)[-1][1]].update(rank=999)),
    ('coverage_changed', lambda o: o['coverage']['v'].update(full=o['coverage']['v']['full'] + 1)),
    ('attribution_changed', lambda o: o['attribution'].update(text='IEX')),
    ('price_status_unknown', lambda o: next(iter(o['rows'].values())).update(price_status='CLOSE')),
    ('supply_not_met', lambda o: o['price_source']['supply'].update(met=False)),
    ('basis_after_requested', lambda o: (o['price_source'].update(basis_date='2026-10-14'), o['times'].update(price_basis_date='2026-10-14'))),
    ('nan', lambda o: o['rows'][_ranked(o)[0][1]].update(total=math.nan)),
])
def test_validator_rejects(official, name, fn):
    qo.require_qgv_official(official)
    _tamper(official, fn)


def _first_row(o):
    return o['rows'][sorted(o['rows'])[0]]


# Every scalar is typed (review 2026-10-24): a price-like value smuggled into any field is refused, by the validator and so by
# the Pages guard that runs it.
@pytest.mark.parametrize('name,fn', [
    ('inputs_as_of_value', lambda o: o['inputs'][0].update(as_of=CANARY)),
    ('inputs_acquired_newest_value', lambda o: o['inputs'][0].update(acquired_newest=CANARY)),
    ('inputs_acquired_oldest_text', lambda o: o['inputs'][0].update(acquired_oldest=str(CANARY))),
    ('inputs_calc_version_other', lambda o: o['inputs'][0].update(calc_version='qgv2-calc/2026-10-23.2')),
    ('times_inputs_as_of_value', lambda o: o['times'].update(inputs_as_of=CANARY)),
    ('times_inputs_as_of_other_clock', lambda o: o['times'].update(inputs_as_of='2026-10-13T00:00:00Z')),
    ('supply_eligible_value', lambda o: o['price_source']['supply'].update(eligible=CANARY)),
    ('supply_supplied_text', lambda o: o['price_source']['supply'].update(supplied='x')),
    ('supply_one_of_eligible_met', lambda o: o['price_source']['supply'].update(supplied=1, met=True)),
    ('supply_eligible_zero', lambda o: o['price_source']['supply'].update(eligible=0, supplied=0)),
    ('supply_supplied_over_eligible', lambda o: o['price_source']['supply'].update(supplied=o['price_source']['supply']['eligible'] + 1)),
    ('supply_eligible_over_rows', lambda o: o['price_source']['supply'].update(eligible=400, supplied=400)),
    ('supply_minimum_other', lambda o: o['price_source']['supply'].update(minimum_share=0.5)),
    ('supply_bool_count', lambda o: o['price_source']['supply'].update(eligible=True)),
    ('month_end_months_value', lambda o: o['price_source']['month_end'].update(months=CANARY)),
    ('month_end_months_negative', lambda o: o['price_source']['month_end'].update(months=-5)),
    ('month_end_months_bool', lambda o: o['price_source']['month_end'].update(months=True)),
    ('month_end_stamp_list', lambda o: o['price_source']['month_end'].update(stamp=[CANARY, CANARY])),
    ('month_end_stamp_short', lambda o: o['price_source']['month_end'].update(stamp='2026102')),
    ('month_end_store_other', lambda o: o['price_source']['month_end'].update(store='iex-monthend/2')),
    ('month_end_basis_other', lambda o: o['price_source']['month_end'].update(basis='ANYTHING')),
    ('currency_other', lambda o: o['price_source'].update(currency='EUR')),
    ('feed_other', lambda o: o['price_source'].update(feed='X')),
    ('price_source_supplied_value', lambda o: o['price_source'].update(supplied=CANARY)),
    ('engine_status_value', lambda o: o['engine'].update(status=CANARY)),
    ('weights_version_value', lambda o: o['weights'].update(weights_version=CANARY)),
    ('weights_profile_other', lambda o: o['weights'].update(profile_id='qgv-v2/balanced/gate-off')),
    ('weights_type_weights_value', lambda o: o['weights'].update(type_weights=CANARY)),
    ('config_type_config_value', lambda o: o['config_versions'].update(type_config=CANARY)),
    ('config_dcf_other', lambda o: o['config_versions'].update(dcf_parameters='dcf_parameters/v1-default')),
    ('type_scope_other', lambda o: o.update(type_scope=CANARY)),
    ('population_registry_value', lambda o: o['population'].update(registry_sha256=CANARY)),
    ('population_version_other', lambda o: o['population'].update(version=str(CANARY))),
    ('population_pooled_digest_other', lambda o: o['population'].update(pooled_digest='0' * 64)),
    ('calc_version_value', lambda o: (o.update(calc_version=str(CANARY)), o['inputs'][0].update(calc_version=str(CANARY)))),
    ('calc_version_before_u7', lambda o: (o.update(calc_version='qgv2-calc/2026-10-17.1'), o['inputs'][0].update(calc_version='qgv2-calc/2026-10-17.1'))),
    ('row_acquired_at_text', lambda o: _first_row(o).update(acquired_at=str(CANARY))),
    ('row_selected_type_value', lambda o: _first_row(o).update(selected_types=[str(CANARY)])),
])
def test_validator_types_every_scalar(official, name, fn):
    qo.require_qgv_official(official)
    _tamper(official, fn)


def test_parse_rejects_duplicate_keys_and_oversize(official):
    body = qo._canonical(official)
    assert qo.parse(body)['publication_id'] == official['publication_id']
    with pytest.raises(ValueError):
        qo.parse(b'{"schema":"a","schema":"b"}')
    with pytest.raises(ValueError):
        qo.parse(b' ' * (qo.MAX_BYTES + 1))


# ---- rows, ranks, reasons -------------------------------------------------------------------------------------------
def _row(cik, total, v, *, state='LIVE', cross=True):
    axes = {a: {'score': None, 'state': 'NOT_AVAILABLE', 'weight_available': 0, 'factors_available': 0, 'reason': 'X'} for a in 'QGV'}
    axes['V']['score'] = v
    return {'cik': cik, 'total': total, 'axes': axes, 'state': state, 'in_cross_section': cross, 'total_reason': None,
            'rank': None, 'qg_reference_order': None, 'rank_row': None}


def test_one_rank_per_cik_target_row_stands_for_its_universe_issuer():
    rows = {'NASDAQ:GOOGL': _row('0000000001', 70.0, 50.0), 'NASDAQ:GOOG': _row('0000000001', 69.0, 50.0, cross=False),
            'TARGET:googl': _row('0000000001', 71.0, 55.0),                       # D-CV8: stands for the CIK
            'NYSE:BBB': _row('0000000002', 80.0, 40.0), 'NYSE:CCC': _row('0000000003', 75.0, None),   # Q·G only
            'TARGET:asml': _row('0000000009', 99.0, 60.0),                        # outside the Universe: no rank
            'NYSE:DDD': _row('0000000004', None, None)}
    qo.assign_ranks(rows)
    assert {k: (r['rank'], r['qg_reference_order'], r['rank_row']) for k, r in rows.items()} == {
        'NYSE:BBB': (1, None, 'NYSE:BBB'), 'TARGET:googl': (2, None, 'TARGET:googl'), 'NASDAQ:GOOGL': (None, None, 'TARGET:googl'),
        'NASDAQ:GOOG': (None, None, 'TARGET:googl'), 'NYSE:CCC': (None, 1, 'NYSE:CCC'), 'TARGET:asml': (None, None, None),
        'NYSE:DDD': (None, None, None)}


def _engine_row(**over):
    r = {'factors': {k: {'score': 50.0, 'state': 'CALCULATED', 'reason': None, 'basis': 'UNIVERSE'} for k in qgv_v2.FACTORS},
         'axes': {a: {'score': 50.0, 'state': 'READY', 'weight_available': 1.0, 'factors_available': 5, 'reason': None} for a in 'QGV'},
         'weights': {'Q': 34.0, 'G': 33.0, 'V': 33.0}, 'type_weights': {'Q': 34, 'G': 33, 'V': 33}, 'type_reason': None,
         'selected_types': [], 'q_industry_percentile': 50.0, 'value_trap_gate': False, 'v_excluded': None, 'flags': [],
         'total': 50.0, 'total_reason': None}
    r.update(over)
    return r


REC = {'cik': '0000000001', 'published_profile': 'GENERAL', 'industry_group': 'services_software_health', 'in_cross_section': True,
       'state': 'LIVE', 'na_reasons': [], 'acquired_at': '2026-10-13T00:00:00Z', 'fiscal_year_end': '2025-12-31'}


def test_validator_checks_the_tie_order():
    rows = {'NYSE:BBB': _row('0000000002', 70.0, 40.0), 'NYSE:AAA': _row('0000000001', 70.0, 50.0), 'NYSE:CCC': _row('0000000003', 60.0, 10.0)}
    qo.assign_ranks(rows)
    assert [(k, r['rank']) for k, r in sorted(rows.items(), key=lambda x: x[1]['rank'])] == [('NYSE:AAA', 1), ('NYSE:BBB', 2), ('NYSE:CCC', 3)]
    qo._ranks_ok(rows)
    rows['NYSE:AAA']['rank'], rows['NYSE:BBB']['rank'] = 2, 1          # same total, ticker order broken
    with pytest.raises(ValueError):
        qo._ranks_ok(rows)


def test_v4_public_reason_merger_cut_and_identity_stop():
    res = _engine_row()
    res['factors']['v_vs_own_history'] = {'score': None, 'state': 'NOT_AVAILABLE', 'reason': 'HISTORY_TOO_SHORT', 'basis': None}
    row = qo.public_row('NASDAQ:PSKY', REC, res, 'SUPPLIED', [('2023-12', 'MERGER_PRE_BASIS_UNCONFIRMED'), ('2024-12', 'MERGER_PRE_BASIS_UNCONFIRMED')])
    assert row['factors']['v_vs_own_history']['reason'] == 'MERGER_PRE_BASIS_UNCONFIRMED'
    row = qo.public_row('NYSE:X', REC, res, 'SUPPLIED', None)
    assert row['factors']['v_vs_own_history']['reason'] == 'HISTORY_TOO_SHORT'     # nothing left out: engine reason
    stop = qo.public_row('TARGET:x', REC, _engine_row(), 'PRICE_IDENTITY_CONFLICT', None)
    assert stop['total'] is None and stop['total_reason'] == 'PRICE_IDENTITY_CONFLICT' and stop['axes']['V']['score'] is None
    assert 'PRICE_IDENTITY_CONFLICT' in stop['flags']
    mismatch = qo.public_row('NYSE:Y', REC, None, 'SUPPLIED', None)
    assert mismatch['total_reason'] == 'CALC_VERSION_MISMATCH' and mismatch['flags'] == ['CALC_VERSION_MISMATCH']


def test_status_file_shapes():
    st = qo.status_payload(attempt_at=NOW, state='SUPPLY_FAILED', reason='IEX_MD5_MISMATCH', official=None, inputs_sha256='a' * 64,
                           inputs_as_of='2026-10-13T00:50:26.737954Z')
    qo.require_status(st)
    assert st['attempt_state'] == 'NO_OFFICIAL_YET' and st['reason_code'] == 'IEX_MD5_MISMATCH'
    for bad in ('x', '4321.0987', 4321.0987):           # latest_inputs.as_of is a clock or null, never a free value
        with pytest.raises(ValueError):
            qo.require_status(dict(st, latest_inputs={'sha256': 'a' * 64, 'as_of': bad}))
    with pytest.raises(ValueError):
        qo.status_payload(attempt_at=NOW, state='OK', reason=None, official=None, inputs_sha256=None, inputs_as_of=None)


# ---- publish tool: keep-last-good ---------------------------------------------------------------------------------
@pytest.fixture
def artifact(tmp_path):
    out = tmp_path / 'artifact'
    out.mkdir()
    payload = base_payload()
    (out / 'sec-qgv2.json').write_bytes(sec_qgv2.encode(payload))
    parser = tmp_path / 'parser'
    parser.write_text('')
    return out, payload, str(parser)


def _run(out, parser, *, previous=None, day=None, key=KEY, months=None, fail=None, now=NOW):
    def fetch_day(keys, basis, parser=None, workdir=None):
        if fail:
            raise iex_hist.IexHistError(fail)
        assert basis == dt.date(2026, 10, 13)          # shard_day(now): the run's New York day
        return day
    return tool.run(out=out, parser=parser, monthend_stamp='20261023', monthend_shards=6, previous=previous, raw_token='t',
                    hmac_key=key, now=now, workdir=out.parent / 'w', fetch_day=fetch_day,
                    read_store=lambda stamp, n: months if months is not None else {}, clock=lambda: now)


def _status(out):
    st = json.loads((out / qo.STATUS_FILENAME).read_text())
    qo.require_status(st)
    return st


def test_tool_first_publication_then_same_id_then_supply_failure_keeps_last_good(artifact, tmp_path):
    out, payload, parser = artifact
    day = synthetic_day(payload, canary_key='NYSE:ABT')
    s = _run(out, parser, day=day)
    assert (s['attempt'], s['published']) == ('OK', 'NEW')
    body = (out / qo.FILENAME).read_bytes()
    live = qo.parse(body)
    assert live['times']['verified_at'] is not None and _status(out)['official_publication_id'] == live['publication_id']
    for name in (qo.FILENAME, qo.STATUS_FILENAME):
        assert '4321.09' not in (out / name).read_text()
    prev = tmp_path / 'live.json'
    prev.write_bytes(body)
    # same inputs + same prices -> same id: live bytes stay
    (out / qo.FILENAME).unlink()
    s = _run(out, parser, previous=str(prev), day=day)
    assert (s['attempt'], s['published']) == ('OK', 'KEPT_SAME_ID') and (out / qo.FILENAME).read_bytes() == body
    # supply failure: the live copy is in the artifact byte for byte, the status says why
    (out / qo.FILENAME).unlink()
    s = _run(out, parser, previous=str(prev), fail='MD5_MISMATCH')
    assert (s['attempt'], s['reason'], s['published']) == ('SUPPLY_FAILED', 'IEX_MD5_MISMATCH', 'KEPT_LAST_GOOD')
    assert (out / qo.FILENAME).read_bytes() == body
    st = _status(out)
    assert st['official_publication_id'] == live['publication_id'] and st['official_price_basis_date'] == '2026-10-13'
    # an older IEX day than the live publication never replaces it
    older = iex_hist.IexDay('2026-10-12', '2026-10-13', day.quotes, day.status, NOW, NOW, {})
    s = _run(out, parser, previous=str(prev), day=older)
    assert (s['reason'], s['published']) == ('BASIS_OLDER_THAN_OFFICIAL', 'KEPT_LAST_GOOD')


def test_tool_broken_live_copy_is_not_shipped_and_no_official_yet(artifact, tmp_path):
    out, payload, parser = artifact
    prev = tmp_path / 'live.json'
    prev.write_text('{"schema":"qgv-official/1"}')
    (out / qo.FILENAME).write_text('{}')
    s = _run(out, parser, previous=str(prev), fail='DOWNLOAD_FAILED')
    assert (s['attempt'], s['reason']) == ('NO_OFFICIAL_YET', 'IEX_DOWNLOAD_FAILED')
    assert not (out / qo.FILENAME).exists()
    s = _run(out, parser, key=None)
    assert (s['attempt'], s['reason']) == ('NO_OFFICIAL_YET', 'HMAC_KEY_MISSING')
    assert _status(out)['official_publication_id'] is None


def test_tool_missing_secret_or_old_file_is_not_run_without_any_download(artifact, tmp_path):
    out, payload, parser = artifact

    def no_fetch(*a, **k):
        raise AssertionError('download attempted')
    for kw, code in (({'raw_token': None}, 'MONTHEND_TOKEN_MISSING'), ({'hmac_key': None}, 'HMAC_KEY_MISSING'),
                     ({'hmac_key': b'short'}, 'HMAC_KEY_MISSING')):
        args = dict(out=out, parser=parser, monthend_stamp='20261023', monthend_shards=6, previous=None, raw_token='t', hmac_key=KEY,
                    now=NOW, workdir=tmp_path / 'w', fetch_day=no_fetch, read_store=no_fetch, clock=lambda: NOW)
        args.update(kw)
        s = tool.run(**args)
        assert (s['attempt'], s['reason'], s['published']) == ('NO_OFFICIAL_YET', code, 'NONE')
        assert _status(out)['reason_code'] == code
    (out / 'sec-qgv2.json').write_bytes(sec_qgv2.encode(pre_u7(payload)))
    s = tool.run(out=out, parser=parser, monthend_stamp='20261023', monthend_shards=6, previous=None, raw_token='t', hmac_key=KEY,
                 now=NOW, workdir=tmp_path / 'w', fetch_day=no_fetch, read_store=no_fetch, clock=lambda: NOW)
    assert (s['attempt'], s['reason']) == ('NO_OFFICIAL_YET', 'SEC_QGV2_CALC_VERSION_BEFORE_U7') and not (out / qo.FILENAME).exists()


def test_tool_holiday_run_keeps_requested_and_actual_basis_and_same_basis_may_replace(artifact, tmp_path):
    """Requested and actual basis are both published (D3): synthetic IexDay with basis 2026-10-12 for the requested New York day
    2026-10-13 (a day without its own file; US markets are open on 2026-10-12, so the real calendar case is the Thanksgiving
    test below, through the real select_day). A later run on the same IEX day (new inputs or prices) is not older and replaces
    the live copy; an older IEX day never does."""
    out, payload, parser = artifact
    holiday = synthetic_day(payload)
    holiday = iex_hist.IexDay('2026-10-12', '2026-10-13', holiday.quotes, holiday.status, NOW, NOW, {})
    s = _run(out, parser, day=holiday)
    live = qo.parse((out / qo.FILENAME).read_bytes())
    assert (s['published'], live['price_source']['requested_basis_date'], live['price_source']['basis_date']) == ('NEW', '2026-10-13', '2026-10-12')
    assert _status(out)['official_price_basis_date'] == '2026-10-12'
    prev = tmp_path / 'live.json'
    prev.write_bytes((out / qo.FILENAME).read_bytes())
    again = synthetic_day(payload, price_of={k: 77.25 for k in holiday.quotes})
    again = iex_hist.IexDay('2026-10-12', '2026-10-13', again.quotes, again.status, NOW, NOW, {})
    s = _run(out, parser, previous=str(prev), day=again)
    assert s['published'] == 'NEW' and qo.parse((out / qo.FILENAME).read_bytes())['publication_id'] != live['publication_id']


def test_tool_source_has_no_price_output_path():
    src = (ROOT / 'tools/qgv_official_publish.py').read_text() + (ROOT / 'src/investment_system/providers/iex_hist.py').read_text()
    assert 'GITHUB_STEP_SUMMARY' not in src and 'actions/cache' not in src and 'upload' not in src.lower().replace('uploaded', '')
    for name in ('quotes', 'price'):
        assert f'print({name}' not in src


def test_tool_preserve_only_copies_valid_bytes_and_drops_broken_ones(artifact, tmp_path):
    out, payload, parser = artifact
    assert _run(out, parser, day=synthetic_day(payload))['published'] == 'NEW'
    live, status = tmp_path / 'live.json', tmp_path / 'status.json'
    live.write_bytes((out / qo.FILENAME).read_bytes())
    status.write_bytes((out / qo.STATUS_FILENAME).read_bytes())
    dest = tmp_path / 'manual'
    dest.mkdir()
    assert tool.preserve(dest, str(live), str(status)) == qo.FILENAME + '+' + qo.STATUS_FILENAME
    assert (dest / qo.FILENAME).read_bytes() == live.read_bytes()
    live.write_text('{"broken":1}')
    assert tool.preserve(dest, str(live), str(status)) == qo.STATUS_FILENAME
    assert not (dest / qo.FILENAME).exists()


def test_main_pops_both_secrets_so_no_child_process_inherits_them(tmp_path, monkeypatch, capsys):
    """Review 2026-10-24: only the publisher's Python process holds the HMAC key and the read token (as arguments); curl, gzip,
    the C parser and node (subprocess without env=) see neither name. Real stream_day / js_check with fake child programs that
    report their environment keys."""
    import gzip
    import hashlib
    import os
    import stat
    import subprocess
    import sys
    names = ('QGV_OFFICIAL_HMAC_KEY', 'RAW_REPO_READ_TOKEN')
    monkeypatch.setenv(names[0], 'test-only-hmac-key-0123456789abcdef')
    monkeypatch.setenv(names[1], 'test-only-read-token')
    dump = tmp_path / 'child-env-keys.txt'

    def program(path, body):
        path.write_text(f'#!{sys.executable}\nimport os, sys\nopen({str(dump)!r}, "a").write("\\n".join(os.environ) + "\\n")\n{body}\n')
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path)
    parser = program(tmp_path / 'parser', 'sys.stdin.buffer.read()\nsys.stdout.write("AAA\\tNO_TRADE\\t0\\t0\\t0\\n")')
    node = program(tmp_path / 'node', 'sys.stdin.read()\nsys.stdout.write("{}")')
    gz = gzip.compress(b'')
    seen = {}

    def stub_run(**kw):
        seen['args'] = (kw['raw_token'], kw['hmac_key'])
        seen['parent'] = [n for n in names if n in os.environ]
        rows = iex_hist.stream_day('https://storage.googleapis.com/iex/data/feeds/20261013/x.pcap.gz', ['AAA'], day='20261013',
                                   size=len(gz), md5=hashlib.md5(gz).hexdigest(), parser=parser, workdir=tmp_path / 'w',
                                   download=lambda link: [sys.executable, '-c', f'import sys; sys.stdout.buffer.write({gz!r})'])
        assert rows == {'AAA': ('NO_TRADE', None)}
        tool.js_check({}, {}, {}, node=node)
        seen['shell'] = subprocess.run([sys.executable, '-c', 'import os; print(" ".join(os.environ))'], capture_output=True,
                                       text=True).stdout.split()
        return {'attempt': 'OK', 'reason': None, 'published': 'NONE', 'basis': '-', 'rows': 0, 'ranked': 0, 'supplied': '-'}
    monkeypatch.setattr(tool, 'run', stub_run)
    out = tmp_path / 'out'
    out.mkdir()
    assert tool.main(['--out', str(out), '--parser', parser, '--monthend-stamp', '20261023', '--previous', '']) == 0
    assert seen['args'] == ('test-only-read-token', b'test-only-hmac-key-0123456789abcdef')
    assert seen['parent'] == [] and not set(names) & set(seen['shell'])
    keys = set(dump.read_text().split())
    assert keys and not set(names) & keys                 # parser and node ran and saw neither name
    assert 'test-only' not in capsys.readouterr().out


# ---- live read: fail closed (review 2026-10-24) -----------------------------------------------------------------------
class _Response:
    def __init__(self, url, body, status=200):
        self.url, self.body, self.status = url, body, status

    def geturl(self):
        return self.url

    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def pages(script):
    """open_response stub: `script` maps a file name to a list of outcomes, one per request: bytes (200), an int HTTP code,
    'timeout', 'redirect'. Requests are recorded (url, headers)."""
    import urllib.error
    seen = []

    def open_response(request, timeout=None):
        url = request.full_url
        seen.append((url, dict(request.header_items())))
        name = url.split('?', 1)[0].rsplit('/', 1)[1]
        outcome = script[name].pop(0) if len(script[name]) > 1 else script[name][0]
        if outcome == 'timeout':
            raise TimeoutError('timed out')
        if outcome == 'redirect':
            return _Response('https://example.invalid/x', b'{}')
        if isinstance(outcome, int):
            raise urllib.error.HTTPError(url, outcome, 'x', {}, None)
        return _Response(url, outcome)
    open_response.seen = seen
    return open_response


def test_load_previous_404_is_none_other_failures_retry_then_unreachable():
    sleeps = []
    o = pages({qo.FILENAME: [404]})
    assert tool.load_previous(tool.LIVE_URL, open_response=o, sleep=sleeps.append, nonce='1-1') is None and sleeps == []
    url, headers = o.seen[0]
    assert url == tool.LIVE_URL + '?qgv-official-step=1-1' and headers.get('Cache-control') == 'no-cache'
    for failure in (500, 503, 'timeout', 'redirect', 403):
        sleeps = []
        o = pages({qo.FILENAME: [failure]})
        with pytest.raises(tool.LiveUnreachable):
            tool.load_previous(tool.LIVE_URL, open_response=o, sleep=sleeps.append)
        assert len(o.seen) == tool.LIVE_READ_ATTEMPTS == 3 and sleeps == [5, 15]
    o = pages({qo.FILENAME: [502, 'timeout', b'live-bytes']})                       # recovers on the third attempt
    assert tool.load_previous(tool.LIVE_URL, open_response=o, sleep=lambda s: None) == b'live-bytes'
    for source in ('https://example.invalid/qgv-official.json', tool.LIVE_URL + '?x=1'):
        with pytest.raises(tool.LiveUnreachable):
            tool.load_previous(source, open_response=pages({qo.FILENAME: [b'x']}), sleep=lambda s: None)


def test_tool_unreachable_live_copy_is_not_run_never_no_official_yet(artifact):
    """A timeout or 5xx on the live read never deletes a live publication on the claim that none exists: nothing is computed
    (the older-basis check needs the live copy), status NOT_RUN / LIVE_UNREACHABLE without a publication id."""
    out, payload, parser = artifact

    def no_fetch(*a, **k):
        raise AssertionError('IEX download attempted')
    for failure in ('timeout', 500, 503):
        (out / qo.FILENAME).write_text('{}')
        s = tool.run(out=out, parser=parser, monthend_stamp='20261023', monthend_shards=6, previous=tool.LIVE_URL, raw_token='t',
                     hmac_key=KEY, now=NOW, workdir=out.parent / 'w', fetch_day=no_fetch, read_store=no_fetch, clock=lambda: NOW,
                     open_response=pages({qo.FILENAME: [failure]}), sleep=lambda s: None)
        assert (s['attempt'], s['reason'], s['published']) == ('NOT_RUN', 'LIVE_UNREACHABLE', 'NONE')
        st = _status(out)
        assert (st['attempt_state'], st['reason_code'], st['official_publication_id']) == ('NOT_RUN', 'LIVE_UNREACHABLE', None)
        assert st['latest_inputs']['sha256'] == qo.sha256_bytes((out / 'sec-qgv2.json').read_bytes())
        assert not (out / qo.FILENAME).exists()
    with pytest.raises(ValueError):          # the status shape cannot say NO_OFFICIAL_YET with LIVE_UNREACHABLE
        qo.require_status(dict(st, attempt_state='NO_OFFICIAL_YET'))


def test_tool_live_404_is_a_first_publication_and_a_late_live_read_keeps_the_basis_check(artifact):
    out, payload, parser = artifact
    day = synthetic_day(payload)
    s = tool.run(out=out, parser=parser, monthend_stamp='20261023', monthend_shards=6, previous=tool.LIVE_URL, raw_token='t',
                 hmac_key=KEY, now=NOW, workdir=out.parent / 'w', fetch_day=lambda *a, **k: day, read_store=lambda s, n: {},
                 clock=lambda: NOW, open_response=pages({qo.FILENAME: [404]}), sleep=lambda s: None)
    assert (s['attempt'], s['published']) == ('OK', 'NEW')
    live = (out / qo.FILENAME).read_bytes()
    # live read fails twice, then answers: the live copy is carried and an older IEX day is still refused
    older = iex_hist.IexDay('2026-10-12', '2026-10-13', day.quotes, day.status, NOW, NOW, {})
    (out / qo.FILENAME).unlink()
    s = tool.run(out=out, parser=parser, monthend_stamp='20261023', monthend_shards=6, previous=tool.LIVE_URL, raw_token='t',
                 hmac_key=KEY, now=NOW, workdir=out.parent / 'w', fetch_day=lambda *a, **k: older, read_store=lambda s, n: {},
                 clock=lambda: NOW, open_response=pages({qo.FILENAME: ['timeout', 500, live]}), sleep=lambda s: None)
    assert (s['reason'], s['published']) == ('BASIS_OLDER_THAN_OFFICIAL', 'KEPT_LAST_GOOD')
    assert (out / qo.FILENAME).read_bytes() == live


def test_preserve_unreachable_live_copy_carries_neither_file(artifact, tmp_path):
    out, payload, parser = artifact
    assert _run(out, parser, day=synthetic_day(payload))['published'] == 'NEW'
    live, status = (out / qo.FILENAME).read_bytes(), (out / qo.STATUS_FILENAME).read_bytes()
    dest = tmp_path / 'manual'
    dest.mkdir()
    ok = pages({qo.FILENAME: [live], qo.STATUS_FILENAME: [status]})
    assert tool.preserve(dest, tool.LIVE_URL, tool.LIVE_STATUS_URL, open_response=ok, sleep=lambda s: None) == \
        qo.FILENAME + '+' + qo.STATUS_FILENAME
    for failure in ('timeout', 500):
        o = pages({qo.FILENAME: [failure], qo.STATUS_FILENAME: [status]})
        assert tool.preserve(dest, tool.LIVE_URL, tool.LIVE_STATUS_URL, open_response=o, sleep=lambda s: None) == 'LIVE_UNREACHABLE'
        assert not (dest / qo.FILENAME).exists() and not (dest / qo.STATUS_FILENAME).exists()
    # no publication yet (404): a valid status is still carried
    o = pages({qo.FILENAME: [404], qo.STATUS_FILENAME: [status]})
    assert tool.preserve(dest, tool.LIVE_URL, tool.LIVE_STATUS_URL, open_response=o, sleep=lambda s: None) == qo.STATUS_FILENAME
    # the status read alone failing keeps the publication (the status is never compared)
    o = pages({qo.FILENAME: [live], qo.STATUS_FILENAME: [503]})
    assert tool.preserve(dest, tool.LIVE_URL, tool.LIVE_STATUS_URL, open_response=o, sleep=lambda s: None) == qo.FILENAME


def test_tool_thanksgiving_run_after_utc_midnight_uses_the_new_york_day_and_real_select_day(artifact):
    """Review 2026-10-24: the daily run starts ~00:37 UTC, already the next UTC day. On 2026-11-27 00:37Z the New York day is
    Thanksgiving 2026-11-26 (no TOPS file): tool.run must ask for 2026-11-26 (shard_day, not the UTC date) and the real
    iex_hist.fetch_day / select_day must pick 2026-11-25; both dates are published."""
    import base64
    import functools
    import hashlib
    out, payload, parser = artifact
    now = dt.datetime(2026, 11, 27, 0, 37, tzinfo=dt.timezone.utc)
    link = 'https://www.googleapis.com/download/storage/v1/b/iex/o/data%2Ffeeds%2F{d}%2F{d}_IEXTP1_TOPS1.6.pcap.gz?generation=1&alt=media'
    index = {d: [{'feed': 'TOPS', 'version': '1.6', 'protocol': 'IEXTP1', 'link': link.format(d=d), 'size': 1000}]
             for d in ('20261123', '20261124', '20261125', '20261127')}            # 11-26 Thanksgiving: no file
    md5 = base64.b64encode(hashlib.md5(b'synthetic').digest()).decode()
    asked, streamed = [], []

    def fetch(url):
        return index if url == iex_hist.HIST_URL else {'size': '1000', 'md5Hash': md5}

    def stream(link_, wanted, *, day, size, md5, parser, workdir):
        streamed.append(day)
        return {s: ('ROUND', (20 + i) * 10000) for i, s in enumerate(wanted)}

    real = functools.partial(iex_hist.fetch_day, fetch=fetch, stream=stream, clock=lambda: now)

    def fetch_day(keys, basis, *, parser, workdir):
        asked.append(basis)
        return real(keys, basis, parser=parser, workdir=workdir)
    s = tool.run(out=out, parser=parser, monthend_stamp='20261023', monthend_shards=6, previous=None, raw_token='t', hmac_key=KEY,
                 now=now, workdir=out.parent / 'w', fetch_day=fetch_day, read_store=lambda st, n: {}, clock=lambda: now)
    assert asked == [dt.date(2026, 11, 26)] and streamed == ['20261125']
    official = qo.parse((out / qo.FILENAME).read_bytes())
    assert (s['attempt'], s['published'], s['basis']) == ('OK', 'NEW', '2026-11-25')
    assert (official['price_source']['requested_basis_date'], official['price_source']['basis_date']) == ('2026-11-26', '2026-11-25')
    assert official['times']['price_basis_date'] == '2026-11-25' and _status(out)['official_price_basis_date'] == '2026-11-25'
