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


def test_core_adds_nothing_to_the_pages_artifact(tmp_path):
    """Approval-free core: the collector and contract exist, but the Pages build publishes no macro-evidence file and the
    unchanged guard passes. Publication (guard registration, screen) is the separate approval-required change."""
    import build_pages_cockpit
    import pages_artifact_guard as guard
    out = tmp_path / 'site'
    build_pages_cockpit.build_public_cockpit(out)
    assert not any(p.name.startswith('macro-evidence') for p in out.iterdir())
    assert el.FILENAME not in guard.ALLOWED_NAMES
    assert guard.scan_artifact(out)['pages_artifact_guard'] == 'PASS'
