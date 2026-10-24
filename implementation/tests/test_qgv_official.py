"""Central QGV publication (qgv/qgv_official.py, tools/qgv_official_publish.py, tools/qgv_official_js_check.js).

End to end on a SYNTHETIC universe: the strict-valid sec-qgv2 vector base (tests/fixtures/sec_qgv2_vectors_v1.json, expanded to
the 504 Universe codes with empty records) + made-up IEX prices and month-end trades. The F_k (share_basis_factor) history field
of the calc_version lane is simulated by adding it to the payload and validating the stripped copy with the current strict
reader (`fk_reader`). Every price is synthetic; the canary value must never appear in any output, file or exception.
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


def add_fk(payload, factor=1.0):
    p = copy.deepcopy(payload)
    for r in list(p['records'].values()) + list(p['target'].values()):
        for h in (r.get('v_inputs_v2') or {}).get('ebit_per_share_history') or []:
            h['share_basis_factor'] = factor
            h['share_basis_factor_reason'] = None if factor else 'SPLIT_RATIO_UNVERIFIED'
    return p


@pytest.fixture
def fk_reader(monkeypatch):
    """Simulates the calc_version lane's reader extension: F_k keys allowed on history items, everything else strict."""
    original = sec_qgv2.require_qgv2

    def strict(payload):
        q = copy.deepcopy(payload)
        for r in list(q['records'].values()) + list(q['target'].values()):
            for h in (r.get('v_inputs_v2') or {}).get('ebit_per_share_history') or []:
                h.pop('share_basis_factor', None)
                h.pop('share_basis_factor_reason', None)
        original(q)
    monkeypatch.setattr(sec_qgv2, 'require_qgv2', strict)


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
    # V4 without the F_k field (today's file): every month is left out, reason fixed, never filled with 1.0
    v4 = {r['factors']['v_vs_own_history']['reason'] for r in official['rows'].values()
          if r['price_status'] == 'SUPPLIED' and r['profile'] == 'GENERAL' and r['factors']['v_vs_own_history']['score'] is None}
    assert iex_monthend.FK_MISSING in v4 and 'HISTORY_TOO_SHORT' not in v4
    assert all(r['factors']['v_vs_own_history']['score'] is None for r in official['rows'].values())
    # the same inputs give the same id (no clock inside); another price set gives another id
    assert build(payload, synthetic_day(payload, canary_key=canary_key))[0]['publication_id'] == official['publication_id']
    assert build(payload)[0]['publication_id'] != official['publication_id']


def test_share_basis_factor_feeds_v4_raw_divided_by_fk(fk_reader):
    payload = add_fk(base_payload(), 2.0)
    official, internal = build(payload)
    qo.require_qgv_official(official)
    scored = [r for r in official['rows'].values() if r['factors']['v_vs_own_history']['score'] is not None]
    assert scored
    code = next(k for k, q in internal['quotes'].items() if q.get('month_closes'))
    months = synthetic_months(payload)
    for m, close in internal['quotes'][code]['month_closes'].items():
        sym = code.split(':', 1)[1] if ':' in code and not code.startswith('TARGET:') else None
        if sym:
            assert close == months[m]['symbols'][sym]['price_e4'] / 10000 / 2.0
    # F_k null on every item: V4 NA with the item's fixed reason
    off0, _ = build(add_fk(base_payload(), None))
    reasons = {r['factors']['v_vs_own_history']['reason'] for r in off0['rows'].values() if r['price_status'] == 'SUPPLIED'}
    assert 'SPLIT_RATIO_UNVERIFIED' in reasons


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
    ('rank_order', lambda o: (o['rows'][_ranked(o)[0][1]].update(rank=2), o['rows'][_ranked(o)[1][1]].update(rank=1))),
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
