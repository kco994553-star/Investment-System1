"""C7 immutable pre-access declarations; no automatic research configuration."""
from copy import deepcopy
from datetime import datetime
from .metrics import METRIC_VERSION
from .splits import aware
from .selection import number
from .walkforward import digest

POLICY='TC-D3P-006B+G1+D2'
PROFILES=('Aggressive','Balanced','Defensive')
AUTHORITY_REFS={'EVL_SPEC_v0.1':'7e920b6ef9bbe2664f0994b86ba10111daca2919',
    'TC-D3P-006B':'91d3e7d1843d439b8b94f09642ae913b586c6948',
    'TC-D3P-006B-C7-G1-D2':'0fd3de6b95c4bc69738cea5b1a11f0b6109768e6'}
FIXTURE_SCOPE='SYNTHETIC_SOFTWARE_VALIDATION_ONLY'
SCOPES=('SYNTHETIC_SOFTWARE_VALIDATION','REAL_PIT_RESEARCH_VALIDATION')
VIEWS=('GROSS_PRE_TAX','NET_OF_TRADING_COST_PRE_TAX','REAL_PRE_TAX','RISK_FREE_EXCESS_PRE_TAX')
# Canonical C3 paths only. New metrics/derivations require separate authority.
VIEW_METRICS=('total_return','cagr','mdd','annualized_volatility','sharpe','sortino',
              'calmar','longest_drawdown_periods')
UNITS={'total_return':'DECIMAL_RETURN','cagr':'DECIMAL_RETURN_PER_YEAR',
       'mdd':'DECIMAL_DRAWDOWN','annualized_volatility':'DECIMAL_PER_YEAR',
       'sharpe':'DIMENSIONLESS','sortino':'DIMENSIONLESS','calmar':'DIMENSIONLESS',
       'longest_drawdown_periods':'PERIODS'}

def metric_registration(metric_id, view, name, direction):
    if view not in VIEWS or name not in VIEW_METRICS:
        raise ValueError('unsupported canonical metric')
    return {'metric_id':metric_id,'path':['views',view,name],
        'formula_id':METRIC_VERSION+':'+view+':'+name,'version':METRIC_VERSION,
        'units':UNITS[name],'direction':direction,'provenance':'C6_BASELINE_C3_METRICS'}

def validate_plan(plan):
    p=deepcopy(plan)
    t=datetime.fromisoformat(p['registered_at']); aware(t)
    if (p['policy']!=POLICY or p['scope'] not in SCOPES or p['tax_mode']!='EXCLUDED'
            or p['partition']!='oos' or p['graph_policy']!='G1' or p['drift_policy']!='D2'
            or p['numeric_representation']!='CANONICAL_DECIMAL_FRACTION'
            or type(p['seed']) is not int or not p['source_checkpoint']
            or p['authority_refs']!=AUTHORITY_REFS
            or p['attempt_unit']!='ONE_COMPLETE_LANDSCAPE_ALL_PROFILE_SELECTION_AND_DESCRIPTIVE_ASSESSMENT'):
        raise ValueError('unapproved C7 contract/scope')
    if p['scope']==SCOPES[0]:
        if p['configuration_scope']!=FIXTURE_SCOPE:
            raise ValueError('synthetic values require fixture-only scope')
    elif p['configuration_scope']==FIXTURE_SCOPE:
        raise ValueError('fixture configuration cannot support real research')
    elif not p.get('research_configuration_authority'):
        raise ValueError('real numeric configuration requires separately approved authority')
    dims=p['dimensions']
    if not dims or len(set(dims))!=len(dims):
        raise ValueError('unique complete cohort/fold dimensions required')
    if set(p['cohort_metadata'])!=set(dims):
        raise ValueError('metadata coverage mismatch')
    pairs={(v['mode'],v['variant']) for v in p['cohort_metadata'].values()}
    required={(m,v) for m in ('ROLLING','EXPANDING') for v in ('PRIMARY','REBALANCE_GAP_STRESS')}
    if pairs!=required or any(not v['fold_id'] for v in p['cohort_metadata'].values()):
        raise ValueError('all required rolling/expanding primary/stress folds required')
    if set(p['profiles'])!=set(PROFILES):
        raise ValueError('all three integrated profiles required')
    if set(p['drift_registry'])!=set(dims):
        raise ValueError('complete C6 drift metadata required')
    for registry in p['drift_registry'].values():
        times=registry['times']
        if len(times)<2 or times!=sorted(set(times)) or registry['transitions']!=[list(v) for v in zip(times,times[1:])]:
            raise ValueError('explicit registered adjacent drift times required')
        for t in times: aware(datetime.fromisoformat(t))
        if not registry['scales'] or any(number(v)<=0 for v in registry['scales'].values()):
            raise ValueError('positive unchanged registered C6 scales required')
    for profile in p['profiles'].values():
        metrics=profile['metrics']; ids=[m['metric_id'] for m in metrics]
        if not ids or len(ids)!=len(set(ids)):
            raise ValueError('unique registered profile metrics required')
        for m in metrics:
            path=m['path']
            if len(path)!=3 or path[0]!='views':
                raise ValueError('unsupported metric path')
            expected=metric_registration(m['metric_id'],path[1],path[2],m['direction'])
            if m!=expected or m['direction'] not in ('min','max'):
                raise ValueError('canonical formula/version/units/direction required')
        if set(profile['plateau_tolerances'])!=set(ids):
            raise ValueError('explicit complete plateau tolerance registration required')
        for t in profile['plateau_tolerances'].values():
            if number(t)<0: raise ValueError('negative tolerance')
        for c in profile['constraints']:
            if (c['metric_id'] not in ids or c['operator'] not in ('<=','>=')
                    or c['configuration_scope']!=p['configuration_scope']
                    or not c['authority_ref']):
                raise ValueError('explicit constraint authority/metric required')
            number(c['limit'])
    digest(p)  # Reject NaN and noncanonical mutable JSON.
    return p
