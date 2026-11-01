"""Integration exercises the existing scorer/ledger, never precomputed scores."""
import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from test_qgv_backtest_runner import bundle, spec, frozen_spec, manifest_for, tiny_period_writer_contract
from test_qgv_backtest_cache import rights
from test_qgv_backtest_universe import inputs
from investment_system.research.qgv_backtest.extensions import default_extension, selected_cells
from investment_system.research.qgv_backtest.cache import PreparationCache
from investment_system.research.qgv_backtest import runner


def large_bundle():
    data = inputs()
    base_facts = copy.deepcopy(data['companyfacts_by_cik']['0000000001'])
    prices = [r for r in data['prices'] if r['security_id'] == 'SYN00']
    for i in range(11,110):
        cik, sid = str(i+1).zfill(10),f'SYN{i:03}'
        facts = copy.deepcopy(base_facts)
        facts['cik'] = cik
        for tags in facts['facts'].values():
            for info in tags.values():
                for records in info['units'].values():
                    for row in records:
                        row['accn'] = row['accn'].replace('0000000001',cik)
        data['companyfacts_by_cik'][cik] = facts
        data['filings'].append(dict(cik=cik,filed='2015-02-01',sic='3571',accn=f'{i}-old'))
        membership = dict(cik=cik,security_id=sid,start='2000-01-01',end=None)
        data['membership'].append(membership)
        data['security_master'].append(dict(membership,issuer_id=f'I{i}',security_type='COMMON',known_at='2015-01-01T12:00:00Z',source='SYNTHETIC',receipt='HAND'))
        data['capitalization'].append(dict(issuer_id=f'I{i}',effective_date='2016-02-01',known_at='2016-02-01T12:00:00Z',source='SYNTHETIC',receipt='HAND',
            components=[dict(security_id=sid,issued_shares=30000000,share_basis='ISSUED_ORDINARY')]))
        for source in prices:
            row = copy.deepcopy(source)
            row['security_id'] = sid
            row['open'] += i/100
            row['close'] += i/100
            row['basis_alignment']['shares_filing_accn'] = f'{cik}-2014'
            data['prices'].append(row)
    data['factor_inputs'] = [dict(security_id=row['security_id'],effective_date='2016-02-01',filed='2016-02-01',known_at='2016-02-01T12:00:00Z',
        source='SYNTHETIC',receipt='HAND_PIT',currency='USD',period_start='2015-01-01',period_end='2015-12-31',
        eps_share_basis='ORDINARY_USD_ASOF_SIGNAL',eps_price_basis_receipt='HAND',
        values=dict(trailing_eps=1+i/100,net_income_ttm=10000000+i*10000,sales_ttm=100000000,equity=50000000,ebitda_ttm=20000000,
                    debt=10000000,cash=5000000,preferred_equity=0,minority_interest=0,
                    cash_dividends_ttm=2000000,buybacks_ttm=4000000,issuance_ttm=1000000)) for i,row in enumerate(data['membership'])]
    return data


def test_explicit_fixed_n_ids_do_not_execute_other_variants():
    try:
        cells = runner._selected_cells(frozen_spec(),'TARGET_QGV_V2','primary',experiment_ids=['W0-N15-Q'])
    except TypeError:
        pytest.fail('fixed-N allowlist not implemented')
    assert len(cells) == 2
    assert {c['strategy_id'] for c in cells} == {'W0-N15-Q'}
    with pytest.raises(ValueError,match='UNKNOWN_EXPERIMENT'):
        runner._selected_cells(frozen_spec(),'TARGET_QGV_V2','primary',experiment_ids=['typo'])


def test_extension_reuses_ledger_for_dynamic_slots_and_two_independent_pools():
    ext = default_extension()
    cells = [c for c in selected_cells(ext,'primary') if c['id'] in ('DEC-ALL-W0-Q-D1','DEC-SPX-W0-Q-D1')]
    cache = PreparationCache()
    try:
        result = runner.replay_bundle(spec(),large_bundle(),'TARGET_QGV_V2',cells=cells,extension=ext,preparation_cache=cache)
    except TypeError:
        pytest.fail('extension runner dispatcher missing')
    assert result['status'] == 'REPLAY_COMPLETE'
    assert len(result['runs']) == 2
    for run in result['runs']:
        assert run['status'] == 'COMPLETE'
        assert run['coverage'][0]['slots'] == 11
        assert len(run['decisions'][0]['selected']) == 11
        assert run['fills'] and run['fills'][0]['session'] == '2016-02-16'
        assert run['cell']['source_type'] == 'QGV_REPRODUCED'
        assert all(float(row['cash']) >= 0 for row in run['nav'])
    assert cache.stats['misses'] >= 2


def test_factor_cohort_creates_both_paired_portfolios_and_reuses_preparation_for_costs():
    ext, cache = default_extension(), PreparationCache()
    cells = [c for c in selected_cells(ext,'sensitivity',['FAC-SPX-F03-Q']) if c['cost_bps'] in (10,30)]
    try:
        result = runner.replay_bundle(spec(),large_bundle(),'TARGET_QGV_V2',cells=cells,extension=ext,preparation_cache=cache)
    except TypeError:
        pytest.fail('matched runner dispatcher missing')
    assert len(result['runs']) == 4
    assert all(run['status'] == 'COMPLETE' for run in result['runs'])
    assert {r['cell']['role'] for r in result['runs']} == {'FACTOR','MATCHED_QGV'}
    assert all(r['cell']['source_type'] == 'MATCHED_HEAD_TO_HEAD' for r in result['runs'])
    assert len({json.dumps(r['decisions'][0]['selected']) for r in result['runs'] if r['cell']['role']=='FACTOR'}) == 1
    assert result['preparation_stats']['score_calls'] == 1


def test_missing_decile_coverage_does_not_turn_into_cash_or_drop_a_signal_date():
    ext = default_extension()
    cells = selected_cells(ext,'primary',['DEC-SPX-W0-Q-D1'])
    try:
        result = runner.replay_bundle(spec(),inputs(),'TARGET_QGV_V2',cells=cells,extension=ext)
    except TypeError:
        pytest.fail('failed-date gate missing')
    assert result['status'] == 'INCOMPLETE_REPLAY'
    assert result['runs'][0]['status'] == 'NO_DECILE_COVERAGE'
    assert result['runs'][0]['metrics'] is None
    assert not result['runs'][0]['fills']


def test_cli_extension_audit_has_no_fake_results_and_does_not_run_all_fixed30(tmp_path):
    path = tmp_path/'extension.json'
    path.write_text(json.dumps(default_extension()))
    script = Path(__file__).resolve().parents[2]/'tools/qgv_backtest_research.py'
    result = subprocess.run([sys.executable,str(script),'--stage','audit','--extension-spec',str(path),
                             '--experiment-id','DEC-SPX-W0-Q-D1'],capture_output=True,text=True)
    assert result.returncode == 2
    output = json.loads(result.stdout)
    assert output['status'] == 'BLOCKED_ON_DATA'
    assert output['extension']['registered_deciles'] == 40
    assert output['extension']['registered_factor_cohorts'] == 60
    assert output['extension']['requested_cohorts'] == 1
    assert output['real_data_executed'] is False


def test_private_extension_report_renders_22_views_and_never_claims_synthetic_is_real(tmp_path,tiny_period_writer_contract):
    import hashlib
    data=large_bundle()
    manifest=manifest_for(tmp_path,data)
    manifest['cache_rights']=rights()
    manifest['resources']['research_universe']=copy.deepcopy(manifest['resources']['identities'])
    local=Path(manifest['bundle']['path'])
    saved=json.loads(local.read_text())
    saved['source_hashes']={name:row['sha256'] for name,row in manifest['resources'].items()}
    local.write_text(json.dumps(saved))
    manifest['bundle']['sha256']=hashlib.sha256(local.read_bytes()).hexdigest()
    output=tmp_path/'private'/'extension-report'
    result=runner.run_stage(spec(),'report','TARGET_QGV_V2',manifest,output,extension=default_extension(),
                             experiment_ids=['DEC-SPX-W0-Q-D1'])
    assert result['completed_cells']==1
    report=json.loads((output/'report.json').read_text())
    assert len(report['tables'])==22
    assert report['synthetic'] is True
    assert report['real_data_executed'] is False
    assert report['tables']['TABLE-A']['rows'][0]['metrics']['cagr']['verification_status']=='SYNTHETIC_ONLY'
    cached=runner.run_stage(spec(),'report','TARGET_QGV_V2',manifest,output,extension=default_extension(),
                             experiment_ids=['DEC-SPX-W0-Q-D1'])
    assert cached['cached'] is True
    assert cached['extension']['completed_cohorts']==1
