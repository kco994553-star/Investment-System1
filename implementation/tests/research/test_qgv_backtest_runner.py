"""Runner integration checks use invented issuers, prices and session tables only."""
import copy
import hashlib
import importlib
import json
from datetime import date, timedelta
from pathlib import Path

import pytest


def api():
    try:
        return importlib.import_module('investment_system.research.qgv_backtest.runner')
    except ModuleNotFoundError:
        pytest.fail('local research runner is not implemented')


def spec():
    result = json.loads(Path('docs/backtest/QGV_BACKTEST_SPEC_V1_20261026.json').read_text())
    result['period']['data_feasibility_ladder'][0].update(start='2016-02-16', end='2016-02-20')
    return result


def frozen_spec():
    return json.loads(Path('docs/backtest/QGV_BACKTEST_SPEC_V1_20261026.json').read_text())


@pytest.fixture
def tiny_period_writer_contract(monkeypatch):
    """Only writer integration uses a short fixture; the real entrypoint stays frozen."""
    from investment_system.research.qgv_backtest import config
    monkeypatch.setattr(config, 'validate_period_contract', lambda _: None)


def bundle():
    days = [d for i in range(112) if (d := date(2015, 11, 1) + timedelta(days=i))
            not in {date(2016, 2, 13), date(2016, 2, 14), date(2016, 2, 15)}]
    financials = {}
    for i in range(11):
        cik = str(i + 1).zfill(10)
        concepts = {}
        fields = {'Revenues': 100, 'GrossProfit': 40, 'OperatingIncomeLoss': 20,
                  'NetIncomeLoss': 16, 'NetCashProvidedByUsedInOperatingActivities': 25,
                  'PaymentsToAcquirePropertyPlantAndEquipment': 5,
                  'StockholdersEquity': 60, 'Assets': 100,
                  'CashAndCashEquivalentsAtCarryingValue': 10, 'LongTermDebt': 5,
                  'InterestExpense': 1, 'WeightedAverageNumberOfDilutedSharesOutstanding': 10,
                  'EarningsPerShareDiluted': 1.6}
        for concept, value in fields.items():
            unit = 'shares' if concept == 'WeightedAverageNumberOfDilutedSharesOutstanding' else ('USD/shares' if concept == 'EarningsPerShareDiluted' else 'USD')
            rows = []
            for year in range(2009, 2015):
                row = dict(start=f'{year}-01-01', end=f'{year}-12-31', filed=f'{year + 1}-02-01',
                           val=value * (1.05 ** (year - 2009)) * (1 + i / 20), form='10-K',
                           fy=year, fp='FY', accn=f'{cik}-{year}')
                if concept in {'StockholdersEquity', 'Assets', 'CashAndCashEquivalentsAtCarryingValue', 'LongTermDebt'}:
                    row.pop('start')
                rows.append(row)
            concepts[concept] = {'units': {unit: rows}}
        financials[cik] = {'cik': cik, 'facts': {'us-gaap': concepts, 'dei': {
            'EntityCommonStockSharesOutstanding': {'units': {'shares': [dict(
                end=f'{year}-12-31', filed=f'{year + 1}-02-01', val=10 * (1.05 ** (year - 2009)) * (1 + i / 20),
                form='10-K', accn=f'{cik}-{year}') for year in range(2009, 2015)]}}}}}
    return dict(synthetic=True, benchmark_id='SP500_TR_INDEX', coverage_start=str(days[0]), coverage_end=str(days[-1]),
        calendar_source='SYNTHETIC_HAND_TABLE',
        sessions=[dict(day=str(d), open_at=f'{d}T09:30:00-05:00', close_at=f'{d}T16:00:00-05:00') for d in days],
        companyfacts_by_cik=financials,
        filings=[dict(cik=str(i + 1), filed='2015-02-01', sic='3571', accn=f'{i}-old') for i in range(11)],
        membership=[dict(cik=str(i + 1), security_id=f'SYN{i:02}', start='2000-01-01', end=None) for i in range(11)],
        prices=[dict(security_id=f'SYN{i:02}', date=str(d), open=10 + i, close=10 + i + (d.day - 15) / 10,
                     volume=100, currency='USD', price_basis='RAW', shares_basis='RAW',
                     basis_alignment=dict(status='VERIFIED', source='SYNTHETIC_HAND_RECEIPT', signal_day=str(d),
                         shares_period_end='2014-12-31', verified_through=str(d), price_to_shares_factor=1.0,
                         shares_filing_accn=f'{str(i + 1).zfill(10)}-2014', split_events=[])) for i in range(11) for d in days],
        events=[], rates=[dict(public_date=str(d), annual_yield=0.01) for d in days],
        benchmark=[dict(date=str(d), total_return_index=100 + k / 100, open_total_return_index=100 + k / 100,
                        currency='USD') for k, d in enumerate(days)])


def manifest_for(tmp_path, data=None):
    data = bundle() if data is None else copy.deepcopy(data)
    source = tmp_path / 'synthetic-source.json'
    source.write_text('{"synthetic_source":true}')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    names = ('membership', 'identities', 'financials', 'filings', 'prices', 'corporate_actions', 'benchmark', 'rates', 'calendar')
    data['source_hashes'] = {name: digest for name in names}
    local = tmp_path / 'synthetic-bundle.json'
    local.write_text(json.dumps(data))
    return dict(protection_status='AUTHORIZED_NON_PROTECTED', access_receipt='SYNTHETIC_ACCESS',
        rights=dict(research=True, ai_processing=True, storage=True), rights_receipt='SYNTHETIC_RIGHTS',
        private_destination_verified=True, private_output_root=str(tmp_path / 'private'),
        bundle=dict(path=str(local), sha256=hashlib.sha256(local.read_bytes()).hexdigest()),
        resources={name: dict(path=str(source), sha256=digest, verified=True, source='SYNTHETIC',
            rights_receipt='SYNTHETIC_RIGHTS', start='2015-11-01', end='2016-02-20') for name in names})


def test_no_manifest_never_runs_any_of_thirty_strategies():
    result = api().run_stage(frozen_spec(), 'primary', 'TARGET_QGV_V2')
    assert result['status'] == 'BLOCKED_ON_DATA'
    assert len(result['strategies']) == 30
    assert all(r['status'] == 'NOT_RUN' and r['metrics'] is None for r in result['strategies'])


def test_permission_gate_precedes_private_bundle_reads(tmp_path):
    secret = tmp_path / 'private.json'
    secret.write_text('not JSON and must not be read')
    result = api().run_stage(frozen_spec(), 'smoke', 'TARGET_QGV_V2', {'bundle': {'path': str(secret)}})
    assert result['status'] == 'BLOCKED_ON_PERMISSION'
    assert 'private.json' not in json.dumps(result)


def test_pure_replay_requires_explicit_synthetic_bundle():
    data = bundle()
    del data['synthetic']
    with pytest.raises(ValueError, match='SYNTHETIC_ONLY'):
        api().replay_bundle(spec(), data, 'TARGET_QGV_V2')


def test_replay_scores_then_executes_real_ledger_next_open_and_marks_daily():
    cell = dict(strategy_id='W0-N15-Q', panel='COMMON', cost_bps=10)
    result = api().replay_bundle(spec(), bundle(), 'TARGET_QGV_V2', cells=[cell])
    run = result['runs'][0]
    assert run['status'] == 'COMPLETE'
    assert run['decisions'][0]['signal_day'] == '2016-02-12'
    assert run['decisions'][0]['execution_day'] == '2016-02-16'
    assert run['decisions'][0]['selected']
    assert run['fills'] and all(r['session'] >= '2016-02-16' for r in run['fills'])
    assert len(run['nav']) == 6  # Explicit pre-fill baseline plus five actual session marks.
    assert run['nav'][0]['nav'] == '100000'
    assert run['nav'][1]['nav'] != '100000'
    assert run['metrics']['cumulative_return']['value'] is not None
    assert run['coverage'][0]['selected_count'] > 0
    assert run['exposure'][1]['metrics']['security_hhi'] > 0


def test_future_financial_and_price_mutations_cannot_change_initial_selection_or_orders():
    data = bundle()
    cell = dict(strategy_id='W0-N15-Q', panel='COMMON', cost_bps=10)
    first = api().replay_bundle(spec(), data, 'TARGET_QGV_V2', cells=[cell])['runs'][0]
    changed = copy.deepcopy(data)
    for facts in changed['companyfacts_by_cik'].values():
        facts['facts']['us-gaap']['Revenues']['units']['USD'].append(dict(
            start='2014-01-01', end='2014-12-31', filed='2016-02-16', val=1e15, form='10-K', accn='future'))
    for row in changed['prices']:
        if row['date'] > '2016-02-12':
            row['open'] *= 10
            row['close'] *= 10
    second = api().replay_bundle(spec(), changed, 'TARGET_QGV_V2', cells=[cell])['runs'][0]
    assert first['decisions'] == second['decisions']
    assert first['fills'] != second['fills']


def test_unknown_price_basis_blocks_replay_instead_of_empty_cash_performance():
    data = bundle()
    for row in data['prices']:
        row.pop('shares_basis')
    result = api().replay_bundle(spec(), data, 'TARGET_QGV_V2', cells=[dict(strategy_id='W0-N15-Q', panel='COMMON', cost_bps=10)])
    assert result['status'] == 'BLOCKED_ON_DATA'
    assert not result['runs']


def test_empty_common_panel_is_cash_while_practical_qg_can_trade():
    data = bundle()
    for facts in data['companyfacts_by_cik'].values():
        del facts['facts']['us-gaap']['WeightedAverageNumberOfDilutedSharesOutstanding']
    for row in data['prices']:
        row.pop('basis_alignment')  # No attested price/share bridge: V is economically NA.
    result = api().replay_bundle(spec(), data, 'TARGET_QGV_V2', cells=[
        dict(strategy_id='W0-N15-Q', panel=panel, cost_bps=10) for panel in ('COMMON', 'PRACTICAL')])
    common, practical = result['runs']
    assert common['status'] == practical['status'] == 'COMPLETE'
    assert common['decisions'][0]['selected'] == []
    assert practical['decisions'][0]['selected']
    assert not common['fills'] and practical['fills']


def test_missing_rate_cannot_silently_turn_into_zero_cash_yield():
    data = bundle()
    data['rates'] = [dict(public_date='2015-11-01', annual_yield=0.01)]
    result = api().replay_bundle(spec(), data, 'TARGET_QGV_V2', cells=[dict(strategy_id='W0-N15-Q', panel='COMMON', cost_bps=10)])
    assert result['status'] == 'INCOMPLETE_REPLAY'
    assert 'CASH_RATE_UNVERIFIED' in result['blockers']
    assert result['runs'][0]['metrics']['cagr']['value'] is None


def test_missing_current_mark_never_reuses_old_price_or_claims_complete():
    data = bundle()
    data['prices'] = [r for r in data['prices'] if r['date'] != '2016-02-19']
    result = api().replay_bundle(spec(), data, 'TARGET_QGV_V2', cells=[dict(strategy_id='W0-N15-Q', panel='COMMON', cost_bps=10)])
    assert result['status'] == 'INCOMPLETE_REPLAY'
    assert result['runs'][0]['nav'][-2]['nav'] is None
    assert result['runs'][0]['metrics']['cagr']['value'] is None


def test_suspended_quote_with_open_does_not_fill_until_unsuspended_session():
    data = bundle()
    for row in data['prices']:
        if row['date'] == '2016-02-16':
            row['suspended'] = True
    result = api().replay_bundle(spec(), data, 'TARGET_QGV_V2', cells=[dict(strategy_id='W0-N15-Q', panel='COMMON', cost_bps=10)])
    assert result['runs'][0]['fills']
    assert min(fill['session'] for fill in result['runs'][0]['fills']) == '2016-02-17'


def test_non_session_corporate_effective_date_is_explicitly_blocked():
    data = bundle()
    data['events'] = [dict(type='CASH_MERGER', event_id='synthetic-holiday', effective_date='2016-02-14',
                          security_id='SYN00', settlement_date='2016-02-16', cash_per_share=20)]
    result = api().replay_bundle(spec(), data, 'TARGET_QGV_V2', cells=[dict(strategy_id='W0-N15-Q', panel='COMMON', cost_bps=10)])
    assert result['status'] == 'BLOCKED_ON_IMPLEMENTATION'
    assert 'NON_SESSION_CORPORATE_ACTION' in result['blockers']


def test_first_open_has_no_interest_from_pre_entry_signal_weekend():
    from decimal import Decimal
    data = bundle()
    result = api().replay_bundle(spec(), data, 'TARGET_QGV_V2', cells=[dict(strategy_id='W0-N15-Q', panel='COMMON', cost_bps=10)])
    run = result['runs'][0]
    used = sum(Decimal(f['gross']) + Decimal(f['fee']) for f in run['fills'] if f['session'] == '2016-02-16')
    assert abs(used + Decimal(run['nav'][1]['cash']) - Decimal('100000')) < Decimal('1e-20')


def test_negative_verified_rate_is_valid_and_benchmark_entry_cost_is_explicit():
    data = bundle()
    for row in data['rates']:
        row['annual_yield'] = -0.01
    run = api().replay_bundle(spec(), data, 'TARGET_QGV_V2', cells=[dict(strategy_id='W0-N15-Q', panel='COMMON', cost_bps=10)])['runs'][0]
    assert run['status'] == 'COMPLETE'
    assert run['risk_free'] and run['risk_free'][0]['value'] < 0
    assert run['benchmark'] and run['benchmark_nav'][0]['nav'] < 100000
    assert run['benchmark_nav'][0]['raw_reference_nav'] == 100000


def test_private_primary_stage_writes_once_and_reuses_exact_contract(tmp_path, tiny_period_writer_contract):
    manifest = manifest_for(tmp_path)
    output = tmp_path / 'private' / 'run'
    first = api().run_stage(spec(), 'primary', 'TARGET_QGV_V2', manifest, output)
    assert first['status'] == 'PRIMARY_DONE'
    assert first['completed_cells'] == 8
    artifact = output / 'primary-private.json'
    original, modified = artifact.read_bytes(), artifact.stat().st_mtime_ns
    second = api().run_stage(spec(), 'primary', 'TARGET_QGV_V2', manifest, output)
    assert second['status'] == 'PRIMARY_DONE' and second['cached'] is True
    assert artifact.read_bytes() == original and artifact.stat().st_mtime_ns == modified
    assert all(row['metrics'] is None for row in second['strategies'])
    assert 'SYN00' not in json.dumps(second)


def test_private_output_leaf_symlink_never_writes_outside_destination(tmp_path, tiny_period_writer_contract):
    manifest = manifest_for(tmp_path)
    output = tmp_path / 'private' / 'run'
    output.mkdir(parents=True)
    outside = tmp_path / 'outside.json'
    outside.write_text('KEEP_ME')
    (output / 'primary-private.json').symlink_to(outside)
    result = api().run_stage(spec(), 'primary', 'TARGET_QGV_V2', manifest, output)
    assert result['status'] == 'BLOCKED_ON_PERMISSION'
    assert outside.read_text() == 'KEEP_ME'


def test_bundle_source_hashes_must_match_verified_input_resources(tmp_path, tiny_period_writer_contract):
    manifest = manifest_for(tmp_path)
    local = Path(manifest['bundle']['path'])
    data = json.loads(local.read_text())
    data['source_hashes']['prices'] = '0' * 64
    local.write_text(json.dumps(data))
    manifest['bundle']['sha256'] = hashlib.sha256(local.read_bytes()).hexdigest()
    result = api().run_stage(spec(), 'audit', 'TARGET_QGV_V2', manifest)
    assert result['status'] == 'BLOCKED_ON_DATA'
    assert result['blockers'] == ['BUNDLE_SOURCE_HASH_MISMATCH']


def test_duplicate_benchmark_dates_never_depend_on_input_order():
    data = bundle()
    data['benchmark'].append(dict(data['benchmark'][-1], total_return_index=99999))
    for rows in (data['benchmark'], list(reversed(data['benchmark']))):
        candidate = dict(data, benchmark=rows)
        result = api().replay_bundle(spec(), candidate, 'TARGET_QGV_V2')
        assert result['status'] == 'BLOCKED_ON_DATA'
        assert 'DUPLICATE_BENCHMARK_DATE' in result['blockers']


def test_report_stage_writes_private_tables_and_svg_with_explicit_unrun_periods(tmp_path, tiny_period_writer_contract):
    manifest = manifest_for(tmp_path)
    output = tmp_path / 'private' / 'report'
    result = api().run_stage(spec(), 'report', 'TARGET_QGV_V2', manifest, output)
    assert result['status'] == 'REPORT_PARTIAL'
    assert result['completed_cells'] == 340
    assert result['private_artifacts_written'] == 6
    assert '<svg' in (output / 'nav-drawdown.svg').read_text()
    report = json.loads((output / 'report.json').read_text())
    assert len(report['strategy_period_status']) == 90
    assert (output / 'comparisons.csv').read_text().startswith('period_id,strategy_id,panel,cost_bps')


def test_local_stage_never_accepts_a_shorter_frozen_period(tmp_path):
    with pytest.raises(ValueError, match='PERIOD_CONTRACT_CHANGED'):
        api().run_stage(spec(), 'smoke', 'TARGET_QGV_V2', {'bundle': {'path': str(tmp_path / 'must-not-read')}})


def test_long_history_does_not_silently_substitute_a_different_benchmark():
    data = bundle()
    data['benchmark_id'] = 'SPY_TR'
    result = api().replay_bundle(spec(), data, 'TARGET_QGV_V2')
    assert result['status'] == 'BLOCKED_ON_DATA'
    assert 'BENCHMARK_IDENTITY_MISMATCH' in result['blockers']
