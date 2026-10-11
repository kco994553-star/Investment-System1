"""SIC industry group v0, theme v0 membership, concentration reference, SEC parsers/collector and public sidecar.

Synthetic SEC-shaped fixtures only (sec.gov is not reachable here); live collection runs in Actions.
"""
from datetime import datetime, timedelta, timezone
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))

from investment_system.qgv import sic_industry, theme_membership
from investment_system.qgv.theme_exposure import summarize_theme_exposure
from investment_system.providers import sec_classification_inputs as parse
from investment_system.providers.sec_collection import SecCollectionError, SecResponse
from investment_system.providers.sec_classification_collection import (ClassificationSecClient, URLS, collect_company_inputs,
                                                                    collect_etf_inputs)
from investment_system.product.public_classification import (FILENAME, build_classification, company_identity,
                                                             require_public_classification, unavailable_classification)

QGV = ROOT / 'src/investment_system/qgv'
VECTORS = json.loads((ROOT / 'tests/fixtures/theme_concentration_v0_vectors.json').read_text())
NOW = datetime(2026, 10, 11, 23, 0, tzinfo=timezone.utc)
TTL = timedelta(hours=24)
UA = 'Investment System test contact@example.com'


def nport_xml(series, report='2026-08-31', kind='NPORT-P', rows=()):
    items = ''.join(
        f'<invstOrSec><name>X</name><lei>N/A</lei><title>X</title><cusip>{c}</cusip>'
        + (f'<identifiers><isin value="{i}"/></identifiers>' if i else '<identifiers><other otherDesc="x" value="1"/></identifiers>')
        + f'<balance>123</balance><units>NS</units><curCd>USD</curCd><valUSD>4567.5</valUSD><pctVal>3.21</pctVal>'
        f'<payoffProfile>{p}</payoffProfile><assetCat>{a}</assetCat><issuerCat>CORP</issuerCat><invCountry>US</invCountry></invstOrSec>'
        for c, i, a, p in rows)
    return (f'<?xml version="1.0" encoding="UTF-8"?><edgarSubmission xmlns="http://www.sec.gov/edgar/nport">'
            f'<headerData><submissionType>{kind}</submissionType><filerInfo><seriesClassInfo><seriesId>{series}</seriesId>'
            f'<classId>C000000001</classId></seriesClassInfo></filerInfo></headerData><formData><genInfo><regName>Trust</regName>'
            f'<seriesName>Fund</seriesName><seriesId>{series}</seriesId><repPdEnd>2026-12-31</repPdEnd><repPdDate>{report}</repPdDate>'
            f'</genInfo><invstOrSecs>{items}</invstOrSecs></formData></edgarSubmission>').encode()


def atom(entries):
    body = ''.join(f'<entry><category label="form type" scheme="https://www.sec.gov/" term="{t}"/><content type="text/xml">'
                   f'<accession-number>{a}</accession-number><filing-date>{d}</filing-date><filing-type>{t}</filing-type>'
                   f'</content><title>{t}</title></entry>' for a, d, t in entries)
    return f'<?xml version="1.0" encoding="ISO-8859-1" ?><feed xmlns="http://www.w3.org/2005/Atom"><title>x</title>{body}</feed>'.encode()


def submissions(cik, sic='3674', forms=(('10-K', '0001045810-26-000010', '2026-02-20', '2026-01-25', 'nvda-20260125.htm'),)):
    cols = {'form': [], 'accessionNumber': [], 'filingDate': [], 'reportDate': [], 'primaryDocument': []}
    for f, a, d, r, p in forms:
        for k, v in zip(cols, (f, a, d, r, p)):
            cols[k].append(v)
    return json.dumps({'cik': cik, 'name': 'X', 'sic': sic, 'sicDescription': 'x', 'filings': {'recent': cols, 'files': []}}).encode()


BUSINESS = ('We design accelerated computing platforms. Our semiconductor products include GPUs used for artificial intelligence '
            'and machine learning workloads in every data center. ' * 8)
TEN_K = (('<html><head><title>10-K</title><style>.x{}</style></head><body><div style="display:none"><ix:header>artificial intelligence '
          'hidden</ix:header></div><p>TABLE OF CONTENTS</p><p>Item 1. Business 4</p><p>Item 1A. Risk Factors 12</p>'
          '<p>Item 2. Properties 30</p><h2>PART I</h2><p>Item&#160;1. Business</p><p>' + BUSINESS + '</p>'
          '<p>Item 1A. Risk Factors</p><p>Cybersecurity and cloud computing risks could harm us.</p>'
          '<p>Item 2. Properties</p><p>Offices.</p></body></html>').encode())


class SicIndustryV0(unittest.TestCase):
    def test_config_is_the_adopted_draft_table(self):
        cfg = sic_industry.load_sic_config()
        self.assertEqual((cfg['config_version'], cfg['status'], cfg['decided_at']), ('sic_industry_groups/v0', 'V0_UNCALIBRATED_DEFAULT', '2026-10-11'))
        self.assertEqual([tuple(g['sic_ranges'][0]) for g in cfg['groups']],
                         [(1000, 1499), (1500, 1799), (2000, 2199), (2200, 3999), (4000, 4799), (4800, 4899), (4900, 4999),
                          (5000, 5999), (6000, 6799), (7000, 8999)])
        # Only the table's explicit candidate words survive; everything else stays None.
        self.assertEqual({g['id']: g['cyclical_defensive_candidate'] for g in cfg['groups'] if g['cyclical_defensive_candidate']},
                         {'resources_mining': 'CYCLICAL_CANDIDATE', 'construction': 'CYCLICAL_CANDIDATE',
                          'food_tobacco': 'DEFENSIVE_CANDIDATE', 'utilities': 'DEFENSIVE_CANDIDATE'})
        self.assertEqual(sic_industry.validate_sic_config(cfg), [])

    def test_classify(self):
        cfg = sic_industry.load_sic_config()
        c = lambda v: sic_industry.classify_sic(v, cfg)
        self.assertEqual(c('3674'), {'sic': '3674', 'group': 'manufacturing_industrial_tech', 'subgroup': 'semiconductors',
                                     'cyclical_defensive_candidate': None, 'reason_code': None})
        self.assertEqual(c('7372')['subgroup'], 'software')
        self.assertEqual(c(3841)['subgroup'], 'medical_devices')
        self.assertEqual((c('3825')['group'], c('3825')['subgroup']), ('manufacturing_industrial_tech', None))
        self.assertEqual(c('1311')['cyclical_defensive_candidate'], 'CYCLICAL_CANDIDATE')
        self.assertEqual(c('4911')['cyclical_defensive_candidate'], 'DEFENSIVE_CANDIDATE')
        self.assertEqual((c('5411')['group'], c('5411')['subgroup']), ('wholesale_retail', 'food_retail'))
        for missing in (None, '', '0000', '0', 0, 'abc', '12345', True):
            self.assertEqual(c(missing)['reason_code'], 'SIC_NOT_AVAILABLE', missing)
            self.assertIsNone(c(missing)['group'])
        for unmatched in ('0100', '9995', '9721', '6800'):
            r = c(unmatched)
            self.assertEqual((r['reason_code'], r['group'], r['sic']), ('SIC_UNMATCHED', None, unmatched))

    def test_validation_rejects_overlaps_and_foreign_subgroups(self):
        cfg = sic_industry.load_sic_config()
        bad = copy.deepcopy(cfg); bad['groups'][1]['sic_ranges'] = [[1400, 1799]]
        self.assertIn('SIC_GROUP_OVERLAP', sic_industry.validate_sic_config(bad))
        bad = copy.deepcopy(cfg); bad['subgroups'][0]['group'] = 'utilities'
        self.assertIn('SIC_SUBGROUP_OUTSIDE_GROUP', sic_industry.validate_sic_config(bad))
        bad = copy.deepcopy(cfg); bad['gics_used'] = True
        self.assertIn('SIC_CONFIG_STATUS_INVALID', sic_industry.validate_sic_config(bad))


class ThemeConfigV0(unittest.TestCase):
    def test_decisions_applied_and_history_kept(self):
        cfg = theme_membership.load_theme_config_v0()
        self.assertEqual((cfg['config_version'], cfg['status'], cfg['decided_at']), ('theme_config/v0', 'V0_UNCALIBRATED_DEFAULT', '2026-10-11'))
        themes = {t['id']: t for t in cfg['themes']}
        self.assertEqual(len(themes), 14)
        self.assertEqual([e['ticker'] for e in themes['power_infrastructure']['etfs']], ['GRID'])
        self.assertEqual({t for t, v in themes.items() if v['evidence_strength'] == 'WEAK'}, {'consumer_brands'})
        self.assertNotIn('PAVE', theme_membership.basket_tickers(cfg))
        self.assertEqual(cfg['concentration_warning']['single_theme_max_share'], 0.4)
        v1 = json.loads((QGV / 'theme_config_v1.json').read_text())
        self.assertEqual((v1['config_version'], v1['status'], v1['membership_rule']), ('theme_config/1', 'PROPOSED_PENDING_APPROVAL', None))
        self.assertIn('PAVE', [e['ticker'] for t in v1['themes'] for e in t['etfs']])
        self.assertEqual([t['keywords'] for t in v1['themes']], [t['keywords'] for t in cfg['themes']])
        # GSQ-017 official type config is untouched: still no industry groups and theme rule unresolved.
        tc = json.loads((QGV / 'type_config_v1.json').read_text())
        self.assertEqual((tc['industry']['groups'], tc['industry']['mapping_status']), ([], 'PROPOSED_PENDING_APPROVAL'))

    def test_literal_phrase_rule_is_shared_with_theme_exposure(self):
        v1 = json.loads((QGV / 'theme_config_v1.json').read_text())
        text = 'Generative AI and machine-learning; MACHINE LEARNING; wafer-level. ai alone.'
        old = summarize_theme_exposure(config=v1, etf_evidence={}, item1_text=text)['themes']['ai']['keyword_counts']
        self.assertEqual(old, {'artificial intelligence': 0, 'generative ai': 1, 'machine learning': 1})


class Membership(unittest.TestCase):
    def setUp(self):
        self.cfg = theme_membership.load_theme_config_v0()
        self.tickers = theme_membership.basket_tickers(self.cfg)
        self.nvda = frozenset({'ISIN:US67066G1040', 'CUSIP:67066G104'})

    def run_(self, etfs, company=None, state='NOT_AVAILABLE', text=None):
        return theme_membership.theme_memberships(self.cfg, etf_securities=etfs, company_securities=company if company is not None else self.nvda,
                                                  keyword_state=state, item1_text=text)

    def test_etf_or_keyword_with_evidence_kinds(self):
        etfs = {t: frozenset() for t in self.tickers}
        etfs['SMH'] = frozenset({'CUSIP:67066G104'})
        etfs['AIQ'] = frozenset({'ISIN:US67066G1040'})
        out = self.run_(etfs, state='AVAILABLE', text='We sell semiconductor products for artificial intelligence.')
        self.assertEqual(out['semiconductors'], {'member': True, 'evidence': ['ETF', 'KEYWORD'], 'etfs': ['SMH']})
        self.assertEqual(out['ai'], {'member': True, 'evidence': ['ETF', 'KEYWORD'], 'etfs': ['AIQ']})
        self.assertEqual(out['cybersecurity'], {'member': False, 'evidence': [], 'etfs': []})

    def test_negative_needs_complete_evidence(self):
        etfs = {t: frozenset() for t in self.tickers}
        etfs['HACK'] = None
        out = self.run_(etfs, state='AVAILABLE', text='Nothing relevant here.')
        self.assertIsNone(out['cybersecurity']['member'])
        self.assertIs(out['ai']['member'], False)
        self.assertTrue(all(m['member'] is None for m in self.run_({t: frozenset() for t in self.tickers}).values()))
        # Foreign filer without any 10-K: the keyword clause is definitively negative.
        out = self.run_({t: frozenset() for t in self.tickers}, state='TEN_K_NOT_FILED')
        self.assertTrue(all(m['member'] is False for m in out.values()))

    def test_without_exact_identifier_only_keywords_count(self):
        etfs = {t: frozenset({'CUSIP:67066G104'}) for t in self.tickers}
        out = theme_membership.theme_memberships(self.cfg, etf_securities=etfs, company_securities=None, keyword_state='AVAILABLE',
                                                 item1_text='robotics')
        self.assertEqual(out['robotics_automation'], {'member': True, 'evidence': ['KEYWORD'], 'etfs': []})
        self.assertIsNone(out['ai']['member'])

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.run_({}, state='AVAILABLE', text=None)
        with self.assertRaises(ValueError):
            self.run_({'SMH': {'CUSIP:1'}})


class Concentration(unittest.TestCase):
    def test_shared_vectors(self):
        for case in VECTORS['cases']:
            got = theme_membership.theme_concentration(rows=case['rows'], memberships=case['memberships'], theme_ids=case['theme_ids'],
                                                       threshold=VECTORS['threshold'])
            self.assertEqual(got['warnings'], case['expected']['warnings'], case['name'])
            for g, e in zip(got['themes'], case['expected']['themes'], strict=True):
                self.assertEqual((g['id'], g['status']), (e['id'], e['status']), case['name'])
                self.assertAlmostEqual(g['exposure'], e['exposure'], places=12)
                self.assertAlmostEqual(g['unknown'], e['unknown'], places=12)
        for case in VECTORS['status_cases']:
            self.assertEqual(theme_membership.concentration_status(case['exposure'], case['unknown'], VECTORS['threshold']), case['status'])

    def test_threshold_matches_config_and_js(self):
        cfg = theme_membership.load_theme_config_v0()
        self.assertEqual(VECTORS['threshold'], cfg['concentration_warning']['single_theme_max_share'])
        js = (ROOT / 'src/investment_system/product/web_assets/classification-screens.js').read_text()
        self.assertIn('THRESHOLD=0.4,', js)


class Parsers(unittest.TestCase):
    def test_submissions_profile_picks_latest_original_10k(self):
        body = submissions('0001045810', forms=(('10-K', '0001045810-25-000010', '2025-02-26', '2025-01-26', 'old.htm'),
                                                ('10-K/A', '0001045810-26-000099', '2026-05-01', '2026-01-25', 'amend.htm'),
                                                ('10-Q', '0001045810-26-000050', '2026-08-27', '2026-07-27', 'q.htm'),
                                                ('10-K', '0001045810-26-000010', '2026-02-20', '2026-01-25', 'nvda-20260125.htm')))
        p = parse.submissions_profile(body, '0001045810')
        self.assertEqual(p['sic'], '3674')
        self.assertEqual(p['latest_10k'], {'accession': '0001045810-26-000010', 'filing_date': '2026-02-20', 'report_date': '2026-01-25',
                                           'primary_document': 'nvda-20260125.htm'})
        self.assertIsNone(parse.submissions_profile(submissions('0000937966', forms=(('20-F', '0000937966-26-000001', '2026-02-10', '2025-12-31', 'a.htm'),)), '0000937966')['latest_10k'])
        with self.assertRaises(parse.EvidenceError):
            parse.submissions_profile(body, '0000000001')

    def test_item1_skips_table_of_contents_and_risk_factors(self):
        text = parse.extract_item1(TEN_K)
        self.assertTrue(text.startswith('We design accelerated computing'))
        self.assertNotIn('Cybersecurity', text)
        self.assertNotIn('hidden', text)
        self.assertIsNone(parse.extract_item1(b'<p>Item 1. Business</p><p>short</p><p>Item 1A. Risk Factors</p>'))

    def test_etf_series_binding_is_exact_and_unique(self):
        body = json.dumps({'fields': ['cik', 'seriesId', 'classId', 'symbol'], 'data': [
            [1100663, 'S000004354', 'C000012067', 'SOXX'], [1100663, 'S000004354', 'C000099999', 'SOXX'],
            [1137360, 'S000022722', 'C000065000', 'SMH'], [1137360, 'S000099998', 'C000065001', 'SMH'],
            [1000001, 'bad', 'C1', 'AIQ']]}).encode()
        self.assertEqual(parse.bind_etf_series(body, ['SOXX', 'SMH', 'AIQ', 'GRID']),
                         {'SOXX': {'cik': '0001100663', 'series_id': 'S000004354'}, 'SMH': None, 'AIQ': None, 'GRID': None})

    def test_series_filings_and_nport_identifiers(self):
        self.assertEqual(parse.series_filings(atom([('0001752724-26-000001', '2026-05-28', 'NPORT-P'),
                                                    ('0001752724-26-000002', '2026-08-27', 'NPORT-P'),
                                                    ('0001752724-26-000003', '2026-09-01', 'NPORT-P/A')])),
                         [{'accession': '0001752724-26-000002', 'filing_date': '2026-08-27'},
                          {'accession': '0001752724-26-000001', 'filing_date': '2026-05-28'}])
        body = nport_xml('S000004354', rows=[('67066G104', 'US67066G1040', 'EC', 'Long'), ('007903107', None, 'EC', 'Long'),
                                             ('594918104', 'US5949181045', 'EC', 'Short'), ('458140100', 'US4581401001', 'DBT', 'Long'),
                                             ('000000000', 'IE00B8KQN827', 'EC', 'Long')])
        r = parse.nport_securities(body, 'S000004354')
        self.assertEqual(r['report_date'], '2026-08-31')
        self.assertEqual(r['securities'], frozenset({'CUSIP:67066G104', 'ISIN:US67066G1040', 'CUSIP:007903107', 'ISIN:IE00B8KQN827'}))
        for bad, code in ((nport_xml('S000000001'), 'NPORT_SERIES_MISMATCH'), (nport_xml('S000004354', kind='NPORT-P/A'), 'NPORT_NOT_ORIGINAL'),
                          (b'<!DOCTYPE x [<!ENTITY a "b">]><x/>', 'XML_INVALID')):
            with self.assertRaises(parse.EvidenceError) as ctx:
                parse.nport_securities(bad, 'S000004354')
            self.assertEqual(ctx.exception.args[0], code)


class FakeSec:
    """Transport stub keyed by exact URL; records requests. Unknown URLs answer 404."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, url, *, headers, timeout, max_body_bytes):
        self.calls.append(url)
        body = self.routes.get(url)
        return SecResponse(200, body, None, url) if body is not None else SecResponse(404, b'', None, url)


def client(routes, now=NOW):
    fake = FakeSec(routes)
    return ClassificationSecClient(UA, transport=fake, sleep=lambda s: None, monotonic=iter(range(10 ** 6)).__next__,
                                   now=lambda: now - timedelta(minutes=5)), fake


def live_routes():
    cfg = theme_membership.load_theme_config_v0()
    tickers = theme_membership.basket_tickers(cfg)
    data, routes = [], {}
    for n, t in enumerate(tickers):
        series = 'S%09d' % (n + 1)
        data.append([2000000 + n, series, 'C%09d' % (n + 1), t])
        accession = '0009999999-26-%06d' % (n + 1)
        routes[URLS['SERIES_FILINGS'].format(series=series)] = atom([(accession, '2026-08-27', 'NPORT-P')])
        held = [('67066G104', 'US67066G1040', 'EC', 'Long')] if t in ('SMH', 'SOXX', 'AIQ') else [('594918104', 'US5949181045', 'EC', 'Long')]
        routes[URLS['NPORT'].format(cik=2000000 + n, accession=accession.replace('-', ''))] = nport_xml(series, rows=held)
    routes[URLS['MF_TICKERS']] = json.dumps({'fields': ['cik', 'seriesId', 'classId', 'symbol'], 'data': data}).encode()
    for cid, row in company_identity().items():
        if not row['cik']:
            continue
        if cid == 'asml':
            routes[URLS['SUBMISSIONS'].format(cik=row['cik'])] = submissions(row['cik'], sic='3559', forms=(('20-F', row['cik'] + '-26-000001', '2026-02-10', '2025-12-31', 'a.htm'),))
            continue
        if cid == 'amd':  # 10-K document missing -> keyword evidence NOT_AVAILABLE
            routes[URLS['SUBMISSIONS'].format(cik=row['cik'])] = submissions(row['cik'], sic='3674', forms=(('10-K', '0000002488-26-000001', '2026-02-01', '2025-12-31', 'amd.htm'),))
            continue
        accession = row['cik'] + '-26-000010'
        routes[URLS['SUBMISSIONS'].format(cik=row['cik'])] = submissions(row['cik'], sic='0000' if cid == 'gev' else '3674' if cid == 'nvda' else '7372',
                                                                         forms=(('10-K', accession, '2026-02-20', '2026-01-25', cid + '.htm'),))
        routes[URLS['TEN_K'].format(cik=int(row['cik']), accession=accession.replace('-', ''), document=cid + '.htm')] = TEN_K if cid == 'nvda' else (
            '<p>Item 1. Business</p><p>' + 'We sell consumer software subscriptions. ' * 30 + '</p><p>Item 1A. Risk Factors</p>').encode()
    return routes


class CollectionAndPublic(unittest.TestCase):
    def collect(self, routes):
        c, fake = client(routes)
        identity = company_identity()
        cfg = theme_membership.load_theme_config_v0()
        etfs, mf = collect_etf_inputs(c, theme_membership.basket_tickers(cfg))
        companies = collect_company_inputs(c, {cid: r['cik'] for cid, r in identity.items() if r['cik']})
        return build_classification(as_of=NOW, stale_after=TTL, companies_input=companies, etfs_input=etfs, mf_source=mf, identity=identity), fake

    def test_live_like_flow(self):
        self.live_like_flow()

    def live_like_flow(self):
        payload, fake = self.collect(live_routes())
        self.assertEqual(payload['state'], 'LIVE')
        self.assertTrue(all(u.startswith(('https://www.sec.gov/', 'https://data.sec.gov/')) for u in fake.calls))
        rows = payload['data']['companies']
        nvda = rows['nvda']
        self.assertEqual((nvda['industry']['group'], nvda['industry']['subgroup'], nvda['industry']['sic']), ('manufacturing_industrial_tech', 'semiconductors', '3674'))
        self.assertEqual(nvda['themes']['memberships']['semiconductors'], {'member': True, 'evidence': ['ETF', 'KEYWORD'], 'etfs': ['SOXX', 'SMH']})
        self.assertEqual(nvda['themes']['memberships']['ai'], {'member': True, 'evidence': ['ETF', 'KEYWORD'], 'etfs': ['AIQ']})
        self.assertIs(nvda['themes']['memberships']['cybersecurity']['member'], False)  # only in Item 1A, which is excluded
        msft = rows['msft']['themes']['memberships']
        self.assertEqual(msft['cloud_software'], {'member': True, 'evidence': ['ETF'], 'etfs': ['SKYY', 'CLOU']})
        self.assertEqual(msft['ai']['member'], False)
        # 20-F filer: no 10-K is a definitive negative keyword clause; 3559 is a manufacturing SIC.
        self.assertEqual(rows['asml']['themes']['keyword_evidence'], {'state': 'TEN_K_NOT_FILED', 'reason_code': 'TEN_K_NOT_FILED', 'report_date': None})
        self.assertEqual(rows['asml']['themes']['memberships']['semiconductors']['member'], False)
        # 10-K fetch failed: positives still allowed, negatives become NOT_AVAILABLE.
        amd = rows['amd']['themes']
        self.assertEqual(amd['keyword_evidence']['state'], 'NOT_AVAILABLE')
        self.assertTrue(all(m['member'] is None for m in amd['memberships'].values()))
        self.assertEqual((rows['gev']['industry']['state'], rows['gev']['industry']['reason_code']), ('NOT_AVAILABLE', 'SIC_NOT_AVAILABLE'))
        for cid in ('tokyo_electron', 'hanmi'):
            self.assertEqual(rows[cid]['industry']['reason_code'], 'NOT_SEC_REGISTRANT')
            self.assertEqual((rows[cid]['themes']['state'], rows[cid]['themes']['etf_join']), ('NOT_AVAILABLE', 'NOT_AVAILABLE'))
        self.assertIn('PARTIAL_INPUT', payload['reason_codes'])
        self.assertEqual(payload['data']['etfs']['GRID']['report_date'], '2026-08-31')
        text = json.dumps(payload)
        for forbidden in ('valUSD', 'pctVal', 'balance', '4567', '3.21', 'accelerated computing', 'weight', 'price', 'quantity', 'PAVE'):
            self.assertNotIn(forbidden, text)
        return payload

    def test_etf_failures_are_reason_codes(self):
        routes = live_routes()
        cfg = theme_membership.load_theme_config_v0()
        series = {t: 'S%09d' % (n + 1) for n, t in enumerate(theme_membership.basket_tickers(cfg))}
        del routes[URLS['SERIES_FILINGS'].format(series=series['GRID'])]
        routes[URLS['SERIES_FILINGS'].format(series=series['AIQ'])] = atom([])
        mf = json.loads(routes[URLS['MF_TICKERS']])
        mf['data'] = [r for r in mf['data'] if r[3] != 'IHI']
        routes[URLS['MF_TICKERS']] = json.dumps(mf).encode()
        payload, _ = self.collect(routes)
        etfs = payload['data']['etfs']
        self.assertEqual((etfs['GRID']['reason_code'], etfs['AIQ']['reason_code'], etfs['IHI']['reason_code']),
                         ('NPORT_FILING_LIST_NOT_AVAILABLE', 'NPORT_NOT_FOUND', 'ETF_SERIES_UNBOUND'))
        nvda = payload['data']['companies']['nvda']['themes']['memberships']
        self.assertEqual(nvda['ai'], {'member': True, 'evidence': ['KEYWORD'], 'etfs': []})
        self.assertIsNone(nvda['power_infrastructure']['member'])
        routes[URLS['MF_TICKERS']] = b'not json'
        payload, _ = self.collect(routes)
        self.assertEqual({e['reason_code'] for e in payload['data']['etfs'].values()}, {'ETF_SERIES_BINDING_NOT_AVAILABLE'})

    def test_client_url_allowlist(self):
        c, _ = client({})
        for kind, url in (('NPORT', 'https://www.sec.gov/Archives/edgar/data/1/000000000000000001/../x.xml'), ('TEN_K', 'https://example.com/x.htm'),
                          ('SERIES_FILINGS', 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001100663&type=NPORT-P&dateb=&owner=include&count=10&output=atom')):
            with self.assertRaises(SecCollectionError) as ctx:
                c.fetch(kind, url)
            self.assertEqual(ctx.exception.args[0], 'SEC_URL_NOT_ALLOWED')

    def test_offline_and_validator(self):
        p = unavailable_classification(as_of=NOW)
        self.assertEqual(p['state'], 'NOT_AVAILABLE')
        self.assertIn('CYCLICAL_DEFENSIVE_RULE_UNDECIDED', p['reason_codes'])
        self.assertTrue(all(r['industry']['group'] is None and all(m['member'] is None for m in r['themes']['memberships'].values())
                            for r in p['data']['companies'].values()))
        live = self.live_like_flow()
        mutations = [
            lambda q: q['data']['etfs']['SMH'].update(weight=0.05),
            lambda q: q['data']['companies']['nvda']['themes']['memberships']['ai'].update(evidence=[]),
            lambda q: q['data']['companies']['amd']['themes']['memberships']['ai'].update(member=False),
            lambda q: q['data']['companies']['nvda']['themes']['memberships']['ai'].update(etfs=['SOXX']),
            lambda q: q['data']['companies']['nvda']['industry'].update(group='utilities_x'),
            lambda q: q['data']['companies']['gev']['industry'].update(sic='0000'),
            lambda q: q['data']['companies']['nvda']['themes'].update(item1='text'),
            lambda q: q.update(state='STALE'),
            lambda q: q['sources'].append({'agency': 'SEC_13F', 'sha256': 'a' * 64, 'acquired_at': q['as_of']}),
            lambda q: q['data']['theme_config']['themes'][0].update(etfs=['AIQ', 'AIQ']),
        ]
        for i, mutate in enumerate(mutations):
            q = copy.deepcopy(live)
            mutate(q)
            with self.assertRaises(ValueError, msg=i):
                require_public_classification(q)


class PipelineAndGuard(unittest.TestCase):
    def test_cli_offline_live_and_guard(self):
        import public_classification_pipeline as pipe
        from pages_artifact_guard import scan_artifact, _check_payload
        from collections import Counter
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(pipe.main(['--out', d]), 0)
            body = (Path(d) / FILENAME).read_bytes()
            v = Counter(); _check_payload(FILENAME, body, v); self.assertEqual(dict(v), {})
            routes = live_routes()
            payload = pipe.collect(d, environ={'SEC_USER_AGENT': UA}, client_factory=lambda ua: client(routes, datetime.now(timezone.utc))[0])
            self.assertEqual(payload['state'], 'LIVE')
            v = Counter(); _check_payload(FILENAME, (Path(d) / FILENAME).read_bytes(), v); self.assertEqual(dict(v), {})
            self.assertIn('etfs=24/24', pipe.summary(payload))
            tampered = json.loads((Path(d) / FILENAME).read_text())
            tampered['data']['etfs']['SMH']['marketvalue'] = 1
            v = Counter(); _check_payload(FILENAME, json.dumps(tampered).encode(), v)
            self.assertTrue(v['classification_boundary'] and v['sensitive_json_fields'])
            # A failed live run publishes NOT_AVAILABLE instead of failing the deploy.
            out = subprocess.run([sys.executable, str(ROOT / 'tools/public_classification_pipeline.py'), '--out', d, '--live'],
                                 capture_output=True, text=True, env={'PATH': '/usr/bin:/bin'})
            self.assertEqual(out.returncode, 0)
            self.assertIn('PUBLIC_CLASSIFICATION_LIVE_UNAVAILABLE', out.stdout)
            self.assertEqual(json.loads((Path(d) / FILENAME).read_text())['state'], 'NOT_AVAILABLE')


FIXTURE = ROOT / 'tests/fixtures/company_classification_v0_payloads.json'


def fixture_payloads():
    live, _ = CollectionAndPublic().collect(live_routes())
    return {'note': 'Synthetic SEC-shaped evidence (tests/test_sic_theme_v0.py live_routes); shared Python/JS validator fixture.',
            'live': live, 'offline': unavailable_classification(as_of=NOW)}


class SharedFixture(unittest.TestCase):
    def test_fixture_matches_generator(self):
        # Regenerate with: python tests/test_sic_theme_v0.py --write-fixture
        self.assertEqual(json.loads(FIXTURE.read_text()), json.loads(json.dumps(fixture_payloads())))


if __name__ == '__main__' and '--write-fixture' in sys.argv:
    FIXTURE.write_text(json.dumps(fixture_payloads(), ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n')
elif __name__ == '__main__':
    unittest.main()
