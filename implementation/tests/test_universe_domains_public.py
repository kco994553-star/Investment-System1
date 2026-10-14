"""Public universe-domains.json: domains only, strict validation, source priority and the offline/live pipeline."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile

import pytest

from investment_system.universe.universe_codes import source_codes
from investment_system.universe.universe_domains import (EXTRA_CODES, FILENAME, SCHEMA, all_codes, counts, merge,
                                                         normalize_domain, public_payload, require_universe_domains,
                                                         reviewed_rows)

ROOT = Path(__file__).parents[1]
ASSETS = ROOT / 'src/investment_system/product/web_assets'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_payload_is_domains_only_for_every_code_in_order():
    payload = public_payload()
    assert FILENAME == 'universe-domains.json' and payload['schema'] == SCHEMA == 'universe-domains/1'
    assert list(payload) == ['schema', 'rows'] and [r[0] for r in payload['rows']] == [*source_codes(), *EXTRA_CODES]
    assert len(payload['rows']) == 506
    for code, domain, source in payload['rows']:
        assert (domain is None) == (source is None)
        assert domain is None or (normalize_domain(domain) == domain and source in ('sec', 'wikidata', 'manual'))
    values = json.dumps([row[1:] for row in payload['rows']]).lower()  # codes like NASDAQ:COST are tickers, not fields
    for word in ('price', 'marketcap', 'rank', 'quantity', 'cost', 'token', 'logo', '/', '?'):
        assert word not in values
    # The reviewed list covers the TARGET 19 (GOOGL and GOOG share one issuer); everything else stays empty.
    assert counts(payload) == {'sec': 0, 'wikidata': 0, 'manual': 20, 'empty': 486}


@pytest.mark.parametrize('value,expected', [
    ('http://www.Apple.com/investor', 'apple.com'), ('https://investor.nvidia.com', 'investor.nvidia.com'),
    ('abc.xyz', 'abc.xyz'), ('www.tel.com/', 'tel.com'), ('', None), ('https://1.2.3.4', None), ('ftp://a.com', None),
    ('https://user' + chr(64) + 'evil.com', None), ('https://a.com:8443', None), ('not a url', None), ('localhost', None), (None, None),
])
def test_normalize_domain(value, expected):
    assert normalize_domain(value) == expected


@pytest.mark.parametrize('mutate', [
    lambda p: p.update(extra=1),
    lambda p: p.update(schema='universe-domains/2'),
    lambda p: p['rows'].pop(),
    lambda p: p['rows'].reverse(),
    lambda p: p['rows'][0].__setitem__(1, 'https://3m.com'),
    lambda p: p['rows'][0].__setitem__(1, '3m.com'),
    lambda p: p['rows'][0].__setitem__(2, 'manual'),
    lambda p: p['rows'][0].extend([1]),
    lambda p: p['rows'][0].__setitem__(1, 'Bad Domain.com'),
    lambda p: p['rows'].append(['NYSE:MMM', None, None]),
    lambda p: p['rows'][0].__setitem__(2, 'guess'),
])
def test_strict_validator_rejects_changes(mutate):
    payload = copy.deepcopy(public_payload())
    mutate(payload)
    with pytest.raises(ValueError):
        require_universe_domains(payload)


def test_source_priority_sec_then_wikidata_then_manual_and_unknown_stays_empty():
    reviewed = {'NASDAQ:NVDA': ('nvidia.com', 'manual'), 'NYSE:MMM': ('m-manual.com', 'manual')}
    rows = merge(reviewed=reviewed, sec={'NASDAQ:NVDA': 'nvidia-sec.com'}, sec_checked={'NASDAQ:NVDA'},
                 wikidata={'NASDAQ:NVDA': 'nvidia-wd.com', 'NYSE:MMM': '3m.com'})
    assert rows['NASDAQ:NVDA'] == ('nvidia-sec.com', 'sec')
    assert rows['NYSE:MMM'] == ('3m.com', 'wikidata')
    assert rows['NYSE:AOS'] is None
    only_manual = merge(reviewed=reviewed)
    assert only_manual['NYSE:MMM'] == ('m-manual.com', 'manual')


def test_previous_copy_keeps_unchecked_sec_rows_and_wikidata_when_the_query_failed():
    previous = public_payload(merge(reviewed={}, sec={'NYSE:MMM': '3m.com', 'NYSE:AOS': 'aosmith.com'},
                                    sec_checked={'NYSE:MMM', 'NYSE:AOS'}, wikidata={'NYSE:ABT': 'abbott.com'}))
    rows = merge(reviewed={}, previous=previous, sec={}, sec_checked={'NYSE:AOS'}, wikidata=None)
    assert rows['NYSE:MMM'] == ('3m.com', 'sec')          # not checked today: kept
    assert rows['NYSE:AOS'] is None                        # checked today and empty: dropped, not guessed
    assert rows['NYSE:ABT'] == ('abbott.com', 'wikidata')  # Wikidata not run today: kept
    rows = merge(reviewed={}, previous=previous, wikidata={})
    assert rows['NYSE:ABT'] is None                        # Wikidata ran and no longer lists it


def test_reviewed_source_file_is_manual_domains_only():
    rows = reviewed_rows()
    assert set(rows) <= set(all_codes())
    assert all(source == 'manual' for _, source in rows.values())


def test_wikidata_parser_prefers_preferred_rank_and_leaves_ambiguity_empty():
    tool = load('universe_domains_pipeline', ROOT / 'tools/universe_domains_pipeline.py')
    def b(cik, site, rank='Normal'):
        return {'cik': {'value': cik}, 'site': {'value': site}, 'rank': {'value': 'http://wikiba.se/ontology#' + rank + 'Rank'}}
    body = json.dumps({'results': {'bindings': [
        b('0000000001', 'https://www.one.com/'), b('1', 'http://one.com'),
        b('0000000002', 'https://two-a.com'), b('0000000002', 'https://two-b.com'),
        b('0000000003', 'https://three-a.com'), b('0000000003', 'https://three-b.com', 'Preferred'),
        b('0000000004', 'not a url'), b('0000000009', 'https://unknown.com'),
    ]}}).encode()
    out = tool.wikidata_domains(body, {'0000000001', '0000000002', '0000000003', '0000000004'})
    assert out == {'0000000001': 'one.com', '0000000003': 'three-b.com'}
    query = tool.wikidata_query(['0000000001'])
    assert 'wdt:P5531' in query and 'P856' in query and '"0000000001" "1"' in query


def test_pipeline_offline_live_and_preserve_write_validated_domains_only():
    tool = load('universe_domains_pipeline', ROOT / 'tools/universe_domains_pipeline.py')

    class Issuer:
        def __init__(self, cik, codes):
            self.cik, self.codes = cik, codes

    class Registry:
        issuers = (Issuer('0000000066', ('NYSE:MMM',)), Issuer('0001652044', ('NASDAQ:GOOGL', 'NASDAQ:GOOG')))

    def sec_fetch(agent, now=None):
        assert agent == 'synthetic agent'
        return {'NYSE:MMM': '3m.com'}, {'NYSE:MMM'}, Registry()

    def wiki_fetch(ciks):
        assert sorted(ciks) == ['0000000066', '0001652044']
        return {'0001652044': 'abc.xyz', '0000000066': 'wd-3m.com'}

    payload, status = tool.collect(environ={'SEC_USER_AGENT': 'synthetic agent'}, previous_fetch=lambda: None,
                                   sec_fetch=sec_fetch, wiki_fetch=wiki_fetch)
    rows = {code: (domain, source) for code, domain, source in payload['rows']}
    assert rows['NYSE:MMM'] == ('3m.com', 'sec') and rows['NASDAQ:GOOG'] == ('abc.xyz', 'wikidata')
    assert rows['NASDAQ:NVDA'] == ('nvidia.com', 'manual')
    assert status == {'sec_checked': 1, 'sec_filled': 1, 'wikidata': 'OK'}
    line = tool.summary(payload, status)
    assert line.startswith('UNIVERSE_DOMAINS_OK sec=1 wikidata=2 manual=') and '3m.com' not in line and 'synthetic' not in line
    # No SEC agent: nothing live, reviewed rows only, and the line says why.
    payload, status = tool.collect(environ={}, previous_fetch=lambda: None)
    assert counts(payload)['manual'] == 20 and status['sec'] == 'SEC_USER_AGENT_MISSING' and status['wikidata'] == 'NOT_RUN'
    with tempfile.TemporaryDirectory() as folder:
        tool.emit(folder)
        assert json.loads((Path(folder) / FILENAME).read_text()) == public_payload()
        previous = public_payload(merge(sec={'NYSE:MMM': '3m.com'}, sec_checked={'NYSE:MMM'}))
        tool.preserve(folder, previous_fetch=lambda: previous)
        assert ['NYSE:MMM', '3m.com', 'sec'] in json.loads((Path(folder) / FILENAME).read_text())['rows']


def test_previous_copy_fetch_rejects_invalid_or_redirected_copies():
    tool = load('universe_domains_pipeline', ROOT / 'tools/universe_domains_pipeline.py')

    class Response(io.BytesIO):
        def __init__(self, body, url=tool.SOURCE, status=200):
            super().__init__(body)
            self.status, self._url = status, url
        def geturl(self):
            return self._url
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    good = json.dumps(public_payload()).encode()
    assert tool.fetch_previous(open_response=lambda r, timeout: Response(good)) == public_payload()
    assert tool.fetch_previous(open_response=lambda r, timeout: Response(b'{"schema":"x"}')) is None
    with pytest.raises(OSError):
        tool.fetch_previous(open_response=lambda r, timeout: Response(good, url='https://example.com/x'))


def test_build_publishes_domains_and_local_logo_bundle_and_the_guard_checks_it():
    build = load('build_pages_cockpit', ROOT / 'tools/build_pages_cockpit.py')
    guard = load('pages_artifact_guard', ROOT / 'tools/pages_artifact_guard.py')
    with tempfile.TemporaryDirectory() as folder:
        site = Path(folder) / 'site'
        build.build_public_cockpit(site)
        assert json.loads((site / FILENAME).read_text(encoding='utf-8')) == public_payload()
        assert guard.scan_artifact(site)['pages_artifact_guard'] == 'PASS'
        # Logo PNGs are local data images in company-logos.json, never runtime external images.
        images = sorted(p.name for p in site.iterdir() if p.suffix.lower() in {'.png', '.ico', '.svg', '.jpg', '.jpeg', '.webp', '.gif'})
        assert images == ['icon-192.png', 'icon-512.png']
        payload = json.loads((site / FILENAME).read_text())
        payload['rows'][0][1:] = ['evil.example', 'sec']
        (site / FILENAME).write_text(json.dumps(payload))
        assert guard.scan_artifact(site)['pages_artifact_guard'] == 'PASS'
        payload['rows'][0][2] = 'guess'
        (site / FILENAME).write_text(json.dumps(payload))
        assert guard.scan_artifact(site)['violations'] == {'universe_domains_boundary': 1}
    assert sorted(p.name for p in ASSETS.iterdir() if p.suffix.lower() in {'.png', '.ico', '.svg', '.jpg', '.jpeg', '.webp', '.gif'}) == ['icon-192.png', 'icon-512.png']
