"""Dual QGV forward versions: same-session only, immutable old records, no price inputs."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from investment_system.validation import forward_ledger as fl
from investment_system.universe import sec_qgv2 as q

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
MON = datetime(2026, 10, 19, 22, 30, tzinfo=timezone.utc)


def source(at='2026-10-19T22:30:00Z'):
    from sec_qgv2_reference import expand
    value = expand(json.loads((ROOT / 'tests/fixtures/sec_qgv2_vectors_v1.json').read_text())['base'])
    # Source fixture represents real-shaped SEC inputs with synthetic amounts, never live data.
    value['as_of'] = at
    for row in [*value['records'].values(), *value['target'].values()]:
        if row['acquired_at']:
            row['acquired_at'] = at
    return q.encode(q.require_qgv2(value))


def test_valid_source_v2_qg_same_session_and_target_weights(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('_build_v2_test', ROOT / 'tools/build_pages_cockpit.py')
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    build.build_public_cockpit(tmp_path / 'site')
    result = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=source(),
                                catalog_body=(tmp_path / 'site/actual-catalog.json').read_bytes())
    assert result['state'] == 'RECORDED'
    assert result['version'] == fl.V2_VERSION and result['strategy'] == fl.V2_STRATEGY
    assert result['companies']['nvda']['Q']['missing_factor_count'] <= 5
    assert all(set(row) == {'state', 'Q', 'G'} for row in result['companies'].values())
    ledger = fl.append(fl.new_ledger(MON), result, MON)
    fl.require_ledger(ledger)
    node = subprocess.run(['node', '-e', "const m=require(process.argv[1]);m.validate(JSON.parse(process.argv[2]));", str(ROOT / 'src/investment_system/product/web_assets/forward-validation.js'), fl.encode(ledger).decode()], capture_output=True)
    assert node.returncode == 0, node.stderr.decode()


def test_missing_stale_future_v2_sources_are_na_never_backfilled():
    missing = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=None, catalog_body=None)
    assert missing['reason_codes'] == ['TARGET_CATALOG_MISSING', 'SEC_QGV2_MISSING']
    old = json.loads(source('2026-10-18T22:30:00Z'))
    stale = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=q.encode(old), catalog_body=None)
    assert 'SEC_QGV2_NOT_SAME_SESSION' in stale['reason_codes']
    ledger = fl.new_ledger(MON)
    with pytest.raises(ValueError):
        fl.require_ledger(fl.append(ledger, {**missing, 'date': '2026-10-18'}, MON + timedelta(days=1)))


def test_schema_one_upgrade_preserves_every_record_and_v2_starts_now():
    v1 = fl.build_record(now=MON, session=MON.date(), qg_body=None, catalog_body=None)
    old = fl.append(fl.new_ledger(MON), v1, MON)
    old['schema_version'], old['strategy'] = 1, fl.STRATEGY
    old['versions'].pop(fl.V2_VERSION)
    old['version_status'].pop(fl.V2_VERSION)
    fl.require_ledger(old)
    upgraded = fl.finalize(old, MON + timedelta(days=1))
    assert fl.canonical(old['versions'][fl.VERSION]) == fl.canonical(upgraded['versions'][fl.VERSION])
    assert upgraded['versions'][fl.V2_VERSION] == []
    fl.require_append_only(old, upgraded)
    fl.require_ledger(upgraded)


def test_dart_reference_is_optional_same_session_hashed_and_v2_only(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('_build_dart_reference', ROOT / 'tools/build_pages_cockpit.py')
    build = importlib.util.module_from_spec(spec); spec.loader.exec_module(build)
    build.build_public_cockpit(tmp_path / 'site')
    catalog = (tmp_path / 'site/actual-catalog.json').read_bytes()
    dart = b'{"synthetic":true}'
    from investment_system.qgv.v2_scoring import Q_WEIGHTS_V2, G_WEIGHTS_V2
    factors = {f: 50.0 for f in (*Q_WEIGHTS_V2, *G_WEIGHTS_V2)}
    reference = {'state': 'LIVE', 'as_of': '2026-10-19T22:00:00Z', 'source_kind': 'DART', 'reference_only': True,
                 'comparison_basis': 'US_UNIVERSE_504_GENERAL', 'factors': factors,
                 'axes': {a: {'score': 50.0} for a in ('Q', 'G')}}
    provider = lambda financials, sec, **kw: reference
    plain = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=source(), catalog_body=catalog)
    with_ref = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=source(), catalog_body=catalog, dart_body=dart, reference_provider=provider)
    assert plain['companies']['hanmi']['Q']['score'] is None and 'reference_sources' not in plain
    assert fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=source(), catalog_body=catalog, dart_body=dart) == plain
    assert with_ref['companies']['hanmi']['Q']['score'] == 50
    assert with_ref['reference_sources']['hanmi']['sha256'] == sha256(dart).hexdigest()
    v1 = fl.build_record(now=MON, session=MON.date(), qg_body=None, catalog_body=catalog)
    ledger = fl.append(fl.append(fl.new_ledger(MON), v1, MON), with_ref, MON)
    fl.require_ledger(ledger)
    assert ledger['versions'][fl.VERSION] == [v1]
    code = "const m=require(process.argv[1]);m.validate(JSON.parse(process.argv[2]));"
    assert subprocess.run(['node', '-e', code, str(ROOT / 'src/investment_system/product/web_assets/forward-validation.js'), fl.encode(ledger).decode()], capture_output=True).returncode == 0
    for changes in ({'as_of': '2026-10-18T22:00:00Z'}, {'as_of': '2026-10-19T23:00:00Z'}, {'reference_only': False}, {'source_kind': 'SEC'}, {'axes': {'Q': {'score': 90}, 'G': {'score': 50}}}):
        bad = lambda financials, sec, **kw: {**reference, **changes}
        result = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=source(), catalog_body=catalog, dart_body=dart, reference_provider=bad)
        assert result == plain
    broken = lambda *a, **kw: (_ for _ in ()).throw(ValueError('bad'))
    assert fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=source(), catalog_body=catalog, dart_body=dart, reference_provider=broken) == plain
    wrong = json.loads(fl.encode(ledger));wrong['versions'][fl.V2_VERSION][0]['reference_sources']['hanmi']['kind'] = 'SEC'
    with pytest.raises(ValueError): fl.require_ledger(wrong)
    assert subprocess.run(['node', '-e', code, str(ROOT / 'src/investment_system/product/web_assets/forward-validation.js'), json.dumps(wrong)], capture_output=True).returncode != 0
    # UTC midnight does not create a new US trading session.
    late = MON + timedelta(hours=4)
    overnight = lambda *a, **kw: {**reference, 'as_of': '2026-10-20T01:00:00Z'}
    night = fl.build_v2_record(now=late, session=MON.date(), qgv2_body=source(), catalog_body=catalog, dart_body=dart, reference_provider=overnight)
    assert night['companies']['hanmi']['Q']['score'] == 50
    fl.require_ledger(fl.append(fl.new_ledger(late), night, late))


# ---- observation basis (owner instruction 2026-10-16): synthetic only ----
VERSION_A, VERSION_B = 'qgv2-calc/2026-10-15.1', 'qgv2-calc/2026-11-02.1'
READER = ROOT / 'src/investment_system/product/web_assets/forward-validation.js'


def screen(*, q=504, g=504, version=VERSION_A, acquired='2026-10-19T21:00:00Z', old_version_rows=0, normal_na_rows=0,
           stale_at=None):
    """A minimal validated-shape sec-qgv2 payload (only the fields the basis reads). 504 Universe rows, one CIK each."""
    records = {}
    for i in range(fl.UNIVERSE_SIZE):
        na = i >= fl.UNIVERSE_SIZE - normal_na_rows
        row = {'cik': None if na else f'{i + 1:010d}', 'state': 'NOT_AVAILABLE' if na else 'LIVE',
               'acquired_at': None if na else (stale_at if stale_at and i == 0 else acquired),
               'axes': {'Q': {'score': 50.0 if i < q and not na else None}, 'G': {'score': 40.0 if i < g and not na else None}}}
        if version is not None:
            row['calc_version'] = None if na else ('qgv2-calc/2026-10-01.1' if i < old_version_rows else version)
        records[f'C{i:03d}'] = row
    target = {'nvda': {'cik': '0001045810', 'state': 'LIVE', 'acquired_at': acquired, 'axes': {},
                       **({'calc_version': version} if version is not None else {})}}
    same = lambda r: version is None or r.get('calc_version') == version
    payload = {'records': records, 'target': target, 'as_of': '2026-10-19T22:00:00Z',
               'cross_section_size': sum(1 for r in records.values() if r['state'] == 'LIVE' and same(r))}
    if version is not None:
        payload['calc_version'] = version
    return payload


def basis_for(**kwargs):
    return fl.observation_basis(screen(**kwargs), MON.date())


def test_primary_only_when_coverage_version_and_row_freshness_all_hold():
    b = basis_for()
    assert b['evaluation'] == {'eligible': True, 'status': 'PRIMARY', 'reasons': []}
    assert b['calc_version'] == b['segment'] == VERSION_A and (b['q_scored'], b['g_scored']) == (504, 504)
    assert b['population']['n'] == 504 and len(b['population']['id']) == 16 and b['acquired'] == ['2026-10-19', '2026-10-19']
    assert set(b) == set(fl.BASIS_KEYS)  # counts, an id and dates only: no per-company list
    assert basis_for(q=454, g=454)['evaluation']['status'] == 'PRIMARY'  # T-COV boundary: 454 of 504 passes
    # A normal NA row (no data, no calc_version) never blocks; it stays in the 504 denominator.
    assert basis_for(normal_na_rows=40)['evaluation']['status'] == 'PRIMARY'


def test_preparatory_with_reasons_when_a_condition_fails():
    assert basis_for(q=453)['evaluation'] == {'eligible': False, 'status': 'PREPARATORY', 'reasons': ['Q_BELOW_454']}
    assert basis_for(q=300, g=200)['evaluation']['reasons'] == ['Q_BELOW_454', 'G_BELOW_454']
    # One valued row still carries an older calculation result -> CALC_VERSION_MIXED (it left the ranking population).
    mixed = basis_for(old_version_rows=1, q=503)
    assert mixed['evaluation']['reasons'] == ['CALC_VERSION_MIXED'] and mixed['population']['n'] == 503
    legacy = basis_for(version=None)
    assert legacy['evaluation']['reasons'] == ['CALC_VERSION_MISSING'] and legacy['segment'] == 'NONE'
    # T-FRESH: the row's own acquisition, never the file as_of (which is new here).
    stale = basis_for(stale_at='2026-10-11T23:00:00Z')
    assert stale['evaluation']['reasons'] == ['ROW_DATA_STALE'] and stale['acquired'] == ['2026-10-11', '2026-10-19']
    assert basis_for(stale_at='2026-10-12T00:00:00Z')['evaluation']['status'] == 'PRIMARY'  # 7 days: still fresh


def _catalog(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location('_build_basis', ROOT / 'tools/build_pages_cockpit.py')
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    build.build_public_cockpit(tmp_path / 'site')
    return (tmp_path / 'site/actual-catalog.json').read_bytes()


def node_ok(payload):
    code = ("const m=require(process.argv[1]);try{m.validate(JSON.parse(require('fs').readFileSync(0,'utf8')));"
            "console.log('OK')}catch(e){console.log('REJECT')}")
    done = subprocess.run(['node', '-e', code, str(READER)], input=json.dumps(payload), text=True, capture_output=True)
    return done.stdout.strip() == 'OK'


def test_new_v2_record_carries_the_basis_of_the_input_it_used(tmp_path):
    catalog = _catalog(tmp_path)
    body = source()
    record = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=body, catalog_body=catalog)
    used = q.require_qgv2(q.parse_json(body))
    assert record['basis'] == fl.observation_basis(used, MON.date())
    assert record['source_sha256']['sec-qgv2.json'] == sha256(body).hexdigest()  # the input pointer is reused, not repeated
    assert record['basis']['calc_version'] == used.get('calc_version')
    b = record['basis']
    expected = [r for r, hit in (('Q_BELOW_454', b['q_scored'] < 454), ('G_BELOW_454', b['g_scored'] < 454),
                                 ('CALC_VERSION_MISSING', used.get('calc_version') is None)) if hit]
    assert b['evaluation'] == {'eligible': False, 'status': 'PREPARATORY', 'reasons': expected}
    missing = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=None, catalog_body=catalog)
    assert missing['basis'] == fl.not_available_basis()
    v1 = fl.build_record(now=MON, session=MON.date(), qg_body=None, catalog_body=catalog)
    assert 'basis' not in v1  # the v1 comparison record is unchanged
    ledger = fl.append(fl.append(fl.new_ledger(MON), v1, MON), record, MON)
    fl.require_ledger(ledger)
    assert node_ok(ledger)
    ledger = fl.append(ledger, {**missing, 'date': '2026-10-20', 'created_at': '2026-10-20T22:30:00+00:00'}, MON + timedelta(days=1))
    fl.require_ledger(ledger)
    assert node_ok(ledger)


def basis_ledger(tmp_path):
    """10/19 row written before the basis existed, then PRIMARY (A), PREPARATORY (A, stale) and PRIMARY (B) rows."""
    catalog = _catalog(tmp_path)
    days = [MON + timedelta(days=d) for d in (0, 1, 2, 3)]
    ledger = fl.new_ledger(MON)
    for i, when in enumerate(days):
        record = fl.build_v2_record(now=when, session=when.date(), qgv2_body=source(when.strftime('%Y-%m-%dT%H:%M:%SZ')),
                                    catalog_body=catalog)
        if i == 0:
            record.pop('basis')
        else:
            kwargs = [{}, {'stale_at': '2026-10-11T00:00:00Z'}, {'version': VERSION_B}][i - 1]
            record['basis'] = fl.observation_basis(screen(**kwargs), when.date())
        ledger = fl.append(ledger, record, when)
    return ledger, days


def test_old_rows_without_basis_stay_valid_and_byte_identical(tmp_path):
    ledger, days = basis_ledger(tmp_path)
    fl.require_ledger(ledger)
    assert node_ok(ledger)
    old = json.loads(fl.encode(ledger))
    old['versions'][fl.V2_VERSION] = old['versions'][fl.V2_VERSION][:1]
    old = fl.finalize(old, days[0])
    fl.require_ledger(old)
    fl.require_append_only(old, ledger)
    assert fl.canonical(old['versions'][fl.V2_VERSION][0]) == fl.canonical(ledger['versions'][fl.V2_VERSION][0])
    assert 'basis' not in ledger['versions'][fl.V2_VERSION][0]


def test_basis_validator_agrees_between_python_and_the_device_reader(tmp_path):
    ledger, _ = basis_ledger(tmp_path)

    def at(index, *path, value=KeyError):
        def apply(p):
            node = p['versions'][fl.V2_VERSION][index]
            for key in path[:-1]:
                node = node[key]
            if value is KeyError:
                del node[path[-1]]
            else:
                node[path[-1]] = value
        return apply
    mutations = [
        at(1, 'basis', 'evaluation', 'status', value='PREPARATORY'),         # preparatory without a reason
        at(2, 'basis', 'evaluation', 'reasons', value=[]),                   # a stale row shown without its reason
        at(2, 'basis', 'evaluation', 'reasons', value=['ROW_DATA_STALE', 'ROW_DATA_STALE']),
        at(1, 'basis', 'evaluation', 'eligible', value=False),
        at(1, 'basis', 'q_scored', value=453),                               # below 454 without Q_BELOW_454
        at(1, 'basis', 'segment', value=VERSION_B),                          # the segment is the calc_version
        at(1, 'basis', 'calc_version', value=None),
        at(1, 'basis', 'acquired', value=['2026-10-21', '2026-10-21']),      # acquired after the record
        at(1, 'basis', 'population', 'codes', value=['C000']),               # no per-company list
        at(1, 'basis', 'population', 'id', value='XYZ'),
        at(3, 'basis'),                                                      # basis dropped once it started
        at(1, 'basis', 'evaluation', 'reasons', value=['G_BELOW_454', 'Q_BELOW_454']),
    ]
    assert node_ok(ledger)
    for mutate in mutations:
        bad = json.loads(fl.encode(ledger))
        mutate(bad)
        with pytest.raises(ValueError, match='FORWARD_LEDGER_INVALID'):
            fl.require_ledger(bad)
        assert not node_ok(bad)
    # The basis belongs to v2 rows only.
    v1 = fl.build_record(now=MON, session=MON.date(), qg_body=None, catalog_body=None)
    bad = json.loads(fl.encode(fl.append(fl.new_ledger(MON), v1, MON)))
    bad['versions'][fl.VERSION][0]['basis'] = fl.not_available_basis()
    with pytest.raises(ValueError):
        fl.require_ledger(bad)
    assert not node_ok(bad)


def test_a_calc_version_change_starts_a_separate_segment_and_preparatory_rows_stay_out(tmp_path):
    ledger, _ = basis_ledger(tmp_path)
    segments = fl.evaluation_segments(ledger['versions'][fl.V2_VERSION])
    assert [(s['segment'], s['eligible_dates'], s['preparatory_dates']) for s in segments] == [
        ('LEGACY', ['2026-10-19'], []), (VERSION_A, ['2026-10-20'], ['2026-10-21']), (VERSION_B, ['2026-10-22'], [])]
    from investment_system.qgv import virtual_trading_inputs as vi
    assert [r['date'] for r in vi.evaluation_records(ledger['versions'][fl.V2_VERSION])] == ['2026-10-22']
    script = ("const f=require(process.argv[1]),r=require(process.argv[2]);const p=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "f.validate(p);const rows=p.versions['forward_validation/v2'];"
              "console.log(JSON.stringify({segments:f.segments(rows),run:r.evaluationRecords(rows).map(x=>x.date),"
              "labels:rows.map(x=>f.rowEvaluation(x).status)}));")
    done = subprocess.run(['node', '-e', script, str(READER), str(READER.parent / 'virtual-trading-runner.js')],
                          input=fl.encode(ledger).decode(), text=True, capture_output=True)
    assert done.returncode == 0, done.stderr[-400:]
    out = json.loads(done.stdout)
    assert out['segments'] == segments and out['run'] == ['2026-10-22']
    assert out['labels'] == ['LEGACY', 'PRIMARY', 'PREPARATORY', 'PRIMARY']


def test_basis_stays_compact():
    b = basis_for()
    reasons = [r for r in fl.EVALUATION_REASONS if r not in ('RECORD_NOT_AVAILABLE', 'BASIS_NOT_COMPUTED')]
    worst = dict(b, evaluation={'eligible': False, 'status': 'PREPARATORY', 'reasons': reasons})
    assert len(fl.canonical(b)) < 300 and len(fl.canonical(worst)) < 400


def test_a_basis_failure_never_loses_the_days_row(tmp_path, monkeypatch):
    catalog = _catalog(tmp_path)

    def broken(*_args, **_kwargs):
        raise KeyError('synthetic')
    monkeypatch.setattr(fl, 'observation_basis', broken)
    record = fl.build_v2_record(now=MON, session=MON.date(), qgv2_body=source(), catalog_body=catalog)
    assert record['state'] == 'RECORDED' and record['basis'] == fl.unknown_basis()
    assert fl.row_evaluation(record) == {'status': 'PREPARATORY', 'segment': 'NONE', 'reasons': ['BASIS_NOT_COMPUTED']}
    ledger = fl.append(fl.new_ledger(MON), record, MON)
    fl.require_ledger(ledger)
    assert node_ok(ledger)
    bad = json.loads(fl.encode(ledger))
    bad['versions'][fl.V2_VERSION][0]['basis']['q_scored'] = 504
    with pytest.raises(ValueError):
        fl.require_ledger(bad)
    assert not node_ok(bad)
