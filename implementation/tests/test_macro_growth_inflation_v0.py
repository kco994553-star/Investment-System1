"""Macro v0 Growth/Inflation axes. Author-created synthetic fixtures only; no network."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from investment_system.macro import growth_inflation_v0 as v0
from investment_system.providers import macro_v0_collection as mc
from investment_system.product.public_engine_screens import generate_screen_bundle, require_public_screen
from investment_system.providers.macro_v0_collection import collect_macro_v0

NOW = datetime(2026, 10, 11, 1, tzinfo=timezone.utc)
ACQ = '2026-10-11T00:00:00+00:00'
TTL = timedelta(hours=24)
JS = Path(__file__).parents[1] / 'src/investment_system/product/web_assets/public-screens.js'
SECRET = 'SYNTHETIC_PRIVATE_KEY_CANARY'


def flat(rows=(('A191RL', '2026Q1', '-0.6'), ('A191RL', '2026Q2', '3.8')), header='%SeriesCode%,Period,Value'):
    lines = [header, 'A191RC,2026Q2,"31,000.1"', 'A191RLX,2026Q3,9.9']
    lines += [','.join(r) for r in rows]
    return ('\n'.join(lines) + '\n').encode()


def cpi(rows=(('2026', 'M08', '330.000'), ('2025', 'M08', '320.000'), ('2025', 'M10', '-')), status='REQUEST_SUCCEEDED'):
    data = [{'year': y, 'period': p, 'periodName': 'synthetic', 'value': v, 'footnotes': [{}]} for y, p, v in rows]
    return json.dumps({'status': status, 'Results': {'series': [{'seriesID': 'CUUR0000SA0', 'data': data}]}}).encode()


def manifest(tmp_path, growth=None, inflation=None, *, gfmt='BEA_NIPA_FLAT_Q', synthetic=False, acquired=ACQ):
    entries = []
    for axis, body, fmt, name in (('Growth', flat() if growth is None else growth, gfmt, 'g.input'),
                                  ('Inflation', cpi() if inflation is None else inflation, 'BLS_API_V1_JSON', 'i.input')):
        if body is False:
            continue
        (tmp_path / name).write_bytes(body)
        entries.append({'axis': axis, 'format': fmt, 'file': name, 'acquired_at': acquired, 'synthetic': synthetic})
    return {'schema_version': 1, 'sec': [], 'macro': [], 'thirteen_f': [], 'macro_v0': entries}


def macro(tmp_path, m, as_of=NOW):
    return generate_screen_bundle(manifest=m, input_root=tmp_path, as_of=as_of, stale_after=TTL)['macro-screen.json']


def block(tmp_path, *args, **kwargs):
    return macro(tmp_path, manifest(tmp_path, *args, **kwargs))['data']['growth_inflation_v0']


def test_growth_is_published_annualized_percent_over_100_without_recompute(tmp_path):
    g = block(tmp_path)['axes']['Growth']
    assert (g['state'], g['period'], g['published_percent'], g['value']) == ('LIVE', '2026Q2', '3.8', '0.038')
    assert (g['source_series_id'], g['source_series_code'], g['seasonal_adjustment']) == ('BEA:NIPA:T10101:1:Q', 'A191RL', 'SAAR')
    assert g['acquired_at'] == ACQ and len(g['source_sha256']) == 64 and g['release_at'] is None


def test_inflation_is_nsa_index_yoy_and_missing_month_is_never_filled(tmp_path):
    i = block(tmp_path)['axes']['Inflation']
    assert (i['period'], i['base_period'], i['index_value'], i['base_index_value']) == ('2026-08', '2025-08', '330.000', '320.000')
    assert Decimal(i['value']) == Decimal('0.03125') and i['seasonal_adjustment'] == 'NSA'
    # The base month was published as "-" (not collected): NOT_AVAILABLE, no interpolation or 0.
    i = block(tmp_path, inflation=cpi((('2026', 'M10', '331.0'), ('2025', 'M10', '-'), ('2025', 'M09', '321.0'))))['axes']['Inflation']
    assert i['state'] == 'NOT_AVAILABLE' and i['value'] is None and i['reason_codes'] == ['BASE_MONTH_MISSING']
    i = block(tmp_path, inflation=cpi((('2026', 'M08', '330.0'),)))['axes']['Inflation']
    assert i['reason_codes'] == ['BASE_MONTH_MISSING'] and i['index_value'] is None


@pytest.mark.parametrize('growth,inflation,state,label', [
    ('3.8', ('330.0', '322.0'), 'NORMAL', 'EXPANSION'),
    ('-1.2', ('340.0', '320.0'), 'WARNING', 'STAGFLATION_RISK'),
    ('2.0', ('350.0', '320.0'), 'EMERGENCY', 'INFLATION_SHOCK'),
    ('1.0', ('330.0', '320.0'), 'NORMAL', 'NEUTRAL'),
])
def test_existing_engine_thresholds_only_and_regime_stays_not_available(tmp_path, growth, inflation, state, label):
    b = block(tmp_path, flat((('A191RL', '2026Q2', growth),)), cpi((('2026', 'M08', inflation[0]), ('2025', 'M08', inflation[1]))))
    assert (b['engine']['state'], b['engine']['rule_label'], b['engine']['version']) == (state, label, 'v0.1.1')
    assert b['regime'] == {'state': 'NOT_AVAILABLE', 'value': None, 'reason_codes': ['EIGHT_AXIS_MAPPING_NOT_ADOPTED']}
    assert b['config']['marker'] == 'v0 · UNCALIBRATED' and b['config']['calibration'] == 'UNCALIBRATED'


def test_one_missing_axis_never_reaches_engine_defaults(tmp_path):
    out = macro(tmp_path, manifest(tmp_path, inflation=False))
    b = out['data']['growth_inflation_v0']
    assert b['axes']['Inflation']['reason_codes'] == ['SOURCE_NOT_COLLECTED'] and b['axes']['Growth']['state'] == 'LIVE'
    assert b['engine'] == {'name': 'MacroEngine', 'version': 'v0.1.1', 'state': 'NOT_AVAILABLE', 'rule_label': None, 'reason_codes': ['AXIS_NOT_AVAILABLE']}
    assert out['state'] == 'LIVE'
    empty = generate_screen_bundle(manifest={'schema_version': 1, 'sec': [], 'macro': [], 'thirteen_f': []}, input_root=tmp_path, as_of=NOW, stale_after=TTL)['macro-screen.json']
    assert empty['state'] == 'NOT_AVAILABLE' and empty['data']['growth_inflation_v0']['engine']['state'] == 'NOT_AVAILABLE'


@pytest.mark.parametrize('body,reason', [
    (flat(header='Series,Period,Value'), 'SCHEMA_MISMATCH'),
    (flat((('A191RL', '2026Q2', 'abc'),)), 'INVALID_VALUE'),
    (flat((('A191RL', '2026Q2', '3.8'), ('A191RL', '2026Q2', '3.9'))), 'CONFLICTING_DUPLICATE'),
    (flat((('A191RL', '2026-06', '3.8'),)), 'SCHEMA_MISMATCH'),
    (flat((('A191RL', '2026Q2', '(NA)'),)), 'MISSING_SOURCE'),
    (flat(()), 'MISSING_SOURCE'),
    (b'\xff\xfe', 'SCHEMA_MISMATCH'),
])
def test_growth_flat_file_doubt_is_not_available(tmp_path, body, reason):
    g = block(tmp_path, growth=body)['axes']['Growth']
    assert g['state'] == 'NOT_AVAILABLE' and g['reason_codes'] == [reason] and g['value'] is None


def test_growth_skips_published_missing_quarter_and_uses_latest_value(tmp_path):
    g = block(tmp_path, flat((('A191RL', '2026Q1', '1.5'), ('A191RL', '2026Q2', '---'))))['axes']['Growth']
    assert (g['period'], g['value']) == ('2026Q1', '0.015')


def test_bea_api_fallback_uses_t10101_line1_a191rl(tmp_path):
    from tests.test_macro_primary_input import bea_payload
    p = bea_payload('T10101', '3.8'); p['BEAAPI']['Results']['Data'][0].update(SeriesCode='A191RL', TimePeriod='2026Q2')
    b = block(tmp_path, json.dumps(p).encode(), gfmt='BEA_API_NIPA_JSON')
    assert b['axes']['Growth']['value'] == '0.038' and 'SYNTHETIC_PRIVATE_SENTINEL' not in json.dumps(b)
    p['BEAAPI']['Results']['Data'][0]['SeriesCode'] = 'OTHER'
    assert block(tmp_path, json.dumps(p).encode(), gfmt='BEA_API_NIPA_JSON')['axes']['Growth']['reason_codes'] == ['SCHEMA_MISMATCH']


def test_bls_provider_error_synthetic_and_future_capture_are_not_public(tmp_path):
    assert block(tmp_path, inflation=cpi(status='REQUEST_NOT_PROCESSED'))['axes']['Inflation']['reason_codes'] == ['PROVIDER_ERROR']
    b = block(tmp_path, synthetic=True)
    assert all(r['reason_codes'] == ['SYNTHETIC_INPUT_NOT_PUBLIC'] for r in b['axes'].values())
    b = block(tmp_path, acquired='2026-10-12T00:00:00+00:00')
    assert all(r['reason_codes'] == ['SOURCE_AFTER_AS_OF'] for r in b['axes'].values())
    stale = macro(tmp_path, manifest(tmp_path), as_of=NOW + timedelta(days=3))
    assert stale['state'] == 'STALE' and stale['data']['growth_inflation_v0']['axes']['Growth']['state'] == 'STALE'


def test_reason_only_manifest_entries(tmp_path):
    m = {'schema_version': 1, 'sec': [], 'macro': [], 'thirteen_f': [], 'macro_v0': [{'axis': 'Growth', 'reason': 'SOURCE_KEY_NOT_CONFIGURED'}]}
    g = macro(tmp_path, m)['data']['growth_inflation_v0']['axes']['Growth']
    assert g['reason_codes'] == ['SOURCE_KEY_NOT_CONFIGURED'] and g['source_sha256'] is None
    # FX is never collected for public output; reason codes are fixed per axis family.
    for bad in ({'axis': 'Growth', 'reason': 'FREE_TEXT'}, {'axis': 'FX', 'reason': 'SOURCE_NOT_AVAILABLE'},
                {'axis': 'Growth', 'reason': 'SERIES_NOT_CONFIGURED'}):
        with pytest.raises(ValueError):
            macro(tmp_path, dict(m, macro_v0=[bad]))


def tamper_cases():
    return [
        lambda b: b['axes']['Growth'].update(value='0.04'),
        lambda b: b['axes']['Inflation'].update(value='0.0400000000'),
        lambda b: b['axes']['Inflation'].update(base_period='2025-07'),
        lambda b: b['axes']['Growth'].update(source_sha256='0' * 64),
        lambda b: b['axes']['Growth'].update(source_series_id='BEA:NIPA:T10106:1:Q'),
        lambda b: b['axes']['Inflation'].update(seasonal_adjustment='SA'),
        lambda b: b['axes']['Growth'].update(state='NOT_AVAILABLE'),
        lambda b: b['axes']['Growth'].update(state='STALE'),
        lambda b: b['axes']['Growth'].update(price='1'),
        lambda b: b['engine'].update(state='EMERGENCY'),
        lambda b: b['engine'].update(rule_label='EXPANSION', state='NOT_AVAILABLE'),
        lambda b: b['regime'].update(state='EXPANSION'),
        lambda b: b['config'].update(marker='v1 · CALIBRATED'),
    ]


@pytest.mark.parametrize('change', tamper_cases())
def test_python_validator_rejects_incoherent_v0_block(tmp_path, change):
    out = macro(tmp_path, manifest(tmp_path)); require_public_screen('macro-screen.json', out)
    change(out['data']['growth_inflation_v0'])
    with pytest.raises(ValueError, match='PUBLIC_SCREEN_INVALID'):
        require_public_screen('macro-screen.json', out)


def test_previous_payload_without_v0_block_still_validates(tmp_path):
    out = macro(tmp_path, manifest(tmp_path, growth=False, inflation=False))
    del out['data']['growth_inflation_v0']
    require_public_screen('macro-screen.json', out)


def node_validate(payload):
    return subprocess.run(['node', '-e', "const a=require(process.argv[1]);a.validate('macro-screen.json',JSON.parse(require('fs').readFileSync(0,'utf8')))", str(JS)],
                          input=json.dumps(payload), text=True, capture_output=True).returncode


@pytest.mark.skipif(shutil.which('node') is None, reason='node is required for reader parity')
def test_browser_reader_parity_for_v0_block(tmp_path):
    good = macro(tmp_path, manifest(tmp_path))
    assert node_validate(good) == 0
    partial = macro(tmp_path, manifest(tmp_path, inflation=False))
    assert node_validate(partial) == 0
    old = macro(tmp_path, manifest(tmp_path, growth=False, inflation=False)); del old['data']['growth_inflation_v0']
    assert node_validate(old) == 0
    # Without the block, a LIVE envelope has no live evidence left.
    orphan = deepcopy(partial); del orphan['data']['growth_inflation_v0']
    assert node_validate(orphan) != 0
    for change in tamper_cases():
        bad = deepcopy(good); change(bad['data']['growth_inflation_v0'])
        assert node_validate(bad) != 0


class Transport:
    def __init__(self, fail=()):
        self.calls, self.fail = [], fail

    def __call__(self, url, *, data, query, max_bytes):
        self.calls.append((url, data, query))
        if any(f in url for f in self.fail):
            raise OSError('synthetic failure with ' + url)
        if 'bls' in url:
            return cpi()
        if 'NipaDataQ' in url:
            return flat()
        if 'federalreserve' in url or 'fiscaldata' in url:
            raise OSError('synthetic: raw axes are covered by test_macro_raw_axes_v0')
        from tests.test_macro_primary_input import bea_payload
        p = bea_payload('T10101', '3.8'); p['BEAAPI']['Results']['Data'][0].update(SeriesCode='A191RL', TimePeriod='2026Q2')
        return json.dumps(p).encode()


def clock():
    return datetime(2026, 10, 11, tzinfo=timezone.utc)


def test_collector_uses_fixed_series_and_flat_file_without_key(tmp_path):
    t = Transport()
    entries = collect_macro_v0(tmp_path, environ={}, transport=t, clock=clock)
    assert [(e['axis'], e.get('format')) for e in entries][:3] == [('Inflation', 'BLS_API_V1_JSON'), ('Labor', 'BLS_API_V1_JSON'), ('Growth', 'BEA_NIPA_FLAT_Q')]
    # One batched BLS v1 request serves Inflation and Labor (same captured body).
    assert json.loads(t.calls[0][1]) == {'seriesid': ['CUUR0000SA0', 'LNS14000000'], 'startyear': '2024', 'endyear': '2026'}
    assert entries[0]['file'] == entries[1]['file'] and sum('bls' in c[0] for c in t.calls) == 1
    assert t.calls[1][0] == v0.BEA_FLAT_Q_URL


def test_collector_key_fallback_and_never_exposes_key(tmp_path, capsys):
    growth = lambda entries: [e for e in entries if e['axis'] == 'Growth']
    entries = collect_macro_v0(tmp_path, environ={}, transport=Transport(fail=('NipaDataQ',)), clock=clock)
    assert growth(entries) == [{'axis': 'Growth', 'reason': 'SOURCE_KEY_NOT_CONFIGURED'}]
    t = Transport(fail=('NipaDataQ',))
    entries = collect_macro_v0(tmp_path, environ={'BEA_USERID': SECRET}, transport=t, clock=clock)
    assert growth(entries)[0]['format'] == 'BEA_API_NIPA_JSON' and any(c[2] and 'TableName=T10101' in c[2] for c in t.calls)
    assert SECRET not in json.dumps(entries) and SECRET not in capsys.readouterr().out
    entries = collect_macro_v0(tmp_path, environ={'BEA_USERID': SECRET}, transport=Transport(fail=('NipaDataQ', 'api/data', 'bls')), clock=clock)
    assert [e for e in entries if e['axis'] in ('Inflation', 'Labor', 'Growth')] == [{'axis': 'Inflation', 'reason': 'SOURCE_NOT_AVAILABLE'}, {'axis': 'Labor', 'reason': 'SOURCE_NOT_AVAILABLE'}, {'axis': 'Growth', 'reason': 'SOURCE_NOT_AVAILABLE'}]


def test_default_transport_rejects_unlisted_urls():
    from investment_system.providers.macro_v0_collection import MacroV0FetchError, default_transport
    with pytest.raises(MacroV0FetchError):
        default_transport('https://example.com/prices', data=None, query=None, max_bytes=10)


def test_pipeline_publishes_v0_projection_and_no_raw_capture(tmp_path):
    sys.path.insert(0, str(Path(__file__).parents[1] / 'tools'))
    from public_screens_pipeline import collect
    from tests.test_public_sec_inputs import raw

    class Client:
        def __init__(self, _): pass

        def collect(self, company, cik):
            return *(json.dumps(x).encode() for x in raw(company)), datetime(2026, 10, 10, 12, tzinfo=timezone.utc)

    t = Transport()
    collect(tmp_path, environ={'SEC_USER_AGENT': 'synthetic setting'}, client_factory=Client,
            macro_v0=lambda root: collect_macro_v0(root, environ={'BEA_USERID': SECRET}, transport=t, clock=clock))
    names = sorted(p.name for p in tmp_path.iterdir())
    assert not any(n.startswith('macro-v0-') for n in names)
    payload = json.loads((tmp_path / 'macro-screen.json').read_text())
    require_public_screen('macro-screen.json', payload)
    assert payload['data']['growth_inflation_v0']['axes']['Growth']['source_series_code'] == 'A191RL'
    assert SECRET not in (tmp_path / 'macro-screen.json').read_text()


def test_fed_fetch_failures_are_logged_as_fixed_tokens_only(tmp_path):
    class FedFail(Transport):
        def __call__(self, url, *, data, query, max_bytes):
            if 'federalreserve' in url:
                if 'H15_FF_O' in url:
                    raise mc.MacroV0FetchError('FETCH_FAILED')
                raise mc.MacroV0FetchError('HTTP_STATUS', status=404, content='HTML')
            return super().__call__(url, data=data, query=query, max_bytes=max_bytes)
    diagnostics = []
    entries = collect_macro_v0(tmp_path, environ={'BEA_USERID': SECRET}, transport=FedFail(), clock=clock, diagnostics=diagnostics)
    assert {e['axis']: e.get('reason') for e in entries if e['axis'] in ('Liquidity', 'Credit', 'Monetary Policy')} == {
        'Liquidity': 'SOURCE_NOT_AVAILABLE', 'Credit': 'SOURCE_NOT_AVAILABLE', 'Monetary Policy': 'SOURCE_NOT_AVAILABLE'}
    by = {d['axis']: d for d in diagnostics}
    assert by['Monetary Policy'] == {'axis': 'Monetary Policy', 'stage': 'H15_POINTER', 'code': 'FETCH_FAILED', 'http': None,
                                     'content': None, 'size': None, 'rel': None, 'series8': None, 'type': None}
    assert by['Liquidity']['stage'] == 'DDP_PACKAGE' and by['Liquidity']['code'] == 'HTTP_STATUS' and by['Liquidity']['http'] == 404
    assert by['Liquidity']['content'] == 'HTML' and by['Liquidity']['rel'] == 'H41' and by['Liquidity']['type'] == 'series'
    assert by['Credit']['rel'] == 'H8' and by['Credit']['type'] == 'package' and len(by['Credit']['series8']) == 8
    text = json.dumps(diagnostics)
    assert SECRET not in text and 'http' not in text.replace('"http"', '') and mc.FED_DDP_PACKAGES['Credit']['series'] not in text


def test_content_and_size_classes_are_fixed_tokens():
    assert mc._content_class('text/csv; charset=utf-8') == 'CSV' and mc._content_class('text/html') == 'HTML'
    assert mc._content_class(None) == 'NONE' and mc._content_class('application/octet-stream') == 'OTHER'
    assert [mc._size_class(n) for n in (0, 10, 5000, 100000, 2000000)] == ['0', '<1KB', '<64KB', '<1MB', '>=1MB']
