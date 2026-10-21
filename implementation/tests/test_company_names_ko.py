"""KR-NAMES (owner decision 2026-10-18): reviewed company-names-ko.json, its build tool and the Pages guard check.

The tool is exercised on small synthetic saved inputs only (no network: sockets are disabled while it runs). The
committed file is checked for the decision's invariants: every Universe504 code and TARGET company_id exactly once, no
ticker-only link, UNREGISTERED means a null Korean name, aliases unique per company, cross-company collisions reported.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import tempfile

import pytest

from investment_system.markets.us import OUT_OF_US_TRACK, US_LISTINGS
from investment_system.universe.company_names_ko import (FILENAME, SCHEMA, alias_collisions, check_shape, compact,
                                                         public_payload, require_company_names_ko, source_payload)
from investment_system.universe.universe_codes import source_codes

ROOT = Path(__file__).parents[1]
SEARCH = ROOT / 'src/investment_system/product/web_assets/entity-search.js'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = load('build_company_names_ko', ROOT / 'tools/build_company_names_ko.py')


def test_committed_file_is_valid_and_complete():
    payload = public_payload()
    assert FILENAME == 'company-names-ko.json' and payload['schema'] == SCHEMA == 'company-names-ko/1'
    records = payload['records']
    codes = [r['universe_code'] for r in records if r['universe_code']]
    assert sorted(codes) == sorted(source_codes()) and len(codes) == len(set(codes)) == 504
    targets = [r['key'] for r in records if r['key_kind'] == 'TARGET_COMPANY_ID']
    assert sorted(targets) == sorted([*US_LISTINGS, *OUT_OF_US_TRACK]) and len(targets) == 19
    assert len({r['key'] for r in records}) == len(records) == 504 + 19 - sum(1 for r in records if r['key_kind'] == 'TARGET_COMPANY_ID' and r['universe_code'])
    c = payload['counts']
    assert c['official'] + c['common'] + c['unregistered'] == c['records'] == len(records)
    assert c['en_name_present'] + c['en_name_missing'] == len(records)
    assert all(len(i['sha256']) == 64 for i in payload['inputs'])


def test_no_record_links_by_ticker_alone():
    for r in public_payload()['records']:
        if r['key_kind'] == 'UNIVERSE_CODE':
            # The Universe code itself is the key; ticker/exchange are only its parts and a CIK cross-checks it.
            assert r['universe_code'] == r['key'] == r['exchange'] + ':' + r['ticker'] and r['cik']
        elif r['key'] in US_LISTINGS:
            listing = US_LISTINGS[r['key']]
            assert r['cik'] == listing['cik'] and r['universe_code'] in (None, listing['exchange'] + ':' + listing['yahoo'])
        else:
            assert r['cik'] is None and r['universe_code'] is None
    # Several codes of one issuer are told apart by their share class.
    per_cik = {}
    for r in public_payload()['records']:
        if r['cik']:
            per_cik.setdefault(r['cik'], []).append(r)
    multi = {cik: sorted((r['ticker'], r['class_label']) for r in rows) for cik, rows in per_cik.items() if len(rows) > 1}
    assert multi == {'0001652044': [('GOOG', 'C'), ('GOOGL', 'A')], '0001754301': [('FOX', 'B'), ('FOXA', 'A')],
                     '0001564708': [('NWS', 'B'), ('NWSA', 'A')]}


def test_unregistered_names_and_aliases():
    records = public_payload()['records']
    for r in records:
        if r['ko_status'] == 'UNREGISTERED':
            assert r['ko_name'] is None and r['ko_source'] is None
        else:
            assert r['ko_name'] and r['ko_source'].startswith('https://')
        forms = [compact(a['text']) for a in r['aliases']] + ([compact(r['ko_name'])] if r['ko_name'] else [])
        assert len(forms) == len(set(forms)), r['key']
        assert all(a['source'].startswith('https://') for a in r['aliases'])
    # Cross-company collisions are reported; today they are only share classes of one issuer.
    by_key = {r['key']: r for r in records}
    for _form, keys in alias_collisions(public_payload()):
        assert len({by_key[k]['cik'] for k in keys}) == 1


def test_reviewed_tables_hash_matches_the_tool():
    reviewed = json.dumps({'official': TOOL.OFFICIAL, 'share_class': TOOL.SHARE_CLASS, 'preferred': TOOL.PREFERRED,
                           'no_current_name': sorted(TOOL.NO_CURRENT_NAME),
                           'excluded_aliases': {k: sorted(v) for k, v in TOOL.EXCLUDED_ALIASES.items()}},
                          ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    inputs = {i['name']: i['sha256'] for i in public_payload()['inputs']}
    assert inputs['reviewed_official_and_share_class_tables'] == hashlib.sha256(reviewed).hexdigest()


@pytest.mark.parametrize('mutate', [
    lambda p: p.update(extra=1),
    lambda p: p.update(schema='company-names-ko/2'),
    lambda p: p['records'].pop(),
    lambda p: p['records'].append(copy.deepcopy(p['records'][-1])),
    lambda p: p['records'][-1].update(price=1),
    lambda p: next(r for r in p['records'] if r['ko_status'] == 'UNREGISTERED').update(ko_name='임의 이름'),
    lambda p: next(r for r in p['records'] if r['ko_status'] == 'COMMON').update(ko_source=None),
    lambda p: next(r for r in p['records'] if r['aliases']).update(aliases=[{'text': 'x', 'lang': 'ko', 'source': 'no-url'}]),
    lambda p: next(r for r in p['records'] if r['key'] == 'nvda').update(cik='0000000001'),
    lambda p: next(r for r in p['records'] if r['key'] == 'nvda').update(universe_code='NASDAQ:AMD'),
    lambda p: p['counts'].update(official=0),
])
def test_strict_validator_rejects_changes(mutate):
    payload = copy.deepcopy(public_payload())
    mutate(payload)
    with pytest.raises(ValueError):
        require_company_names_ko(payload)


# ---------- the build tool on synthetic saved inputs ----------

def synthetic_inputs(*, nvda_cik=None):
    codes = source_codes()
    rows, fake = [], 900000
    target_code = {v['exchange'] + ':' + v['yahoo']: v['cik'] for v in US_LISTINGS.values()}
    for code in codes:
        venue, symbol = code.split(':')
        if code in target_code:
            cik = int(target_code[code])
        elif code in ('NASDAQ:GOOG', 'NASDAQ:GOOGL'):
            cik = 1652044
        elif code in ('NASDAQ:FOX', 'NASDAQ:FOXA'):
            cik = 1754301
        elif code in ('NASDAQ:NWS', 'NASDAQ:NWSA'):
            cik = 1564708
        else:
            fake += 1
            cik = fake
        if code == 'NASDAQ:NVDA' and nvda_cik:
            cik = nvda_cik
        exchange = {'NASDAQ': 'Nasdaq', 'NYSE': 'NYSE', 'BATS': 'CBOE'}[venue]
        rows.append([cik, 'Company ' + symbol + ' Inc', symbol.replace('.', '-'), exchange])
    sec = json.dumps({'fields': ['cik', 'name', 'ticker', 'exchange'], 'data': rows}).encode()

    def b(item, cik, **kw):
        out = {'item': {'value': 'http://www.wikidata.org/entity/' + item}, 'cik': {'value': cik}}
        out.update({k: {'value': v} for k, v in kw.items()})
        return out
    first = rows[1]  # NYSE:AOS: an ordinary code
    bindings = [
        b('Q1', str(first[0]).zfill(10), ko='가나 회사 (기업)', en='Company AOS', koalt='가나'),  # Hangul label, disambiguator dropped
        b('Q2', '0000002488', ko='AMD', en='AMD'),                                             # TARGET with an OFFICIAL override
        b('Q3', '0000789019', ko='Microsoft', kowiki='https://ko.wikipedia.org/wiki/%EB%A7%88%EC%9D%B4%ED%81%AC%EB%A1%9C'),
        b('Q4', str(rows[2][0]), ko='Latin Only'),                                             # no Hangul anywhere: UNREGISTERED
        b('Q5', '0000048898', ko='허벨', en='Other Name'),                                        # two items, none matches the SEC title
        b('Q6', '0000048898', ko='허벨 2', en='Another Name'),
        b('Q7', '0001652044', ko='알파벳', en='Company GOOG Inc'),
    ]
    wd = json.dumps({'results': {'bindings': bindings}}).encode()
    non_sec = json.dumps({'results': {'bindings': [{'item': {'value': 'http://www.wikidata.org/entity/Q9'},
                                                    'ex': {'value': 'http://www.wikidata.org/entity/Q217475'},
                                                    'tk': {'value': '8035'}, 'ko': {'value': '도쿄 일렉트론'},
                                                    'en': {'value': 'Tokyo Electron'}}]}}).encode()
    return sec, wd, non_sec


@pytest.fixture
def offline(monkeypatch):
    def refuse(*_a, **_k):
        raise AssertionError('the build tool must not open network connections')
    monkeypatch.setattr(socket, 'socket', refuse)
    monkeypatch.setattr(socket, 'create_connection', refuse)


def test_tool_builds_from_saved_inputs_without_network(offline):
    sec, wd, non_sec = synthetic_inputs()
    notes = []
    payload = TOOL.build(sec, wd, non_sec, '2026-10-18', notes)
    check_shape(payload)
    by = {r['key']: r for r in payload['records']}
    aos = by['NYSE:AOS']
    assert (aos['ko_name'], aos['ko_status'], aos['ko_source']) == ('가나 회사', 'COMMON', 'https://www.wikidata.org/wiki/Q1')
    assert [a['text'] for a in aos['aliases']] == ['가나'] and aos['en_name'] == 'Company AOS Inc'
    assert (by['amd']['ko_name'], by['amd']['ko_status']) == ('AMD', 'OFFICIAL')
    assert (by['msft']['ko_status'], by['msft']['universe_code']) == ('OFFICIAL', 'NASDAQ:MSFT')
    latin = next(r for r in payload['records'] if r['cik'] == str(json.loads(sec)['data'][2][0]).zfill(10))
    assert latin['ko_status'] == 'UNREGISTERED' and latin['ko_name'] is None and latin['aliases'] == []
    assert by['hubb']['ko_status'] == 'UNREGISTERED' and any(n.get('key') == 'hubb' and n['chosen'] is None for n in notes)
    assert (by['googl']['ko_name'], by['googl']['class_label'], by['NASDAQ:GOOG']['class_label']) == ('알파벳', 'A', 'C')
    assert (by['tokyo_electron']['ko_name'], by['tokyo_electron']['en_name']) == ('도쿄 일렉트론', 'Tokyo Electron')
    assert by['hanmi']['ko_status'] == 'OFFICIAL' and by['hanmi']['en_name'] is None
    assert TOOL.build(sec, wd, non_sec, '2026-10-18') == payload  # deterministic
    report = TOOL.report(payload, notes)
    assert report['alias_collisions'] == [('알파벳', ['NASDAQ:GOOG', 'googl'])]


def test_tool_never_links_a_target_by_ticker_alone(offline):
    # NASDAQ:NVDA bound to another CIK in the registry: same ticker, different issuer -> no link, two records.
    sec, wd, non_sec = synthetic_inputs(nvda_cik=4242)
    payload = TOOL.build(sec, wd, non_sec, '2026-10-18')
    by = {r['key']: r for r in payload['records']}
    assert by['nvda']['universe_code'] is None and by['nvda']['cik'] == US_LISTINGS['nvda']['cik']
    assert by['NASDAQ:NVDA']['cik'] == '0000004242' and by['NASDAQ:NVDA']['key_kind'] == 'UNIVERSE_CODE'


def test_build_publishes_it_and_the_guard_checks_it():
    build = load('build_pages_cockpit', ROOT / 'tools/build_pages_cockpit.py')
    guard = load('pages_artifact_guard', ROOT / 'tools/pages_artifact_guard.py')
    with tempfile.TemporaryDirectory() as folder:
        site = Path(folder) / 'site'
        build.build_public_cockpit(site)
        published = json.loads((site / FILENAME).read_text(encoding='utf-8'))
        assert published == source_payload()
        assert guard.scan_artifact(site)['pages_artifact_guard'] == 'PASS'
        renamed = copy.deepcopy(published)
        next(r for r in renamed['records'] if r['key'] == 'nvda')['ko_name'] = '다른 이름'
        for bad in (renamed, {**published, 'records': published['records'][:-1]}):
            (site / FILENAME).write_text(json.dumps(bad, ensure_ascii=False), encoding='utf-8')
            receipt = guard.scan_artifact(site)
            assert receipt['pages_artifact_guard'] == 'FAIL' and receipt['violations'].get('company_names_boundary') == 1


def test_browser_index_reads_the_committed_file():
    script = ('const E=require(process.argv[1]);const n=E.nameIndex(JSON.parse(require("fs").readFileSync(0,"utf8")));'
              'process.stdout.write(JSON.stringify([n.codes().length,E.companyTitle(n.get("NASDAQ:GOOG"),null,"ko-KR"),'
              'E.companyTitle(n.get("googl"),null,"ko-KR"),E.companyTitle(n.get("NASDAQ:GOOGL"),null,"ko-KR"),'
              'E.companyTitle(n.get("hubb"),null,"ko-KR"),E.companyTitle(n.get("lrcx"),null,"ko-KR")]));')
    out = subprocess.run(['node', '-e', script, str(SEARCH)], input=json.dumps(source_payload()), capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout) == [504, '알파벳 C · GOOG', '알파벳 A · GOOGL', '알파벳 A · GOOGL', 'HUBBELL INC · HUBB', '램리서치 · LRCX']
