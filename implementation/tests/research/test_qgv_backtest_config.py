"""Registry and fail-closed execution contracts; no market fixtures."""
import copy
import importlib
import json
from pathlib import Path
import pytest

SPEC = Path('docs/backtest/QGV_BACKTEST_SPEC_V1_20261026.json')

def api():
    try:
        return importlib.import_module('investment_system.research.qgv_backtest.config')
    except ModuleNotFoundError:
        pytest.fail('research configuration implementation missing')

def test_registry_exact_set_and_run_dimensions():
    m=api(); s=json.loads(SPEC.read_text()); m.validate_spec(s)
    cells=m.execution_cells(s,'TARGET_QGV_V2')
    assert len(cells)==300
    assert len({tuple(sorted(c.items())) for c in cells})==300
    assert sum(c['cost_bps']==10 and c['strategy_id'].endswith('N15-Q') for c in cells)==8

def test_duplicate_or_unregistered_annual_rejected():
    m=api();s=json.loads(SPEC.read_text());s['strategies'][-1]=copy.deepcopy(s['strategies'][0])
    with pytest.raises(ValueError):m.validate_spec(s)

def test_no_manifest_blocks_every_strategy_without_fake_metrics():
    m=api();s=json.loads(SPEC.read_text());r=m.audit_inputs(s,None,'TARGET_QGV_V2')
    assert r['status']=='BLOCKED_ON_DATA'
    assert len(r['strategies'])==30
    assert all(x['status']=='NOT_RUN' and x['metrics'] is None for x in r['strategies'])
    assert r['oos_status']=='OOS_NOT_ESTABLISHED'

def test_unknown_protection_is_checked_before_any_resource_read(tmp_path):
    m=api();s=json.loads(SPEC.read_text());p=tmp_path/'must-not-read.json'
    p.write_text('invalid private payload')
    r=m.audit_inputs(s,{'protection_status':'UNKNOWN','bundle':str(p)},'TARGET_QGV_V2')
    assert r['status']=='BLOCKED_ON_PERMISSION'

def test_unknown_period_rejected():
    m=api();s=json.loads(SPEC.read_text())
    with pytest.raises(ValueError):m.audit_inputs(s,None,'AFTER_SEEING_RETURNS')

def test_protected_scope_required_before_integrity_reads():
    m=api();s=json.loads(SPEC.read_text())
    manifest={'protection_status':'AUTHORIZED_PROTECTED','access_receipt':'receipt',
              'rights':dict(research=True,ai_processing=True,storage=True),
              'rights_receipt':'receipt','private_destination_verified':True}
    r=m.audit_inputs(s,manifest,'TARGET_QGV_V2')
    assert r['status']=='BLOCKED_ON_PERMISSION'
    assert r['blockers']==['PROTECTED_SCOPE_NOT_ESTABLISHED']

@pytest.mark.parametrize('mutation',['axis','factor_names','cost','source','capital'])
def test_runtime_contract_rejects_spec_changes_it_cannot_execute(mutation):
    m=api();s=json.loads(SPEC.read_text())
    if mutation=='axis':s['variants']['W1']['axis_input']={'Q':100,'G':0,'V':0}
    if mutation=='factor_names':s['variants']['W0']['inner']['Q']={f'invented{i}':20 for i in range(5)}
    if mutation=='cost':s['costs']['sensitivity_one_way_bps']=[777]
    if mutation=='source':s['source']['scoring_source_sha']='changed'
    if mutation=='capital':s['portfolio']['initial_capital']=999
    with pytest.raises(ValueError):m.validate_spec(s)

def test_private_audit_rejects_silent_shortening_before_read():
    m=api();s=json.loads(SPEC.read_text())
    s['period']['data_feasibility_ladder'][0]['start']='2016-02-16'
    with pytest.raises(ValueError,match='PERIOD_CONTRACT_CHANGED'):
        m.audit_inputs(s,None,'TARGET_QGV_V2')
