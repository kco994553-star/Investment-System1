"""Synthetic SEC submissions/13F XML only: manager CIK verification and the 13F step.

No network. Candidate CIKs in the real config are verified only by the Actions run.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tests.test_sec_13f import _row, _xml

TOOLS = Path(__file__).parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
BASE = Path(__file__).resolve().parents[1] / 'src/investment_system'
NOW = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
AGENT = 'Synthetic Tester tester@example.com'
CIK, OTHER = '0000000123', '0000000456'


def styles():
    return importlib.import_module('investment_system.config.manager_styles')


def provider():
    return importlib.import_module('investment_system.providers.sec_13f_managers')


def screens():
    return importlib.import_module('investment_system.product.public_engine_screens')


def tool():
    return importlib.import_module('sec_13f_managers')


def config(**manager):
    base = styles().load_manager_styles()
    out = deepcopy(base)
    out['managers'] = [
        dict(base['managers'][0], id='synthetic_value', display_name='Synthetic Value', expected_sec_name='Synthetic Capital LLC',
             candidate_cik=CIK, **manager),
        dict(base['managers'][1], id='synthetic_other', display_name='Synthetic Other', expected_sec_name='Other Partners LP',
             candidate_cik=OTHER),
        dict(base['managers'][2], id='synthetic_unset', display_name='Synthetic Unset', candidate_cik=None),
    ]
    return styles().validate_manager_styles(out)


def submissions(cik=CIK, name='SYNTHETIC  capital llc', rows=None):
    rows = rows if rows is not None else [
        ('0000000123-26-000003', '2026-08-10', '2026-06-30', '13F-HR'),
        ('0000000123-26-000002', '2026-05-11', '2026-03-31', '13F-HR'),
        ('0000000123-26-000009', '2026-04-01', '', '8-K'),
    ]
    recent = {'accessionNumber': [r[0] for r in rows], 'filingDate': [r[1] for r in rows],
              'reportDate': [r[2] for r in rows], 'form': [r[3] for r in rows],
              'primaryDocument': ['xslForm13F_X02/primary_doc.xml' if r[3].startswith('13F') else 'doc.htm' for r in rows]}
    return json.dumps({'cik': str(int(cik)), 'name': name, 'filings': {'recent': recent, 'files': []}}).encode()


def cover(quarter='06-30-2026', cik=CIK, entries=1, value=2000, confidential='false', amendment=None, report='13F HOLDINGS REPORT', others=''):
    amend = '<isAmendment>true</isAmendment><amendmentInfo><amendmentType>%s</amendmentType></amendmentInfo>' % amendment if amendment else '<isAmendment>false</isAmendment>'
    return (f'<edgarSubmission xmlns="http://www.sec.gov/edgar/thirteenffiler" xmlns:com="http://www.sec.gov/edgar/common">'
            f'<headerData><submissionType>{"13F-HR/A" if amendment else "13F-HR"}</submissionType><filerInfo><liveTestFlag>LIVE</liveTestFlag>'
            f'<filer><credentials><cik>{cik}</cik><ccc>XXXXXXXX</ccc></credentials></filer><periodOfReport>{quarter}</periodOfReport></filerInfo></headerData>'
            f'<formData><coverPage><reportCalendarOrQuarter>{quarter}</reportCalendarOrQuarter>{amend}'
            f'<filingManager><name>Synthetic</name></filingManager><reportType>{report}</reportType></coverPage>'
            f'<summaryPage><otherIncludedManagersCount>0</otherIncludedManagersCount><tableEntryTotal>{entries}</tableEntryTotal>'
            f'<tableValueTotal>{value}</tableValueTotal><isConfidentialOmitted>{confidential}</isConfidentialOmitted>{others}</summaryPage>'
            f'</formData></edgarSubmission>').encode()


def site(**overrides):
    """URL -> bytes for one verified synthetic manager and one name-mismatched one."""
    folder = lambda acc: acc.replace('-', '')
    index = lambda names: json.dumps({'directory': {'item': [{'name': n, 'type': 'text.gif'} for n in names], 'name': 'x'}}).encode()
    files = {
        'https://data.sec.gov/submissions/CIK0000000123.json': submissions(),
        'https://data.sec.gov/submissions/CIK0000000456.json': submissions(OTHER, 'Other Partners, L.P.'),
    }
    for acc, quarter, quantity in (('0000000123-26-000003', '06-30-2026', 150), ('0000000123-26-000002', '03-31-2026', 100)):
        root = f'https://www.sec.gov/Archives/edgar/data/123/{folder(acc)}/'
        files[root + 'index.json'] = index(['primary_doc.xml', 'infotable.xml', acc + '.txt'])
        files[root + 'primary_doc.xml'] = cover(quarter)
        files[root + 'infotable.xml'] = _xml(_row(quantity=str(quantity), sole=str(quantity)))
    files.update(overrides)
    return files


class Clock:
    def __init__(self):
        self.t = 0.0

    def monotonic(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def client(files, calls=None):
    api = provider()
    clock = Clock()

    def transport(url, *, headers, timeout, max_body_bytes):
        api._require_url(url)
        if calls is not None:
            calls.append((url, dict(headers)))
        body = files.get(url)
        return api.SecResponse(200, body, None, url) if body is not None else api.SecResponse(404, b'', None, url)
    return api.Sec13FClient(AGENT, transport=transport, sleep=clock.sleep, monotonic=clock.monotonic, now=lambda: NOW)


def run(tmp_path, files=None, cfg=None):
    out = tmp_path / 'site'
    out.mkdir(exist_ok=True)
    payload, mismatched = tool().build(out, config=cfg or config(), fetch=client(files or site()).fetch, now=lambda: NOW)
    return out, payload, mismatched


def managers(payload):
    return {m['id']: m for m in payload['data']['managers']}


def test_real_config_is_versioned_v0_with_ten_managers_and_device_copy_is_equal():
    cfg = styles().load_manager_styles()
    assert cfg['config_version'] == 'manager_styles/v0' and cfg['status'] == 'V0_UNCALIBRATED'
    assert cfg['label_ko'] == '일반적 평가 기반 v0 분류'
    names = [m['display_name'] for m in cfg['managers']]
    assert names == ['Berkshire Hathaway', 'Baupost Group', 'Pershing Square', 'Third Point', 'Appaloosa',
                     'Duquesne Family Office', 'Coatue Management', 'Tiger Global', 'ARK Investment Management',
                     'Renaissance Technologies']
    labels = {s['id']: s['label_ko'] for s in cfg['styles']}
    assert [labels[m['styles'][0]] for m in cfg['managers']] == ['가치', '가치', '행동주의', '이벤트', '역발상', '매크로',
                                                               '성장·기술', '성장·기술', '혁신 성장', '퀀트']
    assert {s['id'] for s in cfg['styles'] if s['reference_only']} == {'macro', 'quant'}
    script = 'process.stdout.write(JSON.stringify(require(process.argv[1])))'
    out = subprocess.run(['node', '-e', script, str(BASE / 'product/web_assets/manager-styles-v0.js')],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == json.loads((BASE / 'config/manager_styles_v0.json').read_text())


@pytest.mark.parametrize('mutate', [
    lambda c: c['managers'].append(dict(c['managers'][0])),
    lambda c: c['managers'][0].update(styles=['unknown']),
    lambda c: c['managers'][0].update(styles=[]),
    lambda c: c['managers'][0].update(candidate_cik='123'),
    lambda c: c['managers'][1].update(candidate_cik=c['managers'][0]['candidate_cik']),
    lambda c: c['managers'][0].update(extra=1),
    lambda c: c['managers'][0].update(description_ko='<b>x</b>'),
    lambda c: c['styles'].append(dict(c['styles'][0])),
    lambda c: c.update(status='OFFICIAL'),
    lambda c: c.pop('label_ko'),
])
def test_config_validator_fails_closed(mutate):
    cfg = deepcopy(styles().load_manager_styles())
    mutate(cfg)
    with pytest.raises(ValueError, match='MANAGER_STYLES_INVALID'):
        styles().validate_manager_styles(cfg)


def test_multiple_styles_and_null_cik_are_allowed():
    cfg = deepcopy(styles().load_manager_styles())
    cfg['managers'][0]['styles'] = ['value', 'activist']
    cfg['managers'][1]['candidate_cik'] = None
    assert styles().validate_manager_styles(cfg)['managers'][0]['styles'] == ['value', 'activist']


def test_verification_requires_exact_normalized_name_cik_and_recent_13f():
    api, manager = provider(), config()['managers'][0]
    record, rows = api.verify_manager(manager, submissions(), NOW, as_of=NOW)
    assert record['state'] == 'VERIFIED' and record['matched_name'] == 'SYNTHETIC capital llc'
    assert record['latest_13f_accession'] == '0000000123-26-000003' and record['verified_at'] == NOW.isoformat()
    assert len(rows) == 2
    cases = {
        'NAME_MISMATCH': submissions(name='Synthetic Capital, LLC'),
        'CIK_MISMATCH': submissions(cik='0000000999'),
        'NO_RECENT_13F_HR': submissions(rows=[('0000000123-25-000001', '2025-02-10', '2024-12-31', '13F-HR')]),
        'SUBMISSIONS_INVALID': b'{"cik":"123","cik":"123"}',
    }
    for reason, body in cases.items():
        record, rows = api.verify_manager(manager, body, NOW, as_of=NOW)
        assert (record['state'], record['reason_code'], record['matched_name'], rows) == ('NOT_AVAILABLE', reason, None, [])
    assert api.verify_manager(manager, None, None, as_of=NOW)[0]['reason_code'] == 'SUBMISSIONS_UNAVAILABLE'
    assert api.verify_manager(dict(manager, candidate_cik=None), submissions(), NOW, as_of=NOW)[0]['reason_code'] == 'CIK_NOT_CONFIGURED'
    only_amendment = submissions(rows=[('0000000123-26-000003', '2026-08-10', '2026-06-30', '13F-HR/A')])
    assert api.verify_manager(manager, only_amendment, NOW, as_of=NOW)[0]['reason_code'] == 'NO_RECENT_13F_HR'


def test_verified_manager_gets_reported_quantity_changes_and_others_stay_not_available(tmp_path):
    out, payload, mismatched = run(tmp_path)
    assert sorted(p.name for p in out.iterdir()) == ['sec-13f-changes.json']
    written = json.loads((out / 'sec-13f-changes.json').read_text())
    assert written == payload and screens().require_public_screen('sec-13f-changes.json', written)
    report, = payload['data']['reports']
    assert (report['manager_cik'], report['state'], report['previous_quarter'], report['current_quarter']) == (CIK, 'LIVE', '2026-03-31', '2026-06-30')
    change, = report['changes']
    assert (change['kind'], change['reported_before'], change['reported_after'], change['reported_delta']) == ('ADD', 100, 150, 50)
    m = managers(payload)
    assert m['synthetic_value']['state'] == 'VERIFIED' and m['synthetic_value']['comparison_reasons'] == []
    assert (m['synthetic_other']['state'], m['synthetic_other']['reason_code']) == ('NOT_AVAILABLE', 'NAME_MISMATCH')
    assert (m['synthetic_unset']['reason_code'], m['synthetic_unset']['cik']) == ('CIK_NOT_CONFIGURED', None)
    assert mismatched == {'synthetic_other': 'Other Partners, L.P.'}
    text = json.dumps(payload)
    for private in ('XXXXXXXX', 'value_total', '"value"', AGENT, 'Other Partners'):
        assert private not in text


@pytest.mark.parametrize('overrides,reason', [
    ({'https://www.sec.gov/Archives/edgar/data/123/000000012326000003/primary_doc.xml': cover(confidential='true')}, 'CONFIDENTIAL_OMISSIONS_UNRESOLVED'),
    ({'https://www.sec.gov/Archives/edgar/data/123/000000012326000003/primary_doc.xml': cover(entries=2)}, 'ENTRY_TOTAL_MISMATCH'),
    ({'https://www.sec.gov/Archives/edgar/data/123/000000012326000003/primary_doc.xml': cover(cik='0000000999')}, 'COVER_BINDING_UNCONFIRMED'),
    ({'https://www.sec.gov/Archives/edgar/data/123/000000012326000003/primary_doc.xml': cover(report='13F COMBINATION REPORT')}, 'NON_HOLDINGS_REPORT'),
    ({'https://data.sec.gov/submissions/CIK0000000123.json': submissions(rows=[
        ('0000000123-26-000004', '2026-09-01', '2026-06-30', '13F-HR/A'),
        ('0000000123-26-000003', '2026-08-10', '2026-06-30', '13F-HR'),
        ('0000000123-26-000002', '2026-05-11', '2026-03-31', '13F-HR')])}, 'UNRESOLVED_QUARTER_LINEAGE'),
])
def test_existing_13f_eligibility_rules_keep_comparison_not_available(tmp_path, overrides, reason):
    _, payload, _ = run(tmp_path, site(**overrides))
    report, = payload['data']['reports']
    assert report['state'] == 'NOT_AVAILABLE' and report['changes'] == []
    record = managers(payload)['synthetic_value']
    assert record['state'] == 'VERIFIED' and reason in record['comparison_reasons'] and 'INELIGIBLE_CAPTURE' in record['comparison_reasons']
    assert record['latest_13f_accession'] == ('0000000123-26-000004' if reason == 'UNRESOLVED_QUARTER_LINEAGE' else '0000000123-26-000003')


@pytest.mark.parametrize('overrides,reason', [
    ({'https://www.sec.gov/Archives/edgar/data/123/000000012326000003/index.json':
      json.dumps({'directory': {'item': [{'name': 'primary_doc.xml'}, {'name': 'a.xml'}, {'name': 'b.xml'}]}}).encode()}, 'INFOTABLE_NOT_IDENTIFIED'),
    ({'https://www.sec.gov/Archives/edgar/data/123/000000012326000003/index.json': b'not json'}, 'FILING_INDEX_UNAVAILABLE'),
    ({'https://www.sec.gov/Archives/edgar/data/123/000000012326000003/primary_doc.xml': b'<!DOCTYPE x><edgarSubmission/>'}, 'COVER_INVALID'),
    ({'https://www.sec.gov/Archives/edgar/data/123/000000012326000002/infotable.xml': None}, 'INFOTABLE_UNAVAILABLE'),
    ({'https://data.sec.gov/submissions/CIK0000000123.json': submissions(rows=[('0000000123-26-000003', '2026-08-10', '2026-06-30', '13F-HR')])}, 'INSUFFICIENT_13F_HISTORY'),
])
def test_capture_failures_are_recorded_without_a_report(tmp_path, overrides, reason):
    files = {k: v for k, v in site(**overrides).items() if v is not None}
    _, payload, _ = run(tmp_path, files)
    assert payload['data']['reports'] == [] and payload['state'] == 'NOT_AVAILABLE'
    record = managers(payload)['synthetic_value']
    assert (record['state'], record['capture_reason']) == ('VERIFIED', reason)


def test_size_budget_withholds_whole_report_instead_of_truncating(tmp_path, monkeypatch):
    monkeypatch.setattr(tool(), 'SIZE_BUDGET', 100)
    _, payload, _ = run(tmp_path)
    assert payload['data']['reports'] == []
    assert managers(payload)['synthetic_value']['capture_reason'] == 'PUBLIC_SIZE_LIMIT'


def test_public_validator_binds_reports_to_verified_managers(tmp_path):
    _, payload, _ = run(tmp_path)
    check = lambda p: screens().require_public_screen('sec-13f-changes.json', p)
    for mutate in (
        lambda p: p['data']['managers'][0].update(state='NOT_AVAILABLE', reason_code='NAME_MISMATCH', matched_name=None, verified_at=None, latest_13f_accession=None),
        lambda p: p['data']['managers'][0].update(latest_13f_accession=None),
        lambda p: p['data']['managers'][1].update(matched_name='Other Partners, L.P.'),
        lambda p: p['data']['managers'][2].update(cik='0000000789'),
        lambda p: p['data']['managers'][0].update(capture_reason='ANYTHING'),
        lambda p: p['data']['managers'][0].update(verified_at='2027-01-01T00:00:00+00:00'),
        lambda p: p['data']['managers'].append(dict(p['data']['managers'][0])),
        lambda p: p['data'].update(extra=[]),
    ):
        bad = deepcopy(payload)
        mutate(bad)
        with pytest.raises(ValueError, match='PUBLIC_SCREEN_INVALID'):
            check(bad)
    legacy = deepcopy(payload)
    del legacy['data']['managers']
    assert check(legacy)


def test_transport_and_client_allow_only_fixed_sec_routes():
    api = provider()
    for url in ('https://example.com/x.json', 'https://www.sec.gov/Archives/edgar/data/123/0000000123/../x.xml',
                'http://data.sec.gov/submissions/CIK0000000123.json', 'https://www.sec.gov/cgi-bin/browse-edgar'):
        with pytest.raises(api.SecCollectionError, match='SEC_URL_NOT_ALLOWED'):
            api.default_transport(url, headers={}, timeout=1, max_body_bytes=10)
        with pytest.raises(api.SecCollectionError, match='SEC_URL_NOT_ALLOWED'):
            client({}).fetch(url)
    calls = []
    body, acquired = client(site(), calls).fetch('https://data.sec.gov/submissions/CIK0000000123.json')
    assert acquired == NOW and calls[0][1]['User-Agent'] == AGENT
    with pytest.raises(api.SecCollectionError, match='SEC_HTTP_FAILED'):
        client({}).fetch('https://data.sec.gov/submissions/CIK0000000999.json')


def test_main_reads_only_the_secret_slot_name_and_never_prints_its_value(tmp_path, capsys, monkeypatch):
    out = tmp_path / 'site'
    out.mkdir()
    assert tool().main(['--out', str(out)], environ={}) == 1
    assert capsys.readouterr().out.strip() == 'SEC_13F_MANAGERS_FAILED code=SEC_USER_AGENT_MISSING'
    monkeypatch.setattr(tool(), 'load_manager_styles', lambda: config())
    files = site()

    def transport(url, *, headers, timeout, max_body_bytes):
        body = files.get(url)
        return provider().SecResponse(200 if body else 404, body or b'', None, url)
    monkeypatch.setattr(provider().Sec13FClient, '_pace', lambda self: None)
    assert tool().main(['--out', str(out)], environ={'SEC_USER_AGENT': AGENT}, transport=transport) == 0
    printed = capsys.readouterr().out
    assert AGENT not in printed and 'tester@example.com' not in printed
    assert 'SEC_13F_MANAGER id=synthetic_value state=VERIFIED' in printed
    assert 'id=synthetic_other state=NOT_AVAILABLE reason=NAME_MISMATCH' in printed and 'sec_name="Other Partners, L.P."' in printed
    assert printed.strip().endswith('SEC_13F_MANAGERS_OK verified=1 reports=1 available=1 state=LIVE')
    assert json.loads((out / 'sec-13f-changes.json').read_text())['state'] == 'LIVE'


def test_step_output_passes_pages_guard_after_pipeline(tmp_path):
    from build_pages_cockpit import build_public_cockpit
    from pages_artifact_guard import scan_artifact
    out = tmp_path / 'cockpit'
    build_public_cockpit(out)
    tool().build(out, config=config(), fetch=client(site()).fetch, now=lambda: datetime.now(timezone.utc))
    receipt = scan_artifact(out)
    assert receipt['pages_artifact_guard'] == 'PASS', receipt
