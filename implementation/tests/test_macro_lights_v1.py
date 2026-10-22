"""Macro lights v1 (PLAYBOOK_V1 13-5). Author-created synthetic fixtures only; no network."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import parse_qsl

import pytest

from investment_system.macro import macro_lights_v1 as ml
from investment_system.macro import macro_lights_public as mlp
from investment_system.product.public_engine_screens import generate_screen_bundle, require_public_screen
from investment_system.providers import macro_v0_collection as collection

ROOT = Path(__file__).parents[1]
NOW = datetime(2026, 10, 11, 1, tzinfo=timezone.utc)
ACQ = '2026-10-11T00:00:00+00:00'
TTL = timedelta(hours=24)
JS = ROOT / 'src/investment_system/product/web_assets/public-screens.js'
sys.path.insert(0, str(ROOT / 'tools'))


def months_back(n, end=(2026, 9)):
    y, m = end
    out = []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def bls(unrate=None, cpi=None):
    """Synthetic BLS v1 body: 15 months of unemployment (4.0 then rising) and CPI 100 → 106 over 12 months."""
    periods = months_back(15)
    unrate = unrate or ([4.0] * 12 + [4.5, 4.6, 4.7])
    cpi = cpi or {(2025, 9): '100.0', (2026, 9): '106.0'}
    lab = [{'year': str(y), 'period': 'M%02d' % m, 'periodName': 's', 'value': v if isinstance(v, str) else '%.1f' % v, 'footnotes': [{}]}
           for (y, m), v in zip(periods, unrate)]
    cp = [{'year': str(y), 'period': 'M%02d' % m, 'periodName': 's', 'value': v, 'footnotes': [{}]} for (y, m), v in cpi.items()]
    return json.dumps({'status': 'REQUEST_SUCCEEDED', 'Results': {'series': [
        {'seriesID': 'CUUR0000SA0', 'data': cp}, {'seriesID': 'LNS14000000', 'data': lab}]}}).encode()


def treasury_xml(rows):
    """rows: [(date, 3-month text or None, 10-year text or None)] → synthetic Atom feed like the Treasury XML."""
    def field(name, value):
        if value is None:
            return '<d:%s m:null="true" />' % name
        return '<d:%s m:type="Edm.Double">%s</d:%s>' % (name, value, name)
    entries = ''.join('<entry><content type="application/xml"><m:properties><d:NEW_DATE m:type="Edm.DateTime">%sT00:00:00</d:NEW_DATE>%s%s%s</m:properties></content></entry>'
                      % (d, field('BC_1MONTH', '4.00'), field('BC_3MONTH', m3), field('BC_10YEAR', y10)) for d, m3, y10 in rows)
    return ('<?xml version="1.0" encoding="utf-8" standalone="yes"?><feed xmlns="http://www.w3.org/2005/Atom" '
            'xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" '
            'xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"><title>synthetic</title>%s</feed>' % entries).encode()


def weekdays(start, end):
    d, out = date.fromisoformat(start), []
    while d <= date.fromisoformat(end):
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def curve_years(inverted_from='2026-09-01'):
    prev = [(d, '4.50', '4.80') for d in weekdays('2025-01-02', '2025-12-31')]
    cur = [(d, '4.50', '4.20' if d >= inverted_from else '4.80') for d in weekdays('2026-01-02', '2026-10-09')]
    return treasury_xml(prev), treasury_xml(cur)


def manifest(tmp_path, *, bls_body=None, curves=None, curve_entries=None):
    m = {'schema_version': 1, 'sec': [], 'macro': [], 'thirteen_f': []}
    if bls_body is not False:
        (tmp_path / 'b.input').write_bytes(bls_body or bls())
        m['macro_v0'] = [{'axis': a, 'format': 'BLS_API_V1_JSON', 'file': 'b.input', 'acquired_at': ACQ, 'synthetic': False} for a in ('Inflation', 'Labor')]
    if curve_entries is not None:
        m['macro_curve_v1'] = curve_entries
    elif curves is not False:
        entries = []
        for i, body in enumerate(curves or curve_years()):
            (tmp_path / ('c%d.input' % i)).write_bytes(body)
            entries.append({'format': mlp.CURVE_FORMAT, 'file': 'c%d.input' % i, 'acquired_at': ACQ, 'synthetic': False})
        m['macro_curve_v1'] = entries
    return m


def macro(tmp_path, m, as_of=NOW):
    return generate_screen_bundle(manifest=m, input_root=tmp_path, as_of=as_of, stale_after=TTL)['macro-screen.json']


def node_validate(payload):
    return subprocess.run(['node', '-e', "const a=require(process.argv[1]);a.validate('macro-screen.json',JSON.parse(require('fs').readFileSync(0,'utf8')))", str(JS)],
                          input=json.dumps(payload), text=True, capture_output=True).returncode


def test_config_is_v1_uncalibrated_and_never_for_selling():
    raw = json.loads((ROOT / 'src/investment_system/macro/macro_lights_v1.json').read_text())
    assert raw == ml.CONFIG and (raw['version'], raw['status'], raw['marker']) == ('v1', 'UNCALIBRATED', 'v1 · UNCALIBRATED')
    assert raw['sell_decisions'] is False and raw['source_section'] == 'PLAYBOOK_V1 13-5'
    assert raw['lights']['employment']['gap_pp_gte'] == 0.5 and raw['lights']['inflation']['yoy_gt'] == 0.05
    assert raw['lights']['curve']['min_run_days'] == 20 and raw['lights']['market']['drawdown_lte'] == -0.2
    assert raw['lights']['market']['rv_top_share'] == 0.05 and raw['lights']['market']['rv_history_years'] == 3
    assert raw['lights']['credit']['change_lte'] == -0.05 and raw['lights']['credit']['window_sessions'] == 20 and raw['lights']['credit']['estimate'] is True
    assert raw['state']['crisis_inflation_gt'] == 0.08 and raw['state']['low_confidence_available_lt'] == 3
    assert raw['state']['crisis_inflation_other_lit_min'] == 1
    assert [(r['id'], r['decided_on'], r['source_section']) for r in raw['revisions']] == [('M-RULE-C', '2026-10-15', 'PLAYBOOK_V1 18')]
    assert raw['revisions'][0]['status'] == 'HYPOTHESIS' and raw['revisions'][0]['text'].startswith('가설(검증 중)')


def _lights(**on):
    return {name: on.get(name, False) for name in ml.LIGHTS}


def test_m_rule_c_inflation_over_8_alone_is_warning():
    s = ml.macro_state(_lights(inflation=True), 0.09, 0.03)
    assert (s['state'], s['reasons'], s['lit_count']) == ('WARNING', ['INFLATION_GT_8PCT_ALONE'], 1)
    s = ml.macro_state(_lights(inflation=True), 0.12, -0.01)
    assert (s['state'], s['reasons']) == ('WARNING', ['INFLATION_GT_8PCT_ALONE', 'INFLATION_GT_5PCT_AND_GROWTH_LT_0'])
    # Unavailable lights are not "other lit": still a warning (with low confidence).
    s = ml.macro_state({'inflation': True}, 0.09, 0.03)
    assert (s['state'], s['reasons']) == ('WARNING', ['INFLATION_GT_8PCT_ALONE', 'AVAILABLE_LT_3'])


@pytest.mark.parametrize('other', ['employment', 'curve', 'market', 'credit'])
def test_m_rule_c_inflation_over_8_with_another_light_is_crisis(other):
    s = ml.macro_state(_lights(inflation=True, **{other: True}), 0.09, 0.03)
    assert (s['state'], s['reasons'], s['lit_count']) == ('CRISIS', ['INFLATION_GT_8PCT_WITH_OTHER_LIT'], 2)
    s = ml.macro_state(_lights(inflation=True, **{other: True}), 0.08, 0.03)  # exactly 8 % is not > 8 %
    assert (s['state'], s['reasons']) == ('WARNING', ['LIT_COUNT_EQ_2'])


def test_m_rule_c_leaves_other_state_rules_unchanged():
    cases = [(_lights(), 0.02, 0.02, 'NORMAL', ['LIT_COUNT_LE_1']),
             (_lights(employment=True), 0.02, 0.02, 'NORMAL', ['LIT_COUNT_LE_1']),
             (_lights(employment=True, curve=True), 0.02, 0.02, 'WARNING', ['LIT_COUNT_EQ_2']),
             (_lights(employment=True, curve=True, market=True), 0.02, 0.02, 'CRISIS', ['LIT_COUNT_GE_3']),
             (_lights(market=True, credit=True), 0.02, 0.02, 'CRISIS', ['MARKET_AND_CREDIT_LIT']),
             (_lights(inflation=True), 0.06, -0.01, 'WARNING', ['INFLATION_GT_5PCT_AND_GROWTH_LT_0']),
             (_lights(inflation=True), 0.06, 0.01, 'NORMAL', ['LIT_COUNT_LE_1']),
             (_lights(employment=True, inflation=True, curve=True), 0.09, 0.03, 'CRISIS', ['LIT_COUNT_GE_3', 'INFLATION_GT_8PCT_WITH_OTHER_LIT'])]
    for lights, cpi, growth, state, reasons in cases:
        s = ml.macro_state(lights, cpi, growth)
        assert (s['state'], s['reasons']) == (state, reasons), (lights, cpi, growth)


def test_m_rule_c_replay_tool_2022_shape_is_warning_not_crisis(tmp_path, capsys):
    """Synthetic 2022-like path (CPI YoY ~ 9 %, other public lights off): the repo replay tool now reports warning, no crisis."""
    import macro_lights_replay as replay
    months = ['%04d-%02d-01' % (y, m) for y in range(2027, 2031) for m in range(1, 13)]
    (tmp_path / 'u.csv').write_text('DATE,UNRATE\n' + ''.join('%s,4.0\n' % d for d in months))
    (tmp_path / 'c.csv').write_text('DATE,CPI\n' + ''.join('%s,%.4f\n' % (d, 100 * 1.09 ** (i / 12)) for i, d in enumerate(months)))
    (tmp_path / 'g.csv').write_text('DATE,G\n' + ''.join('%s,1.0\n' % d for d in months[::3]))
    (tmp_path / 't.csv').write_text('DATE,T10Y3M\n' + ''.join('%s,0.5\n' % d for d in weekdays('2028-01-03', '2030-12-31')))
    data = {k: replay.read_series([str(tmp_path / f)]) for k, f in (('unrate', 'u.csv'), ('cpi', 'c.csv'), ('gdp', 'g.csv'), ('curve', 't.csv'))}
    data.update(spy={}, hyg={}, ief={})
    states = {replay.evaluate(date.fromisoformat(d), data)[1]['state'] for d in weekdays('2029-03-01', '2029-12-31')}
    assert states == {'WARNING'}
    lights, state, cpi, _ = replay.evaluate(date(2029, 6, 1), data)
    assert cpi > 0.08 and lights['inflation']['lit'] is True and state['reasons'] == ['INFLATION_GT_8PCT_ALONE']


def test_vectors_are_current_python_reference():
    import macro_lights_reference as ref
    stored = json.loads((ROOT / 'tests/fixtures/macro_lights_v1_vectors.json').read_text())
    assert stored == json.loads(json.dumps(ref.build()))
    assert all(c['synthetic'] for c in stored['cases']) and 'SYNTHETIC' in stored['note']


@pytest.mark.skipif(shutil.which('node') is None, reason='node is required for JS parity')
def test_js_mirror_matches_python_vectors():
    result = subprocess.run(['node', str(ROOT / 'tools/macro_lights_node_test.js')], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]


def test_missing_lights_are_excluded_never_zero():
    assert ml.macro_state({}, None, None) == {'state': 'NORMAL', 'lit_count': 0, 'available_count': 0, 'low_confidence': True,
                                              'reasons': ['LIT_COUNT_LE_1', 'AVAILABLE_LT_3']}
    assert ml.employment_light([['2026-01', None], ['2026-02', None]])['lit'] is None
    assert ml.inflation_light([['2026-01', 0]])['reason'] == 'NO_DATA'


def test_treasury_curve_parser_keeps_nulls_and_rejects_unsafe_xml():
    rows = mlp.parse_treasury_curve(treasury_xml([('2026-10-08', '4.10', None), ('2026-10-09', '4.10', '3.90')]))
    assert rows == {'2026-10-08': (4.1, None), '2026-10-09': (4.1, 3.9)}
    assert mlp.parse_treasury_curve(treasury_xml([])) == {}
    for body in (b'<!DOCTYPE x><feed/>', b'<feed xmlns="http://www.w3.org/2005/Atom"><entry/></feed>', b'not xml',
                 treasury_xml([('2026-13-01', '1', '2')]), treasury_xml([('2026-10-09', 'abc', '2')])):
        with pytest.raises(mlp.CurveUnavailable):
            mlp.parse_treasury_curve(body)
    with pytest.raises(mlp.CurveUnavailable, match='CONFLICTING_DUPLICATE'):
        mlp.parse_treasury_curve(treasury_xml([('2026-10-09', '4.1', '3.9'), ('2026-10-09', '4.1', '4.0')]))


def test_public_block_has_three_lights_with_as_of_and_source(tmp_path):
    out = macro(tmp_path, manifest(tmp_path))
    require_public_screen('macro-screen.json', out)
    block = out['data']['macro_lights_v1']
    assert block['config'] == {k: ml.CONFIG[k] for k in ('id', 'version', 'status', 'marker', 'decided_on', 'source_section')}
    assert set(block['lights']) == {'employment', 'inflation', 'curve'} and block['device_lights'] == ['market', 'credit']
    e, i, c = (block['lights'][k] for k in ('employment', 'inflation', 'curve'))
    assert (e['state'], e['lit'], e['as_of'], e['source_series_id']) == ('LIVE', True, '2026-09', 'BLS:LNS14000000')
    assert e['values']['low12'] == 4.0 and abs(e['values']['gap'] - 0.6) < 1e-12 and e['values']['low12_count'] == 12
    assert (i['lit'], i['as_of'], i['values']['base_period']) == (True, '2026-09', '2025-09') and abs(i['values']['yoy'] - 0.06) < 1e-12
    assert (c['state'], c['lit'], c['as_of'], c['agency']) == ('LIVE', True, '2026-10-09', 'TREASURY') and c['values']['run_days'] == 29
    assert len(c['inputs']) == 2 and {s['agency'] for s in out['sources']} >= {'BLS', 'TREASURY'}
    for row in block['lights'].values():
        assert row['source'] and all(len(x['sha256']) == 64 for x in row['inputs'])


def test_public_json_carries_no_device_light_or_price(tmp_path):
    text = json.dumps(macro(tmp_path, manifest(tmp_path)))
    for word in ('SPY', 'HYG', 'IEF', '"market"', '"credit"', 'drawdown', 'rv20', 'ratio_change', 'close', 'price'):
        assert word not in text.replace('"device_lights": ["market", "credit"]', ''), word


def test_curve_needs_both_years_and_reason_only_entries(tmp_path):
    prev, cur = curve_years()
    out = macro(tmp_path, manifest(tmp_path, curves=[cur]))
    assert out['data']['macro_lights_v1']['lights']['curve']['lit'] is True
    (tmp_path / 'x').write_bytes(cur)
    out = macro(tmp_path, manifest(tmp_path, curve_entries=[{'reason': 'SOURCE_NOT_AVAILABLE'}, {'format': mlp.CURVE_FORMAT, 'file': 'x', 'acquired_at': ACQ, 'synthetic': False}]))
    row = out['data']['macro_lights_v1']['lights']['curve']
    assert (row['state'], row['lit'], row['reason'], row['inputs']) == ('NOT_AVAILABLE', None, 'SOURCE_NOT_AVAILABLE', [])
    out = macro(tmp_path, manifest(tmp_path, curves=False))
    assert out['data']['macro_lights_v1']['lights']['curve']['reason'] == 'SOURCE_NOT_COLLECTED'
    short = treasury_xml([(d, '4.5', '4.2') for d in weekdays('2026-10-01', '2026-10-09')])
    out = macro(tmp_path, manifest(tmp_path, curves=[short]))
    row = out['data']['macro_lights_v1']['lights']['curve']
    assert (row['lit'], row['reason'], len(row['inputs'])) == (None, 'INSUFFICIENT_HISTORY', 1)
    require_public_screen('macro-screen.json', out)
    with pytest.raises(ValueError, match='PUBLIC_SCREENS_INPUT_INVALID'):
        macro(tmp_path, manifest(tmp_path, curve_entries=[{'reason': 'BOGUS'}]))


def test_bls_failures_and_synthetic_inputs_are_not_available(tmp_path):
    m = manifest(tmp_path, bls_body=False, curves=False)
    m['macro_v0'] = [{'axis': 'Inflation', 'reason': 'SOURCE_NOT_AVAILABLE'}, {'axis': 'Labor', 'reason': 'SOURCE_NOT_AVAILABLE'}]
    lights = macro(tmp_path, m)['data']['macro_lights_v1']['lights']
    assert lights['employment']['reason'] == lights['inflation']['reason'] == 'SOURCE_NOT_AVAILABLE'
    m = manifest(tmp_path, curves=False)
    for e in m['macro_v0']:
        e['synthetic'] = True
    lights = macro(tmp_path, m)['data']['macro_lights_v1']['lights']
    assert lights['employment']['reason'] == 'SYNTHETIC_INPUT_NOT_PUBLIC' and lights['employment']['inputs'] == []
    # A month BLS did not publish ("-") is skipped in the 12-month low, never filled.
    body = bls(unrate=[4.0] * 5 + ['-'] + [4.0] * 6 + [4.5, 4.6, 4.7])
    e = macro(tmp_path, manifest(tmp_path, bls_body=body, curves=False))['data']['macro_lights_v1']['lights']['employment']
    assert e['lit'] is True and e['values']['low12_count'] == 11
    body = bls(cpi={(2026, 9): '106.0'})
    i = macro(tmp_path, manifest(tmp_path, bls_body=body, curves=False))['data']['macro_lights_v1']['lights']['inflation']
    assert (i['lit'], i['reason'], i['state']) == (None, 'BASE_MONTH_MISSING', 'NOT_AVAILABLE')
    stale = macro(tmp_path, manifest(tmp_path), as_of=NOW + timedelta(days=3))['data']['macro_lights_v1']['lights']
    assert {r['state'] for r in stale.values()} == {'STALE'}


def tamper_cases():
    def flip(b): b['lights']['employment']['lit'] = False; b['lights']['employment']['reason'] = 'NOT_LIT'
    def gap(b): b['lights']['employment']['values']['gap'] = 0.1
    def yoy(b): b['lights']['inflation']['values']['yoy'] = 0.04
    def run(b): b['lights']['curve']['values']['run_days'] = 3
    def sha(b): b['lights']['curve']['inputs'][0]['sha256'] = '0' * 64
    def extra(b): b['lights']['market'] = deepcopy(b['lights']['curve'])
    def key(b): b['lights']['curve']['values']['close'] = 1.0
    def state(b): b['lights']['inflation']['state'] = 'STALE'
    def config(b): b['config']['status'] = 'CALIBRATED'
    def asof(b): b['lights']['curve']['as_of'] = '2026-10-08'
    def null(b): b['lights']['inflation'].update(lit=None, reason='LIT')
    def source(b): b['lights']['employment']['source_series_id'] = 'BLS:CUUR0000SA0'
    return [flip, gap, yoy, run, sha, extra, key, state, config, asof, null, source]


@pytest.mark.parametrize('change', tamper_cases())
def test_python_validator_rejects_incoherent_lights_block(tmp_path, change):
    out = macro(tmp_path, manifest(tmp_path))
    change(out['data']['macro_lights_v1'])
    with pytest.raises(ValueError, match='PUBLIC_SCREEN_INVALID'):
        require_public_screen('macro-screen.json', out)


@pytest.mark.skipif(shutil.which('node') is None, reason='node is required for reader parity')
def test_browser_reader_parity_for_lights_block(tmp_path):
    good = macro(tmp_path, manifest(tmp_path))
    assert node_validate(good) == 0
    assert node_validate(json.loads(json.dumps(good, sort_keys=True))) == 0
    missing = macro(tmp_path, manifest(tmp_path, bls_body=False, curves=False))
    assert node_validate(missing) == 0
    old = deepcopy(good); del old['data']['macro_lights_v1']
    require_public_screen('macro-screen.json', old)
    assert node_validate(old) == 0
    for change in tamper_cases():
        bad = deepcopy(good); change(bad['data']['macro_lights_v1'])
        assert node_validate(bad) != 0, change.__name__


class Transport:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def __call__(self, url, *, data, query, max_bytes):
        self.calls.append((url, query))
        if self.fail:
            raise collection.MacroV0FetchError('HTTP_STATUS', status=503, content='HTML')
        year = dict(parse_qsl(query))['field_tdr_date_value']
        return curve_years()[0 if year == '2025' else 1]


def clock():
    return datetime(2026, 10, 11, tzinfo=timezone.utc)


def test_collector_fetches_previous_and_current_year_from_the_allowed_url(tmp_path):
    t = Transport()
    entries = collection.collect_treasury_curve(tmp_path, transport=t, clock=clock)
    assert [dict(parse_qsl(q)) for _, q in t.calls] == [{'data': 'daily_treasury_yield_curve', 'field_tdr_date_value': '2025'},
                                                       {'data': 'daily_treasury_yield_curve', 'field_tdr_date_value': '2026'}]
    for url, query in t.calls:
        assert url == collection.TREASURY_CURVE_URL and url in collection.ALLOWED and collection._query_allowed(url, query)
    assert [e['format'] for e in entries] == [mlp.CURVE_FORMAT] * 2 and all((tmp_path / e['file']).is_file() for e in entries)
    for query in ('data=daily_treasury_bill_rates&field_tdr_date_value=2026', 'data=daily_treasury_yield_curve&field_tdr_date_value=all',
                  'data=daily_treasury_yield_curve&field_tdr_date_value=2026&page=2', None):
        with pytest.raises(collection.MacroV0FetchError, match='URL_NOT_ALLOWED'):
            collection.default_transport(collection.TREASURY_CURVE_URL, data=None, query=query, max_bytes=10)


def test_collector_failure_is_reason_only_with_fixed_token_diagnostics(tmp_path):
    diagnostics = []
    entries = collection.collect_treasury_curve(tmp_path, transport=Transport(fail=True), clock=clock, diagnostics=diagnostics)
    assert entries == [{'reason': 'SOURCE_NOT_AVAILABLE'}] * 2 and not list(tmp_path.iterdir())
    assert [d['stage'] for d in diagnostics] == ['TREASURY_XML_PREVIOUS', 'TREASURY_XML_CURRENT']
    assert all(d['code'] == 'HTTP_STATUS' and d['http'] == 503 and d['content'] == 'HTML' for d in diagnostics)
    assert 'treasury.gov' not in json.dumps(diagnostics)


def test_pipeline_keeps_raw_curve_private_and_logs_states_only(tmp_path, capsys):
    from public_screens_pipeline import collect, _print_macro_v0
    from tests.test_public_sec_inputs import raw as sec_raw

    class Client:
        def __init__(self, _): pass

        def collect(self, company, cik):
            return *(json.dumps(x).encode() for x in sec_raw(company)), datetime(2026, 10, 10, 12, tzinfo=timezone.utc)

    collect(tmp_path, environ={'SEC_USER_AGENT': 'synthetic setting'}, client_factory=Client,
            macro_curve=lambda root: collection.collect_treasury_curve(root, transport=Transport(), clock=clock))
    assert not any(p.name.startswith('macro-v1-') for p in tmp_path.iterdir())
    payload = json.loads((tmp_path / 'macro-screen.json').read_text())
    require_public_screen('macro-screen.json', payload)
    assert payload['data']['macro_lights_v1']['lights']['curve']['lit'] is True
    capsys.readouterr()
    _print_macro_v0(tmp_path)
    lines = [l.replace('state=STALE', 'state=LIVE') for l in capsys.readouterr().out.splitlines() if l.startswith('MACRO_V1_LIGHT')]
    assert lines == ['MACRO_V1_LIGHT light=curve state=LIVE lit=ON reason=LIT',
                     'MACRO_V1_LIGHT light=employment state=NOT_AVAILABLE lit=NO_DATA reason=SOURCE_NOT_COLLECTED',
                     'MACRO_V1_LIGHT light=inflation state=NOT_AVAILABLE lit=NO_DATA reason=SOURCE_NOT_COLLECTED']


def test_replay_tool_reads_local_csv_and_prints_only(tmp_path, capsys):
    """Synthetic CSVs only. The replay prints to stdout and writes nothing (market/credit output stays private)."""
    import macro_lights_replay as replay
    months = ['%04d-%02d-01' % (y, m) for y in range(2027, 2031) for m in range(1, 13)]
    (tmp_path / 'u.csv').write_text('DATE,UNRATE\n' + ''.join('%s,%s\n' % (d, '4.0' if d < '2029-06' else '5.0') for d in months))
    (tmp_path / 'c.csv').write_text('DATE,CPI\n' + ''.join('%s,%.2f\n' % (d, 100 + 0.1 * i) for i, d in enumerate(months)))
    (tmp_path / 'g.csv').write_text('DATE,G\n' + ''.join('%s,1.0\n' % d for d in months[::3]))
    days = weekdays('2028-01-03', '2030-12-31')
    (tmp_path / 't.csv').write_text('DATE,T10Y3M\n' + ''.join('%s,%s\n' % (d, '-0.5' if d >= '2029-03-01' else '.') for d in days))
    before = sorted(p.name for p in tmp_path.iterdir())
    assert replay.main(['--unrate', str(tmp_path / 'u.csv'), '--cpi', str(tmp_path / 'c.csv'), '--gdp', str(tmp_path / 'g.csv'),
                        '--curve', str(tmp_path / 't.csv'), '--period', 'synthetic:2029-01-01:2030-06-30']) == 0
    out = capsys.readouterr().out
    assert '== synthetic (2029-01-01 → 2030-06-30' in out and 'input spy     NOT PROVIDED' in out
    assert 'first 경고: 2029-' in out and 'curve 2029-' in out
    assert sorted(p.name for p in tmp_path.iterdir()) == before
