"""News signals (GDELT DOC 2.0 + company IR feeds): rules, providers, public file, tool, workflow, JS == Python.

Synthetic transports only: GDELT, company IR sites and sec.gov are never contacted.
"""
from datetime import datetime, timedelta, timezone
import copy
import importlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from investment_system.markets.us import US_LISTINGS
from investment_system.product import news_signals as ns
from investment_system.product import sec_disclosures as sd
from investment_system.providers import news_feeds as nf

NOW = datetime(2026, 10, 11, 22, 40, tzinfo=timezone.utc)
JS = ROOT / 'src/investment_system/product/web_assets/news-signals.js'
SEC_JS = ROOT / 'src/investment_system/product/web_assets/sec-disclosures.js'
NODE = shutil.which('node')


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


def acc(n, cik='0001045810'):
    return f'{cik}-26-{n:06d}'


MSFT_CIK = '0000789019'


def sec_payload():
    """Validated sec-disclosures.json: NVDA results 8-K with a generic EX-99.1 title, MSFT agreement 8-K with a specific one."""
    rows = {
        'nvda': [{'accession': acc(101), 'form': '8-K', 'filing_date': '2026-10-08', 'event_date': '2026-10-08',
                  'accepted_at': '2026-10-08T20:20:31+00:00', 'items': ['2.02', '9.01']}],
        'msft': [{'accession': acc(160, MSFT_CIK), 'form': '8-K', 'filing_date': '2026-10-09', 'event_date': '2026-10-09',
                  'accepted_at': '2026-10-09T13:00:00+00:00', 'items': ['1.01', '9.01']}],
    }
    exhibits = {
        acc(101): {'title': 'PRESS RELEASE, DATED OCTOBER 8, 2026',
                   'url': 'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000101/q3pr.htm'},
        acc(160, MSFT_CIK): {'title': 'Microsoft and Contoso announce strategic cloud agreement',
                             'url': 'https://www.sec.gov/Archives/edgar/data/789019/000078901926000160/ex991.htm'},
    }
    collected = {cid: {'acquired_at': NOW - timedelta(minutes=20), 'rows': r} for cid, r in rows.items()}
    return sd.merge(None, collected, as_of=NOW - timedelta(minutes=10), exhibits=exhibits)


GDELT_ROWS = {
    'nvda': [
        ('Nvidia posts record quarterly revenue on AI demand', 'https://news.example.com/nvda-record', '2026-10-08T21:00:00'),
        ('Nvidia posts record quarterly revenue as AI demand surges', 'https://wire.example.org/nvda-revenue', '2026-10-09T02:00:00'),
        ('Nvidia posts record quarterly revenue on AI demand', 'https://copy.example.net/same-title', '2026-10-09T03:00:00'),
        ('Nvidia copy with tracking parameters', 'https://news.example.com/nvda-record?utm_source=feed#top', '2026-10-09T04:00:00'),
        ('Nvidia sued over chip patent in Delaware court', 'https://law.example.com/nvda-suit', '2026-10-10T09:15:00'),
        ('Nvidia posts record quarterly revenue on AI demand, again', 'https://late.example.com/nvda', '2026-10-11T22:00:00'),
        ('Nvidia old story outside the window', 'https://old.example.com/nvda', '2026-09-20T00:00:00'),
        ('Some unrelated headline', 'https://x.example.com/unrelated', '2026-10-10T00:00:00'),
        ('<b>Nvidia</b> markup title', 'https://x.example.com/markup', '2026-10-10T00:00:00'),
        ('Nvidia on an ftp link', 'ftp://x.example.com/file', '2026-10-10T00:00:00'),
    ],
    'googl': [('Google unveils new Pixel phone lineup', 'https://tech.example.com/pixel', '2026-10-10T15:00:00')],
    'amzn': [('Amazon rainforest deforestation hits record', 'https://env.example.com/amazon', '2026-10-10T15:00:00'),
             ('AWS launches new AI chips for Amazon cloud customers', 'https://tech.example.com/aws', '2026-10-10T16:00:00')],
    'rtx': [('Nvidia GeForce RTX 5090 review', 'https://games.example.com/rtx', '2026-10-10T15:00:00'),
            ('RTX wins Army missile contract', 'https://defense.example.com/rtx', '2026-10-10T15:30:00')],
    'intc': [('Intel officials warn of new threat', 'https://world.example.com/intel', '2026-10-10T15:00:00'),
             ('Intel to acquire AI chip startup', 'https://biz.example.com/intel', '2026-10-10T17:00:00')],
    'hanmi': [('Hanmi Semiconductor wins TC bonder order', 'https://kr.example.com/hanmi', '2026-10-10T01:00:00')],
}
IR_ROWS = {
    'nvda': [('NVIDIA Announces Financial Results for Third Quarter Fiscal 2027',
              'https://investor.nvidia.com/news/press-release-details/2026/q3/default.aspx', '2026-10-08T20:25:00'),
             ('NVIDIA unveils new robotics platform', 'https://nvidianews.nvidia.com/news/robotics', '2026-10-02T15:00:00'),
             ('Phishing copy on a foreign domain', 'https://nvidia.com.evil.example/x', '2026-10-05T15:00:00')],
    'msft': [('Microsoft and Contoso announce strategic cloud agreement',
              'https://news.microsoft.com/2026/10/09/contoso/', '2026-10-09T13:05:00'),
             ('Microsoft announces quarterly dividend', 'https://news.microsoft.com/2026/09/30/dividend/', '2026-09-30T20:00:00')],
}


def raw(rows):
    return [{'title': t, 'link': link, 'published_at': at(when)} for t, link, when in rows]


def collected():
    return {'GDELT': {cid: {'acquired_at': NOW - timedelta(minutes=5), 'rows': raw(r)} for cid, r in GDELT_ROWS.items()},
            'IR': {cid: {'acquired_at': NOW - timedelta(minutes=3), 'rows': raw(r)} for cid, r in IR_ROWS.items()}}


def payload(sec=True):
    counts = {}
    p = ns.merge(None, collected(), as_of=NOW, sec=sec_payload() if sec else None, counts=counts)
    return p, counts


# --- rules and tables -----------------------------------------------------------------------------

def test_tables_are_normalized_and_cover_target():
    assert set(ns.GDELT_COMPANIES) == set(US_LISTINGS) | {'tokyo_electron', 'hanmi'} and len(ns.GDELT_COMPANIES) == 19
    assert set(ns.IR_COMPANIES) == set(US_LISTINGS) and set(ns.IR_FEEDS) <= set(US_LISTINGS)
    assert len(ns.GDELT_COMPANIES) <= nf.GDELT_REQUEST_BUDGET and len(ns.IR_FEEDS) <= nf.IR_REQUEST_BUDGET
    assert nf.GDELT_MIN_INTERVAL >= 5
    for cid, rule in ns.MATCH.items():
        for phrase in rule['names'] + rule['exclude']:
            assert ' '.join(ns.tokens(phrase)) == phrase, (cid, phrase)
        assert all(re.fullmatch(r'[A-Za-z]{2,10}', s) for s in rule['symbols'])
        assert rule['names'] or rule['symbols']
        assert 'sourcelang' not in rule['query']
        assert nf.gdelt_url(cid).startswith('https://api.gdeltproject.org/api/v2/doc/doc?query=')
        assert 'mode=artlist&format=json&maxrecords=75&timespan=7d' in nf.gdelt_url(cid)
    for cid, feed in ns.IR_FEEDS.items():
        assert feed['status'] == 'UNVERIFIED_URL' and feed['url'].startswith('https://')
        host = feed['url'].split('/')[2]
        assert any(host == d or host.endswith('.' + d) for d in feed['domains']), cid


@pytest.mark.parametrize('cid,title,expected', [
    ('googl', 'Alphabet shares rise', True), ('googl', 'Google unveils Pixel', True), ('googl', 'GOOGL climbs', True),
    ('googl', 'alphabet soup recipe', False), ('googl', 'Googleplex tour', False),
    ('amd', 'AMD launches new GPU', True), ('amd', 'amd in lowercase is not a ticker', False),
    ('amd', 'AMD drug slows macular degeneration', False), ('amd', 'Advanced Micro Devices beats', True),
    ('amzn', 'Amazon rainforest fires spread', False), ('amzn', 'Amazon to hire 100,000', True), ('amzn', 'AWS outage', True),
    ('rtx', 'RTX wins Army contract', True), ('rtx', 'Nvidia RTX 5090 tested', False), ('rtx', 'Pratt & Whitney engine order', True),
    ('intc', 'Intel cuts jobs', True), ('intc', 'US intel officials say', False), ('intc', 'intel report on Russia', False),
    ('etn', 'Eaton Vance fund closes', False), ('etn', 'Eaton fire victims sue utility', False), ('etn', 'Eaton raises outlook', True),
    ('stry', 'Stryker brigade deploys', False), ('stry', 'Stryker recalls hip implant', True),
    ('rok', 'Rockwell Automation Q4 results', True), ('rok', 'ROK military drill', False),
    ('klac', 'KLA beats estimates', True), ('klac', 'kla in lowercase', False),
    ('hanmi', 'Hanmi Semiconductor order', True), ('hanmi', 'Hanmi Financial bank results', False),
    ('tokyo_electron', 'Tokyo Electron raises forecast', True), ('nvda', "NVIDIA's new chip", True),
])
def test_relevance_rule_v0(cid, title, expected):
    assert ns.relevant(cid, title) is expected


@pytest.mark.parametrize('title,expected', [
    ('Nvidia sued over patent', 'LEGAL'), ('EU antitrust probe into Google', 'LEGAL'),
    ('Microsoft to acquire gaming studio', 'MA'), ('Intel takes stake in startup', 'MA'),
    ('Broadcom quarterly revenue beats estimates', 'EARNINGS'), ('Qualcomm raises dividend', 'EARNINGS'),
    ('Google unveils Pixel', 'PRODUCT'), ('AWS launches chips', 'PRODUCT'),
    ('Microsoft CEO speaks at conference', 'OTHER'), ('Court blocks Amazon acquisition', 'LEGAL'),
])
def test_classification_v0(title, expected):
    assert ns.classify(title) == expected


@pytest.mark.parametrize('link,expected', [
    ('HTTPS://News.Example.COM/a/b?id=1&utm_source=x#frag', 'https://news.example.com/a/b?id=1'),
    ('http://example.com', 'http://example.com'), ('https://user:pw@example.com/', None), ('ftp://example.com/x', None),
    ('javascript:alert(1)', None), ('https://example.com/a b', None), ('https://exämple.com/', None),
    ('https://example.com:8443/x', 'https://example.com:8443/x'), ('https://localhost/x', None),
])
def test_canonical_link(link, expected):
    assert ns.canonical_link(link) == expected


# --- providers -------------------------------------------------------------------------------------

def gdelt_body(rows):
    return json.dumps({'articles': [{'url': link, 'url_mobile': '', 'title': title, 'seendate': at(when).strftime('%Y%m%dT%H%M%SZ'),
                                     'socialimage': 'https://img.example.com/x.jpg', 'domain': 'example.com',
                                     'language': 'English', 'sourcecountry': 'United States'}
                                    for title, link, when in rows]}).encode()


def rss_body(rows):
    items = ''.join(f'<item><title><![CDATA[{t}]]></title><link>{link}</link>'
                    f'<pubDate>{at(when).strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>'
                    f'<description>Body text that must never be stored</description></item>' for t, link, when in rows)
    return f'<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>x</title>{items}</channel></rss>'.encode()


def test_parse_gdelt_reads_title_link_time_only():
    rows = nf.parse_gdelt(gdelt_body([('A &amp; B Nvidia', 'https://e.example.com/x', '2026-10-10T01:02:03')]))
    assert rows == [{'title': 'A & B Nvidia', 'link': 'https://e.example.com/x', 'published_at': at('2026-10-10T01:02:03')}]
    assert nf.parse_gdelt(b'') == [] and nf.parse_gdelt(b'{}') == []
    for body, code in ((b'Please limit requests to one every 5 seconds', 'GDELT_RATE_LIMITED'),
                       (b'Your search contained a phrase that was too short', 'GDELT_RESPONSE_INVALID'),
                       (b'[1,2]', 'GDELT_RESPONSE_INVALID'), (b'\xff', 'GDELT_RESPONSE_INVALID'),
                       (b'{"articles":{}}', 'GDELT_RESPONSE_INVALID')):
        with pytest.raises(ValueError, match=code):
            nf.parse_gdelt(body)
    bad_date = json.loads(gdelt_body([('Nvidia', 'https://e.example.com/x', '2026-10-10T01:02:03')]))
    bad_date['articles'][0]['seendate'] = '2026-10-10'
    assert nf.parse_gdelt(json.dumps(bad_date).encode())[0]['published_at'] is None


def test_parse_feed_rss_atom_and_unsafe_xml():
    rows = nf.parse_feed(rss_body(IR_ROWS['msft']))
    assert [r['title'] for r in rows] == [t for t, _, _ in IR_ROWS['msft']]
    assert rows[0]['published_at'] == at('2026-10-09T13:05:00') and set(rows[0]) == {'title', 'link', 'published_at'}
    atom = (b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>x</title><entry><title>Atom release</title>'
            b'<link rel="enclosure" href="https://e.example.com/img.png"/><link href="https://ir.amd.com/news/1"/>'
            b'<updated>2026-10-10T12:00:00Z</updated><content>never stored</content></entry></feed>')
    assert nf.parse_feed(atom) == [{'title': 'Atom release', 'link': 'https://ir.amd.com/news/1', 'published_at': at('2026-10-10T12:00:00')}]
    for body in (b'<!DOCTYPE rss [<!ENTITY x "y">]><rss><channel><item><title>&x;</title></item></channel></rss>',
                 b'<?xml version="1.0"?><!doctype rss SYSTEM "http://e.example.com/x.dtd"><rss/>',
                 b'<rss><channel><item><title>&undefined;</title></item></channel></rss>',
                 b'<html><body>not a feed</body></html>', b'<rss>', b'x' * (nf.MAX_BODY_BYTES + 1), b'<rss version="2.0"/>'):
        with pytest.raises(ValueError, match='IR_FEED_INVALID'):
            nf.parse_feed(body)


class Clock:
    def __init__(self):
        self.t, self.sleeps = 0.0, []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.t += seconds

    def time(self):
        return self.t


class Transport:
    """URL -> NewsResponse; records calls (URL and headers)."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, url, *, headers, timeout, max_body_bytes):
        self.calls.append((url, dict(headers)))
        found = self.routes.get(url)
        if callable(found):
            found = found()
        if isinstance(found, Exception):
            raise found
        if found is None:
            return nf.NewsResponse(404, b'', url)
        status, body = found if isinstance(found, tuple) else (200, found)
        return nf.NewsResponse(status, body, url)


def client(transport, clock, *, interval=nf.GDELT_MIN_INTERVAL, budget=nf.GDELT_REQUEST_BUDGET):
    return nf.PacedClient(min_interval=interval, budget=budget, transport=transport, sleep=clock.sleep, monotonic=clock.time,
                          now=lambda: NOW)


def test_paced_client_interval_budget_retry_and_fixed_urls():
    urls = [nf.gdelt_url(c) for c in ('nvda', 'amd', 'msft')]
    clock = Clock()
    transport = Transport({urls[0]: b'{}', urls[1]: iter([(429, b''), (200, b'{}')]).__next__, urls[2]: (500, b'')})
    c = client(transport, clock)
    assert c.get(urls[0], accept='application/json') == (b'{}', NOW)
    assert c.get(urls[1], accept='application/json')[0] == b'{}'
    with pytest.raises(nf.NewsFetchError, match='HTTP_FAILED'):
        c.get(urls[2], accept='application/json')
    assert c.used == 5
    starts = []
    clock2 = Clock()

    def stamp(url, **kw):
        starts.append(clock2.t)
        return nf.NewsResponse(200, b'{}', url)
    c2 = client(stamp, clock2)
    for url in urls:
        c2.get(url, accept='application/json')
    assert all(b - a >= nf.GDELT_MIN_INTERVAL for a, b in zip(starts, starts[1:]))
    assert transport.calls[0][1]['User-Agent'] == nf.USER_AGENT
    with pytest.raises(nf.NewsFetchError, match='URL_NOT_ALLOWED'):
        c.get('https://example.com/', accept='x')
    small = client(Transport({urls[0]: b'{}'}), Clock(), budget=1)
    small.get(urls[0], accept='x')
    with pytest.raises(nf.NewsFetchError, match='BUDGET_EXHAUSTED'):
        small.get(urls[0], accept='x')
    moved = client(lambda url, **kw: nf.NewsResponse(200, b'{}', url + 'x'), Clock())
    with pytest.raises(nf.NewsFetchError, match='RESPONSE_INVALID'):
        moved.get(urls[0], accept='x')
    redirect = client(lambda url, **kw: (_ for _ in ()).throw(nf.NewsFetchError('REDIRECT_REJECTED')), Clock())
    with pytest.raises(nf.NewsFetchError, match='REDIRECT_REJECTED'):
        redirect.get(urls[0], accept='x')
    with pytest.raises(nf.NewsFetchError, match='URL_NOT_ALLOWED'):
        nf.default_transport('https://evil.example.com/', headers={}, timeout=5, max_body_bytes=10)


# --- public payload --------------------------------------------------------------------------------

def by_link(p):
    return {i['link']: i for i in p['items']}


def test_merge_relevance_dedupe_grouping_and_8k_relation():
    p, counts = payload()
    items = by_link(p)
    assert p['state'] == 'LIVE' and p['channel'] == 'NEWS' and p['score_effect'] == 'NONE'
    assert p['attribution']['GDELT']['url'] == 'https://www.gdeltproject.org/'
    assert all(set(i) == set(ns.ITEM_KEYS) for i in p['items'])
    record, repeat = items['https://news.example.com/nvda-record'], items['https://wire.example.org/nvda-revenue']
    assert record['occurrence'] == 'NEW' and repeat['occurrence'] == 'REPEAT' and repeat['group_id'] == record['group_id']
    assert record['group_id'] == 'news:nvda:20261008T210000Z:0' and record['classification'] == 'EARNINGS'
    # more than 72h after the group's first item: a new group even though the title is similar
    assert items['https://late.example.com/nvda']['occurrence'] == 'NEW'
    assert items['https://law.example.com/nvda-suit']['classification'] == 'LEGAL'
    assert 'https://copy.example.net/same-title' not in items and counts['duplicates'] == 2
    assert not any('utm_' in link or '#' in link for link in items)
    assert counts['irrelevant'] == 4 and counts['out_of_window'] == 1 and counts['invalid'] == 2 and counts['foreign_link'] == 1
    assert {i['company_id'] for i in p['items'] if i['source'] == 'GDELT'} == {'nvda', 'googl', 'amzn', 'rtx', 'intc', 'hanmi'}
    # IR: rule B (generic EX-99.1 title, RESULTS 8-K, EARNINGS release, within 24h) and rule A (similar titles)
    nv = items['https://investor.nvidia.com/news/press-release-details/2026/q3/default.aspx']
    assert (nv['relation'], nv['related_8k_accession'], nv['group_id'], nv['occurrence']) == (
        'RELATED_TO_8K', acc(101), 'nvda:' + acc(101), 'REPEAT')
    ms = items['https://news.microsoft.com/2026/10/09/contoso/']
    assert ms['relation'] == 'RELATED_TO_8K' and ms['related_8k_accession'] == acc(160, MSFT_CIK)
    dividend = items['https://news.microsoft.com/2026/09/30/dividend/']
    assert dividend['relation'] == 'NONE' and dividend['related_8k_accession'] is None and dividend['occurrence'] == 'NEW'
    assert p['sources']['IR']['nvda']['feed_status'] == 'UNVERIFIED_URL'
    assert p['sources']['IR']['googl'] == {'state': 'NOT_AVAILABLE', 'acquired_at': None, 'reason_code': 'NO_OFFICIAL_FEED_KNOWN',
                                           'feed_status': 'NOT_AVAILABLE'}
    assert p['sources']['GDELT']['asml'] == {'state': 'NOT_AVAILABLE', 'acquired_at': None, 'reason_code': 'NOT_COLLECTED'}
    body = ns.encode(p).decode()
    for forbidden in ('never be stored', 'socialimage', 'img.example.com', 'price', 'description'):
        assert forbidden not in body
    assert len(ns.encode(p)) < 20_000
    # without the SEC file the releases stay plain news (no relation guessed)
    q, _ = payload(sec=False)
    assert all(i['relation'] == 'NONE' for i in q['items'])


def test_related_8k_rules_need_time_window_and_single_generic_candidate():
    sec = sec_payload()
    item = {'company_id': 'nvda', 'source': 'IR', 'title': 'NVIDIA Announces Financial Results for Third Quarter Fiscal 2027',
            'link': 'https://investor.nvidia.com/x', 'published_at': '2026-10-09T21:00:00+00:00', 'classification': 'EARNINGS'}
    assert ns.related_8k(item, sec['events']) is None  # more than 24h later
    item['published_at'] = '2026-10-08T10:00:00+00:00'
    assert ns.related_8k(item, sec['events']) == (acc(101), 'nvda:' + acc(101))
    assert ns.related_8k(dict(item, classification='PRODUCT'), sec['events']) is None
    twin = copy.deepcopy(sec['events'][-1] if sec['events'][-1]['company_id'] == 'nvda' else sec['events'][0])
    twin.update(accession=acc(102), group_id='nvda:' + acc(102))
    assert ns.related_8k(item, sec['events'] + [twin]) is None  # ambiguous generic match
    assert ns.generic_exhibit_title('nvda', 'Press release issued by NVIDIA Corporation on October 8, 2026')
    assert not ns.generic_exhibit_title('msft', 'Microsoft and Contoso announce strategic cloud agreement')


def test_rolling_window_carry_forward_caps_and_preserve():
    p, _ = payload()
    later = NOW + timedelta(days=3)
    # GDELT nvda collected again (one new row), everything else not collected: carried with old acquisition times
    again = {'GDELT': {'nvda': {'acquired_at': later, 'rows': raw([('Nvidia opens new Taiwan office', 'https://n.example.com/tw',
                                                                    '2026-10-14T10:00:00')])}}}
    q = ns.merge(p, again, as_of=later)
    assert q['sources']['GDELT']['nvda']['state'] == 'LIVE' and q['sources']['GDELT']['googl']['state'] == 'STALE'
    assert q['state'] == 'LIVE' and 'https://n.example.com/tw' in by_link(q)
    assert by_link(q)['https://news.microsoft.com/2026/10/09/contoso/']['relation'] == 'RELATED_TO_8K'  # kept without SEC file
    cutoff = later - timedelta(days=ns.WINDOW_DAYS)
    assert len(q['items']) == sum(datetime.fromisoformat(i['published_at']) >= cutoff for i in p['items']) + 1
    assert 'https://news.microsoft.com/2026/09/30/dividend/' not in by_link(q)  # left the 14-day window
    # 14-day window
    r = ns.merge(q, {}, as_of=NOW + timedelta(days=20))
    assert all(datetime.fromisoformat(i['published_at']) >= NOW + timedelta(days=6) for i in r['items'])
    assert r['state'] == 'STALE' and r['reason_codes'] == ['STALE_INPUT']
    many = {'GDELT': {'nvda': {'acquired_at': NOW, 'rows': raw([(f'Nvidia topic {n} alpha{n} beta{n}', f'https://m.example.com/{n}',
                                                                 (NOW - timedelta(hours=n + 1)).replace(tzinfo=None).isoformat())
                                                                for n in range(60)])}}}
    capped = ns.merge(None, many, as_of=NOW)
    assert len(capped['items']) == ns.PER_COMPANY_MAX['GDELT']
    assert ns.merge(None, {}, as_of=NOW)['state'] == 'NOT_AVAILABLE'


def bad_payloads():
    def first(source):
        return lambda p: next(i for i in p['items'] if i['source'] == source)
    g, r = first('GDELT'), first('IR')
    related = lambda p: next(i for i in p['items'] if i['relation'] == 'RELATED_TO_8K')
    return [
        lambda p: g(p).update(body='article text'), lambda p: g(p).update(price=1), lambda p: p.update(score_effect='Q'),
        lambda p: p['items'].reverse(), lambda p: g(p).update(title='Unrelated headline'), lambda p: g(p).update(title='<b>Nvidia</b>'),
        lambda p: g(p).update(link='javascript:alert(1)'), lambda p: r(p).update(link='https://evil.example.com/x'),
        lambda p: g(p).update(classification='OTHER'), lambda p: g(p).update(occurrence='REPEAT'),
        lambda p: related(p).update(related_8k_accession=None), lambda p: g(p).update(relation='RELATED_TO_8K'),
        lambda p: g(p).update(published_at='2026-09-01T00:00:00+00:00'), lambda p: g(p).update(published_at='2026-10-11T23:59:00+00:00'),
        lambda p: p['attribution']['GDELT'].update(url='https://example.com/'), lambda p: p.update(channel='DISCLOSURE'),
        lambda p: p['sources']['IR']['googl'].update(feed_status='VERIFIED'), lambda p: p['sources']['GDELT'].pop('asml'),
        lambda p: p['sources']['GDELT']['nvda'].update(state='STALE'), lambda p: p['items'].append(dict(p['items'][0])),
        lambda p: p.update(state='STALE'), lambda p: p['items'][0].update(group_id='news:x'),
    ]


@pytest.mark.parametrize('mutate', bad_payloads())
def test_validator_fails_closed(mutate):
    p, _ = payload()
    mutate(p)
    with pytest.raises(ValueError, match='NEWS_SIGNALS_INVALID'):
        ns.require_news_signals(p)


def test_verified_feed_status_stays_valid():
    p, _ = payload()
    p['sources']['IR']['nvda']['feed_status'] = 'VERIFIED'
    ns.require_news_signals(p)


def test_guard_accepts_valid_and_rejects_invalid(tmp_path):
    guard = importlib.import_module('pages_artifact_guard')
    from build_pages_cockpit import build_public_cockpit
    site = tmp_path / 'site'
    build_public_cockpit(site)
    assert json.loads((site / ns.FILENAME).read_text())['state'] == 'NOT_AVAILABLE'
    assert ns.FILENAME in guard.ALLOWED_NAMES and 'news-signals.js' in guard.APPROVED_SHA256
    p, _ = payload()
    (site / ns.FILENAME).write_bytes(ns.encode(p))
    assert guard.scan_artifact(site)['pages_artifact_guard'] == 'PASS'
    p['items'][0]['price'] = 1
    (site / ns.FILENAME).write_bytes(ns.encode(p))
    receipt = guard.scan_artifact(site)
    assert receipt['violations'].get('sensitive_json_fields') and receipt['violations'].get('news_signals_boundary')


# --- tool -------------------------------------------------------------------------------------------

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


def routes(gdelt=None, ir=None):
    gdelt = GDELT_ROWS if gdelt is None else gdelt
    ir = IR_ROWS if ir is None else ir
    out = {nf.gdelt_url(cid): gdelt_body(gdelt.get(cid, [])) for cid in ns.GDELT_COMPANIES}
    out.update({ns.IR_FEEDS[cid]['url']: rss_body(ir.get(cid, [])) for cid in ns.IR_FEEDS})
    return out


def run_tool(tmp_path, capsys, *, previous=opener(), transport=None, live=True, preserve=False, sec=True):
    t = importlib.import_module('news_signals')
    if sec:
        (tmp_path / sd.FILENAME).write_bytes(sd.encode(sec_payload()))
    transport = transport or Transport(routes())
    clock = Clock()
    kwargs = {'transport': transport, 'sleep': clock.sleep, 'monotonic': clock.time, 'now': lambda: NOW}
    code = t.run(tmp_path, live=live, preserve_only=preserve, now=lambda: NOW, gdelt_kwargs=kwargs, ir_kwargs=kwargs,
                 open_previous=previous)
    return code, capsys.readouterr().out, transport, clock


def test_tool_live_writes_validated_file_and_prints_codes_only(tmp_path, capsys):
    code, out, transport, clock = run_tool(tmp_path, capsys)
    assert code == 0
    p = ns.require_news_signals(json.loads((tmp_path / ns.FILENAME).read_text()))
    assert p['state'] == 'LIVE' and sum(i['relation'] == 'RELATED_TO_8K' for i in p['items']) == 2
    assert 'NEWS_SIGNALS gdelt_companies=19 gdelt_collected=19 gdelt_requests=19 gdelt_budget=40 ir_feeds=10 ir_collected=10' in out
    assert 'sec_reference=AVAILABLE' in out and 'related_8k=2' in out
    gdelt_calls = [u for u, _ in transport.calls if u.startswith(nf.GDELT_API)]
    assert len(gdelt_calls) == 19 <= nf.GDELT_REQUEST_BUDGET
    assert min(clock.sleeps) > 0 and sum(s >= nf.GDELT_MIN_INTERVAL - 1e-9 for s in clock.sleeps) >= 18
    for secret in ('Nvidia', 'nvda', 'NVDA', 'example.com', 'gdeltproject', 'microsoft', 'record'):
        assert secret not in out


def test_tool_failures_never_block_and_previous_paths(tmp_path, capsys):
    # network failure reading the previous copy: nothing written, exit 0 (SEC deploy continues)
    code, out, _, _ = run_tool(tmp_path, capsys, previous=opener(exc=urllib.error.URLError('down')))
    assert code == 0 and 'PREVIOUS_FETCH_FAILED nothing_written' in out and not (tmp_path / ns.FILENAME).exists()
    # invalid previous copy: discarded, fresh collection proceeds
    code, out, _, _ = run_tool(tmp_path, capsys, previous=opener(200, b'{"kind":"NEWS_SIGNALS"}'))
    assert code == 0 and 'PREVIOUS_DISCARDED' in out
    previous = (tmp_path / ns.FILENAME).read_bytes()
    # GDELT rate limit: remaining GDELT companies are not requested and keep previous rows; IR still runs
    limited = routes()
    first = nf.gdelt_url(ns.GDELT_COMPANIES[1])
    limited[first] = b'Please limit requests to one every 5 seconds or contact us'
    transport = Transport(limited)
    code, out, transport, _ = run_tool(tmp_path, capsys, previous=opener(200, previous), transport=transport)
    assert code == 0 and 'NEWS_SIGNALS_FAILURE source=GDELT company_index=2 code=GDELT_RATE_LIMITED' in out
    assert 'company_index=3 code=NOT_RUN_GDELT_RATE_LIMITED' in out
    assert len([u for u, _ in transport.calls if u.startswith(nf.GDELT_API)]) == 2
    carried = ns.require_news_signals(json.loads((tmp_path / ns.FILENAME).read_text()))
    assert len(carried['items']) == len(json.loads(previous)['items'])
    # every source down, no previous copy: NOT_AVAILABLE file, exit 0
    (tmp_path / ns.FILENAME).unlink()
    dead = Transport({})
    code, out, _, _ = run_tool(tmp_path, capsys, transport=dead, sec=False)
    assert code == 0 and 'ALL_SOURCES_FAILED not_available' in out and 'code=HTTP_FAILED' in out
    assert json.loads((tmp_path / ns.FILENAME).read_text())['state'] == 'NOT_AVAILABLE'
    # preserve-only: no source requests, previous restated; 404 / failures keep the build copy
    quiet = Transport({})
    code, out, _, _ = run_tool(tmp_path, capsys, previous=opener(200, previous), transport=quiet, live=False, preserve=True)
    assert code == 0 and 'PREVIOUS_RESTORED items=' in out and quiet.calls == []
    for prev, text in ((opener(404), 'PREVIOUS_NOT_AVAILABLE'), (opener(exc=urllib.error.URLError('x')), 'PREVIOUS_FETCH_FAILED'),
                       (opener(200, b'[]'), 'PREVIOUS_DISCARDED')):
        code, out, _, _ = run_tool(tmp_path, capsys, previous=prev, transport=quiet, live=False, preserve=True)
        assert code == 0 and text in out
    code, out, _, _ = run_tool(tmp_path, capsys, live=False)
    assert code == 1 and 'LIVE_OPT_IN_REQUIRED' in out
    with pytest.raises(SystemExit):
        importlib.import_module('news_signals').main(['--out', str(tmp_path), '--bogus'])
    assert capsys.readouterr().out == 'NEWS_SIGNALS ARGUMENTS_INVALID\n'


def test_tool_drops_secret_like_rows(tmp_path, capsys):
    rows = dict(GDELT_ROWS, msft=[('Microsoft leak: password = "hunter2" found', 'https://s.example.com/x', '2026-10-10T10:00:00')])
    code, out, _, _ = run_tool(tmp_path, capsys, transport=Transport(routes(gdelt=rows)))
    assert code == 0 and 'rows_secret_like=1' in out
    assert 'hunter2' not in (tmp_path / ns.FILENAME).read_text()


def test_workflows_add_one_live_step_and_one_preserve_line():
    daily = (ROOT.parent / '.github/workflows/sec-daily-public-inputs.yml').read_text()
    pages = (ROOT.parent / '.github/workflows/cockpit-pages.yml').read_text()
    live = 'python implementation/tools/news_signals.py --live --out "$RUNNER_TEMP/public-cockpit"'
    assert daily.count(live) == 1 and daily.count('news_signals.py') == 1
    assert daily.index('sec_disclosures.py --live') < daily.index(live) < daily.index('actions/upload-pages-artifact')
    step = daily[daily.rindex('- name:', 0, daily.index(live)):daily.index(live) + 200]
    assert 'pages_artifact_guard.py' in step and 'secrets.' not in step
    assert pages.count('news_signals.py --preserve-only --out "$RUNNER_TEMP/public-cockpit"') == 1 and pages.count('news_signals.py') == 1
    assert pages.index('sec_disclosures.py --preserve-only') < pages.index('news_signals.py --preserve-only') < pages.index('actions/upload-pages-artifact')


# --- JS == Python ---------------------------------------------------------------------------------

def node(script, data):
    result = subprocess.run([NODE, '-e', script], input=json.dumps(data), capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout)


TITLES = [t for rows in list(GDELT_ROWS.values()) + list(IR_ROWS.values()) for t, _, _ in rows] + [
    'Alphabet shares rise', 'alphabet soup recipe', 'AMD drug slows macular degeneration', 'US intel officials say',
    'Pratt & Whitney engine order', 'KLA beats estimates', 'kla in lowercase', 'Ünïcödé Nvidia ÄRGER', 'İntel', 'Nvidia’s RTX',
    'EU antitrust probe into Google', 'Court blocks Amazon acquisition', 'a b', ' padded', 'two  spaces', 'x' * 201]


@pytest.mark.skipif(NODE is None, reason='node not installed')
def test_js_reader_matches_python_vectors():
    p, _ = payload()
    cases = {'valid': p, 'empty': ns.merge(None, {}, as_of=NOW)}
    for i, mutate in enumerate(bad_payloads()):
        bad = copy.deepcopy(p)
        mutate(bad)
        cases[f'bad{i}'] = bad
    links = ['https://news.example.com/a?id=1', 'http://example.com', 'https://example.com:8443/x', 'https://localhost/x',
             'https://Example.com/x', 'https://example.com/a b', 'https://example.com/#x', 'javascript:alert(1)',
             'https://investor.nvidia.com/x', 'https://nvidia.com.evil.example/x', 'http://investor.nvidia.com/x']
    script = ("const api=require(%s);let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{const c=JSON.parse(s),out={};"
              "for(const[k,v]of Object.entries(c.cases)){try{api.validate(v);out[k]=true;}catch(_){out[k]=false;}}"
              "out.tokens=c.titles.map(api.tokens);out.classify=c.titles.map(api.classify);out.validTitle=c.titles.map(api.validTitle);"
              "out.relevant=c.titles.map(t=>Object.keys(api.MATCH).filter(id=>api.relevant(id,t)));"
              "out.similar=c.titles.map(a=>c.titles.map(b=>api.similar(api.significant(a),api.significant(b))));"
              "out.hosts=c.links.map(api.linkHost);out.ir=c.links.map(l=>api.irLinkAllowed('nvda',l));"
              "out.groups=api.groups(c.cases.valid.items);out.match=api.MATCH;out.domains=api.IR_DOMAINS;out.rules=api.CLASS_RULES;"
              "out.stop=[...api.STOPWORDS].sort();out.attribution=api.ATTRIBUTION;out.gdelt=api.GDELT_COMPANIES;out.irc=api.IR_COMPANIES;"
              "process.stdout.write(JSON.stringify(out));});") % json.dumps(str(JS))
    out = node(script, {'cases': cases, 'titles': TITLES, 'links': links})
    assert out.pop('validTitle') == [ns.valid_title(t) for t in TITLES]
    assert out.pop('tokens') == [ns.tokens(t) for t in TITLES]
    assert out.pop('classify') == [ns.classify(t) for t in TITLES]
    assert out.pop('relevant') == [[cid for cid in sorted(ns.MATCH) if ns.relevant(cid, t)] for t in TITLES]
    assert out.pop('similar') == [[ns.similar(ns.significant(a), ns.significant(b)) for b in TITLES] for a in TITLES]
    assert out.pop('hosts') == [list(ns.link_host(l)) if ns.link_host(l) else None for l in links]
    assert out.pop('ir') == [ns.ir_link_allowed('nvda', l) for l in links]
    assert out.pop('groups') == [{'group_id': i['group_id'], 'occurrence': i['occurrence']} for i in p['items']]
    assert out.pop('match') == {cid: [list(r['names']), list(r['symbols']), list(r['exclude'])] for cid, r in ns.MATCH.items()}
    assert out.pop('domains') == {cid: list(f['domains']) for cid, f in ns.IR_FEEDS.items()}
    assert out.pop('rules') == [[name, list(phrases)] for name, phrases in ns.CLASS_RULES]
    assert out.pop('stop') == sorted(ns.STOPWORDS) and out.pop('attribution') == ns.ATTRIBUTION
    assert out.pop('gdelt') == list(ns.GDELT_COMPANIES) and out.pop('irc') == list(ns.IR_COMPANIES)
    assert out.pop('valid') is True
    assert out.pop('empty') is True
    assert all(v is False for v in out.values()), out


@pytest.mark.skipif(NODE is None, reason='node not installed')
def test_js_timeline_nests_related_ir_under_8k_and_collapses_repeats():
    p, _ = payload()
    sec = sec_payload()
    script = ("const api=require(%s);let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{const c=JSON.parse(s);"
              "const rows=api.timeline({sec:c.sec,news:c.news});process.stdout.write(JSON.stringify(rows.map(r=>[r.channel,r.source,r.time,"
              "r.channel==='NEWS'?r.item.link:r.event.accession,(r.related||[]).map(i=>i.link),(r.repeats||[]).map(i=>i.link)])));});") % json.dumps(str(JS))
    rows = node(script, {'sec': sec, 'news': p})
    times = [r[2] for r in rows]
    assert times == sorted(times, reverse=True)
    sec_rows = {r[3]: r for r in rows if r[0] == 'DISCLOSURE'}
    assert sec_rows[acc(101)][4] == ['https://investor.nvidia.com/news/press-release-details/2026/q3/default.aspx']
    assert sec_rows[acc(160, MSFT_CIK)][4] == ['https://news.microsoft.com/2026/10/09/contoso/']
    news = {r[3]: r for r in rows if r[0] == 'NEWS'}
    assert news['https://news.example.com/nvda-record'][5] == ['https://wire.example.org/nvda-revenue']
    assert 'https://wire.example.org/nvda-revenue' not in news
    assert all(r[3] not in news for r in [('', '', '', link) for link in sec_rows[acc(101)][4]])
