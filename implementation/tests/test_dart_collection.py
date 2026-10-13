"""OpenDART 042700 collection: synthetic transports only (no network). Key masking, call budget, corp_code, mapping."""
import copy
from datetime import timedelta
import io
import json
from pathlib import Path
import subprocess
import sys
import urllib.error
from urllib.parse import parse_qs, urlsplit
import zipfile

import pytest

from investment_system.product import dart_public as dp
from investment_system.providers import dart_collection as dc
from investment_system.providers.dart_collection import DartResponse
from tests.dart_fake_opendart import CORP_CODE, FAKE_KEY, NOW, FakeOpenDart, corp_zip

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
sys.path.insert(0, str(TOOLS))
import dart_daily  # noqa: E402


def no_previous(request, timeout):
    raise urllib.error.HTTPError(request.full_url, 404, 'not found', {}, None)


def run(tmp_path, transport=None, *, key=FAKE_KEY, now=NOW, max_calls=30, previous=no_previous):
    out = tmp_path / 'site'
    out.mkdir(parents=True, exist_ok=True)
    dart_daily.emit(out, as_of=now)
    environ = {} if key is None else {'DART_API_KEY': key}
    code = dart_daily.run(out, environ=environ, transport=transport, now=now, max_calls=max_calls, open_previous=previous)
    files = {name: json.loads((out / name).read_text()) for name in dp.FILENAMES}
    return code, files, out


def assert_no_key(*texts):
    for text in texts:
        assert FAKE_KEY not in (text if isinstance(text, str) else text.decode('utf-8', 'replace'))


# ---------------------------------------------------------------- happy path and mapping


def test_full_run_publishes_validated_files_with_ten_calls(tmp_path, capsys):
    fake = FakeOpenDart()
    code, files, out = run(tmp_path, fake)
    printed = capsys.readouterr()
    assert code == 0 and 'DART_COLLECTION_OK' in printed.out
    assert 'DART_CALLS used=10 budget=30 hard_max=50 documented_daily_limit=20000' in printed.out
    assert len(fake.requests) == 10 and {e for e, _ in fake.requests} <= dc.ENDPOINTS
    disclosures, financials = files[dp.DISCLOSURES_FILENAME], files[dp.FINANCIALS_FILENAME]
    dp.require_disclosures(disclosures)
    dp.require_financials(financials)
    assert disclosures['collection'] == {'api_calls': 10, 'api_call_budget': 30}
    company = disclosures['companies']['hanmi']
    assert company['state'] == 'LIVE' and company['corp_code'] == CORP_CODE and company['corp_code_basis'] == 'CORPCODE_XML'
    events = {e['rcept_no']: e for e in disclosures['events']}
    results = events['20260725000301']
    assert results['classification'] == 'RESULTS' and results['source'] == 'DART' and results['accepted_at'] is None
    assert results['link'] == 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260725000301'
    assert events['20260814000101']['classification'] == 'PERIODIC'
    assert events['20260901000201']['classification'] == 'MAJOR_EVENT'
    assert events['20260725000302']['classification'] == 'FAIR_DISCLOSURE'
    assert events['20260910000301']['classification'] == 'EXCHANGE'
    assert events['20261002000401']['classification'] == 'OTHER'
    amended = events['20260801000301']
    assert amended['amended'] and amended['occurrence'] == 'REPEAT' and amended['group_id'] == 'hanmi:20260720000301'
    assert events['20260910000301']['occurrence'] == 'NEW'
    assert '20260320000101' not in events  # periodic rows outside the 90-day window are not listed
    text = (out / dp.DISCLOSURES_FILENAME).read_text() + (out / dp.FINANCIALS_FILENAME).read_text()
    for forbidden in ('SYNTHETIC FILER', 'flr_nm', 'corp_name', 'thstrm', 'price'):
        assert forbidden not in text
    assert_no_key(text, printed.out, printed.err)
    from pages_artifact_guard import scan_artifact
    site = tmp_path / 'built'
    import build_pages_cockpit
    build_pages_cockpit.build_public_cockpit(site)
    for name in dp.FILENAMES:
        (site / name).write_bytes((out / name).read_bytes())
    assert scan_artifact(site)['pages_artifact_guard'] == 'PASS'


def test_financial_mapping_cfs_ofs_and_no_zero_fill(tmp_path):
    _, files, _ = run(tmp_path, FakeOpenDart())
    company = files[dp.FINANCIALS_FILENAME]['companies']['hanmi']
    annual, interim = company['annual'], company['latest_interim']
    assert (annual['period'], annual['fs_div'], annual['fs_label'], annual['basis']) == ('ANNUAL', 'CFS', 'CONSOLIDATED', 'FISCAL_YEAR')
    assert annual['rcept_no'] == '20260320000101' and annual['report_name'] == '[기재정정]사업보고서 (2025.12)'
    inputs = annual['inputs']
    assert inputs['revenue'] == 558_734_000_000 and inputs['revenue_prev'] == 159_000_000_000
    assert inputs['operating_income'] == 255_400_000_000 and inputs['eps'] == 2100 and inputs['eps_prev'] == 270
    assert inputs['capex'] == -40_000_000_000 and inputs['shares'] == 95_000_000
    assert inputs['equity'] == 900_000_000_000  # owners of parent preferred over total equity
    assert annual['concepts']['equity'] == 'ifrs-full_EquityAttributableToOwnersOfParent'
    assert annual['concepts']['eps'] == 'ifrs-full_BasicEarningsLossPerShare'
    assert inputs['total_debt'] is None and annual['missing']['total_debt'] == 'MISSING'
    assert (interim['period'], interim['fs_div'], interim['fs_label'], interim['basis']) == ('HALF', 'OFS', 'SEPARATE_FALLBACK', 'YEAR_TO_DATE')
    assert 'SEPARATE_STATEMENTS_FALLBACK' in interim['reason_codes'] and 'SHARES_NOT_AVAILABLE' in interim['reason_codes']
    assert interim['inputs']['revenue'] == 300_000_000_000  # year-to-date column of the half-year report
    assert interim['inputs']['revenue_prev'] is None and interim['missing']['revenue_prev'] == 'NOT_IN_INTERIM_SCOPE'
    assert interim['inputs']['capex'] is None and interim['inputs']['eps'] is None
    # Q·G: the unchanged engine on the annual inputs; factors without inputs stay NOT_AVAILABLE.
    from investment_system.qgv.raw_map import map_raw
    from investment_system.qgv.sec_m2 import _mapping_view
    raw = {**dp.raw_inputs(inputs), 'profile_kind': 'GENERAL_CORPORATE', 'period_quality': 'FORM_ALIGNED',
           'reporting_currency': 'KRW', 'stamp': {'data_stamp_id': 'x'}}
    expected = map_raw(_mapping_view('hanmi', raw, False))
    for fid, factor in company['qg']['factors'].items():
        assert factor['score'] == expected[fid].score_0_100
    assert company['qg']['factors']['financial_health'] == {'score': None, 'state': 'NOT_AVAILABLE'}  # debt missing, not 0
    assert company['qg']['factors']['roic_wacc']['state'] == 'NOT_AVAILABLE'
    assert company['qg']['factors']['margin_quality']['state'] == 'LIVE'
    assert dp.raw_inputs(inputs)['fcf'] == 140_000_000_000 and dp.raw_inputs(inputs)['invested_capital'] == 900_000_000_000


def test_extract_financials_withholds_ambiguous_unparseable_and_foreign_currency():
    def row(account, sj, amount, currency='KRW', add=''):
        return {'sj_div': sj, 'account_id': account, 'thstrm_amount': amount, 'thstrm_add_amount': add, 'frmtrm_amount': '',
                'currency': currency, 'reprt_code': '11011'}
    payload = {'list': [row('ifrs-full_Revenue', 'IS', '100'), row('ifrs-full_Revenue', 'CIS', '101'),
                        row('dart_OperatingIncomeLoss', 'IS', '-'), row('ifrs-full_ProfitLoss', 'IS', '10'),
                        row('ifrs-full_ProfitLoss', 'CIS', '10')]}
    values, concepts, reasons = dc.extract_financials(payload, reprt_code='11011')
    assert values['revenue'] is None and reasons['revenue'] == 'AMBIGUOUS'
    assert values['operating_income'] is None and reasons['operating_income'] == 'UNPARSEABLE'
    assert values['net_income'] == 10 and values['cash_and_equivalents'] is None and reasons['cash_and_equivalents'] == 'MISSING'
    with pytest.raises(dc.DartCollectionError, match='DART_FINANCIALS_INVALID'):
        dc.extract_financials({'list': [row('ifrs-full_Revenue', 'IS', '1', currency='USD')]}, reprt_code='11011')
    with pytest.raises(dc.DartCollectionError, match='DART_IDENTITY_MISMATCH'):
        dc.extract_financials({'list': [row('ifrs-full_Revenue', 'IS', '1')]}, reprt_code='11012')
    half = {'list': [{**row('ifrs-full_Revenue', 'IS', '30', add='70'), 'reprt_code': '11012'}]}
    assert dc.extract_financials(half, reprt_code='11012')[0]['revenue'] == 70
    assert [dc.parse_amount(v) for v in ('1,234', '-5', '', '-', '1e5', None, '12.5')] == [1234, -5, None, None, None, None, 12.5]


def test_periodic_report_names():
    assert dc.periodic_report('사업보고서 (2025.12)') == ('ANNUAL', '2025', '11011')
    assert dc.periodic_report('[기재정정]반기보고서 (2026.06)') == ('HALF', '2026', '11012')
    assert dc.periodic_report('분기보고서 (2026.03)') == ('Q1', '2026', '11013')
    assert dc.periodic_report('분기보고서 (2026.09)') == ('Q3', '2026', '11014')
    for name in ('사업보고서 (2025.06)', '분기보고서 (2026.06)', '감사보고서 (2025.12)', '사업보고서', None):
        assert dc.periodic_report(name) is None


# ---------------------------------------------------------------- corp_code


def test_corp_code_only_from_exactly_one_official_row():
    assert dc.resolve_corp_code(corp_zip(), stock_code='042700', corp_name='한미반도체') == CORP_CODE
    for rows in ([('00000001', '삼성전자', '005930')], [(CORP_CODE, '한미반도체', '042700'), ('00000043', '한미반도체', '042700')],
                 [(CORP_CODE, '다른이름', '042700')], [('0000004', '한미반도체', '042700')]):
        with pytest.raises(dc.DartCollectionError, match='CORP_CODE_UNCONFIRMED'):
            dc.resolve_corp_code(corp_zip(rows), stock_code='042700', corp_name='한미반도체')
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('CORPCODE.xml', '<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "y">]><result><list><corp_code>&x;</corp_code></list></result>')
    for body in (b'not a zip', buffer.getvalue(), corp_zip([])):
        with pytest.raises(dc.DartCollectionError, match='DART_ZIP_INVALID'):
            dc.resolve_corp_code(body, stock_code='042700', corp_name='한미반도체')
    assert not hasattr(dc, 'PINNED_CORP_CODE') and 'corp_code' not in dc.KR_TARGETS['hanmi']


def test_unconfirmed_corp_code_fails_closed_without_further_calls(tmp_path, capsys):
    fake = FakeOpenDart(corp=corp_zip([(CORP_CODE, '한미반도체', '042700'), ('00000043', '한미반도체', '042700')]))
    code, files, _ = run(tmp_path, fake)
    assert code == 0 and [e for e, _ in fake.requests] == ['corpCode.xml']
    assert files[dp.DISCLOSURES_FILENAME]['companies']['hanmi']['reason_code'] == 'CORP_CODE_UNCONFIRMED'
    assert files[dp.DISCLOSURES_FILENAME]['events'] == []
    assert files[dp.FINANCIALS_FILENAME]['companies']['hanmi']['reason_codes'] == ['CORP_CODE_UNCONFIRMED']
    assert 'DART_COLLECTION_DEGRADED codes=CORP_CODE_UNCONFIRMED' in capsys.readouterr().out


def test_zip_endpoint_status_document_maps_to_fixed_code():
    fake = FakeOpenDart(corp=b'<?xml version="1.0"?><result><status>010</status><message>key</message></result>')
    client = dc.DartClient(FAKE_KEY, budget=dc.CallBudget(5), transport=fake)
    with pytest.raises(dc.DartCollectionError, match='DART_KEY_NOT_REGISTERED'):
        client.corp_code_zip()


# ---------------------------------------------------------------- status codes and budget


@pytest.mark.parametrize('status,code', [('010', 'DART_KEY_NOT_REGISTERED'), ('011', 'DART_KEY_DISABLED'), ('012', 'DART_IP_NOT_ALLOWED'),
                                         ('020', 'DART_LIMIT_EXCEEDED'), ('100', 'DART_INVALID_FIELD'), ('800', 'DART_MAINTENANCE'),
                                         ('900', 'DART_UNDEFINED_ERROR'), ('901', 'DART_KEY_EXPIRED'), ('999', 'DART_UNKNOWN_STATUS')])
def test_status_codes_map_to_fixed_reasons(tmp_path, status, code):
    message = 'upstream text ' + FAKE_KEY
    fake = FakeOpenDart(overrides={('list.json', 'A', None, None): FakeOpenDart.json({'status': status, 'message': message})})
    rc, files, _ = run(tmp_path, fake)
    company = files[dp.DISCLOSURES_FILENAME]['companies']['hanmi']
    assert rc == 0 and company['state'] == 'NOT_AVAILABLE' and company['reason_code'] == code
    assert 'upstream text' not in json.dumps(files)
    if code in dc.FATAL_CODES:
        assert [e for e, _ in fake.requests] == ['corpCode.xml', 'list.json']


def test_no_data_is_not_an_error():
    fake = FakeOpenDart()
    client = dc.DartClient(FAKE_KEY, budget=dc.CallBudget(5), transport=fake)
    assert client.json('fnlttSinglAcntAll.json', {'corp_code': CORP_CODE, 'bsns_year': '2019', 'reprt_code': '11011', 'fs_div': 'CFS'}) is None
    with pytest.raises(dc.DartCollectionError, match='DART_NO_DATA'):
        dc.fetch_statements(client, CORP_CODE, bsns_year='2019', reprt_code='11011')
    assert client.budget.used == 3


def test_budget_spends_before_sending_and_fails_closed():
    fake = FakeOpenDart()
    client = dc.DartClient(FAKE_KEY, budget=dc.CallBudget(2), transport=fake)
    client.corp_code_zip()
    client.corp_code_zip()
    with pytest.raises(dc.DartCollectionError, match='DART_CALL_BUDGET_EXCEEDED'):
        client.corp_code_zip()
    assert len(fake.requests) == 2 and client.budget.used == 2
    for limit in (0, 51, 10.0, True):
        with pytest.raises(dc.DartCollectionError, match='DART_CONFIG_INVALID'):
            dc.CallBudget(limit)
    assert dc.HARD_MAX_CALLS == 50 and dc.DEFAULT_MAX_CALLS <= 50 and dc.DOCUMENTED_DAILY_LIMIT == 20000


@pytest.mark.parametrize('limit', [1, 3, 6, 8])
def test_run_budget_exhaustion_stops_requests_and_logs_count(tmp_path, capsys, limit):
    fake = FakeOpenDart()
    rc, files, _ = run(tmp_path, fake, max_calls=limit)
    printed = capsys.readouterr().out
    assert rc == 0 and len(fake.requests) == limit
    assert f'DART_CALLS used={limit} budget={limit}' in printed and 'DART_CALL_BUDGET_EXCEEDED' in printed
    assert files[dp.DISCLOSURES_FILENAME]['collection'] == {'api_calls': limit, 'api_call_budget': limit}
    financial = files[dp.FINANCIALS_FILENAME]['companies']['hanmi']
    blocks = [financial['annual'], financial['latest_interim']]
    assert any('DART_CALL_BUDGET_EXCEEDED' in b['reason_codes'] for b in blocks) or 'DART_CALL_BUDGET_EXCEEDED' in financial['reason_codes']


def test_cli_rejects_budget_above_hard_max(tmp_path, capsys):
    assert dart_daily.main(['--out', str(tmp_path), '--max-calls', '51'], environ={'DART_API_KEY': FAKE_KEY}) == 2
    assert dart_daily.main(['--out', str(tmp_path), '--max-calls', '0'], environ={'DART_API_KEY': FAKE_KEY}) == 2
    assert capsys.readouterr().out.count('DART_DAILY ARGUMENTS_INVALID') == 2


# ---------------------------------------------------------------- key masking


def test_key_sent_only_as_crtfc_key_query_parameter():
    seen = []

    def transport(url, *, timeout, max_bytes):
        parts = urlsplit(url)
        seen.append(url)
        assert parts.scheme == 'https' and parts.netloc == 'opendart.fss.or.kr'
        params = parse_qs(parts.query)
        assert params['crtfc_key'] == [FAKE_KEY]
        assert url.count(FAKE_KEY) == 1 and FAKE_KEY not in parts.path
        return FakeOpenDart.json({'status': '013', 'message': 'none'})
    client = dc.DartClient(FAKE_KEY, budget=dc.CallBudget(3), transport=transport)
    assert client.json('list.json', {'corp_code': CORP_CODE}) is None
    assert dc.KEY_PARAMETER == 'crtfc_key' and len(seen) == 1
    assert FAKE_KEY not in repr(client) and FAKE_KEY not in str(client)
    with pytest.raises(dc.DartCollectionError, match='DART_CONFIG_INVALID'):
        client.json('list.json', {'crtfc_key': 'x'})
    with pytest.raises(dc.DartCollectionError, match='DART_CONFIG_INVALID'):
        client.json('document.xml', {})


def test_transport_exception_text_with_url_and_key_is_replaced(tmp_path, capsys):
    def leaky(url, *, timeout, max_bytes):
        raise ValueError("URL can't contain control characters. " + url)
    client = dc.DartClient(FAKE_KEY, budget=dc.CallBudget(3), transport=leaky)
    with pytest.raises(dc.DartCollectionError) as caught:
        client.corp_code_zip()
    error = caught.value
    assert str(error) == 'DART_TRANSPORT_FAILED' and error.__context__ is None and error.__cause__ is None
    assert_no_key(str(error), repr(error), repr(error.args))
    rc, files, out = run(tmp_path, leaky)
    printed = capsys.readouterr()
    assert rc == 0 and files[dp.DISCLOSURES_FILENAME]['companies']['hanmi']['reason_code'] == 'DART_TRANSPORT_FAILED'
    assert_no_key(printed.out, printed.err, *(p.read_bytes() for p in out.iterdir()))


def test_echoed_key_in_response_is_never_published_or_printed(tmp_path, capsys):
    row = {'corp_cls': 'K', 'corp_name': '한미반도체', 'corp_code': CORP_CODE, 'stock_code': '042700',
           'report_nm': '단일판매 ' + FAKE_KEY, 'rcept_no': '20260930000999', 'flr_nm': 'x', 'rcept_dt': '20260930', 'rm': ''}
    fake = FakeOpenDart(overrides={('list.json', 'B', None, None): FakeOpenDart.json(
        {'status': '000', 'message': 'ok', 'page_no': 1, 'page_count': 100, 'total_count': 1, 'total_page': 1, 'list': [row]})})
    rc, _, out = run(tmp_path, fake)
    printed = capsys.readouterr()
    assert rc == 1 and 'DART_COLLECTION_FAILED code=DART_OUTPUT_REJECTED' in printed.out
    assert_no_key(printed.out, printed.err, *(p.read_bytes() for p in out.iterdir()))


def test_missing_or_malformed_key_sends_nothing(tmp_path, capsys):
    for key, code in ((None, 'DART_API_KEY_MISSING'), ('', 'DART_API_KEY_MISSING'), ('short', 'DART_API_KEY_INVALID_FORMAT'),
                      (FAKE_KEY + '\n', 'DART_API_KEY_INVALID_FORMAT')):
        fake = FakeOpenDart()
        rc, files, _ = run(tmp_path, fake, key=key)
        assert rc == 0 and fake.requests == []
        assert files[dp.DISCLOSURES_FILENAME]['companies']['hanmi']['reason_code'] == code
        assert files[dp.FINANCIALS_FILENAME]['companies']['hanmi']['reason_codes'] == [code]
    assert_no_key(capsys.readouterr().out)


def test_redirect_and_http_errors_are_fixed_codes(tmp_path):
    def redirect(url, *, timeout, max_bytes):
        raise dc.DartCollectionError('DART_REDIRECT_REJECTED')
    rc, files, _ = run(tmp_path, redirect)
    assert files[dp.DISCLOSURES_FILENAME]['companies']['hanmi']['reason_code'] == 'DART_REDIRECT_REJECTED'
    fake = FakeOpenDart(overrides={('list.json', None, None, None): DartResponse(500, b'')})
    client = dc.DartClient(FAKE_KEY, budget=dc.CallBudget(3), transport=fake)
    with pytest.raises(dc.DartCollectionError, match='DART_HTTP_ERROR'):
        client.json('list.json', {'corp_code': CORP_CODE})


def test_subprocess_stdout_stderr_never_contain_key(tmp_path):
    """The real CLI with a fake key and no network access (proxy pointed at a closed port) prints fixed codes only."""
    out = tmp_path / 'site'
    out.mkdir()
    env = {'PATH': '/usr/bin:/bin', 'DART_API_KEY': FAKE_KEY, 'HTTPS_PROXY': 'http://127.0.0.1:9', 'https_proxy': 'http://127.0.0.1:9',
           'HTTP_PROXY': 'http://127.0.0.1:9', 'NO_PROXY': ''}
    result = subprocess.run([sys.executable, str(TOOLS / 'dart_daily.py'), '--out', str(out), '--max-calls', '3'],
                            env=env, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert b'DART_CALLS used=1 budget=3' in result.stdout and b'DART_TRANSPORT_FAILED' in result.stdout
    assert_no_key(result.stdout, result.stderr, *(p.read_bytes() for p in out.iterdir()))
    assert b'opendart' not in result.stdout + result.stderr and b'crtfc_key' not in result.stdout + result.stderr


def test_daily_workflow_adds_one_step_with_named_secret_only():
    source = (ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    assert source.count('dart_daily.py') == 1 and source.count('secrets.DART_API_KEY') == 1 and source.count('DART_API_KEY:') == 1
    assert 'DART_API_KEY: ${{ secrets.DART_API_KEY }}' in source
    step = source[source.index('Collect OpenDART'):]
    step = step[:step.index('      - name:', 1)]
    assert 'python implementation/tools/dart_daily.py --out "$RUNNER_TEMP/public-cockpit"' in step
    assert 'pages_artifact_guard.py --artifact-dir "$RUNNER_TEMP/public-cockpit"' in step
    assert 'SEC_USER_AGENT' not in step and 'RAW_REPO_TOKEN' not in step and 'echo' not in step
    assert source.index('dart_daily.py') < source.index('actions/upload-pages-artifact')
    pages = (ROOT.parent / '.github/workflows/cockpit-pages.yml').read_text()
    assert 'python implementation/tools/dart_daily.py --preserve-only --out "$RUNNER_TEMP/public-cockpit"' in pages
    assert 'DART_API_KEY' not in pages


# ---------------------------------------------------------------- previous copy, preserve-only


class Response(io.BytesIO):
    def __init__(self, body, url, status=200):
        super().__init__(body)
        self.status, self._url = status, url

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def serve(bodies):
    def opener(request, timeout):
        name = request.full_url.rsplit('/', 1)[1]
        if name not in bodies:
            raise urllib.error.HTTPError(request.full_url, 404, 'nf', {}, None)
        return Response(bodies[name], request.full_url)
    return opener


def test_failed_run_carries_previous_rows_and_goes_stale_after_48h(tmp_path):
    _, first, out = run(tmp_path, FakeOpenDart())
    previous = serve({name: (out / name).read_bytes() for name in dp.FILENAMES})
    rc, files, _ = run(tmp_path / 'b', None, key='', now=NOW + timedelta(hours=30), previous=previous)
    assert rc == 0
    d, f = files[dp.DISCLOSURES_FILENAME], files[dp.FINANCIALS_FILENAME]
    assert d['companies']['hanmi']['state'] == 'LIVE' and d['events'] == first[dp.DISCLOSURES_FILENAME]['events']
    assert f['companies']['hanmi']['state'] == 'LIVE' and f['companies']['hanmi']['annual'] == first[dp.FINANCIALS_FILENAME]['companies']['hanmi']['annual']
    rc, files, _ = run(tmp_path / 'c', None, key='', now=NOW + timedelta(days=3), previous=previous)
    d, f = files[dp.DISCLOSURES_FILENAME], files[dp.FINANCIALS_FILENAME]
    assert d['state'] == 'STALE' and d['reason_codes'] == ['STALE_INPUT'] and d['companies']['hanmi']['state'] == 'STALE'
    company = f['companies']['hanmi']
    assert company['state'] == 'STALE' and company['reason_codes'] == ['STALE_INPUT']
    assert {x['state'] for x in company['qg']['factors'].values()} == {'STALE', 'NOT_AVAILABLE'}


def test_new_run_keeps_first_seen_time_of_known_receipts(tmp_path):
    _, first, out = run(tmp_path, FakeOpenDart())
    previous = serve({name: (out / name).read_bytes() for name in dp.FILENAMES})
    _, files, _ = run(tmp_path / 'b', FakeOpenDart(), now=NOW + timedelta(days=1), previous=previous)
    seen = {e['rcept_no']: e['first_seen_at'] for e in files[dp.DISCLOSURES_FILENAME]['events']}
    assert set(seen.values()) == {dp.instant(NOW)}


def test_preserve_only_restores_validated_bytes_or_keeps_offline(tmp_path, capsys):
    _, _, out = run(tmp_path, FakeOpenDart())
    bodies = {name: (out / name).read_bytes() for name in dp.FILENAMES}
    target = tmp_path / 'ui'
    target.mkdir()
    dart_daily.emit(target)
    assert dart_daily.main(['--out', str(target), '--preserve-only'], open_response=serve(bodies)) == 0
    assert all((target / n).read_bytes() == b for n, b in bodies.items())
    fresh = tmp_path / 'ui2'
    fresh.mkdir()
    dart_daily.emit(fresh)
    before = {n: (fresh / n).read_bytes() for n in dp.FILENAMES}
    assert dart_daily.main(['--out', str(fresh), '--preserve-only'], open_response=serve({})) == 0
    assert before == {n: (fresh / n).read_bytes() for n in dp.FILENAMES}
    broken = dict(bodies)
    broken[dp.DISCLOSURES_FILENAME] = bodies[dp.DISCLOSURES_FILENAME].replace(b'"score_effect":"NONE"', b'"score_effect":"ADJUST"')
    assert dart_daily.main(['--out', str(fresh), '--preserve-only'], open_response=serve(broken)) == 1
    out_text = capsys.readouterr().out
    assert 'DART_PREVIOUS_RESTORED files=2' in out_text and 'DART_PREVIOUS_RESTORED files=0' in out_text and 'DART_PREVIOUS_RESTORE_FAILED' in out_text


# ---------------------------------------------------------------- public contract and vectors


def test_vectors_are_current_and_python_verdicts_hold():
    result = subprocess.run([sys.executable, str(TOOLS / 'dart_public_vectors.py'), '--check'], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    vectors = json.loads((ROOT / 'tests/fixtures/dart_public_vectors_v1.json').read_text())
    assert vectors['synthetic'] is True and len(vectors['cases']) >= 30
    for case in vectors['cases']:
        try:
            dp.require_disclosures(copy.deepcopy(case['payload']))
            ok = True
        except ValueError:
            ok = False
        assert ok == case['valid'], case['name']


def test_financials_validator_rejects_zero_fill_and_tampered_scores(tmp_path):
    _, files, _ = run(tmp_path, FakeOpenDart())
    good = files[dp.FINANCIALS_FILENAME]
    dp.require_financials(copy.deepcopy(good))
    for change in (lambda c: c['annual']['inputs'].__setitem__('total_debt', 0),
                   lambda c: c['qg']['factors']['margin_quality'].__setitem__('score', 1.0),
                   lambda c: c['qg']['factors']['financial_health'].update(score=50.0, state='LIVE'),
                   lambda c: c['annual'].__setitem__('fs_div', 'OFS'),
                   lambda c: c['annual']['inputs'].__setitem__('price', 1),
                   lambda c: c.__setitem__('corp_code', None),
                   lambda c: c['latest_interim']['inputs'].__setitem__('revenue_prev', 1.0)):
        bad = copy.deepcopy(good)
        change(bad['companies']['hanmi'])
        with pytest.raises(ValueError):
            dp.require_financials(bad)


def test_offline_build_emits_not_available_files_that_pass_the_guard(tmp_path):
    import build_pages_cockpit
    from pages_artifact_guard import scan_artifact
    site = tmp_path / 'site'
    build_pages_cockpit.build_public_cockpit(site)
    disclosures = json.loads((site / dp.DISCLOSURES_FILENAME).read_text())
    financials = json.loads((site / dp.FINANCIALS_FILENAME).read_text())
    assert disclosures['state'] == financials['state'] == 'NOT_AVAILABLE' and disclosures['events'] == []
    assert disclosures['companies']['hanmi']['reason_code'] == 'NOT_COLLECTED'
    assert scan_artifact(site)['pages_artifact_guard'] == 'PASS'
    payload = copy.deepcopy(disclosures)
    payload['events'] = [{'body': 'x'}]
    (site / dp.DISCLOSURES_FILENAME).write_text(json.dumps(payload))
    receipt = scan_artifact(site)
    assert receipt['pages_artifact_guard'] == 'FAIL' and receipt['violations'].get('dart_public_boundary') == 1


def test_shares_failure_keeps_statements_and_marks_shares_not_available(tmp_path):
    fake = FakeOpenDart(overrides={('stockTotqySttus.json', None, '11011', None): FakeOpenDart.json({'status': '100', 'message': 'x'})})
    rc, files, _ = run(tmp_path, fake)
    annual = files[dp.FINANCIALS_FILENAME]['companies']['hanmi']['annual']
    assert rc == 0 and annual['state'] == 'LIVE' and annual['inputs']['shares'] is None
    assert 'SHARES_NOT_AVAILABLE' in annual['reason_codes'] and annual['missing']['shares'] == 'MISSING'
    assert annual['inputs']['revenue'] == 558_734_000_000


def test_list_pagination_is_bounded_and_marked_truncated(tmp_path):
    from tests.dart_fake_opendart import _row

    class Paged(FakeOpenDart):
        def __call__(self, url, *, timeout, max_bytes):
            parts = urlsplit(url)
            params = {k: v[0] for k, v in parse_qs(parts.query).items()}
            if parts.path.endswith('list.json') and 'pblntf_ty' not in params:
                self.requests.append(('list.json', params))
                page = int(params['page_no'])
                return self.json({'status': '000', 'message': 'ok', 'page_no': page, 'page_count': 100, 'total_count': 500,
                                  'total_page': '5', 'list': [_row(f'2026100{page}000501', f'2026100{page}', '기타공시 안내')]})
            return super().__call__(url, timeout=timeout, max_bytes=max_bytes)
    fake = Paged()
    rc, files, _ = run(tmp_path, fake)
    company = files[dp.DISCLOSURES_FILENAME]['companies']['hanmi']
    untyped = [p for e, p in fake.requests if e == 'list.json' and 'pblntf_ty' not in p]
    assert rc == 0 and [p['page_no'] for p in untyped] == ['1', '2', '3']
    assert company['state'] == 'LIVE' and company['truncated'] and company['reason_code'] == 'DART_LIST_TRUNCATED'
    assert {'20261001000501', '20261003000501'} <= {e['rcept_no'] for e in files[dp.DISCLOSURES_FILENAME]['events']}


def test_debt_is_short_plus_long_plus_bonds_plus_leases_without_double_counting():
    """PLAYBOOK_V1 §13-7: 단기차입금 + 장기차입금(유동성 포함) + 사채 + 리스부채; a total account wins over its parts."""
    from tests.dart_fake_opendart import _fs as fs
    from investment_system.providers.dart_collection import extract_financials

    def _fs(*args):
        return dict(fs(*args), reprt_code='11011')
    base = [_fs('ifrs-full_Revenue', 'CIS', '10')]
    rows = base + [_fs('ifrs-full_ShorttermBorrowings', 'BS', '100'), _fs('ifrs-full_LongtermBorrowings', 'BS', '200'),
                   _fs('ifrs-full_CurrentPortionOfLongtermBorrowings', 'BS', '50'),
                   _fs('ifrs-full_NoncurrentPortionOfNoncurrentBondsIssued', 'BS', '70'), _fs('ifrs-full_CurrentPortionOfNoncurrentBondsIssued', 'BS', '5'),
                   _fs('ifrs-full_LeaseLiabilities', 'BS', '40'), _fs('ifrs-full_NoncurrentLeaseLiabilities', 'BS', '30')]
    values, concepts, reasons = extract_financials({'list': rows}, reprt_code='11011')
    assert values['total_debt'] == 465 and 'total_debt' not in reasons
    assert concepts['total_debt'] == ('ifrs-full_ShorttermBorrowings+ifrs-full_LongtermBorrowings+ifrs-full_CurrentPortionOfLongtermBorrowings'
                                      '+ifrs-full_NoncurrentPortionOfNoncurrentBondsIssued+ifrs-full_CurrentPortionOfNoncurrentBondsIssued'
                                      '+ifrs-full_LeaseLiabilities')
    only_leases = base + [_fs('ifrs-full_CurrentLeaseLiabilities', 'BS', '12')]
    values, concepts, _ = extract_financials({'list': only_leases}, reprt_code='11011')
    assert values['total_debt'] == 12 and concepts['total_debt'] == 'ifrs-full_CurrentLeaseLiabilities'
    values, concepts, reasons = extract_financials({'list': base}, reprt_code='11011')
    assert values['total_debt'] is None and reasons['total_debt'] == 'MISSING'
    bad = base + [_fs('ifrs-full_ShorttermBorrowings', 'BS', '100'), _fs('ifrs-full_LongtermBorrowings', 'BS', 'n/a')]
    values, _, reasons = extract_financials({'list': bad}, reprt_code='11011')
    assert values['total_debt'] is None and reasons['total_debt'] == 'UNPARSEABLE'


def test_public_debt_lineage_accepts_multiple_defined_components_only(tmp_path):
    import copy
    _, files, _ = run(tmp_path, FakeOpenDart())
    payload = files[dp.FINANCIALS_FILENAME]
    company = payload['companies']['hanmi']
    annual = company['annual']
    annual['inputs']['total_debt'] = 300
    annual['concepts']['total_debt'] = 'ifrs-full_ShorttermBorrowings+ifrs-full_LongtermBorrowings'
    annual['missing']['total_debt'] = None
    company['qg'] = dp.compute_qg('hanmi', annual)
    assert dp.require_financials(payload) is payload
    for value in ('ifrs-full_ShorttermBorrowings+ifrs-full_Revenue',
                  'ifrs-full_ShorttermBorrowings+ifrs-full_ShorttermBorrowings'):
        bad = copy.deepcopy(payload)
        bad['companies']['hanmi']['annual']['concepts']['total_debt'] = value
        with pytest.raises(ValueError):
            dp.require_financials(bad)
