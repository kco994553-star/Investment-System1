"""Forward validation ledger: append-only, price-free, fail-closed (synthetic SEC data and mocked transport only)."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import urllib.error

import pytest

from investment_system.product.public_engine_screens import generate_screen_bundle
from investment_system.validation import forward_device_reference as ref
from investment_system.validation import forward_ledger as fl

ROOT = Path(__file__).resolve().parents[1]
TOKEN = 'synthetic-raw-token-value-0123456789'
BEFORE = datetime(2026, 10, 16, 22, 30, tzinfo=timezone.utc)      # Fri, before the start
MON = datetime(2026, 10, 19, 22, 30, tzinfo=timezone.utc)         # 18:30 New York, start session
TUE = datetime(2026, 10, 20, 22, 30, tzinfo=timezone.utc)
SAT = datetime(2026, 10, 24, 22, 30, tzinfo=timezone.utc)
JS = ROOT / 'src/investment_system/product/web_assets/forward-validation.js'


def load_tool(name):
    spec = importlib.util.spec_from_file_location('_t_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sec_manifest(tmp, acquired):
    cik = '0001045810'
    rows, forms = [], []
    for year, value in zip(range(2022, 2026), (100, 115, 132.25, 152.0875)):
        accn = f'{cik}-{year + 1 - 2000:02d}-000001'
        filed = f'{year + 1}-02-01'
        rows.append({'start': f'{year}-01-01', 'end': f'{year}-12-31', 'val': value, 'accn': accn, 'form': '10-K',
                     'filed': filed, 'fp': 'FY', 'fy': year})
        forms.append((accn, filed, f'{year}-12-31'))
    facts = {'cik': 1045810, 'facts': {'us-gaap': {'Revenues': {'units': {'USD': rows}}}}}
    subs = {'cik': 1045810, 'filings': {'recent': {'form': ['10-K'] * 4, 'accessionNumber': [r[0] for r in forms],
            'filingDate': [r[1] for r in forms], 'reportDate': [r[2] for r in forms],
            'acceptanceDateTime': [r[1] + 'T12:00:00Z' for r in forms]}}}
    (tmp / 'facts.json').write_text(json.dumps(facts))
    (tmp / 'submissions.json').write_text(json.dumps(subs))
    return {'schema_version': 1, 'sec': [{'company_id': 'nvda', 'companyfacts': 'facts.json', 'submissions': 'submissions.json',
            'acquired_at': acquired.isoformat(), 'synthetic': False}], 'macro': [], 'thirteen_f': []}


def site(tmp_path, when, *, live=True, name='site'):
    """Offline price-free build plus that run's sec-qg-factors.json (LIVE for nvda when `live`)."""
    build = load_tool('build_pages_cockpit')
    out = tmp_path / name
    build.build_public_cockpit(out)
    raw = tmp_path / (name + '-raw')
    raw.mkdir()
    manifest = sec_manifest(raw, when - timedelta(hours=1)) if live else {'schema_version': 1, 'sec': [], 'macro': [], 'thirteen_f': []}
    screens = generate_screen_bundle(manifest=manifest, input_root=raw, as_of=when, stale_after=timedelta(hours=24))
    (out / 'sec-qg-factors.json').write_text(json.dumps(screens['sec-qg-factors.json'], sort_keys=True))
    return out


class Response:
    def __init__(self, url, body, status=200):
        self.url, self.body, self.status = url, body, status
    def geturl(self):
        return self.url
    def read(self, n=-1):
        return self.body if n < 0 else self.body[:n]
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False


def missing(request, **_):
    raise urllib.error.HTTPError(request.full_url, 404, '', {}, None)


def serving(body):
    return lambda request, **_: Response(request.full_url, body)


def run(tool, out, when, previous, **kwargs):
    return tool.run(out, environ=kwargs.pop('environ', {}), now=lambda: when, open_previous=previous, **kwargs)


# ---- calendar ----
def test_completed_session_is_same_new_york_day_after_close_only():
    assert fl.completed_session(MON) == MON.date()
    assert fl.completed_session(datetime(2026, 10, 19, 19, 59, tzinfo=timezone.utc)) is None   # 15:59 New York
    assert fl.completed_session(datetime(2026, 10, 20, 2, 0, tzinfo=timezone.utc)) == MON.date()  # 22:00 New York Monday
    assert fl.completed_session(datetime(2026, 10, 20, 14, 0, tzinfo=timezone.utc)) is None   # Tuesday morning: never Monday
    assert fl.completed_session(SAT) is None
    assert fl.completed_session(datetime(2026, 11, 26, 22, 30, tzinfo=timezone.utc)) is None  # Thanksgiving
    assert fl.completed_session(datetime(2026, 12, 21, 22, 30, tzinfo=timezone.utc)) == datetime(2026, 12, 21).date()  # EST
    with pytest.raises(fl.CalendarNotConfigured):
        fl.completed_session(datetime(2029, 1, 2, 22, 30, tzinfo=timezone.utc))


# ---- tool: lifecycle ----
def test_before_start_publishes_not_started_with_zero_records(tmp_path, capsys):
    tool = load_tool('forward_validation_ledger')
    out = site(tmp_path, BEFORE)
    assert run(tool, out, BEFORE, missing) == 0
    ledger = fl.require_ledger(fl.parse_json((out / fl.FILENAME).read_bytes()))
    assert ledger['status'] == 'NOT_STARTED' and ledger['versions'] == {fl.VERSION: [], fl.V_VERSION: []}
    assert ledger['version_status'][fl.V_VERSION] == {'state': 'NOT_AVAILABLE', 'v_included': True, 'reason_codes': ['V_REQUIRES_DEVICE_PRICES']}
    assert ledger['holdout'] == 'UNCONFIRMED_NOT_USED' and ledger['start_date'] == '2026-10-19'
    printed = capsys.readouterr().out
    assert 'status=NOT_STARTED records=0 appended=0' in printed and 'RAW_UPLOAD_NOT_CONFIGURED' in printed


def test_session_record_holds_target_weights_and_q_g_without_v(tmp_path, capsys):
    tool = load_tool('forward_validation_ledger')
    previous = site(tmp_path, BEFORE, name='before')
    assert run(tool, previous, BEFORE, missing) == 0
    out = site(tmp_path, MON)
    assert run(tool, out, MON, serving((previous / fl.FILENAME).read_bytes())) == 0
    ledger = fl.require_ledger(fl.parse_json((out / fl.FILENAME).read_bytes()))
    assert ledger['status'] == 'ACTIVE'
    [record] = ledger['versions'][fl.VERSION]
    assert record['date'] == '2026-10-19' and record['state'] == 'RECORDED' and record['reason_codes'] == []
    assert record['strategy'] == 'QGV_STANDARD_V1' and record['version'] == 'forward_validation/v1' and record['calibration'] == 'UNCALIBRATED'
    catalog = json.loads((out / 'actual-catalog.json').read_text())
    assert record['target']['weights_units'] == dict(zip(fl.IDS, (i['target_units'] for i in catalog['instruments'])))
    assert record['target']['root_sha256'] == catalog['target_root_sha256'] and sum(record['target']['weights_units'].values()) == 10000
    assert record['source_sha256'] == {name: sha256((out / name).read_bytes()).hexdigest() for name in fl.SOURCES}
    nvda = record['companies']['nvda']
    assert nvda['state'] == 'LIVE' and nvda['G']['score'] is not None and nvda['G']['coverage'] == 'PARTIAL'
    assert record['companies']['asml'] == {'state': 'NOT_AVAILABLE', 'Q': {'score': None, 'coverage': 'BLOCKED', 'missing_factor_count': 7},
                                           'G': {'score': None, 'coverage': 'BLOCKED', 'missing_factor_count': 6}}
    assert all(set(row) == {'state', 'Q', 'G'} for row in record['companies'].values())
    assert ledger['versions'][fl.V_VERSION] == []
    assert 'appended=1 record=RECORDED session=2026-10-19' in capsys.readouterr().out


def test_records_are_immutable_and_only_appended(tmp_path, capsys):
    tool = load_tool('forward_validation_ledger')
    first = site(tmp_path, MON, name='mon')
    assert run(tool, first, MON, missing, bootstrap=True) == 0
    monday = (first / fl.FILENAME).read_bytes()
    # A second run on the same day keeps the existing record exactly (later inputs never rewrite it).
    again = site(tmp_path, MON + timedelta(minutes=50), name='again')
    assert run(tool, again, MON + timedelta(minutes=50), serving(monday)) == 0
    kept = fl.parse_json((again / fl.FILENAME).read_bytes())
    assert fl.canonical(kept['versions'][fl.VERSION]) == fl.canonical(fl.parse_json(monday)['versions'][fl.VERSION])
    assert 'appended=0 record=EXISTS' in capsys.readouterr().out
    # Next session: Monday stays byte-identical, Tuesday is appended after it. A Saturday adds nothing.
    tue = site(tmp_path, TUE, name='tue')
    assert run(tool, tue, TUE, serving((again / fl.FILENAME).read_bytes())) == 0
    rows = fl.parse_json((tue / fl.FILENAME).read_bytes())['versions'][fl.VERSION]
    assert [r['date'] for r in rows] == ['2026-10-19', '2026-10-20']
    assert fl.canonical(rows[0]) == fl.canonical(fl.parse_json(monday)['versions'][fl.VERSION][0])
    assert fl.canonical(rows[0]) in (tue / fl.FILENAME).read_text()
    sat = site(tmp_path, SAT, name='sat')
    assert run(tool, sat, SAT, serving((tue / fl.FILENAME).read_bytes())) == 0
    assert len(fl.parse_json((sat / fl.FILENAME).read_bytes())['versions'][fl.VERSION]) == 2


def test_missing_inputs_record_not_available_with_reasons_never_zeros(tmp_path):
    tool = load_tool('forward_validation_ledger')
    out = site(tmp_path, MON)
    (out / 'sec-qg-factors.json').unlink()
    assert run(tool, out, MON, missing, bootstrap=True) == 0
    [record] = fl.parse_json((out / fl.FILENAME).read_bytes())['versions'][fl.VERSION]
    assert record['state'] == 'NOT_AVAILABLE' and record['reason_codes'] == ['SEC_QG_FACTORS_MISSING']
    assert record['companies'] is None and record['target'] is not None and record['source_sha256']['sec-qg-factors.json'] is None
    for mutate, reason in [(lambda o: (o / 'actual-catalog.json').write_text('{}'), 'TARGET_CATALOG_INVALID'),
                           (lambda o: (o / 'sec-qg-factors.json').write_text('{"price":1}'), 'SEC_QG_FACTORS_INVALID')]:
        other = site(tmp_path, MON, name='m' + reason)
        mutate(other)
        assert run(tool, other, MON, missing, bootstrap=True) == 0
        [record] = fl.parse_json((other / fl.FILENAME).read_bytes())['versions'][fl.VERSION]
        assert reason in record['reason_codes'] and record['companies'] is None
    stale_day = site(tmp_path, MON - timedelta(days=1), name='yesterday')
    shutil.copy(stale_day / 'sec-qg-factors.json', out / 'sec-qg-factors.json')
    (out / fl.FILENAME).unlink()
    assert run(tool, out, MON, missing, bootstrap=True) == 0
    assert fl.parse_json((out / fl.FILENAME).read_bytes())['versions'][fl.VERSION][0]['reason_codes'] == ['SEC_QG_FACTORS_NOT_SAME_SESSION']
    empty = site(tmp_path, MON, live=False, name='empty')
    assert run(tool, empty, MON, missing, bootstrap=True) == 0
    assert fl.parse_json((empty / fl.FILENAME).read_bytes())['versions'][fl.VERSION][0]['reason_codes'] == ['SEC_QG_FACTORS_NOT_AVAILABLE']


# ---- tool: fail closed ----
def test_previous_network_error_or_invalid_previous_writes_nothing(tmp_path, capsys):
    tool = load_tool('forward_validation_ledger')
    out = site(tmp_path, MON)
    def broken(request, **_):
        raise urllib.error.URLError('synthetic')
    assert run(tool, out, MON, broken) == 1
    assert not (out / fl.FILENAME).exists() and 'PREVIOUS_FETCH_FAILED nothing_written' in capsys.readouterr().out
    def server_error(request, **_):
        raise urllib.error.HTTPError(request.full_url, 503, '', {}, None)
    assert run(tool, out, MON, server_error) == 1 and not (out / fl.FILENAME).exists()
    assert run(tool, out, MON, serving(b'{"price":1}')) == 1 and not (out / fl.FILENAME).exists()
    assert 'PREVIOUS_INVALID' in capsys.readouterr().out
    assert run(tool, out, MON, serving(b'{}'), preserve_only=True) == 1 and not (out / fl.FILENAME).exists()


def test_404_after_start_needs_explicit_bootstrap(tmp_path, capsys):
    tool = load_tool('forward_validation_ledger')
    out = site(tmp_path, TUE)
    assert run(tool, out, TUE, missing) == 1 and not (out / fl.FILENAME).exists()
    assert 'PREVIOUS_MISSING_AFTER_START nothing_written' in capsys.readouterr().out
    assert run(tool, out, TUE, missing, bootstrap=True) == 0
    assert [r['date'] for r in fl.parse_json((out / fl.FILENAME).read_bytes())['versions'][fl.VERSION]] == ['2026-10-20']


def test_preserve_only_restores_exact_bytes_and_tolerates_404(tmp_path, capsys):
    tool = load_tool('forward_validation_ledger')
    first = site(tmp_path, MON, name='mon')
    assert run(tool, first, MON, missing, bootstrap=True) == 0
    body = (first / fl.FILENAME).read_bytes()
    out = tmp_path / 'ui'
    out.mkdir()
    assert run(tool, out, TUE, serving(body), preserve_only=True) == 0
    assert (out / fl.FILENAME).read_bytes() == body
    other = tmp_path / 'ui404'
    other.mkdir()
    assert run(tool, other, TUE, missing, preserve_only=True) == 0 and not (other / fl.FILENAME).exists()
    assert 'PREVIOUS_RESTORED records=1' in capsys.readouterr().out


def test_raw_upload_uses_dated_private_release_and_never_prints_token(tmp_path, capsys):
    tool = load_tool('forward_validation_ledger')
    out = site(tmp_path, MON)
    calls = []
    def call(method, url, *, data=None, headers=None, auth=True):
        calls.append((method, url, data, dict(headers or {})))
        if method == 'GET':
            return 404, {}, b''
        if url.endswith('/releases'):
            return 201, {}, json.dumps({'id': 7, 'assets': []}).encode()
        return 201, {}, b'{"size":1}'
    assert run(tool, out, MON, missing, bootstrap=True, environ={'RAW_REPO_TOKEN': TOKEN}, upload_call=call) == 0
    printed = capsys.readouterr().out
    assert TOKEN not in printed and 'RAW_UPLOADED tag=forward-ledger-2026-10-19' in printed
    assert calls[0][1].endswith('/repos/kco994553-star/investment-system1-raw/releases/tags/forward-ledger-2026-10-19')
    assert json.loads(calls[1][2])['tag_name'] == 'forward-ledger-2026-10-19'
    assert calls[2][1].endswith('assets?name=forward-validation-ledger.json') and calls[2][2] == (out / fl.FILENAME).read_bytes()
    assert calls[3][2].decode().startswith(sha256(calls[2][2]).hexdigest())
    def denied(method, url, **_):
        return 403, {}, b''
    other = site(tmp_path, MON, name='denied')
    assert run(tool, other, MON, missing, bootstrap=True, environ={'RAW_REPO_TOKEN': TOKEN}, upload_call=denied) == 0
    printed = capsys.readouterr().out
    assert 'RAW_UPLOAD_FAILED code=RELEASE_LOOKUP_FAILED' in printed and TOKEN not in printed and (other / fl.FILENAME).exists()
    weekend = site(tmp_path, SAT, name='weekend')
    assert run(tool, weekend, SAT, serving((out / fl.FILENAME).read_bytes()), environ={'RAW_REPO_TOKEN': TOKEN}, upload_call=denied) == 0
    assert 'RAW_UPLOAD_SKIPPED no_session_record' in capsys.readouterr().out


# ---- validator ----
def ledger_with_records(tmp_path):
    tool = load_tool('forward_validation_ledger')
    mon = site(tmp_path, MON, name='vmon')
    assert tool.run(mon, environ={}, now=lambda: MON, open_previous=missing, bootstrap=True) == 0
    tue = site(tmp_path, TUE, name='vtue')
    assert tool.run(tue, environ={}, now=lambda: TUE, open_previous=serving((mon / fl.FILENAME).read_bytes())) == 0
    return fl.parse_json((tue / fl.FILENAME).read_bytes())


def mutations():
    def at(path, value):
        def apply(p):
            node = p
            for key in path[:-1]:
                node = node[key]
            if value is KeyError:
                del node[path[-1]]
            else:
                node[path[-1]] = value
        return apply
    rec = ('versions', fl.VERSION, 0)
    return [
        at(('price',), 1), at(('status',), 'NOT_STARTED'), at(('holdout',), 'USED'), at(('start_date',), '2026-10-12'),
        at(('versions', fl.V_VERSION), [{'date': '2026-10-19'}]), at(rec + ('date',), '2026-10-18'),
        at(rec + ('date',), '2026-10-20'), at(rec + ('companies', 'nvda', 'V'), {'score': 1}),
        at(rec + ('companies', 'asml', 'Q', 'score'), 0), at(rec + ('target', 'weights_units', 'asml'), 901),
        at(rec + ('target', 'weights_units', 'price'), 1), at(rec + ('reason_codes',), ['SEC_QG_FACTORS_MISSING']),
        at(rec + ('created_at',), '2026-10-19T19:00:00+00:00'), at(rec + ('strategy',), 'QGV_V2'),
        at(rec + ('companies', 'nvda', 'G', 'score'), 101), at(rec + ('qg_screen_state',), 'STALE'),
    ]


def test_validator_rejects_rewrites_v_values_zeros_and_dates(tmp_path):
    good = ledger_with_records(tmp_path)
    fl.require_ledger(good)
    for mutate in mutations():
        bad = json.loads(json.dumps(good))
        mutate(bad)
        with pytest.raises(ValueError, match='FORWARD_LEDGER_INVALID'):
            fl.require_ledger(bad)
    previous = json.loads(json.dumps(good))
    for change in (lambda p: p['versions'][fl.VERSION].pop(0), lambda p: p['versions'][fl.VERSION].reverse(),
                   lambda p: p['versions'][fl.VERSION][0].update(created_at='2026-10-19T22:31:00+00:00')):
        current = json.loads(json.dumps(good))
        change(current)
        with pytest.raises(ValueError, match='FORWARD_LEDGER_NOT_APPEND_ONLY|FORWARD_LEDGER_INVALID'):
            fl.require_append_only(previous, current)
            fl.require_ledger(current)
    with pytest.raises(ValueError):
        fl.append(good, dict(good['versions'][fl.VERSION][0]), TUE)


def test_parser_rejects_nonfinite_duplicate_and_oversized():
    for body in (b'{"a":NaN}', b'{"a":1,"a":2}', b'\xff', b' ' * (fl.MAX_BYTES + 1)):
        with pytest.raises(ValueError, match='FORWARD_LEDGER_INVALID'):
            fl.parse_json(body)


def test_pages_guard_allows_ledger_and_rejects_tampered_values(tmp_path):
    guard = load_tool('pages_artifact_guard')
    good = ledger_with_records(tmp_path)
    out = site(tmp_path, TUE, name='guard')
    (out / fl.FILENAME).write_bytes(fl.encode(good))
    assert guard.scan_artifact(out)['pages_artifact_guard'] == 'PASS'
    good['versions'][fl.VERSION][0]['companies']['nvda']['Q']['score'] = 0
    (out / fl.FILENAME).write_text(json.dumps(good))
    receipt = guard.scan_artifact(out)
    assert receipt['pages_artifact_guard'] == 'FAIL' and receipt['violations'].get('forward_ledger_boundary') == 1


def test_offline_build_does_not_emit_a_ledger(tmp_path):
    out = tmp_path / 'offline'
    load_tool('build_pages_cockpit').build_public_cockpit(out)
    assert not (out / fl.FILENAME).exists()


# ---- device reference vectors ----
def test_reference_fixture_is_regenerated_from_python_reference():
    tool = load_tool('forward_validation_reference')
    assert (ROOT / 'tests/fixtures/forward_validation_reference_v1.json').read_text() == tool.text()
    with pytest.raises(ValueError, match='SYNTHETIC_ONLY'):
        tool.replay({'synthetic': False, 'operation': 'forward_return', 'input': {}})


def test_reference_never_turns_missing_prices_into_zero():
    weights = {'a': 600, 'b': 400}
    out = ref.forward_return(start_date='2026-10-19', weights_units=weights, series={'a': [
        {'session_date': '2026-10-19', 'adjusted_close': 10.0, 'session_status': 'COMPLETE'},
        {'session_date': '2026-10-20', 'adjusted_close': 11.0, 'session_status': 'COMPLETE'}]})
    assert out['state'] == 'NOT_AVAILABLE' and out['portfolio_return'] is None
    assert out['instruments']['b'] == {'state': 'NOT_AVAILABLE', 'reason': 'HISTORY_NOT_LOADED'}
    assert out['benchmark'] == {'state': 'NOT_AVAILABLE', 'reason': 'SP500_NOT_IN_PRIVATE_HISTORY_WORKER'}


@pytest.mark.skipif(shutil.which('node') is None, reason='Node runtime required')
def test_browser_reader_validator_agrees_with_python_validator(tmp_path):
    script = ("const a=require(process.argv[1]),p=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "try{a.validate(p);console.log('OK')}catch(e){console.log('REJECT')}")
    node = lambda payload: subprocess.run(['node', '-e', script, str(JS)], input=json.dumps(payload), text=True,
                                          capture_output=True).stdout.strip()
    good = ledger_with_records(tmp_path)
    assert node(good) == 'OK' and node(fl.new_ledger(BEFORE)) == 'OK'
    for mutate in mutations():
        bad = json.loads(json.dumps(good))
        mutate(bad)
        assert node(bad) == 'REJECT'
