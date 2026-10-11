"""SEC 8-K disclosures (queue 2.2 a/d/e): provider, public file, tool, earnings confirmation, JS == Python."""
from datetime import date, datetime, timedelta, timezone
import copy
import importlib
import io
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.error

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from investment_system.markets.us import US_LISTINGS
from investment_system.product import sec_disclosures as sd
from investment_system.providers import sec_8k_disclosures as p8
from investment_system.providers.sec_collection import SecCollectionError, SecResponse

NOW = datetime(2026, 10, 11, 22, 30, tzinfo=timezone.utc)
JS = ROOT / 'src/investment_system/product/web_assets/sec-disclosures.js'
SCREENS_JS = ROOT / 'src/investment_system/product/web_assets/public-screens.js'
UA = 'Synthetic Tester synthetic-contact@example.com'
NODE = shutil.which('node')


def submissions(company_id, rows, extra_forms=()):
    """rows: (form, accession, filing_date, report_date, acceptance, items)."""
    cols = ('form', 'accessionNumber', 'filingDate', 'reportDate', 'acceptanceDateTime', 'items', 'primaryDocument')
    recent = {c: [] for c in cols}
    for row in list(rows) + list(extra_forms):
        for c, v in zip(cols, row + ('doc.htm',)):
            recent[c].append(v)
    return {'cik': int(US_LISTINGS[company_id]['cik']), 'filings': {'recent': recent}}


def acc(n, year=26, cik='0001045810'):
    return f'{cik}-{year:02d}-{n:06d}'


NVDA_ROWS = [
    ('8-K', acc(101), '2026-08-27', '2026-08-27', '2026-08-27T20:20:31.000Z', '2.02,9.01'),
    ('8-K/A', acc(140), '2026-09-02', '2026-08-27', '2026-09-02T12:00:00.000Z', '2.02,9.01'),
    ('8-K', acc(150), '2026-09-15', '2026-09-12', '2026-09-15T21:00:00.000Z', '5.02'),
    ('8-K', acc(160), '2026-10-01', '2026-09-30', '2026-10-01T13:00:00.000Z', '1.01,2.03,9.01'),
    ('8-K', acc(170), '2026-10-05', '2026-10-05', '2026-10-05T13:00:00.000Z', '8.01,99.99'),
    ('8-K', acc(90), '2026-05-28', '2026-05-28', '2026-05-28T20:20:00.000Z', '2.02,9.01'),  # outside 90 days
    ('10-Q', acc(102), '2026-08-27', '2026-07-26', '2026-08-27T20:30:00.000Z', ''),
]


def index_html(company_id, accession, rows):
    cik = int(US_LISTINGS[company_id]['cik'])
    folder = accession.replace('-', '')
    body = ['<html><body><table class="tableFile" summary="Document Format Files">',
            '<tr><th scope="col">Seq</th><th scope="col">Description</th><th scope="col">Document</th>'
            '<th scope="col">Type</th><th scope="col">Size</th></tr>']
    for seq, (description, name, kind) in enumerate(rows, 1):
        href = name if name.startswith('/') else f'/Archives/edgar/data/{cik}/{folder}/{name}'
        body.append(f'<tr><td scope="row">{seq}</td><td scope="row">{description}</td>'
                    f'<td scope="row"><a href="{href}">x</a> &nbsp;<span class="small">iXBRL</span></td>'
                    f'<td scope="row">{kind}</td><td scope="row">100</td></tr>')
    body.append('</table><table class="tableFile" summary="Data Files"><tr><td>1</td><td>EX-101.SCH</td>'
                '<td><a href="/x.xsd">x</a></td><td>EX-99.1</td></tr></table></body></html>')
    return '\n'.join(body).encode()


class Transport:
    def __init__(self, subs, indexes, fail=()):
        self.subs, self.indexes, self.fail, self.calls = subs, indexes, set(fail), []

    def __call__(self, url, *, headers, timeout, max_body_bytes):
        self.calls.append((url, dict(headers)))
        for cid, payload in self.subs.items():
            if url == f"https://data.sec.gov/submissions/CIK{US_LISTINGS[cid]['cik']}.json":
                if cid in self.fail:
                    return SecResponse(403, b'', None, url)
                return SecResponse(200, json.dumps(payload).encode(), None, url)
        for (cid, accession), body in self.indexes.items():
            if url == p8.index_url(cid, accession):
                return SecResponse(200, body, None, url) if body is not None else SecResponse(404, b'', None, url)
        return SecResponse(404, b'', None, url)


def client_kwargs(transport, now=NOW):
    tick = itertools.count(0, 1)
    return {'transport': transport, 'sleep': lambda _s: None, 'monotonic': lambda: float(next(tick)), 'now': lambda: now}


def full_subs():
    out = {cid: submissions(cid, []) for cid in US_LISTINGS}
    out['nvda'] = submissions('nvda', NVDA_ROWS)
    return out


def full_indexes():
    return {
        ('nvda', acc(101)): index_html('nvda', acc(101), [('8-K', '/ix?doc=/Archives/edgar/data/1045810/000104581026000101/nvda-8k.htm', '8-K'),
                                                          ('PRESS RELEASE, DATED AUGUST 27, 2026', 'q2pr.htm', 'EX-99.1')]),
        ('nvda', acc(140)): index_html('nvda', acc(140), [('8-K/A', 'nvda-8ka.htm', '8-K/A')]),
        ('nvda', acc(150)): None,
        ('nvda', acc(160)): index_html('nvda', acc(160), [('', 'ex991.htm', 'EX-99.1')]),
        ('nvda', acc(170)): index_html('nvda', acc(170), [('Bad &lt;b&gt; title', 'ex991.htm', 'EX-99.1')]),
    }


# --- provider ------------------------------------------------------------------------------------

def test_item_table_and_classification_priority():
    for code in ('1.01', '2.01', '2.02', '5.02', '7.01', '8.01', '9.01'):
        assert code in p8.ITEMS and all(p8.ITEMS[code])
    assert p8.ITEMS['2.02'][0] == 'Results of Operations and Financial Condition'
    assert p8.classify(['2.02', '5.02']) == 'RESULTS' and p8.classify(['1.01', '5.02']) == 'OFFICERS_DIRECTORS'
    assert p8.classify(['1.01', '2.01']) == 'MATERIAL_AGREEMENT' and p8.classify(['2.01', '9.01']) == 'ACQUISITION_DISPOSITION'
    assert p8.classify(['7.01', '9.01']) == 'OTHER' and p8.classify([]) == 'OTHER'
    assert p8.parse_items('9.01, 2.02,2.02,7') == (['2.02', '9.01'], 1)
    assert p8.parse_items(None) == ([], 0) and p8.parse_items(['2.02']) == ([], 1)


def test_current_reports_window_dedup_conflict_and_acceptance_bound():
    rows = NVDA_ROWS + [NVDA_ROWS[0],  # identical duplicate folds
                        ('8-K', acc(180), '2026-10-06', '2026-10-06', '2026-10-06T13:00:00Z', '7.01'),
                        ('8-K', acc(180), '2026-10-06', '2026-10-06', '2026-10-06T13:00:00Z', '8.01'),  # conflict
                        ('8-K', acc(190), '2026-10-12', '2026-10-12', '2026-10-12T13:00:00Z', '8.01'),  # after acquisition
                        ('8-K', 'bad', '2026-10-01', '', '2026-10-01T13:00:00Z', '8.01')]
    out, counts = p8.current_reports('nvda', submissions('nvda', rows), acquired_at=NOW, since=date(2026, 7, 13))
    assert [r['accession'] for r in out] == [acc(101), acc(140), acc(150), acc(160), acc(170)]
    assert counts == {'excluded': 2, 'conflicts': 1, 'unknown_items': 1}
    assert out[0] == {'accession': acc(101), 'form': '8-K', 'filing_date': '2026-08-27', 'event_date': '2026-08-27',
                      'accepted_at': '2026-08-27T20:20:31+00:00', 'items': ['2.02', '9.01']}
    with pytest.raises(ValueError):
        p8.current_reports('nvda', submissions('amd', []), acquired_at=NOW, since=date(2026, 1, 1))
    broken = submissions('nvda', NVDA_ROWS)
    del broken['filings']['recent']['items']
    with pytest.raises(ValueError):
        p8.current_reports('nvda', broken, acquired_at=NOW, since=date(2026, 1, 1))


def test_exhibit_99_1_title_link_only():
    found = p8.exhibit_99_1('nvda', acc(101), full_indexes()[('nvda', acc(101))])
    assert found == {'title': 'PRESS RELEASE, DATED AUGUST 27, 2026',
                     'url': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000101/q2pr.htm'}
    assert p8.exhibit_99_1('nvda', acc(160), full_indexes()[('nvda', acc(160))])['title'] == 'EX-99.1'
    assert p8.exhibit_99_1('nvda', acc(140), full_indexes()[('nvda', acc(140))]) == 'NO_EXHIBIT_99_1'
    # a description with markup characters falls back to the exhibit type as the title
    assert p8.exhibit_99_1('nvda', acc(170), full_indexes()[('nvda', acc(170))])['title'] == 'EX-99.1'
    other = index_html('nvda', acc(101), [('Press release', '/Archives/edgar/data/320193/000104581026000101/x.htm', 'EX-99.1')])
    assert p8.exhibit_99_1('nvda', acc(101), other) == 'EXHIBIT_LINK_INVALID'
    assert p8.exhibit_99_1('nvda', acc(101), b'<html>no table</html>') == 'INDEX_INVALID'
    assert p8.exhibit_99_1('nvda', acc(101), b'\xff\xfe') == 'INDEX_INVALID'


def test_client_fixed_routes_user_agent_and_redirect_refusal():
    transport = Transport(full_subs(), full_indexes())
    client = p8.SecDisclosureClient(UA, **client_kwargs(transport))
    body, acquired = client.submissions('nvda')
    assert json.loads(body)['cik'] == 1045810 and acquired == NOW
    assert client.filing_index('nvda', acc(101)).startswith(b'<html>')
    assert all(h['User-Agent'] == UA for _, h in transport.calls)
    with pytest.raises(SecCollectionError):
        client.submissions('tokyo_electron')
    with pytest.raises(SecCollectionError):
        client.filing_index('nvda', '../../etc')
    with pytest.raises(SecCollectionError, match='SEC_HTTP_FAILED'):
        client.filing_index('nvda', acc(150))
    moved = lambda url, **_: SecResponse(200, b'<html></html>', None, url + '?moved')
    with pytest.raises(SecCollectionError, match='SEC_RESPONSE_INVALID'):
        p8.SecDisclosureClient(UA, **client_kwargs(moved)).filing_index('nvda', acc(101))
    with pytest.raises(SecCollectionError, match='SEC_URL_NOT_ALLOWED'):
        p8.default_transport('https://www.sec.gov/Archives/edgar/data/1045810/000104581026000101/q2pr.htm',
                             headers={}, timeout=1, max_body_bytes=10)
    with pytest.raises(SecCollectionError, match='SEC_USER_AGENT_INVALID'):
        p8.SecDisclosureClient('no contact', **client_kwargs(transport))


# --- public file ---------------------------------------------------------------------------------

def collected_nvda(now=NOW):
    rows, _ = p8.current_reports('nvda', submissions('nvda', NVDA_ROWS), acquired_at=now, since=(now - timedelta(days=90)).date())
    return {'nvda': {'acquired_at': now, 'rows': rows}}


def exhibits_nvda():
    return {a: p8.exhibit_99_1(c, a, b) if b is not None else 'INDEX_UNAVAILABLE' for (c, a), b in full_indexes().items()}


def payload_nvda():
    return sd.merge(None, collected_nvda(), as_of=NOW, exhibits=exhibits_nvda())


def test_merge_groups_amendment_and_stores_only_metadata():
    p = payload_nvda()
    assert p['state'] == 'LIVE' and p['channel'] == 'DISCLOSURE' and p['score_effect'] == 'NONE'
    assert p['companies']['nvda']['state'] == 'LIVE' and p['companies']['amd'] == {'state': 'NOT_AVAILABLE', 'acquired_at': None, 'reason_code': 'NOT_COLLECTED'}
    events = {e['accession']: e for e in p['events']}
    assert [e['accession'] for e in p['events']] == [acc(170), acc(160), acc(150), acc(140), acc(101)]
    assert events[acc(101)]['occurrence'] == 'NEW' and events[acc(140)]['occurrence'] == 'REPEAT'
    assert events[acc(140)]['group_id'] == events[acc(101)]['group_id'] == 'nvda:' + acc(101)
    assert events[acc(101)]['classification'] == 'RESULTS' and events[acc(150)]['classification'] == 'OFFICERS_DIRECTORS'
    assert events[acc(160)]['classification'] == 'MATERIAL_AGREEMENT' and events[acc(170)]['classification'] == 'OTHER'
    assert events[acc(101)]['exhibit_99_1'] == {'state': 'AVAILABLE', 'title': 'PRESS RELEASE, DATED AUGUST 27, 2026',
                                                'url': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000101/q2pr.htm',
                                                'released_at': '2026-08-27T20:20:31+00:00'}
    assert events[acc(150)]['exhibit_99_1'] == {'state': 'NOT_AVAILABLE', 'reason_code': 'INDEX_UNAVAILABLE'}
    assert events[acc(101)]['link'] == 'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000101/0001045810-26-000101-index.htm'
    assert set(events[acc(101)]) == set(sd.EVENT_KEYS)
    assert len(sd.encode(p)) < 10_000


def test_rolling_window_carry_forward_first_seen_and_retry():
    first = payload_nvda()
    assert sd.pending_exhibits(first, collected_nvda()) == [('nvda', acc(150))]  # INDEX_UNAVAILABLE retried only
    later = NOW + timedelta(days=50)
    # nvda not collected later (failure): previous rows and acquisition time are carried, now STALE.
    carried = sd.merge(first, {}, as_of=later)
    assert carried['companies']['nvda']['state'] == 'STALE' and carried['state'] == 'STALE'
    assert {e['accession'] for e in carried['events']} == {acc(140), acc(150), acc(160), acc(170)}  # 101 left the 90-day window
    assert all(e['first_seen_at'] == first['as_of'] for e in carried['events'])
    again = sd.merge(first, collected_nvda(later), as_of=later)
    assert again['companies']['nvda']['state'] == 'LIVE'
    kept = {e['accession']: e for e in again['events']}
    assert kept[acc(160)]['exhibit_99_1']['title'] == 'EX-99.1' and kept[acc(160)]['first_seen_at'] == first['as_of']


@pytest.mark.parametrize('mutate', [
    lambda p: p['events'][0].update(body='full text'),
    lambda p: p['events'][0].update(price=1),
    lambda p: p.update(score_effect='Q+1'),
    lambda p: p['events'][0].update(classification='RESULTS'),
    lambda p: p['events'][1].update(occurrence='REPEAT'),
    lambda p: p['events'][3].update(group_id='nvda:' + acc(140)),
    lambda p: p['events'].reverse(),
    lambda p: p['events'][0].update(link='https://example.com/x'),
    lambda p: p['events'][-1]['exhibit_99_1'].update(title='<script>x</script>'),
    lambda p: p['events'][-1]['exhibit_99_1'].update(title='two  spaces'),
    lambda p: p['events'][-1]['exhibit_99_1'].update(url='https://www.sec.gov/Archives/edgar/data/1/000104581026000101/q2pr.htm'),
    lambda p: p['events'][-1]['exhibit_99_1'].update(released_at='2026-08-28T00:00:00+00:00'),
    lambda p: p['events'][0].update(items=['9.01', '8.01']),
    lambda p: p['events'][0].update(items=['99.99']),
    lambda p: p['events'][0].update(accepted_at='2026-10-05T13:00:00Z'),
    lambda p: p['events'][0].update(filing_date='2026-06-01'),
    lambda p: p['events'][0].update(company_id='amd'),
    lambda p: p['companies']['nvda'].update(state='STALE'),
    lambda p: p.update(state='STALE'),
    lambda p: p['events'].append(copy.deepcopy(p['events'][0])),
])
def test_validator_fails_closed(mutate):
    p = payload_nvda()
    mutate(p)
    with pytest.raises(ValueError, match='SEC_DISCLOSURES_INVALID'):
        sd.require_sec_disclosures(p)


def test_guard_accepts_valid_and_rejects_price_or_invalid(tmp_path):
    guard = importlib.import_module('pages_artifact_guard')
    from build_pages_cockpit import build_public_cockpit
    site = tmp_path / 'site'
    build_public_cockpit(site)
    assert json.loads((site / sd.FILENAME).read_text())['state'] == 'NOT_AVAILABLE'
    (site / sd.FILENAME).write_bytes(sd.encode(payload_nvda()))
    assert guard.scan_artifact(site)['pages_artifact_guard'] == 'PASS'
    bad = payload_nvda()
    bad['events'][0]['price'] = 1
    (site / sd.FILENAME).write_bytes(sd.encode(bad))
    receipt = guard.scan_artifact(site)
    assert receipt['violations'].get('sensitive_json_fields') and receipt['violations'].get('sec_disclosures_boundary')


# --- tool ----------------------------------------------------------------------------------------

def opener(status=404, body=None, exc=None):
    def open_(request, timeout):
        if exc is not None:
            raise exc
        if status != 200:
            raise urllib.error.HTTPError(request.full_url, status, 'x', {}, None)

        class R(io.BytesIO):
            def __init__(self):
                super().__init__(body)
                self.status = 200

            def geturl(self):
                return request.full_url
        return R()
    return open_


def tool():
    return importlib.import_module('sec_disclosures')


def run_tool(tmp_path, capsys, *, previous=opener(), transport=None, live=True, preserve=False, environ=None):
    t = tool()
    transport = transport or Transport(full_subs(), full_indexes())
    code = t.run(tmp_path, live=live, preserve_only=preserve, environ={'SEC_USER_AGENT': UA} if environ is None else environ,
                 now=lambda: NOW, client_kwargs=client_kwargs(transport), open_previous=previous)
    return code, capsys.readouterr().out


def test_tool_live_writes_validated_file_and_prints_codes_only(tmp_path, capsys):
    code, out = run_tool(tmp_path, capsys)
    assert code == 0
    payload = sd.require_sec_disclosures(json.loads((tmp_path / sd.FILENAME).read_text()))
    assert len(payload['events']) == 5 and payload['companies']['nvda']['state'] == 'LIVE'
    assert 'SEC_8K_DISCLOSURES companies=17 collected=17 failed=0' in out and 'results=2' in out and 'exhibit_99_1=3' in out
    for secret in (UA, 'PRESS RELEASE', 'sec.gov', 'nvda', 'NVDA'):
        assert secret not in out


def test_tool_previous_and_failure_paths(tmp_path, capsys):
    t = tool()
    # network failure reading the previous copy: nothing written, exit 1
    code, out = run_tool(tmp_path, capsys, previous=opener(exc=urllib.error.URLError('down')))
    assert code == 1 and 'PREVIOUS_FETCH_FAILED nothing_written' in out and not (tmp_path / sd.FILENAME).exists()
    # invalid previous copy: discarded, fresh collection proceeds
    code, out = run_tool(tmp_path, capsys, previous=opener(200, b'{"kind":"SEC_DISCLOSURES"}'))
    assert code == 0 and 'PREVIOUS_DISCARDED' in out
    previous = (tmp_path / sd.FILENAME).read_bytes()
    # one company fails: others collected, failure printed with index and fixed code only
    failing = Transport(full_subs(), full_indexes(), fail={'nvda'})
    code, out = run_tool(tmp_path, capsys, previous=opener(200, previous), transport=failing)
    assert code == 0 and 'SEC_8K_FAILURE company_index=13 code=SEC_HTTP_403' in out
    carried = json.loads((tmp_path / sd.FILENAME).read_text())
    assert len(carried['events']) == 5  # nvda rows carried from the previous copy
    # all fail without previous: nothing written
    (tmp_path / sd.FILENAME).unlink()
    dead = Transport(full_subs(), full_indexes(), fail=set(US_LISTINGS))
    code, out = run_tool(tmp_path, capsys, transport=dead)
    assert code == 1 and 'ALL_FAILED nothing_written' in out and not (tmp_path / sd.FILENAME).exists()
    # missing user agent
    code, out = run_tool(tmp_path, capsys, environ={})
    assert code == 1 and 'SEC_USER_AGENT_MISSING' in out
    # preserve-only: no SEC requests, previous restated
    quiet = Transport({}, {})
    code, out = run_tool(tmp_path, capsys, previous=opener(200, previous), transport=quiet, live=False, preserve=True)
    assert code == 0 and 'PREVIOUS_RESTORED events=5' in out and quiet.calls == []
    code, out = run_tool(tmp_path, capsys, previous=opener(404), transport=quiet, live=False, preserve=True)
    assert code == 0 and 'PREVIOUS_NOT_AVAILABLE' in out
    with pytest.raises(SystemExit):
        t.main(['--out', str(tmp_path), '--bogus'])
    assert capsys.readouterr().out == 'SEC_8K_DISCLOSURES ARGUMENTS_INVALID\n'


def test_workflows_add_one_live_step_and_one_preserve_line():
    daily = (ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    pages = (ROOT.parent / '.github/workflows/cockpit-pages.yml').read_text()
    live = 'python implementation/tools/sec_disclosures.py --live --out "$RUNNER_TEMP/public-cockpit"'
    assert daily.count(live) == 1 and daily.index(live) < daily.index('actions/upload-pages-artifact')
    step = daily[daily.index(live) - 400:daily.index(live) + 200]
    assert 'SEC_USER_AGENT: ${{ secrets.SEC_USER_AGENT }}' in step and 'pages_artifact_guard.py' in step
    assert pages.count('sec_disclosures.py --preserve-only --out "$RUNNER_TEMP/public-cockpit"') == 1
    assert pages.index('sec_disclosures.py --preserve-only') < pages.index('actions/upload-pages-artifact')


# --- earnings date: estimated -> confirmed --------------------------------------------------------

def screens_manifest(tmp_path, rows):
    from investment_system.product.public_engine_screens import generate_screen_bundle
    periodic = [('10-Q', acc(10 + i, y), f'20{y}-{m}', f'20{y}-{r}', f'20{y}-{m}T20:30:00Z', '')
                for i, (y, r, m) in enumerate([(25, '04-27', '05-28'), (25, '07-27', '08-27'), (25, '10-26', '11-19'),
                                               (26, '01-25', '02-25'), (26, '04-26', '05-27'), (26, '07-26', '08-27')])]
    subs = submissions('nvda', list(rows) + periodic)
    facts = {'cik': 1045810, 'facts': {}}
    (tmp_path / 'f.json').write_text(json.dumps(facts))
    (tmp_path / 's.json').write_text(json.dumps(subs))
    manifest = {'schema_version': 1, 'sec': [{'company_id': 'nvda', 'companyfacts': 'f.json', 'submissions': 's.json',
                                             'acquired_at': '2026-10-11T22:00:00Z', 'synthetic': False}], 'macro': [], 'thirteen_f': []}
    return generate_screen_bundle(manifest=manifest, input_root=tmp_path, as_of=NOW, stale_after=timedelta(hours=24))['sec-filing-windows.json']


def test_results_8k_flips_latest_quarter_to_confirmed(tmp_path):
    p = screens_manifest(tmp_path, NVDA_ROWS[:2])
    row = p['data']['companies']['nvda']
    assert row['role'] == 'ESTIMATED_PATTERN_NOT_CONFIRMED' and row['groups']
    assert p8.latest_period_end(row['groups'], NOW.date()) == date(2026, 7, 27)
    # 20:20 UTC on 2026-08-27 is 16:20 Eastern: the release date is the Eastern date.
    assert row['confirmed_earnings_date'] == '2026-08-27'
    assert row['earnings_confirmation'] == {'basis': 'SEC_8K_ITEM_2_02', 'period_end': '2026-07-27',
                                            'accession': acc(101), 'accepted_at': '2026-08-27T20:20:31+00:00'}


@pytest.mark.parametrize('rows', [
    [],
    [('8-K/A', acc(140), '2026-09-02', '2026-08-27', '2026-09-02T12:00:00Z', '2.02,9.01')],  # an amendment does not confirm
    [('8-K', acc(150), '2026-09-15', '2026-09-12', '2026-09-15T21:00:00Z', '5.02')],
    [('8-K', acc(90), '2026-07-20', '2026-07-20', '2026-07-20T20:00:00Z', '2.02')],  # before the period end
])
def test_without_results_8k_the_quarter_stays_estimated(tmp_path, rows):
    row = screens_manifest(tmp_path, rows)['data']['companies']['nvda']
    assert row['confirmed_earnings_date'] is None and row['earnings_confirmation'] is None


def test_filing_window_validator_accepts_legacy_and_rejects_forged_confirmation(tmp_path):
    from investment_system.product.public_engine_screens import require_public_screen
    p = screens_manifest(tmp_path, NVDA_ROWS[:1])
    legacy = copy.deepcopy(p)
    for r in legacy['data']['companies'].values():
        del r['earnings_confirmation']
        r['confirmed_earnings_date'] = None
    require_public_screen('sec-filing-windows.json', legacy)
    for mutate in (lambda r: r.update(confirmed_earnings_date='2026-07-01'),
                   lambda r: r['earnings_confirmation'].update(period_end='2026-04-26'),
                   lambda r: r['earnings_confirmation'].update(basis='NEWS'),
                   lambda r: r.update(earnings_confirmation=None),
                   lambda r: r['earnings_confirmation'].update(accepted_at='2026-10-12T00:00:00Z')):
        bad = copy.deepcopy(p)
        mutate(bad['data']['companies']['nvda'])
        with pytest.raises(ValueError):
            require_public_screen('sec-filing-windows.json', bad)
    no_conf = copy.deepcopy(legacy)
    no_conf['data']['companies']['nvda']['confirmed_earnings_date'] = '2026-08-27'
    with pytest.raises(ValueError):
        require_public_screen('sec-filing-windows.json', no_conf)


# --- JS == Python --------------------------------------------------------------------------------

def node(script, payload):
    result = subprocess.run([NODE, '-e', script], input=json.dumps(payload), capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout)


@pytest.mark.skipif(NODE is None, reason='node not installed')
def test_js_reader_matches_python_vectors(tmp_path):
    p = payload_nvda()
    cases = {'valid': p, 'empty': sd.merge(None, {}, as_of=NOW)}
    for i, mutate in enumerate(test_validator_fails_closed.pytestmark[0].args[1]):
        bad = payload_nvda()
        mutate(bad)
        cases[f'bad{i}'] = bad
    script = ("const api=require(%s);let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{const cases=JSON.parse(s),out={};"
              "for(const[k,v]of Object.entries(cases)){try{api.validate(v);out[k]=true;}catch(_){out[k]=false;}}"
              "out.items=api.ITEMS;out.ciks=api.CIKS;out.classes=Object.keys(api.CLASSES);"
              "out.classify=[[],['2.02','5.02'],['1.01','5.02'],['1.01','2.01'],['2.01'],['7.01','9.01']].map(api.classify);"
              "out.timeline=api.timeline(cases.valid,{companyIds:['nvda']}).map(r=>r.channel+':'+r.event.accession);"
              "process.stdout.write(JSON.stringify(out));});") % json.dumps(str(JS))
    out = node(script, cases)
    assert out.pop('valid') is True and out.pop('empty') is True
    assert {k: list(v) for k, v in p8.ITEMS.items()} == out.pop('items')
    assert {k: v['cik'] for k, v in US_LISTINGS.items()} == out.pop('ciks')
    assert out.pop('classes') == list(sd.CLASSIFICATIONS)
    assert out.pop('classify') == [p8.classify(x) for x in [[], ['2.02', '5.02'], ['1.01', '5.02'], ['1.01', '2.01'], ['2.01'], ['7.01', '9.01']]]
    assert out.pop('timeline') == ['DISCLOSURE:' + e['accession'] for e in p['events']]
    assert all(v is False for v in out.values()), out


@pytest.mark.skipif(NODE is None, reason='node not installed')
def test_js_earnings_status_and_period_end_match_python(tmp_path):
    p = screens_manifest(tmp_path, NVDA_ROWS[:1])
    legacy = copy.deepcopy(p)
    for r in legacy['data']['companies'].values():
        del r['earnings_confirmation']
        r['confirmed_earnings_date'] = None
    forged = copy.deepcopy(p)
    forged['data']['companies']['nvda']['earnings_confirmation']['period_end'] = '2026-04-26'
    groups = p['data']['companies']['nvda']['groups']
    days = ['2026-10-11', '2026-07-26', '2026-07-27', '2026-01-01', '2025-02-28', '2026-12-31']
    script = ("const api=require(%s);let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{const c=JSON.parse(s),out={};"
              "const ok=v=>{try{api.validate('sec-filing-windows.json',v);return true;}catch(_){return false;}};"
              "out.valid=ok(c.p);out.legacy=ok(c.legacy);out.forged=ok(c.forged);"
              "out.ends=c.days.map(d=>api.latestPeriodEnd(c.groups,d));const r=c.p.data.companies.nvda;"
              "out.confirmed=api.earningsStatus(r,new Date('2026-10-11T23:00:00Z'));"
              "out.nextQuarter=api.earningsStatus(r,new Date('2026-10-28T12:00:00Z')).status;"
              "process.stdout.write(JSON.stringify(out));});") % json.dumps(str(SCREENS_JS))
    out = node(script, {'p': p, 'legacy': legacy, 'forged': forged, 'groups': groups, 'days': days})
    assert out['valid'] is True and out['legacy'] is True and out['forged'] is False
    expected = [p8.latest_period_end(groups, date.fromisoformat(d)) for d in days]
    assert out['ends'] == [d.isoformat() if d else None for d in expected]
    assert out['confirmed'] == {'status': 'CONFIRMED', 'date': '2026-08-27', 'period_end': '2026-07-27',
                                'accession': acc(101), 'basis': 'SEC_8K_ITEM_2_02'}
    assert out['nextQuarter'] == 'ESTIMATED'
