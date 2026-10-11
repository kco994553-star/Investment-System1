"""Macro v0 raw display of the remaining six axes. Author-created synthetic fixtures only; no network."""
from copy import deepcopy
import csv
from datetime import date, datetime, timedelta, timezone
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import parse_qsl

import pytest

from investment_system.macro import raw_axes_v0 as raw
from investment_system.product.public_engine_screens import generate_screen_bundle, require_public_screen
from investment_system.providers import macro_v0_collection as collection

NOW = datetime(2026, 10, 11, 1, tzinfo=timezone.utc)
ACQ = '2026-10-11T00:00:00+00:00'
TTL = timedelta(hours=24)
JS = Path(__file__).parents[1] / 'src/investment_system/product/web_assets/public-screens.js'
H41_TARGET = 'Assets: Total assets: Total assets (less eliminations from consolidation): Wednesday level'
H8_TARGET = 'Bank credit, all commercial banks, seasonally adjusted'


def bls(labor=(('2026', 'M09', '4.3'), ('2026', 'M10', '-'), ('2026', 'M08', '4.2'))):
    series = [{'seriesID': 'CUUR0000SA0', 'data': [{'year': y, 'period': p, 'periodName': 's', 'value': v, 'footnotes': [{}]}
                                                    for y, p, v in (('2026', 'M08', '330.0'), ('2025', 'M08', '320.0'))]},
              {'seriesID': 'LNS14000000', 'data': [{'year': y, 'period': p, 'periodName': 's', 'value': v, 'footnotes': [{}]}
                                                    for y, p, v in labor]}]
    return json.dumps({'status': 'REQUEST_SUCCEEDED', 'Results': {'series': series}}).encode()


def ddp(columns, rows):
    """columns: [(identifier, description, unit, multiplier)], rows: [(period, [values])]."""
    out = io.StringIO()
    w = csv.writer(out, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
    w.writerow(['Series Description'] + [c[1] for c in columns])
    w.writerow(['Unit:'] + [c[2] for c in columns])
    w.writerow(['Multiplier:'] + [c[3] for c in columns])
    w.writerow(['Currency:'] + ['NA' for _ in columns])
    w.writerow(['Unique Identifier: '] + [c[0] for c in columns])
    w.writerow(['Time Period'] + [c[0].rsplit('/', 1)[-1] for c in columns])
    for period, values in rows:
        w.writerow([period] + list(values))
    return out.getvalue().encode()


def weekdays(year, month):
    d = date(year, month, 1)
    while d.month == month:
        if d.weekday() < 5:
            yield d.isoformat()
        d += timedelta(days=1)


def h15(skip=(), oct_rows=True):
    rows = [(d, ['4.33']) for d in weekdays(2026, 8)]
    sep = list(weekdays(2026, 9))
    for i, d in enumerate(sep):
        if d in skip:
            continue
        rows.append((d, ['ND' if d == '2026-09-07' else '4.33' if i < 12 else '4.08']))
    if oct_rows:
        rows += [('2026-10-01', ['4.08']), ('2026-10-02', ['4.08'])]
    return ddp([('H15/H15/RIFSPFF_N.B', 'Federal funds effective rate', 'Percent:_Per_Year', '1')], rows)


def h41(target=H41_TARGET, dates=('2025-10-08', '2026-09-30', '2026-10-07'), values=('7000000', '6750000', '6700000')):
    cols = [('H41/H41/SYNTH_OTHER.WW', 'Assets: Total assets: Total assets: Wednesday level', 'Currency', '1000000'),
            ('H41/H41/SYNTH_AVG.WW', 'Assets: Total assets (less eliminations from consolidation): Week average', 'Currency', '1000000'),
            ('H41/H41/SYNTH_TA.WW', target, 'Currency', '1000000')]
    return ddp(cols, [(d, ['1', '2', v]) for d, v in zip(dates, values)])


def h8(target=H8_TARGET, base='18000'):
    cols = [('H8/H8/SYNTH_BC_NSA.M', 'Bank credit, all commercial banks, not seasonally adjusted', 'Currency', '1000000000'),
            ('H8/H8/SYNTH_BC.M', target, 'Currency', '1000000000')]
    return ddp(cols, [('2025-08', ['1', base]), ('2026-07', ['1', '18800']), ('2026-08', ['1', '18900'])])


MONTHS = ['2025-%02d' % m for m in range(7, 13)] + ['2026-%02d' % m for m in range(1, 9)]


def month_end(period):
    y, m = int(period[:4]), int(period[5:7])
    return (date(y + m // 12, m % 12 + 1, 1) - timedelta(days=1)).isoformat()


def mts(skip=(), null=(), pages='1', ambiguous=True):
    import calendar
    data = []
    for k, period in enumerate(MONTHS):
        record = month_end(period)
        fy = str(int(period[:4]) + (1 if int(period[5:7]) >= 10 else 0))
        name = calendar.month_name[int(period[5:7])]
        value = 'null' if period in null else '%.2f' % -(100 + k)
        base = {'record_date': record, 'record_fiscal_year': fy}
        if period in skip:
            continue  # No statement for that month at all.
        data.append(dict(base, classification_id='1', parent_id='0', classification_desc='FY ' + fy, current_month_dfct_sur_amt='null'))
        data.append(dict(base, classification_id='10', parent_id='1', classification_desc=name, current_month_dfct_sur_amt=value))
        if ambiguous and period == '2026-08':
            # Table 1 also lists the prior fiscal year's August under its own header.
            data.append(dict(base, classification_id='2', parent_id='0', classification_desc='FY ' + str(int(fy) - 1), current_month_dfct_sur_amt='null'))
            data.append(dict(base, classification_id='20', parent_id='2', classification_desc=name, current_month_dfct_sur_amt='-9999.00'))
    return json.dumps({'data': data, 'meta': {'count': len(data), 'total-pages': pages}, 'links': {'next': None}}).encode()


BODIES = {'Labor': ('BLS_API_V1_JSON', bls), 'Monetary Policy': ('FED_DDP_CSV', h15), 'Liquidity': ('FED_DDP_CSV', h41),
          'Credit': ('FED_DDP_CSV', h8), 'Fiscal': ('FISCALDATA_MTS_JSON', mts)}


def manifest(tmp_path, overrides=None, *, synthetic=False, acquired=ACQ):
    overrides = overrides or {}
    entries = []
    for axis, (fmt, make) in BODIES.items():
        body = overrides.get(axis, make())
        if body is False:
            continue
        name = axis.replace(' ', '_') + '.input'
        (tmp_path / name).write_bytes(body)
        entries.append({'axis': axis, 'format': fmt, 'file': name, 'acquired_at': acquired, 'synthetic': synthetic})
    return {'schema_version': 1, 'sec': [], 'macro': [], 'thirteen_f': [], 'macro_v0': entries}


def macro(tmp_path, m, as_of=NOW):
    return generate_screen_bundle(manifest=m, input_root=tmp_path, as_of=as_of, stale_after=TTL)['macro-screen.json']


def axes(tmp_path, overrides=None, **kwargs):
    return macro(tmp_path, manifest(tmp_path, overrides, **kwargs))['data']['raw_axes_v0']['axes']


def test_all_five_axes_raw_values_and_fx_excluded(tmp_path):
    out = macro(tmp_path, manifest(tmp_path))
    block = out['data']['raw_axes_v0']
    assert block['config']['marker'] == 'v0 · 원자료 표시 · 국면 판정 보류' and block['config']['status'] == 'RAW_DISPLAY_ONLY'
    assert block['regime'] == {'state': 'NOT_AVAILABLE', 'value': None, 'reason_codes': ['REGIME_JUDGEMENT_DEFERRED']}
    a = block['axes']
    assert list(a) == ['Labor', 'Monetary Policy', 'Liquidity', 'Credit', 'Fiscal', 'FX']
    # Labor: latest published month (October "-" was not collected: never filled), % / 100.
    assert (a['Labor']['period'], a['Labor']['published_value'], a['Labor']['value']) == ('2026-09', '4.3', '0.043')
    # H.15: October is in progress, so September; Labor Day (ND) is not an observation.
    mp = a['Monetary Policy']
    assert (mp['period'], mp['observation_count'], mp['published_value'], mp['value']) == ('2026-09', 21, '4.2109523810', '0.04210952381')
    li = a['Liquidity']
    assert (li['period'], li['base_period'], li['source_series_code'], li['value']) == ('2026-10-07', '2025-10-08', 'H41/H41/SYNTH_TA.WW', '-0.0428571429')
    cr = a['Credit']
    assert (cr['period'], cr['base_period'], cr['source_series_code'], cr['value']) == ('2026-08', '2025-08', 'H8/H8/SYNTH_BC.M', '0.0500000000')
    fi = a['Fiscal']
    assert (fi['period'], fi['base_period'], fi['observation_count'], fi['value'], fi['value_unit']) == ('2026-08', '2025-09', 12, '-1290.00', 'CURRENCY_AS_PUBLISHED')
    assert all(a[x]['state'] == 'LIVE' and len(a[x]['source_sha256']) == 64 and a[x]['acquired_at'] == ACQ for x in BODIES)
    assert a['FX']['state'] == 'NOT_AVAILABLE' and a['FX']['reason_codes'] == ['PUBLIC_FX_EXCLUDED'] and a['FX']['value'] is None
    assert {s['agency'] for s in out['sources']} == {'BLS', 'FED_H15', 'FED_H41', 'FED_H8', 'TREASURY_MTS'}
    require_public_screen('macro-screen.json', out)
    # No state, threshold or score keys exist anywhere in the block.
    text = json.dumps(block)
    assert all(k not in text for k in ('"threshold', '"score', '"direction', '"rule_label', '"engine'))


def test_monetary_policy_missing_weekday_is_never_filled(tmp_path):
    a = axes(tmp_path, {'Monetary Policy': h15(skip=('2026-09-15',))})['Monetary Policy']
    assert a['state'] == 'NOT_AVAILABLE' and a['reason_codes'] == ['INCOMPLETE_PERIOD'] and a['value'] is None
    # A complete newest month is used directly.
    a = axes(tmp_path, {'Monetary Policy': h15(oct_rows=False)})['Monetary Policy']
    assert a['period'] == '2026-09'
    other = ddp([('H15/H15/RIFSPFF_N.WW', 'Federal funds effective rate', 'Percent:_Per_Year', '1')], [('2026-09-02', ['4.3'])])
    assert axes(tmp_path, {'Monetary Policy': other})['Monetary Policy']['reason_codes'] == ['SERIES_NOT_FOUND']


@pytest.mark.parametrize('body,reason', [
    (h41(dates=('2025-10-01', '2026-09-30', '2026-10-07')), 'BASE_PERIOD_MISSING'),
    (h41(values=('', '6750000', '6700000')), 'BASE_PERIOD_MISSING'),
    (h41(target='Assets: Total assets (less eliminations from consolidation): Week average II'), 'SERIES_NOT_FOUND'),
    (h41(dates=('2025-10-08', '2026-09-30', '2026-10-08')), 'SCHEMA_MISMATCH'),
    (h41(values=('7000000', 'abc', '6700000')), 'INVALID_VALUE'),
    (b'<html><body>Data Download Program</body></html>', 'SCHEMA_MISMATCH'),
    (b'\xff\xfe\x00', 'SCHEMA_MISMATCH'),
])
def test_liquidity_doubt_is_not_available(tmp_path, body, reason):
    a = axes(tmp_path, {'Liquidity': body})['Liquidity']
    assert a['state'] == 'NOT_AVAILABLE' and a['reason_codes'] == [reason] and a['value'] is None and a['source_series_code'] is None


def test_credit_selects_only_the_sa_all_banks_series(tmp_path):
    assert axes(tmp_path, {'Credit': h8(target='Bank credit, small domestically chartered commercial banks, seasonally adjusted')})['Credit']['reason_codes'] == ['SERIES_NOT_FOUND']
    two = ddp([('H8/H8/A.M', H8_TARGET, 'Currency', '1'), ('H8/H8/B.M', H8_TARGET, 'Currency', '1')], [('2026-08', ['1', '1'])])
    assert axes(tmp_path, {'Credit': two})['Credit']['reason_codes'] == ['SCHEMA_MISMATCH']
    assert axes(tmp_path, {'Credit': h8(base='ND')})['Credit']['reason_codes'] == ['BASE_PERIOD_MISSING']
    growth = ddp([('H8/H8/G.M', H8_TARGET + ', annual growth rate', 'Percent', '1'), ('H8/H8/L.M', H8_TARGET, 'Currency', '1000000000')],
                 [('2025-08', ['5.0', '18000']), ('2026-08', ['4.0', '18900'])])
    assert axes(tmp_path, {'Credit': growth})['Credit']['source_series_code'] == 'H8/H8/L.M'


@pytest.mark.parametrize('body,reason', [
    (mts(skip=('2025-12',)), 'BASE_PERIOD_MISSING'),
    (mts(null=('2026-01',)), 'BASE_PERIOD_MISSING'),
    (mts(pages='2'), 'SCHEMA_MISMATCH'),
    (json.dumps({'error': 'synthetic'}).encode(), 'PROVIDER_ERROR'),
    (b'{"data": [], "meta": {}, "data": []}', 'SCHEMA_MISMATCH'),
])
def test_fiscal_window_must_be_complete(tmp_path, body, reason):
    a = axes(tmp_path, {'Fiscal': body})['Fiscal']
    assert a['state'] == 'NOT_AVAILABLE' and a['reason_codes'] == [reason] and a['value'] is None


def test_fiscal_ambiguous_month_row_fails_closed():
    body = json.loads(mts())
    for row in body['data']:
        if row['classification_desc'] == 'FY 2026' and row['record_date'] == '2026-08-31':
            row['classification_desc'] = 'Current year'
    with pytest.raises(raw.AxisUnavailable) as error:
        raw.parse_mts_months(json.dumps(body).encode())
    assert error.value.reason == 'SCHEMA_MISMATCH'
    # Without a duplicate row the own-month row is used directly.
    assert raw.fiscal(raw.parse_mts_months(mts(ambiguous=False)))['value'] == '-1290.00'


def test_synthetic_future_and_stale_inputs(tmp_path):
    assert all(r['reason_codes'] == ['SYNTHETIC_INPUT_NOT_PUBLIC'] for k, r in axes(tmp_path, synthetic=True).items() if k != 'FX')
    assert all(r['reason_codes'] == ['SOURCE_AFTER_AS_OF'] for k, r in axes(tmp_path, acquired='2026-10-12T00:00:00+00:00').items() if k != 'FX')
    stale = macro(tmp_path, manifest(tmp_path), as_of=NOW + timedelta(days=3))
    assert stale['data']['raw_axes_v0']['axes']['Credit']['state'] == 'STALE'
    require_public_screen('macro-screen.json', stale)


def test_fx_and_unknown_inputs_are_rejected(tmp_path):
    m = manifest(tmp_path)
    for bad in ({'axis': 'FX', 'reason': 'SOURCE_NOT_AVAILABLE'},
                {'axis': 'FX', 'format': 'FED_DDP_CSV', 'file': 'Credit.input', 'acquired_at': ACQ, 'synthetic': False},
                {'axis': 'Labor', 'reason': 'FREE_TEXT'},
                {'axis': 'Credit', 'format': 'BLS_API_V1_JSON', 'file': 'Credit.input', 'acquired_at': ACQ, 'synthetic': False}):
        with pytest.raises(ValueError):
            macro(tmp_path, dict(m, macro_v0=[e for e in m['macro_v0'] if e['axis'] != bad['axis']] + [bad]))
    ok = macro(tmp_path, dict(m, macro_v0=[{'axis': 'Liquidity', 'reason': 'SERIES_NOT_CONFIGURED'}]))
    assert ok['data']['raw_axes_v0']['axes']['Liquidity']['reason_codes'] == ['SERIES_NOT_CONFIGURED']
    assert ok['data']['raw_axes_v0']['axes']['Labor']['reason_codes'] == ['SOURCE_NOT_COLLECTED']


def test_batched_bls_body_serves_inflation_and_labor_once(tmp_path):
    (tmp_path / 'bls.json').write_bytes(bls())
    m = {'schema_version': 1, 'sec': [], 'macro': [], 'thirteen_f': [], 'macro_v0': [
        {'axis': a, 'format': 'BLS_API_V1_JSON', 'file': 'bls.json', 'acquired_at': ACQ, 'synthetic': False} for a in ('Inflation', 'Labor')]}
    out = macro(tmp_path, m)
    assert out['data']['growth_inflation_v0']['axes']['Inflation']['value'] == '0.0312500000'
    assert out['data']['raw_axes_v0']['axes']['Labor']['value'] == '0.043'
    assert [s['agency'] for s in out['sources']] == ['BLS']


def tamper_cases():
    return [
        lambda b: b['axes']['Labor'].update(value='0.05'),
        lambda b: b['axes']['Monetary Policy'].update(published_value='4.5'),
        lambda b: b['axes']['Monetary Policy'].update(observation_count=0),
        lambda b: b['axes']['Liquidity'].update(base_period='2025-10-01'),
        lambda b: b['axes']['Liquidity'].update(value='0.1'),
        lambda b: b['axes']['Liquidity'].update(source_series_code='H8/H8/X'),
        lambda b: b['axes']['Credit'].update(seasonal_adjustment='NSA'),
        lambda b: b['axes']['Fiscal'].update(observation_count=11),
        lambda b: b['axes']['Fiscal'].update(base_period='2025-08'),
        lambda b: b['axes']['Fiscal'].update(source_sha256='0' * 64),
        lambda b: b['axes']['FX'].update(value='0.01', state='LIVE', reason_codes=[]),
        lambda b: b['axes']['FX'].update(reason_codes=['SOURCE_NOT_COLLECTED']),
        lambda b: b['axes']['Labor'].update(state='STALE'),
        lambda b: b['axes']['Credit'].update(threshold='0.02'),
        lambda b: b['regime'].update(state='EXPANSION'),
        lambda b: b['config'].update(marker='v1 · CALIBRATED'),
        lambda b: b.update(engine={'state': 'NORMAL'}),
    ]


@pytest.mark.parametrize('change', tamper_cases())
def test_python_validator_rejects_incoherent_raw_block(tmp_path, change):
    out = macro(tmp_path, manifest(tmp_path))
    change(out['data']['raw_axes_v0'])
    with pytest.raises(ValueError, match='PUBLIC_SCREEN_INVALID'):
        require_public_screen('macro-screen.json', out)


def node_validate(payload):
    return subprocess.run(['node', '-e', "const a=require(process.argv[1]);a.validate('macro-screen.json',JSON.parse(require('fs').readFileSync(0,'utf8')))", str(JS)],
                          input=json.dumps(payload), text=True, capture_output=True).returncode


@pytest.mark.skipif(shutil.which('node') is None, reason='node is required for reader parity')
def test_browser_reader_parity_for_raw_block(tmp_path):
    good = macro(tmp_path, manifest(tmp_path))
    assert node_validate(good) == 0
    partial = macro(tmp_path, manifest(tmp_path, {'Fiscal': False, 'Credit': h8(base='ND')}))
    assert node_validate(partial) == 0
    old = macro(tmp_path, {'schema_version': 1, 'sec': [], 'macro': [], 'thirteen_f': []})
    del old['data']['raw_axes_v0']
    require_public_screen('macro-screen.json', old)
    assert node_validate(old) == 0
    # Without the block, a LIVE envelope has no live evidence left.
    orphan = deepcopy(good)
    del orphan['data']['raw_axes_v0']
    assert node_validate(orphan) != 0
    for change in tamper_cases():
        bad = deepcopy(good)
        change(bad['data']['raw_axes_v0'])
        assert node_validate(bad) != 0


POINTER = (b'The H.15 historical data is available through the Data Download Program at:\n'
           b'https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&series=0123456789abcdef0123456789abcdef'
           b'&lastobs=&from=&to=&filetype=csv&label=include&layout=seriescolumn\n')


class Transport:
    def __init__(self, fail=()):
        self.calls, self.fail = [], fail

    def __call__(self, url, *, data, query, max_bytes):
        self.calls.append((url, data, query))
        if any(f in url + (query or '') for f in self.fail):
            raise OSError('synthetic failure')
        if 'bls' in url:
            return bls()
        if 'NipaDataQ' in url:
            from tests.test_macro_growth_inflation_v0 import flat
            return flat()
        if url == collection.H15_POINTER_URL:
            return POINTER
        if url == collection.MTS_TABLE_1_URL:
            return mts()
        rel = dict(parse_qsl(query))['rel']
        return {'H15': h15, 'H41': h41, 'H8': h8}[rel]()


def clock():
    return datetime(2026, 10, 11, tzinfo=timezone.utc)


def test_collector_requests_and_entries(tmp_path):
    t = Transport()
    entries = collection.collect_macro_v0(tmp_path, environ={}, transport=t, clock=clock)
    assert [e['axis'] for e in entries] == ['Inflation', 'Labor', 'Growth', 'Monetary Policy', 'Liquidity', 'Credit', 'Fiscal']
    assert all('reason' not in e for e in entries) and not any(e['axis'] == 'FX' for e in entries)
    ddp_calls = [dict(parse_qsl(q)) for u, _, q in t.calls if u == collection.FED_DDP_URL]
    assert [c['rel'] for c in ddp_calls] == ['H15', 'H41', 'H8']
    assert ddp_calls[0]['series'] == '0123456789abcdef0123456789abcdef' and all(c['filetype'] == 'csv' for c in ddp_calls)
    for url, _, query in t.calls:
        assert url in collection.ALLOWED and collection._query_allowed(url, query)
    m = {'schema_version': 1, 'sec': [], 'macro': [], 'thirteen_f': [], 'macro_v0': entries}
    out = macro(tmp_path, m)
    assert {k: r['state'] for k, r in out['data']['raw_axes_v0']['axes'].items()} == {
        'Labor': 'LIVE', 'Monetary Policy': 'LIVE', 'Liquidity': 'LIVE', 'Credit': 'LIVE', 'Fiscal': 'LIVE', 'FX': 'NOT_AVAILABLE'}


def test_collector_failures_are_reason_only(tmp_path, monkeypatch):
    entries = collection.collect_macro_v0(tmp_path, environ={}, transport=Transport(fail=('H15_FF_O', 'rel=H8', 'fiscaldata')), clock=clock)
    reasons = {e['axis']: e.get('reason') for e in entries}
    assert reasons['Monetary Policy'] == reasons['Credit'] == reasons['Fiscal'] == 'SOURCE_NOT_AVAILABLE' and reasons['Liquidity'] is None
    monkeypatch.setitem(collection.FED_DDP_PACKAGES, 'Liquidity', None)
    entries = collection.collect_macro_v0(tmp_path, environ={}, transport=Transport(), clock=clock)
    assert {'axis': 'Liquidity', 'reason': 'SERIES_NOT_CONFIGURED'} in entries
    with pytest.raises(collection.MacroV0FetchError):
        collection.h15_package(b'no link here')
    two = POINTER + POINTER.replace(b'0123456789abcdef0123456789abcdef', b'f' * 32)
    with pytest.raises(collection.MacroV0FetchError):
        collection.h15_package(two)


@pytest.mark.parametrize('url,query', [
    (collection.FED_DDP_URL, 'rel=H10&series=' + '0' * 32 + '&filetype=csv'),
    (collection.FED_DDP_URL, 'rel=H15&series=' + '0' * 32 + '&filetype=sdmx'),
    (collection.FED_DDP_URL, 'rel=H15&series=nothex&filetype=csv'),
    (collection.FED_DDP_URL, 'rel=H15&series=' + '0' * 32 + '&filetype=csv&extra=1'),
    (collection.MTS_TABLE_1_URL, 'fields=x&callback=y'),
    (collection.H15_POINTER_URL, 'a=b'),
    ('https://www.federalreserve.gov/releases/h10/current/', None),
])
def test_default_transport_rejects_unlisted_requests(url, query):
    with pytest.raises(collection.MacroV0FetchError, match='URL_NOT_ALLOWED'):
        collection.default_transport(url, data=None, query=query, max_bytes=10)


def test_pipeline_keeps_raw_captures_private(tmp_path):
    sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
    from public_screens_pipeline import collect
    from tests.test_public_sec_inputs import raw as sec_raw

    class Client:
        def __init__(self, _): pass

        def collect(self, company, cik):
            return *(json.dumps(x).encode() for x in sec_raw(company)), datetime(2026, 10, 10, 12, tzinfo=timezone.utc)

    collect(tmp_path, environ={'SEC_USER_AGENT': 'synthetic setting'}, client_factory=Client,
            macro_v0=lambda root: collection.collect_macro_v0(root, environ={}, transport=Transport(), clock=clock))
    assert not any(p.name.startswith('macro-v0-') for p in tmp_path.iterdir())
    payload = json.loads((tmp_path / 'macro-screen.json').read_text())
    require_public_screen('macro-screen.json', payload)
    assert payload['data']['raw_axes_v0']['axes']['Fiscal']['state'] in ('LIVE', 'STALE')
    assert payload['data']['raw_axes_v0']['axes']['FX']['reason_codes'] == ['PUBLIC_FX_EXCLUDED']
