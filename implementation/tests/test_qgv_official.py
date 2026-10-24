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


def test_supply_threshold_keeps_last_good():
    payload = base_payload()
    ctx = qo.prepare(payload, NOW)
    eligible = [k for k, r in ctx['inputs']['records'].items() if not k.startswith('TARGET:') and r['in_cross_section']
                and r['published_profile'] == 'GENERAL' and r['v_inputs']]
    with pytest.raises(qo.OfficialError) as e:
        build(payload, synthetic_day(payload, drop=eligible[:2]))
    assert (e.value.state, e.value.code) == ('SUPPLY_FAILED', 'SUPPLY_BELOW_THRESHOLD')
    official, _ = build(payload, synthetic_day(payload, drop=['NASDAQ:AAPL']))    # a non-eligible miss is fine
    assert official['price_source']['rejected']['NO_IEX_TRADE'] == 1


def _count_from_annual_filing(payload, code):
    """The row's latest diluted-share count is the FY0 annual one (period end = the last history item's fiscal_year_end)."""
    p = copy.deepcopy(payload)
    v = p['records'][code]['v_inputs_v2']
    v['diluted_shares']['period_end'] = v['ebit_per_share_history'][-1]['fiscal_year_end']
    sec_qgv2.require_qgv2(p)
    return p


def test_current_price_split_check_reads_the_fk_evidence_d6a(monkeypatch):
    """D6 (a): SPLIT_TIMING_UNCONFIRMED on the history item at/after the share count's period end = a possible split after the
    count's period end -> SPLIT_AFTER_SHARE_COUNT (no price, V NA, not in the D-CV5 denominator). No new source, no table entry."""
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
    st = qo.status_payload(attempt_at=NOW, state='SUPPLY_FAILED', reason='IEX_MD5_MISMATCH', official=None, inputs_sha256='a' * 64, inputs_as_of='x')
    qo.require_status(st)
    assert st['attempt_state'] == 'NO_OFFICIAL_YET' and st['reason_code'] == 'IEX_MD5_MISMATCH'
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
    """A run on a market holiday: requested = the run's New York day, basis = the last IEX day before it (D3). A later run on the
    same IEX day (new inputs or prices) is not older and replaces the live copy; an older IEX day never does."""
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
