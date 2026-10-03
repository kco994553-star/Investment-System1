"""C7 integrated synthetic-only complete source and preregistered configuration."""
from copy import deepcopy
import json
from tests.evl_c6_fixture import setup_family, run_family, experiment, CODE, T
from investment_system.evl.landscape import checkpoint
from investment_system.evl.selection_contracts import (POLICY, AUTHORITY_REFS, PROFILES,
    FIXTURE_SCOPE, metric_registration)
from investment_system.evl.walkforward import digest
from investment_system.evl.profile_selection import register_selection, run_selection, resolve_selection

def prepare(path):
    cohorts={}
    for mode in ('ROLLING','EXPANDING'):
        for variant in ('PRIMARY','REBALANCE_GAP_STRESS'):
            key=mode+'-'+variant
            args=setup_family(path/key,mode=mode,variant=variant)
            assert run_family(args)['status']=='PASS'
            cohorts[key]=args[:5]
    dimensions=sorted(cohorts)
    meta={k:{'mode':a[1].plan.mode,
              'variant':k[len(a[1].plan.mode)+1:],
              'fold_id':a[1].plan.oos.start.isoformat()} for k,a in cohorts.items()}
    registries={}
    for k,a in cohorts.items():
        c6=json.loads((a[0].directory/'robustness.json').read_text())['body']['plan']
        histories=list(a[4].values())
        times=[h['time'] for h in histories[0]]
        assert all([h['time'] for h in history]==times for history in histories)
        registries[k]={'times':times,'transitions':[list(v) for v in zip(times,times[1:])],
                       'scales':deepcopy(c6['drift_scales'])}
    drift_dimensions=[[k,a,b,c] for k in dimensions for a,b in registries[k]['transitions']
                      for c in sorted(registries[k]['scales'])]
    metrics=[metric_registration('net_cagr','NET_OF_TRADING_COST_PRE_TAX','cagr','max'),
             metric_registration('net_mdd','NET_OF_TRADING_COST_PRE_TAX','mdd','min')]
    # Generic algorithm fixture for all profiles, not a complete research profile config.
    # Shared representatives/zero differences are permitted descriptive evidence.
    profiles={name:{'metrics':deepcopy(metrics),'plateau_tolerances':{'net_cagr':10,'net_mdd':1},
        'constraints':[{'metric_id':'net_mdd','operator':'<=','limit':1,
            'configuration_scope':FIXTURE_SCOPE,'authority_ref':'EXPLICIT_C7_SOFTWARE_FIXTURE'}]}
              for name in PROFILES}
    plan={'policy':POLICY,'scope':'SYNTHETIC_SOFTWARE_VALIDATION',
        'configuration_scope':FIXTURE_SCOPE,'registered_at':T.isoformat(),
        'source_checkpoint':'FROZEN_C4_C5_C6_SYNTHETIC_HASH_CHECKPOINT',
        'authority_refs':AUTHORITY_REFS,'partition':'oos','tax_mode':'EXCLUDED','seed':7,
        'graph_policy':'G1','drift_policy':'D2','numeric_representation':'CANONICAL_DECIMAL_FRACTION',
        'dimensions':dimensions,'cohort_metadata':meta,'profiles':profiles,
        'drift_registry':registries,'drift_dimensions':drift_dimensions,
        'attempt_unit':'ONE_COMPLETE_LANDSCAPE_ALL_PROFILE_SELECTION_AND_DESCRIPTIVE_ASSESSMENT'}
    ledger=experiment(path/'selection',next(iter(cohorts.values()))[1],'c7-fixture',
        digest(checkpoint(cohorts)),{},('selection_complete',),1)
    return ledger,cohorts,plan

def full_acceptance(path):
    ledger,cohorts,plan=prepare(path)
    register_selection(ledger,cohorts,plan)
    result=run_selection(ledger,cohorts,recorded_at=T)
    assert result['status']=='PASS',result
    report=resolve_selection(ledger,cohorts)
    return {'acceptance':result,'report_hash':digest(report),'code_hash':CODE,
        'profiles':report['output']['profiles'],'stage_hashes':[digest(s) for s in report['output']['stages']],
        'source_checkpoint_hash':digest(checkpoint(cohorts)),'holdout_state':'UNCONSUMED',
        'scope':'SYNTHETIC_SOFTWARE_VALIDATION','configuration_scope':FIXTURE_SCOPE,
        'real_pit_research_validation':'NOT_RUN_MISSING_COMPLETE_REAL_FAMILY',
        'Investor_QGV':'FUTURE_TRACK_C_INPUT','official':False}
