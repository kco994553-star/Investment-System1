"""Frozen registry and metadata-first private input gate. No data acquisition."""
import hashlib
from datetime import date
from pathlib import Path
from itertools import product
REQUIRED_INPUTS=('membership','identities','financials','filings','prices','corporate_actions','benchmark','rates','calendar')

def validate_spec(s):
    from .scoring_adapter import variant_options
    from ...qgv.qgv_v2 import official_weights
    from ...qgv.v2_factors import CALC_VERSION
    if s['source']['scoring_source_sha']!='bb57398c9c22a2dfa2443c5f3a23db3848cbe5ce' or s['source']['calc_version']!=CALC_VERSION or s['source']['score_version']!='qgv-v2' or s['source']['type_scope']!='qgv2-type-scope/2026-10-17.1':raise ValueError('SCORING_SOURCE_CHANGED')
    if s['costs']['sensitivity_one_way_bps']!=[0,10,20,25,30] or s['costs']['primary_one_way_bps']!=10:raise ValueError('COST_GRID_CHANGED')
    if s['portfolio']['initial_capital']!=100000 or s['portfolio']['currency']!='USD':raise ValueError('PORTFOLIO_CONTRACT_CHANGED')
    if set(s['variants'])!={'W0','W1','W2','W3'}:raise ValueError('VARIANTS_CHANGED')
    for variant,record in s['variants'].items():
        tree=variant_options(variant)['weights'] or official_weights('balanced')
        if record['axis_input']!=tree['axis'] or record['inner']!=tree['inner']:raise ValueError('SCORING_WEIGHTS_CHANGED')
    expected={(w,n,'QUARTERLY') for w in ('W0','W1','W2','W3') for n in (10,15,20,25,50)}
    expected|={(w,n,'ANNUAL_FEBRUARY') for n in (15,25,50) for w in (('W0','W3') if n==15 else ('W0','W1','W2','W3'))}
    rows=s['strategies']
    if len(rows)!=30 or {(r['variant'],r['n'],r['rebalance']) for r in rows}!=expected or len({r['id'] for r in rows})!=30:raise ValueError('STRATEGY_REGISTRY_MISMATCH')
    for r in rows:
        suffix='Q' if r['rebalance']=='QUARTERLY' else 'Y'
        if r['id']!=f"{r['variant']}-N{r['n']}-{suffix}":raise ValueError('STRATEGY_ID_MISMATCH')
    if {r['id'] for r in rows if r['stage']=='primary'}!={f'W{w}-N15-Q' for w in range(4)}:raise ValueError('PRIMARY_CHANGED')
    for w,v in s['variants'].items():
        if v['type_weights']!=(w in ('W0','W2')) or v['gate'] is not True:raise ValueError('VARIANT_POLICY_MISMATCH')
        for f in v['inner'].values():
            if len(f)!=5 or any(x<0 for x in f.values()) or sum(f.values())!=100:raise ValueError('INNER_WEIGHT_MISMATCH')

def period_for(s, period_id):
    for p in s['period']['data_feasibility_ladder']:
        if p['label']==period_id:return p
    raise ValueError('UNKNOWN_PERIOD')

def execution_cells(s,period_id):
    validate_spec(s);period_for(s,period_id)
    return [dict(period_id=period_id,strategy_id=r['id'],panel=p,cost_bps=c) for r,p,c in product(s['strategies'],('COMMON','PRACTICAL'),s['costs']['sensitivity_one_way_bps'])]

def validate_period_contract(s):
    actual=[(p['label'],p['start'],p['end']) for p in s['period']['data_feasibility_ladder']]
    expected=[('TARGET_QGV_V2','1980-02-19','2025-12-31'),('SECONDARY_DIAGNOSTIC_NOT_TARGET','2000-02-22','2025-12-31'),('DATA_LIMITED_DIAGNOSTIC_NOT_TARGET','2016-02-16','2025-12-31')]
    if actual!=expected or s['period']['first_fill']!='1980-02-19' or s['period']['last_mark']!='2025-12-31':raise ValueError('PERIOD_CONTRACT_CHANGED')

def audit_inputs(s,m,period_id):
    validate_spec(s);validate_period_contract(s);p=period_for(s,period_id)
    out=dict(spec_id=s['spec_id'],period_id=period_id,period=p,status='BLOCKED_ON_DATA',oos_status='OOS_NOT_ESTABLISHED',blockers=[],strategies=[dict(id=r['id'],status='NOT_RUN',metrics=None) for r in s['strategies']],execution_cells=len(execution_cells(s,period_id)))
    if m is None:
        out['blockers']=['MISSING_PRIVATE_MANIFEST']+[f'MISSING_{k.upper()}' for k in REQUIRED_INPUTS];return out
    if m.get('protection_status') not in ('AUTHORIZED_NON_PROTECTED','AUTHORIZED_PROTECTED') or not m.get('access_receipt'):
        out.update(status='BLOCKED_ON_PERMISSION',blockers=['PROTECTION_ACCESS_NOT_ESTABLISHED']);return out
    if not all(m.get('rights',{}).get(k) is True for k in ('research','ai_processing','storage')) or not m.get('rights_receipt') or m.get('private_destination_verified') is not True:
        out.update(status='BLOCKED_ON_PERMISSION',blockers=['RIGHTS_OR_PRIVATE_DESTINATION_UNVERIFIED']);return out
    if m.get('protection_status')=='AUTHORIZED_PROTECTED':
        scope=m.get('protected_scope',{})
        try:
            valid=bool(scope.get('receipt')) and date.fromisoformat(scope['start'])<=date.fromisoformat(p['start']) and date.fromisoformat(scope['end'])>=date.fromisoformat(p['end'])
        except (KeyError,ValueError,TypeError):valid=False
        if not valid:
            out.update(status='BLOCKED_ON_PERMISSION',blockers=['PROTECTED_SCOPE_NOT_ESTABLISHED']);return out
    for name in REQUIRED_INPUTS:
        r=m.get('resources',{}).get(name,{})
        if not r.get('verified') or not r.get('source') or not r.get('rights_receipt'):
            out['blockers'].append(f'UNVERIFIED_{name.upper()}');continue
        try:
            if date.fromisoformat(r['start'])>date.fromisoformat(p['start']) or date.fromisoformat(r['end'])<date.fromisoformat(p['end']):
                out['blockers'].append(f'PERIOD_GAP_{name.upper()}');continue
            path=Path(r['path'])
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=r['sha256']:out['blockers'].append(f'INTEGRITY_{name.upper()}')
        except (KeyError,ValueError,OSError):out['blockers'].append(f'INVALID_{name.upper()}')
    if not out['blockers']:out['status']='INPUT_INTEGRITY_PASS'
    return out
