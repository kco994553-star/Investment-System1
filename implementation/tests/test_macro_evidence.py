"""Macro evidence lines (MEV-1 P1 13): parsers on recorded agency responses, candidate rules, append-only vintages and
release times (MEV-9), the public file contract, the collector's fixed request allowlist, the tool, the guard and the
build. Offline only: recorded fixtures (tests/fixtures/macro_evidence) and synthetic transports; nothing is contacted.

Recorded (real, trimmed, captured 2026-10-20): DOL ETA 539 national XML, Fed DDP G.17 summary and SLOOS chart CSV
(columns trimmed), a DDP Choose page excerpt, the Board's openmarket.htm FOMC tables, data.bts.gov TSI rows, BEA
NipaDataM/NipaDataQ lines. Synthetic (documented formats): BLS v1 JSON (the container is over the BLS daily limit),
Census EITS JSON (key required), Treasury curve XML (yields are not stored as fixtures).
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import urllib.error

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))

from investment_system.macro import evidence_lines as el
from investment_system.macro import evidence_sources as es
from investment_system.providers import macro_evidence_collection as mc
import macro_evidence_fixture as fx

FIX = ROOT / 'tests/fixtures/macro_evidence'
AT = datetime(2026, 10, 20, 1, 0, tzinfo=timezone.utc)


def body(name):
    return (FIX / name).read_bytes()


def bls_body(series):
    return json.dumps({'status': 'REQUEST_SUCCEEDED', 'Results': {'series': [
        {'seriesID': sid, 'data': [{'year': p[:4], 'period': 'M' + p[5:], 'value': v, 'footnotes': [{}]} for p, v in rows]}
        for sid, rows in series.items()]}}).encode()


def curve_xml(days):
    entries = ''.join(
        '<entry><content type="application/xml"><m:properties><d:NEW_DATE m:type="Edm.DateTime">%sT00:00:00</d:NEW_DATE>'
        '<d:BC_3MONTH m:type="Edm.Double">%s</d:BC_3MONTH><d:BC_10YEAR m:type="Edm.Double">%s</d:BC_10YEAR></m:properties></content></entry>'
        % (day, three, ten) for day, three, ten in days)
    return ('<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom" '
            'xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" '
            'xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">' + entries + '</feed>').encode()


# ---------------------------------------------------------------- registry

def test_registry_is_the_catalog_p1_set_with_required_fields():
    assert es.INDICATOR_IDS == ('E09', 'E13', 'E14', 'E16', 'E17', 'E21', 'E22', 'E25', 'E26', 'E36', 'E39', 'E40', 'E01')
    families = {i['id']: i['family'] for i in es.INDICATORS}
    assert families == {'E09': 'C', 'E13': 'LU', 'E14': 'LU', 'E16': 'LD', 'E17': 'LD', 'E21': 'MO', 'E22': 'PO', 'E25': 'PO',
                        'E26': 'HO', 'E36': 'BK', 'E39': 'IN', 'E40': 'PL', 'E01': 'T'}
    for i in es.INDICATORS:
        assert i['official_statistic'] is True and i['license_class'] in es.LICENSE_CLASSES
        assert i['rule']['source_class'] in es.RULE_SOURCES and i['rule']['realtime_validation'] in es.REALTIME_VALIDATION
        assert i['publication'] in es.PUBLICATION and len(i['terms_checked_on']) == 10 and i['terms_note']
        assert set(i['cycles']) <= set(es.CYCLES) and 'economy' in i['cycles']
        for edge in i['edges'].values():
            assert edge['candidate'] in (None, *es.CANDIDATES) and edge['label'] and edge['interpretation']
    # Sahm has one position only: expansion -> contraction (catalog §0).
    assert es.BY_ID['E13']['edges']['down']['interpretation'] == '확장→수축 전환(침체 초기 확인)'
    # E40: the event is a fact; interpretation is not counted (사건과 해석 분리).
    assert all(e['candidate'] is None for e in es.BY_ID['E40']['edges'].values())
    # No market price series in the public set (B-PRICE); FRED is never a source (MEV-3).
    text = json.dumps([dict(i, rule=dict(i['rule']), edges={k: dict(v) for k, v in i['edges'].items()}) for i in es.INDICATORS], ensure_ascii=False)
    for word in ('SPY', 'HYG', 'IEF', 'VIX', 'fred.stlouisfed', 'ICE BofA'):
        assert word not in text
    assert es.BY_ID['E14']['publication'] == 'HELD_TERMS_UNVERIFIED'


# ---------------------------------------------------------------- parsers on recorded responses

def test_dol_weekly_xml_skips_unpublished_weeks():
    rows = es.parse_dol_weekly(body('dol_eta539_national.xml'))
    assert len(rows) >= 140 and min(rows) == '2024-01-06'
    assert all(v > 100000 for v in rows.values())  # blank (&#160;) future weeks are skipped, never 0
    assert max(rows) < '2026-10-17'
    with pytest.raises(es.SourceUnavailable) as caught:
        es.parse_dol_weekly(b'<!DOCTYPE x [<!ENTITY a "b">]><r539cyNational/>')
    assert caught.value.reason == 'UNSAFE_XML'


def test_ddp_csv_selects_the_named_column_only():
    ip = es.parse_ddp_csv(body('fed_ddp_g17_summary.csv'), 'IP.B50001.S')
    assert min(ip) == '2012-01' and max(ip) == '2026-09' and all(80 < v < 130 for v in ip.values())
    with pytest.raises(es.SourceUnavailable) as caught:
        es.parse_ddp_csv(body('fed_ddp_g17_summary.csv'), 'IP.NOT_THERE')
    assert caught.value.reason == 'SERIES_NOT_FOUND'
    sloos = es.parse_ddp_csv(body('fed_ddp_sloos_chart.csv'), 'SUBLPDCILS_N.Q')
    assert min(sloos) == '2005Q1' and max(sloos) == '2026Q3' and any(v < 0 for v in sloos.values())
    assert es.parse_ddp_release_date(body('fed_ddp_choose_g17.html')) == '2026-10-16'
    assert es.parse_ddp_release_date(b'<p>no date</p>') is None


def test_fomc_openmarket_changes_in_date_order():
    rows = es.parse_fomc_openmarket(body('fed_openmarket.html'))
    assert rows[-1] == {'date': '2026-09-17', 'direction': 'up', 'bp': 25, 'level': '3.75-4.00', 'upper': 4.0}
    assert rows == sorted(rows, key=lambda r: r['date']) and len({r['date'] for r in rows}) == len(rows)
    assert {r['direction'] for r in rows} == {'up', 'down'}
    march_2020 = [r for r in rows if r['date'].startswith('2020-03')]
    assert [r['bp'] for r in march_2020] == [50, 100]


def test_bts_bea_and_synthetic_formats():
    tsi = es.parse_bts_tsi(body('bts_tsi_freight.json'))
    assert len(tsi) == 180 and max(tsi) == '2026-08'
    pce = es.parse_bea_flat(body('bea_nipa_m.txt'), 'DPCCRG', 'M')
    assert min(pce) == '2012-01' and max(pce) == '2026-08'  # DPCCRGM lines are not mixed in
    gdp = es.parse_bea_flat(body('bea_nipa_q.txt'), 'A191RL', 'Q')
    assert max(gdp) == '2026Q2' and gdp['2025Q4'] == 0.2
    with pytest.raises(es.SourceUnavailable):
        es.parse_bea_flat(body('bea_nipa_q.txt'), 'NOPE', 'Q')
    out = es.parse_bls_v1(bls_body({'CES6056132001': [('2026-08', '2600.1'), ('2026-07', '-')], 'CES3000000007': []}),
                          ('CES6056132001', 'CES3000000007', 'CUSR0000SA0L1E'))
    assert out == {'BLS:CES6056132001': {'2026-08': 2600.1}, 'BLS:CES3000000007': 'MISSING_SOURCE',
                   'BLS:CUSR0000SA0L1E': 'SERIES_NOT_FOUND'}
    with pytest.raises(es.SourceUnavailable) as caught:
        es.parse_bls_v1(json.dumps({'status': 'REQUEST_NOT_PROCESSED', 'message': ['x'], 'Results': {}}).encode(), ('LNS14000000',))
    assert caught.value.reason == 'PROVIDER_ERROR'
    census = json.dumps([['cell_value', 'data_type_code', 'time_slot_id', 'category_code', 'seasonally_adj', 'time', 'us'],
                         ['74,000', 'NO', '0', 'NXA', 'yes', '2026-08', '1'], ['70000', 'NO', '0', 'NXA', 'no', '2026-08', '1'],
                         ['(S)', 'NO', '0', 'NXA', 'yes', '2026-09', '1']]).encode()
    assert es.parse_census_eits(census, category='NXA', data_type='NO') == {'2026-08': 74000.0}
    spread = es.treasury_monthly_spread([curve_xml([('2026-08-03', '4.0', '4.5'), ('2026-08-04', '4.2', '4.4'),
                                                    ('2026-09-01', '4.0', '3.0')])], before_month='2026-09')
    assert spread == {'2026-08': 0.35}  # the running month is not a completed month


# ---------------------------------------------------------------- candidate rules

def edges(indicator, rows, frequency='M'):
    return el.edges(indicator, sorted(rows.items(), key=lambda kv: el.period_index(kv[0], frequency)), frequency)


def test_rules_follow_the_catalog_text():
    m = list(fx.months('2024-01', 30))
    assert edges('E09', {p: (0.5 if i < 20 else -0.2) for i, p in enumerate(m)}) == [(m[20], 'down')]
    sahm = {p: 4.0 for p in m[:20]} | {m[20]: 5.6}
    assert edges('E13', sahm) == [(m[20], 'down')]
    assert edges('E13', {p: 4.0 for p in m[:20]} | {m[20]: 5.4}) == []  # gap 0.47 < 0.50
    weeks = [(datetime(2025, 1, 4) + timedelta(days=7 * k)).date().isoformat() for k in range(40)]
    claims = {w: 200000.0 + (0 if k < 32 else 30000.0) for k, w in enumerate(weeks)}
    assert edges('E14', {w: 200000.0 + k for k, w in enumerate(weeks[:27])} | {w: claims[w] for w in weeks[27:]}, 'W')[-1][1] == 'up'
    # 130 - i after month 15: the 6-month change is +, then 0 at m[18] (keeps the state), then - at m[19].
    assert edges('E16', {p: 100.0 + (i if i < 15 else 30 - i) for i, p in enumerate(m)})[0] == (m[19], 'down')
    assert edges('E22', {p: 100.0 + (i if i < 16 else 32 - 1.5 * i) for i, p in enumerate(m)})[0][1] == 'down'
    q = list(fx.quarters('2020Q1', 8))
    assert edges('E25', dict(zip(q, [2, 1, -1, -0.5, 0, 1, 2, -1])), 'Q') == [(q[2], 'down'), (q[5], 'up'), (q[7], 'down')]
    assert edges('E36', dict(zip(q, [-5, -1, 0, 3, 2, -4, -1, 0])), 'Q') == [(q[3], 'up'), (q[5], 'down')]
    # E01: a direction change is recorded when it has lasted three months (at the third observation).
    tsi = {p: 100.0 + i for i, p in enumerate(m[:10])} | {m[10]: 108.5, m[11]: 108.0, m[12]: 107.0}
    assert edges('E01', tsi) == [(m[12], 'down')]
    assert edges('E01', {k: v for k, v in tsi.items() if k != m[12]}) == []
    # E39: 3-month annualized above the 12-month rate for 3 consecutive months.
    x, cpi = 100.0, {}
    for i, p in enumerate(m):
        x *= 1.003 if i < 12 else 1.002 if i < 24 else 1.006  # deceleration first establishes the 'down' state
        cpi[p] = x
    assert edges('E39', {p: cpi[p] for p in m[:26]}) == [] and edges('E39', cpi) == [(m[26], 'up')]
    # E40: every change of the published target is an event (fact).
    assert edges('E40', {'2025-01-01': 4.5, '2025-03-01': 4.25, '2025-05-01': 4.0, '2025-07-01': 4.25}, 'E') == [
        ('2025-03-01', 'down'), ('2025-05-01', 'down'), ('2025-07-01', 'up')]


# ---------------------------------------------------------------- vintages, release times, events

def test_baseline_records_nothing_and_rebuilds_replay_only():
    payload = fx.runs()[0]
    assert payload['continuity'] == 'BASELINE' and payload['releases'] == [] and payload['events'] == []
    assert payload['replay_events'] and all(set(e) == {'indicator', 'series', 'rule', 'direction', 'period'} for e in payload['replay_events'])
    dol = payload['series']['DOL:ETA539:INITIAL_CLAIMS_SA']
    assert dol['state'] == 'NOT_AVAILABLE' and dol['reason'] == 'TERMS_UNVERIFIED' and dol['obs'] == [] and dol['history'] == {}
    assert {i['id']: i['reason'] for i in payload['indicators'] if i['state'] != 'LIVE'} == {
        'E14': 'TERMS_UNVERIFIED', 'E21': 'SOURCE_KEY_NOT_CONFIGURED', 'E26': 'SOURCE_KEY_NOT_CONFIGURED'}
    assert payload['scope'] == {'screen': 'EXPLORATION_ONLY', 'official_judgement': False, 'probability': False,
                                'macro_gate': False, 'decision': 'MEV-10'}


def test_runs_are_append_only_and_keep_first_release_values():
    runs = fx.runs()
    for before, after in zip(runs, runs[1:]):
        assert after['releases'][:len(before['releases'])] == before['releases']
        assert after['events'][:len(before['events'])] == before['events']
        for sid, row in before['series'].items():
            for period, versions in row['history'].items():
                assert after['series'][sid]['history'][period][:len(versions)] == versions
    last = runs[-1]
    g17 = last['series']['FED:G17:IP.B50001.S']
    assert g17['history']['2026-06'] == [
        {'v': 104.1, 'kind': 'BASELINE', 'at': '2026-10-01T10:00:00Z', 'basis': 'BASELINE', 'rd': None},
        {'v': 104.0, 'kind': 'REVISION', 'at': '2026-10-04T10:00:00Z', 'basis': 'COLLECTION_TIME', 'rd': '2026-10-01'}]
    assert dict(map(tuple, g17['obs']))['2026-06'] == 104.0
    lns = last['series']['BLS:LNS14000000']['history']['2026-08']
    assert [(v['kind'], v['v']) for v in lns] == [('FIRST', 5.6), ('REVISION', 4.9)]


def test_release_time_basis_and_three_month_rule():
    last = fx.runs()[-1]
    by = {(e['indicator'], e['kind'], e['cause']): e for e in last['events']}
    tsi = by[('E01', 'EDGE', 'FIRST')]
    # posted between the previous and this collection -> the posting time; recorded at the third decline (run 5).
    assert tsi['basis'] == 'SOURCE_LAST_MODIFIED' and tsi['at'] == '2026-10-06T08:00:00Z' and tsi['period'] == '2026-08'
    sahm = by[('E13', 'EDGE', 'FIRST')]
    assert sahm['basis'] == 'COLLECTION_TIME' and sahm['at'] == '2026-10-03T10:00:00Z'
    cleared = by[('E13', 'REVISION_CLEARED', 'REVISION')]
    assert cleared['period'] == '2026-08' and cleared['at'] == '2026-10-08T10:00:00Z'
    flip = by[('E36', 'EDGE', 'REVISION')]
    assert flip['direction'] == 'down' and flip['period'] == '2026Q3'
    accel = by[('E39', 'EDGE', 'FIRST')]
    assert accel['period'] == '2026-09' and accel['at'] == '2026-10-07T10:00:00Z'
    assert len([e for e in last['events'] if e['indicator'] == 'E40']) == 7
    for e in last['events']:
        assert e['at'] >= '2026-10-02'  # nothing back-filled before the first real-time run
    assert last['summary']['economy']['warning_families'] == ['C', 'T']
    assert 'IN' not in sum((last['summary']['economy'][k] for k in ('warning_families', 'improving_families', 'mixed_families')), [])
    assert last['summary']['industry']['realtime_event_indicators'] == ['E01']
    assert last['summary']['market']['realtime_event_indicators'] == ['E40']


def test_posting_time_outside_the_window_falls_back_to_collection_time():
    runs = fx.runs()
    captures = {sid: {'reason': 'SOURCE_NOT_AVAILABLE'} for sid in es.SERIES_IDS}
    rows = dict(map(tuple, runs[-1]['series']['BTS:TSI:FREIGHT']['obs']))
    rows['2026-09'] = 136.0
    at = fx.T0 + timedelta(days=9)
    captures['BTS:TSI:FREIGHT'] = fx.capture(rows, at, posted=fx.T0)  # posted before the previous collection
    out = el.build(captures, previous=runs[-1], previous_state='LOADED', now=at)
    record = out['releases'][-1]
    assert record == {'series': 'BTS:TSI:FREIGHT', 'period': '2026-09', 'kind': 'FIRST', 'at': el.iso(at), 'basis': 'COLLECTION_TIME', 'rd': None}
    # Failed sources keep their published history and say why; nothing becomes 0.
    sahm = out['series']['BLS:LNS14000000']
    assert sahm['state'] == 'NOT_AVAILABLE' and sahm['reason'] == 'SOURCE_NOT_AVAILABLE' and sahm['obs'] == runs[-1]['series']['BLS:LNS14000000']['obs']


def test_previous_unavailable_marks_a_reset():
    first = fx.runs()[0]
    captures = {sid: {'reason': 'SOURCE_NOT_AVAILABLE'} for sid in es.SERIES_IDS}
    out = el.build(captures, previous=None, previous_state='UNAVAILABLE', now=AT)
    assert out['continuity'] == 'RESET_PREVIOUS_UNAVAILABLE' and out['state'] == 'NOT_AVAILABLE'
    placeholder = el.empty_payload(AT)
    again = el.build({}, previous=placeholder, previous_state='LOADED', now=AT)
    assert again['continuity'] == 'BASELINE'  # a placeholder is not history
    assert first['collection_started_at'] == el.iso(fx.T0)


# ---------------------------------------------------------------- contract

def test_validator_rejects_out_of_scope_or_altered_payloads():
    good = fx.runs()[-1]
    el.require_macro_evidence(good)
    mutations = [
        lambda p: p['scope'].update(official_judgement=True),
        lambda p: p['scope'].update(macro_gate=True),
        lambda p: p['series']['DOL:ETA539:INITIAL_CLAIMS_SA']['obs'].append(['2026-09-26', 1.0]),
        lambda p: p['events'].append(dict(p['events'][0])),
        lambda p: p['events'][0].update(layer='REPLAY'),
        lambda p: p['releases'][0].update(basis='BASELINE'),
        lambda p: p['series']['BLS:LNS14000000']['obs'].append(['2026-09', float('nan')]),
        lambda p: p['series']['BLS:LNS14000000'].update(extra=1),
        lambda p: p['indicators'][0]['edges']['down'].update(interpretation='승인됨'),
        lambda p: p['labels'].update(interpretation='해석'),
        lambda p: p['series']['FED:G17:IP.B50001.S']['history']['2026-06'][1].update(kind='BASELINE'),
    ]
    for mutate in mutations:
        bad = copy.deepcopy(good)
        mutate(bad)
        with pytest.raises(ValueError):
            el.require_macro_evidence(bad)


def test_committed_browser_fixture_matches_the_generator():
    assert (FIX / 'browser_payload.json').read_text(encoding='utf-8') == fx.encoded()


# ---------------------------------------------------------------- collector

class FakeTransport:
    def __init__(self, responses):
        self.responses, self.calls = responses, []

    def __call__(self, url, *, data, query, form=False):
        if not mc.query_allowed(url, query, data):
            raise mc.MacroV0FetchError('URL_NOT_ALLOWED')
        self.calls.append((url, query, data))
        for (u, needle), result in self.responses.items():
            if u == url and (needle is None or needle in (query or '') or needle in (data or b'').decode()):
                if isinstance(result, Exception):
                    raise result
                return result
        raise mc.MacroV0FetchError('HTTP_STATUS', status=404)


def responses(override=None):
    out = {
        (mc.ENDPOINTS['BLS'], None): (bls_body({'CES6056132001': [('2026-08', '2600')], 'CES3000000007': [('2026-08', '40.4')],
                                                'CUSR0000SA0L1E': [('2026-08', '330.1')]}), {'last-modified': None}),
        (mc.BEA_FLAT_M_URL, None): (body('bea_nipa_m.txt'), {'last-modified': 'Wed, 30 Sep 2026 12:30:02 GMT'}),
        (mc.FED_DDP_URL, 'G17'): (body('fed_ddp_g17_summary.csv'), {'last-modified': None}),
        (mc.FED_DDP_URL, 'SLOOS'): (body('fed_ddp_sloos_chart.csv'), {'last-modified': None}),
        (mc.DDP_CHOOSE_URL, 'G17'): (body('fed_ddp_choose_g17.html'), {'last-modified': None}),
        (mc.FOMC_URL, None): (body('fed_openmarket.html'), {'last-modified': 'Wed, 16 Sep 2026 18:13:03 GMT'}),
        (mc.DOL_URL, None): (body('dol_eta539_national.xml'), {'last-modified': None}),
        (mc.BTS_URL, None): (body('bts_tsi_freight.json'), {'last-modified': 'Wed, 14 Oct 2026 12:59:26 GMT'}),
    }
    out.update(override or {})
    return out


def reused_root(tmp_path):
    (tmp_path / 'macro-v0-bls.json').write_bytes(bls_body({'CUUR0000SA0': [('2026-08', '320')], 'LNS14000000': [('2026-08', '4.3'), ('2026-07', '4.2')]}))
    (tmp_path / 'macro-v0-bea-nipa-q.txt').write_bytes(body('bea_nipa_q.txt'))
    (tmp_path / 'macro-v1-treasury-curve-2026.xml').write_bytes(curve_xml([('2026-08-03', '4.0', '4.5'), ('2026-09-01', '4.1', '4.3')]))
    stamp = AT.isoformat()
    return {'macro_v0': [{'axis': 'Inflation', 'format': 'BLS_API_V1_JSON', 'file': 'macro-v0-bls.json', 'acquired_at': stamp, 'synthetic': False},
                         {'axis': 'Growth', 'format': 'BEA_NIPA_FLAT_Q', 'file': 'macro-v0-bea-nipa-q.txt', 'acquired_at': stamp, 'synthetic': False}],
            'macro_curve_v1': [{'format': 'TREASURY_DAILY_PAR_YIELD_XML', 'file': 'macro-v1-treasury-curve-2026.xml', 'acquired_at': stamp, 'synthetic': False}]}


def test_collector_reuses_macro_files_and_fetches_only_fixed_requests(tmp_path):
    manifest = reused_root(tmp_path)
    transport, diagnostics = FakeTransport(responses()), []
    caps = mc.collect_macro_evidence(tmp_path, manifest, environ={}, year=2026, transport=transport,
                                     clock=lambda: AT, diagnostics=diagnostics)
    assert caps['BLS:LNS14000000']['rows'] == {'2026-07': 4.2, '2026-08': 4.3}
    assert caps['TREASURY:BC_10YEAR-BC_3MONTH:MONTHLY_MEAN']['rows'] == {'2026-08': 0.5, '2026-09': 0.2}  # September is complete on 10-20
    assert max(caps['BEA:NIPA:A191RL:Q']['rows']) == '2026Q2'
    assert caps['FED:G17:IP.B50001.S']['release'] == {'at': None, 'date': '2026-10-16'}
    assert caps['FED:FOMC:TARGET_RANGE']['release']['at'] == datetime(2026, 9, 16, 18, 13, 3, tzinfo=timezone.utc)
    assert caps['CENSUS:M3:NXA:NO:SA'] == {'reason': 'SOURCE_KEY_NOT_CONFIGURED'}
    # SLOOS Choose page missing -> release date unknown, data still captured.
    assert caps['FED:SLOOS:SUBLPDCILS_N.Q']['release'] == {'at': None, 'date': None}
    urls = [c[0] for c in transport.calls]
    assert not any(u in (mc.ENDPOINTS['BEA'],) or 'treasury' in u or 'NipaDataQ' in u for u in urls)  # reused, not re-fetched
    assert urls.count(mc.ENDPOINTS['BLS']) == 1
    payload = el.build(caps, previous=None, previous_state='NO_LIVE', now=AT)
    assert payload['series']['DOL:ETA539:INITIAL_CLAIMS_SA']['obs'] == []
    assert {d['stage'] for d in diagnostics} == {'DDP_CHOOSE_SLOOS'}


def test_collector_failures_are_reason_codes_and_the_key_stays_private(tmp_path, capsys):
    manifest = reused_root(tmp_path)
    key = 'k' * 40
    census = json.dumps([['cell_value', 'data_type_code', 'time_slot_id', 'category_code', 'seasonally_adj', 'time', 'us'],
                         ['74000', 'NO', '0', 'NXA', 'yes', '2026-08', '1']]).encode()
    transport = FakeTransport(responses({
        (mc.CENSUS_URL + 'm3', None): (census, {'last-modified': None}),
        (mc.CENSUS_URL + 'resconst', None): mc.MacroV0FetchError('HTTP_STATUS', status=503),
        (mc.ENDPOINTS['BLS'], None): (json.dumps({'status': 'REQUEST_NOT_PROCESSED', 'Results': {}}).encode(), {}),
        (mc.FOMC_URL, None): mc.MacroV0FetchError('TIMEOUT'),
    }))
    diagnostics = []
    caps = mc.collect_macro_evidence(tmp_path, manifest, environ={'CENSUS_API_KEY': key}, year=2026, transport=transport,
                                     clock=lambda: AT, diagnostics=diagnostics)
    assert caps['CENSUS:M3:NXA:NO:SA']['rows'] == {'2026-08': 74000.0}
    assert caps['CENSUS:RESCONST:APERMITS:TOTAL:SA'] == {'reason': 'SOURCE_NOT_AVAILABLE'}
    assert caps['BLS:CES6056132001'] == {'reason': 'PROVIDER_ERROR'} and caps['FED:FOMC:TARGET_RANGE'] == {'reason': 'SOURCE_NOT_AVAILABLE'}
    assert key not in json.dumps(diagnostics) and key not in capsys.readouterr().out
    assert any(key in (c[1] or '') for c in transport.calls)  # sent to Census only, as a query parameter
    payload = el.build(caps, previous=None, previous_state='NO_LIVE', now=AT)
    assert key not in json.dumps(payload)


def test_request_allowlist_refuses_everything_else():
    allowed = mc.query_allowed
    assert allowed(mc.FED_DDP_URL, mc.ddp_query(es.DDP_PACKAGES['FED:G17:IP.B50001.S']), None)
    assert not allowed(mc.FED_DDP_URL, mc.ddp_query({'rel': 'G17', 'series': 'a' * 32}), None)
    assert not allowed('https://fred.stlouisfed.org/graph/fredgraph.csv', None, None)
    assert not allowed(mc.FOMC_URL, 'x=1', None)
    assert not allowed(mc.DOL_URL, None, b'level=state&final_yr=2027&strtdate=2021&enddate=2026&filetype=xml')
    assert allowed(mc.DOL_URL, None, b'level=us&final_yr=2027&strtdate=2021&enddate=2026&filetype=xml')
    assert not allowed(mc.CENSUS_URL + 'm3', 'get=x&for=us%3A%2A&time=from+2017&category_code=XXX&data_type_code=NO', None)
    assert allowed(mc.CENSUS_URL + 'm3', mc.census_query(es.CENSUS_QUERIES['CENSUS:M3:NXA:NO:SA'], 2026, None), None)
    with pytest.raises(mc.MacroV0FetchError):
        mc.default_transport('https://example.com/', data=None, query=None)


# ---------------------------------------------------------------- tool, guard, build

def test_tool_writes_validated_file_and_preserves_the_live_copy(tmp_path, capsys):
    import macro_evidence as tool
    manifest = reused_root(tmp_path / 'private') if (tmp_path / 'private').mkdir() is None else None
    out = tmp_path / 'site'
    out.mkdir()
    code = tool.run_from_capture(out, tmp_path / 'private', manifest, environ={}, now=lambda: AT,
                                 transport=FakeTransport(responses()), previous=(None, 'NO_LIVE'))
    assert code == 0
    payload = el.require_macro_evidence(tool.parse_json((out / el.FILENAME).read_bytes()))
    assert payload['continuity'] == 'BASELINE'
    printed = capsys.readouterr().out
    assert 'MACRO_EVIDENCE state=PARTIAL' in printed and 'http' not in printed.replace('http=', '')

    live = (out / el.FILENAME).read_bytes()

    class Response(io.BytesIO):
        status = 200

        def geturl(self):
            return tool.SOURCE

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    restored = tmp_path / 'restored'
    restored.mkdir()
    assert tool.preserve(restored, open_previous=lambda request, timeout: Response(live)) == 0
    assert (restored / el.FILENAME).read_bytes() == live

    def missing(request, timeout):
        raise urllib.error.HTTPError(tool.SOURCE, 404, 'nf', {}, None)
    empty = tmp_path / 'empty'
    empty.mkdir()
    assert tool.preserve(empty, open_previous=missing) == 0 and not (empty / el.FILENAME).exists()
    assert tool.load_previous(lambda r, timeout: Response(b'{"schema":"x"}')) == (None, 'NO_LIVE')
    assert tool.load_previous(lambda r, timeout: (_ for _ in ()).throw(OSError('down'))) == (None, 'UNAVAILABLE')
    assert tool.main(['--out', str(empty)]) == 2


def test_guard_accepts_the_file_and_rejects_a_tampered_copy(tmp_path):
    import pages_artifact_guard as guard
    from collections import Counter
    assert el.FILENAME in guard.ALLOWED_NAMES
    assert 'macro-evidence.js' in guard.APPROVED_SHA256 and 'macro-evidence.css' in guard.APPROVED_SHA256
    violations = Counter()
    guard._check_payload(el.FILENAME, el.encode(fx.runs()[-1]), violations)
    assert not violations
    bad = fx.runs()[-1]
    bad['scope']['probability'] = True
    guard._check_payload(el.FILENAME, json.dumps(bad).encode(), violations)
    assert violations['macro_evidence_boundary'] == 1


def test_build_emits_the_not_collected_placeholder(tmp_path):
    import build_pages_cockpit
    out = tmp_path / 'site'
    build_pages_cockpit.build_public_cockpit(out)
    payload = el.require_macro_evidence(json.loads((out / el.FILENAME).read_text(encoding='utf-8')))
    assert payload['state'] == 'NOT_AVAILABLE' and payload['generated_at'] is None and payload['continuity'] == 'NOT_COLLECTED'
    assert (out / 'macro-evidence.js').is_file() and (out / 'macro-evidence.css').is_file()
    index = (out / 'index.html').read_text(encoding='utf-8')
    assert '<script src="macro-evidence.js"></script>' in index and 'href="macro-evidence.css"' in index
    import pages_artifact_guard as guard
    assert guard.scan_artifact(out)['pages_artifact_guard'] == 'PASS'


def test_pipeline_hook_never_stops_the_sec_collection(tmp_path, monkeypatch, capsys):
    import public_screens_pipeline as pipeline
    import macro_evidence as tool
    seen = {}
    tool.emit_empty(tmp_path, now=lambda: AT)

    def boom(root, manifest):
        seen['called'] = (Path(root).is_dir(), sorted(manifest))
        raise RuntimeError('source text that must not be printed')

    def stop(*a, **k):
        raise pipeline.CollectionFailure([], [], 0) if False else SystemExit('stop-after-hook')
    monkeypatch.setattr(pipeline, 'collect_public_inputs', stop)
    with pytest.raises(SystemExit):
        pipeline.collect(tmp_path, macro_v0=lambda root: [], macro_curve=lambda root: [], macro_evidence=boom,
                         client_factory=lambda agent: None)
    assert seen['called'] == (True, ['macro', 'macro_curve_v1', 'macro_v0', 'schema_version', 'sec', 'thirteen_f'])
    out = capsys.readouterr().out
    assert 'MACRO_EVIDENCE BUILD_FAILED stage=CALLER error=RuntimeError' in out and 'source text' not in out
    # the caller handles the failure: the build-time placeholder is withheld, never published as a result
    assert 'MACRO_EVIDENCE WITHHELD file=macro-evidence.json previous=- status=NONE' in out
    assert not (tmp_path / el.FILENAME).exists()


# ---------------------------------------------------------------- failed attempts (owner 2026-11-07, run 42326419126)

def _site(tmp_path, name):
    out = tmp_path / name
    out.mkdir()
    import macro_evidence as tool
    tool.emit_empty(out, now=lambda: AT)          # the build-time placeholder, as build_pages_cockpit.py writes it
    return out


def _good_previous(tmp_path):
    """A good copy (built from collected data), made by the generator itself."""
    import macro_evidence as tool
    root = tmp_path / 'prev-private'
    root.mkdir()
    out = _site(tmp_path, 'prev-site')
    assert tool.run_from_capture(out, root, reused_root(root), environ={}, now=lambda: AT - timedelta(days=1),
                                 transport=FakeTransport(responses()), previous=(None, 'NO_LIVE')) == 0
    payload = el.require_macro_evidence(tool.parse_json((out / el.FILENAME).read_bytes()))
    assert payload['generated_at'] is not None and sum(1 for r in payload['series'].values() if r['state'] == 'LIVE') > 0
    return payload


def _status(out):
    import macro_evidence as tool
    return el.require_status(tool.parse_json((out / el.STATUS_FILENAME).read_bytes()))


@pytest.mark.parametrize('stage,patch', [
    ('COLLECT', ('investment_system.providers.macro_evidence_collection', 'collect_macro_evidence')),
    ('BUILD', ('investment_system.macro.evidence_lines', 'build')),
])
def test_a_failed_attempt_keeps_the_last_good_copy_unchanged_and_says_so(tmp_path, capsys, monkeypatch, stage, patch):
    import importlib
    import macro_evidence as tool
    good = _good_previous(tmp_path)
    good_body = el.encode(good)
    out = _site(tmp_path, 'site')
    root = tmp_path / 'private'
    root.mkdir()

    def boom(*a, **k):
        raise KeyError('a provider text that must not be printed')
    monkeypatch.setattr(importlib.import_module(patch[0]), patch[1], boom)
    capsys.readouterr()
    code = tool.run_from_capture(out, root, reused_root(root), environ={}, now=lambda: AT, previous=(good, 'LOADED'))
    assert code == 0
    assert (out / el.FILENAME).read_bytes() == good_body, 'the last good copy, byte for byte: never the placeholder'
    kept = el.require_macro_evidence(tool.parse_json((out / el.FILENAME).read_bytes()))
    assert kept['generated_at'] == good['generated_at'], 'its own build time, not re-stamped by the failed attempt'
    status = _status(out)
    assert status['attempt_result'] == 'FAILED' and status['failure_stage'] == stage and status['failure_class'] == 'KeyError'
    assert status['published'] == 'PREVIOUS_KEPT' and status['data_generated_at'] == good['generated_at']
    assert status['attempt_at'] == el.iso(AT) and status['attempt_at'] != status['data_generated_at']
    import hashlib
    assert status['data_sha256'] == hashlib.sha256(good_body).hexdigest()
    printed = capsys.readouterr().out
    assert f'MACRO_EVIDENCE BUILD_FAILED stage={stage} error=KeyError kept=PREVIOUS' in printed
    assert 'provider text' not in printed and 'nothing_written' not in printed


def test_invalid_output_is_never_written_and_the_good_copy_stays(tmp_path, capsys, monkeypatch):
    import macro_evidence as tool
    good = _good_previous(tmp_path)
    good_body = el.encode(good)
    out = _site(tmp_path, 'site')
    root = tmp_path / 'private'
    root.mkdir()
    real_encode, calls = el.encode, []

    def encode(payload):
        calls.append(1)
        if len(calls) > 1:                      # the first call encodes the kept copy; the new output is too large
            raise ValueError('MACRO_EVIDENCE_TOO_LARGE')
        return real_encode(payload)
    monkeypatch.setattr(el, 'encode', encode)
    code = tool.run_from_capture(out, root, reused_root(root), environ={}, now=lambda: AT,
                                 transport=FakeTransport(responses()), previous=(good, 'LOADED'))
    assert code == 0 and (out / el.FILENAME).read_bytes() == good_body
    status = _status(out)
    assert (status['failure_stage'], status['failure_class'], status['published']) == ('VALIDATE', 'ValueError', 'PREVIOUS_KEPT')


def test_no_good_copy_is_never_published_as_a_normal_result(tmp_path, capsys, monkeypatch):
    import macro_evidence as tool
    out = _site(tmp_path, 'site')
    placeholder = (out / el.FILENAME).read_bytes()
    root = tmp_path / 'private'
    root.mkdir()

    def boom(*a, **k):
        raise RuntimeError('x')
    monkeypatch.setattr(el, 'build', boom)
    code = tool.run_from_capture(out, root, reused_root(root), environ={}, now=lambda: AT,
                                 transport=FakeTransport(responses()), previous=(el.empty_payload(AT), 'EMPTY_LIVE'))
    assert code == 1
    assert (out / el.FILENAME).read_bytes() == placeholder, 'only the placeholder (generated_at null), never re-stamped'
    status = _status(out)
    assert status['attempt_result'] == 'FAILED' and status['published'] == 'WITHHELD'
    assert status['data_generated_at'] is None and status['data_sha256'] is None and status['previous'] == 'EMPTY_LIVE'
    assert 'kept=NONE previous=EMPTY_LIVE' in capsys.readouterr().out


def test_a_normal_partial_collection_replaces_the_copy_and_records_it(tmp_path, capsys):
    import macro_evidence as tool
    good = _good_previous(tmp_path)
    out = _site(tmp_path, 'site')
    root = tmp_path / 'private'
    root.mkdir()
    only_bls = {k: v for k, v in responses().items() if k[0] == mc.ENDPOINTS['BLS']}   # most sources fail: a partial run
    code = tool.run_from_capture(out, root, reused_root(root), environ={}, now=lambda: AT,
                                 transport=FakeTransport(only_bls), previous=(good, 'LOADED'))
    assert code == 0
    new = el.require_macro_evidence(tool.parse_json((out / el.FILENAME).read_bytes()))
    assert new['generated_at'] == el.iso(AT) and new['state'] == 'PARTIAL' and new['continuity'] == 'CONTINUOUS'
    status = _status(out)
    assert status['attempt_result'] == 'BUILT' and status['published'] == 'NEW' and status['data_generated_at'] == new['generated_at']


def test_a_placeholder_live_copy_is_not_a_previous_history(tmp_path):
    """After this incident the live copy is the placeholder: the next build is a new baseline that says the earlier
    history is not available, never CONTINUOUS and never a silent BASELINE."""
    import macro_evidence as tool
    out = _site(tmp_path, 'site')
    root = tmp_path / 'private'
    root.mkdir()

    class Response(io.BytesIO):
        status = 200

        def geturl(self):
            return tool.SOURCE

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    placeholder = el.encode(el.empty_payload(AT - timedelta(days=1)))
    good, good_body, read = tool.read_previous(lambda request, timeout: Response(placeholder))
    assert (good, good_body, read) == (None, None, 'EMPTY_LIVE')
    assert tool.run_from_capture(out, root, reused_root(root), environ={}, now=lambda: AT,
                                 transport=FakeTransport(responses()), open_previous=lambda r, timeout: Response(placeholder)) == 0
    new = el.require_macro_evidence(tool.parse_json((out / el.FILENAME).read_bytes()))
    assert new['continuity'] == 'RESET_PREVIOUS_UNAVAILABLE' and new['previous'] == 'UNAVAILABLE'
    assert _status(out)['previous'] == 'EMPTY_LIVE'


def test_status_record_rules():
    ok = dict(attempt_at=AT, result='FAILED', stage='BUILD', error_class='KeyError', published='PREVIOUS_KEPT',
              data_generated_at=el.iso(AT), data_sha256='a' * 64, previous='LOADED')
    el.status_record(**ok)
    for bad in ({'result': 'BUILT'}, {'published': 'NEW'}, {'stage': 'ELSEWHERE'}, {'error_class': 'Key Error: x'},
                {'published': 'WITHHELD'}, {'data_sha256': 'x'}, {'previous': 'MAYBE'}):
        with pytest.raises(ValueError):
            el.status_record(**{**ok, **bad})
    el.status_record(attempt_at=AT, result='BUILT', stage=None, error_class=None, published='NEW',
                     data_generated_at=el.iso(AT), data_sha256='b' * 64, previous='NO_LIVE')
    import pages_artifact_guard as guard
    from collections import Counter
    assert el.STATUS_FILENAME in guard.ALLOWED_NAMES
    violations = Counter()
    guard._check_payload(el.STATUS_FILENAME, el.encode_status(el.status_record(**ok)), violations)
    assert not violations
    guard._check_payload(el.STATUS_FILENAME, b'{"schema":"macro-evidence-status/1"}', violations)
    assert violations['macro_evidence_status_boundary'] == 1


def test_preserve_carries_the_live_attempt_record(tmp_path):
    import macro_evidence as tool
    good = _good_previous(tmp_path)
    good_body = el.encode(good)
    status = el.encode_status(el.status_record(attempt_at=AT, result='FAILED', stage='COLLECT', error_class='KeyError',
                                               published='PREVIOUS_KEPT', data_generated_at=good['generated_at'],
                                               data_sha256=__import__('hashlib').sha256(good_body).hexdigest(), previous='LOADED'))

    class Response(io.BytesIO):
        status = 200

        def __init__(self, data, url):
            super().__init__(data)
            self.url = url

        def geturl(self):
            return self.url

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    served = {tool.SOURCE: good_body, tool.STATUS_SOURCE: status}
    out = tmp_path / 'ui'
    out.mkdir()
    assert tool.preserve(out, open_previous=lambda request, timeout: Response(served[request.full_url], request.full_url)) == 0
    assert (out / el.FILENAME).read_bytes() == good_body and (out / el.STATUS_FILENAME).read_bytes() == status


# ---------------------------------------------------------------- the daily path end to end, checked on the artifact itself
# (owner 2026-11-07 2nd: the caller handles the failure; the deploy check reads the real artifact directory)

def _artifact_checks(out, live):
    """The two checks a deploy runs on this artifact: the Pages guard per file, and the freshness rule against `live`
    (bytes or None). -> (kind, verdict, guard violations)."""
    import pages_artifact_guard as guard
    import pages_freshness_guard as fg
    from collections import Counter
    violations = Counter()
    for f in sorted(out.iterdir()):
        guard._check_payload(f.name, f.read_bytes(), violations)
    live_state = ('NO_LIVE', None, None) if live is None else ('VALID', live, el.require_macro_evidence(fg.macro_tool.parse_json(live)))
    r = fg.compare_macro(live_state, fg._artifact_file(out, el.FILENAME, el.MAX_BYTES, el.require_macro_evidence),
                         fg._artifact_file(out, el.STATUS_FILENAME, el.MAX_BYTES, el.require_status))
    return r['kind'], r['verdict'], dict(violations)


def _daily(tmp_path, monkeypatch, name, *, previous, transport=None):
    """build_pages_cockpit.py's placeholder, then public_screens_pipeline.collect with the real hook wiring (the generator
    on the pipeline's private capture directory), stopped right after the hook."""
    import public_screens_pipeline as pipeline
    import macro_evidence as tool
    out = _site(tmp_path, name)

    def hook(root, manifest):
        return tool.run_from_capture(out, root, reused_root(Path(root)), environ={}, now=lambda: AT,
                                     transport=transport or FakeTransport(responses()), previous=previous)
    monkeypatch.setattr(pipeline, 'collect_public_inputs', lambda *a, **k: (_ for _ in ()).throw(SystemExit('after-hook')))
    with pytest.raises(SystemExit):
        pipeline.collect(out, macro_v0=lambda root: [], macro_curve=lambda root: [], macro_evidence=hook,
                         client_factory=lambda agent: None)
    return out


def test_daily_generation_failure_with_a_good_copy_publishes_it_unchanged(tmp_path, monkeypatch, capsys):
    good = _good_previous(tmp_path)
    live = el.encode(good)
    monkeypatch.setattr(el, 'build', lambda *a, **k: (_ for _ in ()).throw(KeyError('x')))
    out = _daily(tmp_path, monkeypatch, 'site', previous=(good, 'LOADED'))
    assert (out / el.FILENAME).read_bytes() == live, 'values, base dates and check times of the good copy stay'
    status = _status(out)
    assert (status['attempt_result'], status['failure_stage'], status['failure_class'], status['published']) == ('FAILED', 'BUILD', 'KeyError', 'PREVIOUS_KEPT')
    assert status['data_generated_at'] == good['generated_at'] and status['attempt_at'] == el.iso(AT)
    assert _artifact_checks(out, live) == ('EQUAL', 'PASS', {})
    printed = capsys.readouterr().out
    assert 'WITHHELD' not in printed and "'x'" not in printed


def test_daily_generation_failure_without_a_good_copy_withholds_the_file(tmp_path, monkeypatch, capsys):
    placeholder = el.encode(el.empty_payload(AT))
    good = el.encode(_good_previous(tmp_path))
    monkeypatch.setattr(el, 'build', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('x')))
    out = _daily(tmp_path, monkeypatch, 'site', previous=(el.empty_payload(AT), 'EMPTY_LIVE'))
    assert not (out / el.FILENAME).exists(), 'the placeholder is never published as a result'
    assert _status(out)['published'] == 'WITHHELD'
    assert 'MACRO_EVIDENCE WITHHELD file=macro-evidence.json previous=EMPTY_LIVE status=WITHHELD' in capsys.readouterr().out
    assert _artifact_checks(out, placeholder) == ('NO_GOOD_LIVE', 'NO_LIVE', {})
    assert _artifact_checks(out, None) == ('NO_GOOD_LIVE', 'NO_LIVE', {})
    # live good copy that this run could not read: this file is withheld, the rest of the deploy goes on (D-CV16 (a))
    assert _artifact_checks(out, good) == ('MISSING', 'WITHHELD', {})


def test_daily_write_failure(tmp_path, monkeypatch, capsys):
    import macro_evidence as tool
    good = _good_previous(tmp_path)
    live = el.encode(good)
    real, calls = tool.write_bytes, []

    def first_write_fails(directory, body, name=el.FILENAME):
        if name == el.FILENAME and json.loads(body)['generated_at'] is not None:   # not the build placeholder
            calls.append(name)
        if name == el.FILENAME and calls.count(el.FILENAME) == 1 and json.loads(body)['generated_at'] is not None:
            raise OSError('disk')
        return real(directory, body, name)
    monkeypatch.setattr(tool, 'write_bytes', first_write_fails)
    out = _daily(tmp_path, monkeypatch, 'once', previous=(good, 'LOADED'))
    assert (out / el.FILENAME).read_bytes() == live and _status(out)['failure_stage'] == 'WRITE'
    assert _artifact_checks(out, live) == ('EQUAL', 'PASS', {})

    def macro_writes_fail(directory, body, name=el.FILENAME):
        if name == el.FILENAME and json.loads(body)['generated_at'] is not None:   # the build placeholder was written before
            raise OSError('disk')
        return real(directory, body, name)
    monkeypatch.setattr(tool, 'write_bytes', macro_writes_fail)
    out = _daily(tmp_path, monkeypatch, 'always', previous=(good, 'LOADED'))
    assert not (out / el.FILENAME).exists(), 'no good copy could be written: the placeholder is withheld, not published'
    status = _status(out)
    assert (status['failure_stage'], status['published'], status['previous']) == ('WRITE', 'WITHHELD', 'LOADED')
    assert _artifact_checks(out, live) == ('MISSING', 'WITHHELD', {})


def test_daily_normal_partial_collection_is_published(tmp_path, monkeypatch):
    good = _good_previous(tmp_path)
    live = el.encode(good)
    only_bls = {k: v for k, v in responses().items() if k[0] == mc.ENDPOINTS['BLS']}
    out = _daily(tmp_path, monkeypatch, 'site', previous=(good, 'LOADED'), transport=FakeTransport(only_bls))
    new = el.require_macro_evidence(json.loads((out / el.FILENAME).read_bytes()))
    live_now = sum(1 for r in new['series'].values() if r['state'] == 'LIVE')
    assert new['state'] == 'PARTIAL' and 0 < live_now < len(new['series']), 'a partial collection, whatever its count'
    assert new['collection_started_at'] == good['collection_started_at'] and new['releases'][:len(good['releases'])] == good['releases']
    assert _status(out)['published'] == 'NEW'
    assert _artifact_checks(out, live) == ('NEWER', 'PASS', {})


@pytest.mark.parametrize('field,value', [('continuity', 'BASELINE'), ('generated_at', '2026-10-01T00:00:00Z'),
                                         ('collection_started_at', '2027-01-01T00:00:00Z'), ('previous', 'NO_LIVE'), ('state', 'LIVE')])
def test_daily_inconsistent_output_never_replaces_the_good_copy(tmp_path, monkeypatch, field, value):
    good = _good_previous(tmp_path)
    live = el.encode(good)
    real = el.build

    def bent(*a, **k):
        p = real(*a, **k)
        p[field] = value
        return p
    monkeypatch.setattr(el, 'build', bent)
    out = _daily(tmp_path, monkeypatch, 'site', previous=(good, 'LOADED'))
    assert (out / el.FILENAME).read_bytes() == live
    assert _status(out)['failure_stage'] == 'VALIDATE'
    assert _artifact_checks(out, live) == ('EQUAL', 'PASS', {})


def test_ui_deploy_preserve_never_publishes_the_placeholder_as_a_result(tmp_path):
    import macro_evidence as tool
    placeholder = el.encode(el.empty_payload(AT))
    good = _good_previous(tmp_path)
    no_good = el.encode_status(el.status_record(attempt_at=AT, result='FAILED', stage='BUILD', error_class='KeyError',
                                                published='WITHHELD', data_generated_at=None, data_sha256=None, previous='EMPTY_LIVE'))

    class Response(io.BytesIO):
        status = 200

        def __init__(self, data, url):
            super().__init__(data)
            self.url = url

        def geturl(self):
            return self.url

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def site(files):
        def opener(request, timeout):
            if request.full_url not in files:
                raise urllib.error.HTTPError(request.full_url, 404, 'nf', {}, None)
            return Response(files[request.full_url], request.full_url)
        return opener
    for name, files in (('placeholder', {tool.SOURCE: placeholder, tool.STATUS_SOURCE: no_good}), ('none', {})):
        out = _site(tmp_path, 'ui-' + name)
        assert tool.preserve(out, open_previous=site(files)) == 0
        assert not (out / el.FILENAME).exists()
        assert (out / el.STATUS_FILENAME).exists() == (name == 'placeholder')
        assert _artifact_checks(out, None)[:2] == ('NO_GOOD_LIVE', 'NO_LIVE')
    # live unreadable: the build placeholder stays and the deploy check decides (refused when a good copy is live)
    out = _site(tmp_path, 'ui-down')
    assert tool.preserve(out, open_previous=lambda r, timeout: (_ for _ in ()).throw(OSError('down'))) == 0
    assert (out / el.FILENAME).read_bytes() == placeholder or json.loads((out / el.FILENAME).read_bytes())['generated_at'] is None
    assert _artifact_checks(out, el.encode(good))[:2] == ('EMPTIED', 'REFUSED')
    # a live record that does not describe the live copy is not carried
    out = _site(tmp_path, 'ui-good')
    assert tool.preserve(out, open_previous=site({tool.SOURCE: el.encode(good), tool.STATUS_SOURCE: no_good})) == 0
    assert (out / el.FILENAME).read_bytes() == el.encode(good) and not (out / el.STATUS_FILENAME).exists()


# ---------------------------------------------------------------- the previous read, by state (owner 2026-11-07 3rd)

@pytest.fixture(autouse=True)
def _no_retry_wait(monkeypatch):
    import macro_evidence as tool
    monkeypatch.setattr(tool, '_sleep', lambda seconds: None)


class _Live:
    """A live Pages site: {url: bytes} answers 200, an exception instance is raised, anything else is a 404."""

    def __init__(self, files, fail_first=0):
        self.files, self.fail_first, self.calls = files, fail_first, []

    def __call__(self, request, timeout):
        import macro_evidence as tool
        url = request.full_url
        self.calls.append(url)
        if url == tool.SOURCE and self.calls.count(url) <= self.fail_first:
            raise urllib.error.URLError('down')
        value = self.files.get(url)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise urllib.error.HTTPError(url, 404, 'nf', {}, None)

        class Response(io.BytesIO):
            status = 200

            def geturl(self):
                return url

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return Response(value)


def _record(previous='EMPTY_LIVE'):
    return el.encode_status(el.status_record(attempt_at=AT - timedelta(days=1), result='FAILED', stage='BUILD',
                                             error_class='KeyError', published='WITHHELD', data_generated_at=None,
                                             data_sha256=None, previous=previous))


def test_previous_read_states_are_told_apart(tmp_path):
    import macro_evidence as tool
    good = _good_previous(tmp_path)
    body = el.encode(good)
    down = urllib.error.URLError('down')
    assert tool.read_previous_detail(_Live({tool.SOURCE: body}))[2:] == ('LOADED', None)
    assert tool.read_previous_detail(_Live({}))[2:] == ('NO_LIVE', None)                         # confirmed absent
    assert tool.read_previous_detail(_Live({tool.STATUS_SOURCE: _record()}))[2:] == ('REMOVED', None)
    assert tool.read_previous_detail(_Live({tool.SOURCE: el.encode(el.empty_payload(AT))}))[2:] == ('EMPTY_LIVE', None)
    assert tool.read_previous_detail(_Live({tool.SOURCE: down}))[2:] == ('UNAVAILABLE', 'OSError')  # failed read
    assert tool.read_previous_detail(_Live({tool.SOURCE: b'{"schema":'}))[2:] == ('INVALID', 'JSONDecodeError')  # damaged
    assert tool.read_previous_detail(_Live({tool.STATUS_SOURCE: down}))[2:] == ('UNAVAILABLE', 'OSError')
    # a passing failure is tried again: two failures then the good copy
    live = _Live({tool.SOURCE: body}, fail_first=2)
    assert tool.read_previous_detail(live)[2] == 'LOADED' and live.calls.count(tool.SOURCE) == 3
    live = _Live({tool.SOURCE: body}, fail_first=3)
    assert tool.read_previous_detail(live)[2] == 'UNAVAILABLE' and live.calls.count(tool.SOURCE) == 3


def _daily_live(tmp_path, monkeypatch, name, live):
    """_daily with the real previous read against `live` (no injected previous)."""
    import public_screens_pipeline as pipeline
    import macro_evidence as tool
    out = _site(tmp_path, name)

    def hook(root, manifest):
        return tool.run_from_capture(out, root, reused_root(Path(root)), environ={}, now=lambda: AT,
                                     transport=FakeTransport(responses()), open_previous=live)
    monkeypatch.setattr(pipeline, 'collect_public_inputs', lambda *a, **k: (_ for _ in ()).throw(SystemExit('after-hook')))
    with pytest.raises(SystemExit):
        pipeline.collect(out, macro_v0=lambda root: [], macro_curve=lambda root: [], macro_evidence=hook,
                         client_factory=lambda agent: None)
    return out


@pytest.mark.parametrize('case', ['unavailable', 'damaged'])
def test_a_failed_or_damaged_previous_read_never_publishes_a_new_baseline(tmp_path, monkeypatch, capsys, case):
    """Collection would succeed, but without the history it must carry: the file is withheld, the record says why,
    and a deploy that can read the good live copy says the copy leaves the site (it is not kept)."""
    import macro_evidence as tool
    good_body = el.encode(_good_previous(tmp_path))
    capsys.readouterr()
    served = {tool.SOURCE: urllib.error.URLError('down') if case == 'unavailable' else b'{"schema":'}
    out = _daily_live(tmp_path, monkeypatch, 'site', _Live(served))
    assert not (out / el.FILENAME).exists()
    status = _status(out)
    previous, error = ('UNAVAILABLE', 'OSError') if case == 'unavailable' else ('INVALID', 'JSONDecodeError')
    assert (status['attempt_result'], status['failure_stage'], status['failure_class'], status['published'], status['previous']) == \
        ('FAILED', 'PREVIOUS', error, 'WITHHELD', previous)
    printed = capsys.readouterr().out
    assert 'MACRO_EVIDENCE_STATUS result=FAILED stage=PREVIOUS' in printed and 'MACRO_EVIDENCE state=' not in printed
    # deploy: the live copy reads fine now (collect-time failure only) -> this file withheld, the good copy removed
    assert _artifact_checks(out, good_body) == ('MISSING', 'WITHHELD', {})


def test_confirmed_absence_builds_and_says_whether_history_was_lost(tmp_path, monkeypatch):
    import macro_evidence as tool
    out = _daily_live(tmp_path, monkeypatch, 'first', _Live({}))
    first = json.loads((out / el.FILENAME).read_bytes())
    assert (first['continuity'], first['previous'], _status(out)['previous']) == ('BASELINE', 'NO_LIVE', 'NO_LIVE')
    assert _artifact_checks(out, None) == ('NO_GOOD_LIVE', 'NO_LIVE', {})
    # 404 although an attempt record is live: a file was there and is gone -> a reset, never a silent first baseline
    out = _daily_live(tmp_path, monkeypatch, 'removed', _Live({tool.STATUS_SOURCE: _record()}))
    again = json.loads((out / el.FILENAME).read_bytes())
    assert (again['continuity'], again['previous'], _status(out)['previous']) == ('RESET_PREVIOUS_UNAVAILABLE', 'UNAVAILABLE', 'REMOVED')
    assert _artifact_checks(out, None) == ('NO_GOOD_LIVE', 'NO_LIVE', {})


def test_a_new_file_missing_records_never_replaces_the_good_copy(tmp_path, monkeypatch):
    """A built file that drops records or stamps an original time again fails VALIDATE (kept good copy); the same file in
    an artifact is refused by the deploy check (DISCONTINUOUS)."""
    import macro_evidence as tool
    good = _good_previous(tmp_path)
    body = el.encode(good)
    real = el.build

    def lossy(*a, **k):
        p = real(*a, **k)
        sid = next(s for s, r in p['series'].items() if r['baseline_at'] is not None)
        p['series'][sid]['baseline_at'] = '2026-10-21T00:00:00Z'      # original observation time stamped again
        return p
    monkeypatch.setattr(el, 'build', lossy)
    out = _daily_live(tmp_path, monkeypatch, 'site', _Live({tool.SOURCE: body}))
    assert (out / el.FILENAME).read_bytes() == body and _status(out)['failure_stage'] == 'VALIDATE'
    # the same lossy file straight into an artifact
    monkeypatch.setattr(el, 'build', real)
    p = real({}, previous=good, previous_state='LOADED', now=AT)      # nothing collected: every series carried
    assert tool.continues(p, good)
    sid = next(s for s, r in p['series'].items() if r['baseline_at'] is not None)
    p['series'][sid]['baseline_at'] = '2026-10-21T00:00:00Z'
    art = tmp_path / 'art'
    art.mkdir()
    (art / el.FILENAME).write_bytes(el.encode(p))
    assert _artifact_checks(art, body)[:2] == ('DISCONTINUOUS', 'REFUSED')


# ---------------------------------------------------------------- Codex #513 review (comment 6705925939) on f70d68e0

def _codex_capture(at, value):
    return {'BLS:LNS14000000': {'rows': {'2026-08': value}, 'acquired_at': at, 'release': {'at': None, 'date': None}}}


def _codex_prior():
    t0 = datetime(2026, 10, 1, tzinfo=timezone.utc)
    first = el.build(_codex_capture(t0, 4.0), previous=None, previous_state='NO_LIVE', now=t0)
    return el.build(_codex_capture(t0 + timedelta(days=1), 4.2), previous=first, previous_state='LOADED', now=t0 + timedelta(days=1))


def test_codex_review_fetch_failure_never_publishes_a_reset_over_a_good_live_copy(tmp_path, monkeypatch):
    """Review finding 1: a failed previous read must not turn into a reset that replaces the good copy. The generator now
    stops at PREVIOUS and withholds the file; a reset built anyway is refused at deploy (DISCONTINUOUS), never NEWER/PASS."""
    import macro_evidence as tool
    import pages_freshness_guard as guard
    from investment_system.providers import macro_evidence_collection as collector
    old, at = _codex_prior(), datetime(2026, 10, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(collector, 'collect_macro_evidence', lambda *a, **k: _codex_capture(at, 4.2))
    tool.emit_empty(tmp_path, now=lambda: at)
    down = lambda request, timeout: (_ for _ in ()).throw(OSError('SYNTHETIC_CONNECTION_FAILURE'))
    assert tool.run_from_capture(tmp_path, tmp_path, {}, environ={}, now=lambda: at, open_previous=down) == 1
    tool.withhold(tmp_path)                       # what public_screens_pipeline.collect does on a non-zero return
    assert not (tmp_path / el.FILENAME).exists()
    status = _status(tmp_path)
    assert (status['failure_stage'], status['failure_class'], status['published'], status['previous']) == ('PREVIOUS', 'OSError', 'WITHHELD', 'UNAVAILABLE')
    result = guard.compare_macro(('VALID', el.encode(old), old),
                                 guard._artifact_file(tmp_path, el.FILENAME, el.MAX_BYTES, el.require_macro_evidence),
                                 guard._artifact_file(tmp_path, el.STATUS_FILENAME, el.MAX_BYTES, el.require_status))
    assert (result['kind'], result['verdict'], result['live_good']) == ('MISSING', 'WITHHELD', True)   # not kept: removed
    reset = el.build(_codex_capture(at, 4.2), previous=None, previous_state='UNAVAILABLE', now=at)
    art = tmp_path / 'reset'
    art.mkdir()
    (art / el.FILENAME).write_bytes(el.encode(reset))
    result = guard.compare_macro(('VALID', el.encode(old), old), guard._artifact_file(art, el.FILENAME, el.MAX_BYTES, el.require_macro_evidence))
    assert (result['kind'], result['verdict']) == ('DISCONTINUOUS', 'REFUSED')


def test_codex_review_successor_keeps_every_history_version():
    """Review finding 2: dropping one series' revision history (2 versions -> 0) fails require_successor and the deploy check."""
    import macro_evidence as tool
    old, at = _codex_prior(), datetime(2026, 10, 3, tzinfo=timezone.utc)
    new = el.build({}, previous=old, previous_state='LOADED', now=at)
    assert len(old['series']['BLS:LNS14000000']['history']['2026-08']) == 2 and tool.continues(new, old)
    for cut in ({}, {'2026-08': old['series']['BLS:LNS14000000']['history']['2026-08'][:1]}):
        bad = copy.deepcopy(new)
        bad['series']['BLS:LNS14000000']['history'] = cut
        el.require_macro_evidence(bad)
        assert not tool.continues(bad, old)
        with pytest.raises(ValueError):
            tool.require_successor(bad, attempt_at=at, previous=old, read='LOADED')
