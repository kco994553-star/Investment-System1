"""adapters/bundle.py: one S assembled into an engine input bundle + manifest + provenance; the engine accepts it.
Invented source files in tmp_path only; the bundle is written to tmp_path by the test (the adapters write nothing)."""
import ast
from datetime import date
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re

import pytest

import exp_deciles_adapter_fixtures as fx
from investment_system.research.exp_deciles import handoff, ledger, runner
from investment_system.research.exp_deciles.adapters import bundle
from investment_system.research.exp_deciles.adapters.common import AdapterError

IMPL = Path(__file__).resolve().parents[2]
ADAPTERS = IMPL / 'src' / 'investment_system' / 'research' / 'exp_deciles' / 'adapters'


@pytest.fixture()
def src(tmp_path):
    return fx.write_all(tmp_path / 'src')


def _sec(src):
    return {k: src[k] for k in ('companyfacts_zip', 'submissions_zip', 'form_idx', 'fsds')}


def _build(src, securities=None, **kw):
    kw.setdefault('iex', {'rows': fx.iex_rows(), 'iex_day': fx.S})
    kw.setdefault('carried_units', [fx.CIK['H']])
    return bundle.build(year=2018, securities=securities or fx.security_map(src['series']), sec=_sec(src), **kw)


def _attributes(**values):
    return {'source': 'invented listing file for tests', 'sha256': 'a' * 64, 'values': values}


def test_manifest_is_an_engine_input_manifest(src):
    out = _build(src)
    files = fx.file_bytes(out['files'])
    assert [name for name, _ in out['files']][-2:] == ['adapter_provenance.json', 'manifest.json']
    manifest = handoff.parse_input_manifest(files['manifest.json'])
    names = [r['name'] for r in manifest['resources']]
    assert names == ['records:2018', 'quotes:2018', 'companyfacts:pit', 'filings', 'prices']
    for resource in manifest['resources']:
        handoff.verify_resource(resource, files[resource['path']])
        assert resource['period'] == '2018-02-16..2019-02-19'


def test_counts_candidate_input_present_and_unknown_by_reason(src):
    counts = _build(src)['counts']
    assert counts['candidates'] == 10 and counts['candidate_carried_units_without_security'] == 1
    assert counts['eligible_input_present'] == 0 and counts['unknown'] == 10
    assert counts['unknown_by_reason'] == {'CIK_MISSING': 1, 'LISTING_STATUS_NOT_SUPPLIED': 8,
                                           'NOT_IN_SECURITY_MAP_AT_S': 1}
    occ = counts['unknown_reason_occurrences']
    assert occ['MULTI_CLASS_SECURITIES_AT_S'] == 2 and occ['SPLIT_BASIS_NOT_VERIFIABLE_FROM_SEC_BULK'] == 1
    assert occ['ODD_LOT_ONLY'] == 1 and occ['NO_IEX_TRADE'] == 1
    assert counts['shares']['supplied'] == 1 and counts['as_filed_sic']['supplied'] == 2
    assert counts['t_open'] == {'SERIES_NOT_SUPPLIED': 5, 'SERIES_REFUSED': 2, 'SUPPLIED': 1, 'T_OPEN_BAR_MISSING': 1}
    assert counts['terminations'] == {'termination_records': 1, 'with_effective_date': 0, 'without_effective_date': 1}


def test_never_a_complete_population(src):
    with pytest.raises(AdapterError, match='COMPLETE_HISTORICAL_POPULATION_NOT_CLAIMABLE'):
        _build(src, complete_population=True)
    prov = fx.read_json(_build(src)['files'], 'adapter_provenance.json')
    assert prov['population_status'] == 'CALLER_SECURITY_MAP_NOT_A_COMPLETE_HISTORICAL_POPULATION'
    assert prov['candidate_source'] == 'CALLER_SECURITY_MAP'
    assert 'COMPLETE_HISTORICAL_POPULATION' in prov['cannot_supply']
    for item in ('LISTING_STATUS_AT_S', 'SECURITY_TYPE_AND_EXCHANGE', 'ADR_RATIO',
                 'PER_CLASS_SHARE_COUNTS_OF_MULTI_CLASS_ISSUERS', 'CORPORATE_ACTIONS_DIVIDENDS_SPLITS_MERGER_TERMS'):
        assert item in prov['cannot_supply']


def test_iex_is_s_approximation_only_and_never_a_price_row(src):
    files = _build(src)['files']
    prices = fx.read_json(files, 'prices.json')
    assert {r['security_id'] for r in prices} == {'SEC-A', 'SEC-G'}       # SEC-F has an IEX price but no SIP series
    assert {r['source'] for r in prices} == {'ALPACA_SIP_DAILY_BAR_RAW'}
    assert not [r for r in prices if r['security_id'] == 'SEC-G' and r['date'] == fx.T]   # missing T bar: no fill
    records = {r['security_id']: r for r in fx.read_json(files, 'records_2018.json')['records']}
    assert records['SEC-F']['price'] == 9.0007 and records['SEC-F']['price_label'] == 'IEX_LAST_REGULAR_TRADE_APPROX'
    assert records['SEC-B1']['price'] is None and records['SEC-B2']['price'] is None
    quotes = fx.read_json(files, 'quotes_2018.json')['quotes']
    assert quotes['SEC-B1']['withheld_reason'] == 'ODD_LOT_ONLY' and quotes['SEC-B1']['price'] is None
    prov = fx.read_json(files, 'adapter_provenance.json')
    assert prov['s_price'] == {'source': 'IEX_LAST_REGULAR_TRADE_APPROX', 'label': 'IEX_LAST_REGULAR_TRADE_APPROX',
                               'use': 'S_SIGNAL_PRICE_APPROXIMATION_ONLY_NEVER_T_OPEN'}
    assert prov['t_open'] == {'source': 'ALPACA_SIP_DAILY_BAR_RAW', 'role': 'CONSOLIDATED_OPEN_CANDIDATE_FOR_T'}


def test_alpaca_close_as_the_s_price_source(src):
    files = _build(src, s_price_source='ALPACA_SIP_CLOSE')['files']
    records = {r['security_id']: r for r in fx.read_json(files, 'records_2018.json')['records']}
    assert records['SEC-A']['price'] == 10.4007 and records['SEC-A']['price_label'] == 'ALPACA_SIP_CONSOLIDATED_CLOSE_RAW'
    assert records['SEC-F']['price'] is None                                # no series: never the IEX price instead
    quotes = fx.read_json(files, 'quotes_2018.json')['quotes']
    assert quotes['SEC-F']['withheld_reason'] == 'SERIES_NOT_SUPPLIED'
    assert quotes['SEC-D']['withheld_reason'] == 'SERIES_REFUSED'
    with pytest.raises(AdapterError, match='S_PRICE_SOURCE_INVALID'):
        _build(src, s_price_source='IEX_AND_ALPACA')


def test_provenance_per_item(src):
    prov = fx.read_json(_build(src)['files'], 'adapter_provenance.json')
    by_role = {}
    for source in prov['sources']:
        by_role.setdefault(source['role'], []).append(source)
        assert '/' not in source['file'] or source['file'].startswith('RAW_')     # no private directory recorded
    assert by_role['PIT_COMPANYFACTS_AND_COVER_SHARES'][0]['sha256'] == hashlib.sha256(
        Path(src['companyfacts_zip']).read_bytes()).hexdigest()
    assert {s['file'] for s in by_role['LEDGER_PRICES']} >= {'RAW_XQA/page-00.json', 'RAW_XQA/page-01.json'}
    a = prov['securities']['SEC-A']
    assert a['status'] == 'UNKNOWN' and a['reasons'] == ['LISTING_STATUS_NOT_SUPPLIED', 'SECURITY_TYPE_NOT_SUPPLIED',
                                                         'SPLIT_BASIS_NOT_VERIFIABLE_FROM_SEC_BULK']
    assert a['fields']['shares_outstanding'] == {'source': 'SEC companyfacts.zip', 'status': 'SUPPLIED'}
    assert a['fields']['listed'] == {'source': None, 'status': 'LISTING_STATUS_NOT_SUPPLIED'}
    assert prov['securities']['SEC-B1']['fields']['shares_outstanding']['status'] == 'MULTI_CLASS_SECURITIES_AT_S'
    assert prov['alpaca']['SEC-D']['reason'] == 'BAR_TIME_NOT_NY_MIDNIGHT'
    assert prov['terminations'][0]['reasons'][0] == 'EFFECTIVE_DATE_NOT_IN_INDEX_ROW'


def test_deterministic_and_order_free(src):
    one = _build(src)
    securities = fx.security_map(src['series'])
    random.Random(7).shuffle(securities)
    two = _build(src, securities=securities)
    assert one['files'] == two['files']


def test_refusals(src):
    entries = fx.security_map(src['series'])
    with pytest.raises(AdapterError, match='SECURITY_MAP_DUPLICATE_ID'):
        _build(src, securities=entries + [entries[0]])
    with pytest.raises(AdapterError, match='SECURITY_MAP_ENTRY_INVALID'):
        _build(src, securities=[dict(entries[0], listed=True)])
    with pytest.raises(AdapterError, match='ATTRIBUTES_PROVENANCE_REQUIRED'):
        _build(src, attributes={'values': {'SEC-A': {'listed': True}}})
    with pytest.raises(AdapterError, match='ATTRIBUTES_INVALID'):
        _build(src, attributes=_attributes(**{'SEC-A': {'listed': 'yes'}}))
    with pytest.raises(AdapterError, match='EFFECTIVE_DATES_PROVENANCE_REQUIRED'):
        _build(src, effective_dates={'values': {}})
    with pytest.raises(AdapterError, match='CARRIED_UNIT_INVALID'):
        _build(src, carried_units=['x'])


def _cli():
    spec = importlib.util.spec_from_file_location('exp_cli_for_adapters', IMPL / 'tools' / 'exp_stock_indicator_deciles.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    real = module.code_state
    module.code_state = lambda: (real()[0], [])
    return module


def test_engine_select_runs_on_the_bundle_missing_inputs_stay_unknown(src, tmp_path, capsys):
    attrs = _attributes(**{'SEC-A': {'listed': True, 'security_type': 'COMMON', 'share_price_basis': 'CONFIRMED'},
                           'SEC-F': {'listed': True, 'security_type': 'COMMON'}})
    out = _build(src, attributes=attrs)
    assert out['counts']['eligible_input_present'] == 1
    folder = tmp_path / 'bundle'
    folder.mkdir()
    for name, data in out['files']:
        (folder / name).write_bytes(data)
    cli = _cli()
    code = cli.main(['select', '--manifest', str(folder / 'manifest.json'), '--year', '2018', '--out',
                     str(tmp_path / 'select'), '--generated-at', '2026-11-01T00:00:00Z'])
    printed = capsys.readouterr().out
    assert code == 0, printed
    assert 'SEC-' not in printed and '10.4107' not in printed
    selection = json.loads((tmp_path / 'select' / 'selection_inputs.json').read_text())
    counts = selection['counts']['U_A']
    # SEC-A: 50,000,000 x 10.4107 >= 250m -> ELIGIBLE; every other unit UNKNOWN (missing input), none EXCLUDED
    assert (counts['eligible'], counts['excluded']) == (1, 0)
    assert counts['unknown'] == counts['candidate'] - 1
    issuers = selection['universe']['issuers']
    assert issuers[fx.cik10('A')]['U_A']['status'] == 'ELIGIBLE'
    assert issuers[fx.cik10('F')]['U_A']['status'] == 'UNKNOWN'        # listed and typed, but no cover share count
    assert 'SHARES_OUTSTANDING_MISSING' in issuers[fx.cik10('F')]['market_cap_reasons']
    assert issuers[fx.cik10('B')]['U_A']['status'] == 'UNKNOWN'        # multi-class: never a threshold exclusion
    # the Form 25-NSE of the carried unit H reached the engine without an effective date: not a termination at S
    assert [t['status'] for t in selection['universe']['terminations']] == ['TERMINATION_EFFECTIVE_DATE_MISSING']
    assert selection['pit']['rows']['SEC-A']['sic'] == '3571'          # as-filed SIC from FSDS reached the engine
    # the price rows are valid ledger rows
    rows = runner.price_rows(fx.read_json(out['files'], 'prices.json'))
    index = ledger.index_price_rows(rows)
    assert index[date(2018, 2, 20)]['SEC-A'].open == Decimal('10.5007')


def test_count_lines_carry_counts_only(src):
    lines = bundle.count_lines(_build(src)['counts'])
    text = '\n'.join(lines)
    assert lines[0] == 'candidates=10'
    assert 'SEC-' not in text and not re.search(r'\d+\.\d*7\b', text) and 'XQ' not in text


def test_adapters_are_offline_pure_and_silent():
    banned = {'urllib', 'requests', 'http', 'socket', 'subprocess', 'providers', 'ftplib', 'smtplib'}
    modules = sorted(p.name for p in ADAPTERS.glob('*.py'))
    assert modules == ['__init__.py', 'alpaca_bars.py', 'bundle.py', 'common.py', 'iex_signal.py', 'sec_bulk.py']
    for name in modules:
        text = (ADAPTERS / name).read_text(encoding='utf-8')
        tree = ast.parse(text)
        for node in ast.walk(tree):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] + [a.name for a in node.names] if isinstance(node, ast.ImportFrom) else [])
            for imported in names:
                assert not set(imported.split('.')) & banned, (name, imported)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ('print', 'exec', 'eval', '__import__', 'input'), (name, node.func.id)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in ('write_bytes', 'write_text', 'mkdir', 'unlink', 'rename', 'touch',
                                              'makedirs', 'remove', 'system', 'popen'), (name, node.func.attr)
            if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'open':
                modes = [a.value for a in node.args[1:] if isinstance(a, ast.Constant)]
                assert modes == ['rb'], (name, modes)
        assert 'sys.stdout' not in text and 'logging' not in text, name
    # the IEX adapter does not touch files at all
    iex = (ADAPTERS / 'iex_signal.py').read_text(encoding='utf-8')
    assert 'open(' not in iex and 'read_bytes' not in iex and 'Path' not in iex
