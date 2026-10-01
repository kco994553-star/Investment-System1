"""Complete frozen source commitments and current C4/C5/C6 resolution."""
from copy import deepcopy
from hashlib import sha256
import json
from .robustness import (source_inventory, resolve_robustness)
from .statistical_kernels import MissingStatisticalEvidence
from .walkforward import digest
from .execution import input_payload
from .selection import number

def checkpoint(cohorts):
    """Hash bytes without deserializing target OOS metric values."""
    result={}
    for key,args in sorted(cohorts.items()):
        ledger,split,source,bundles,drift=args
        directories={'c5':source.directory,'c6':ledger.directory}
        directories.update({'c4:'+i:b['c4_ledger'].directory for i,b in bundles.items()})
        files={label:{p.name:sha256(p.read_bytes()).hexdigest()
              for p in sorted(directory.iterdir()) if p.suffix in ('.json','.jsonl')}
              for label,directory in directories.items()}
        result[key]={'files':files,'input_hash':digest({'drift':drift,'inputs':{i:{'baseline':input_payload(b['baseline']) if b.get('baseline') is not None else None, 'scenarios':{k:{'definition':v['definition'],'input':input_payload(v['input']) if v.get('input') is not None else None} for k,v in b['scenarios'].items()}} for i,b in bundles.items()}}),
                     'split_hash':digest(split.payload())}
    return result

def resolve_landscape(cohorts, plan, committed):
    if checkpoint(cohorts)!=committed:
        raise ValueError('changed/invalidated complete Landscape checkpoint')
    if set(cohorts)!=set(plan['dimensions']):
        raise MissingStatisticalEvidence('missing required cohort/fold')
    landscape={'cohorts':{},'roster':None,'domain':None,'baseline':None}
    upstream_codes={}
    for key,args in sorted(cohorts.items()):
        ledger,split,source,bundles,drift=args
        meta=plan['cohort_metadata'][key]
        registered=json.loads((ledger.directory/'robustness.json').read_text())['body']
        c6plan=registered['plan']
        if (meta['mode']!=split.plan.mode or meta['variant']!=c6plan['variant']
                or meta['fold_id']!=split.plan.oos.start.isoformat()
                or c6plan['scope']!=plan['scope']):
            raise ValueError('scope/cohort/fold identity mismatch')
        inv=source_inventory(source)
        roster=inv['roster']; domain=inv['spec']['parameter_space']['values']
        baseline=inv['search']['plan']['baseline']
        if landscape['roster'] is None:
            landscape.update(roster=deepcopy(roster),domain=deepcopy(domain),baseline=deepcopy(baseline))
        elif (landscape['roster']!=roster or landscape['domain']!=domain or landscape['baseline']!=baseline):
            raise ValueError('all profiles/cohorts must share complete Landscape')
        if any(r['trial']['status']=='INVALIDATED' for r in inv['rows']):
            raise ValueError('ancestor invalidation')
        c6rows=ledger.trials.records()
        if any(r['trial']['status']=='INVALIDATED' for r in c6rows):
            raise ValueError('C6 invalidation')
        saved_path=ledger.directory/'robustness-acceptance.json'
        if not saved_path.exists():
            raise MissingStatisticalEvidence('C6 mandatory evidence missing')
        saved=json.loads(saved_path.read_text())
        if saved.get('status')!='PASS':
            statuses=[e.get('status') for e in saved.get('results',{}).values()]
            if 'FAIL' in statuses: raise ValueError('C6 mandatory FAIL')
            raise MissingStatisticalEvidence('C6 mandatory NOT_RUN/incomplete')
        acceptance=resolve_robustness(ledger,split,source,bundles,drift)
        reports={}
        for kind in ('PARAMETER','DRIFT'):
            entry=acceptance['results'][kind]
            reports[kind]=json.loads((ledger.directory/entry['report_file']).read_text())['output']
        metrics={i:reports['PARAMETER']['baseline']['reports'][i]['metrics_report'] for i in roster}
        raw_drift=reports['DRIFT']
        landscape['cohorts'][key]={'inventory':inv,'acceptance':acceptance,
            'metrics':metrics,'drift':raw_drift,'c6_plan':c6plan,
            'split_hash':digest(split.payload())}
        upstream_codes[key]={'c5':inv['spec']['code_hash'],'c6':ledger.registration()['code_hash'],
            'c4':{i:b['c4_ledger'].registration()['code_hash'] for i,b in bundles.items()}}
    # Drift dimension registry is metadata, fixed before target result access.
    landscape['drift_dimensions']=plan['drift_dimensions']
    expected=[]
    for key in plan['dimensions']:
        for a,b in plan['drift_registry'][key]['transitions']:
            for coordinate in sorted(plan['drift_registry'][key]['scales']):
                expected.append([key,a,b,coordinate])
    if expected!=plan['drift_dimensions']:
        raise ValueError('drift independent dimension registry mismatch')
    vectors={}
    for identity in landscape['roster']:
        row=[]
        for key,a,b,coordinate in expected:
            item=landscape['cohorts'][key]['drift'][identity]
            registry=plan['drift_registry'][key]
            if (item['coordinate_scales']!=registry['scales']
                    or item['times']!=registry['times']
                    or item['convention']!='REGISTERED_COORDINATE_DELTA_OVER_SCALE'):
                raise ValueError('registered C6 drift scale/time/convention mismatch')
            times=item['times']; index=times.index(a)
            if times[index+1]!=b: raise ValueError('nonadjacent drift transition')
            scale=number(item['coordinate_scales'][coordinate])
            if scale<=0: raise ValueError('invalid C6 registered scale')
            raw=item['raw']
            delta=number(raw[index+1]['parameters'][coordinate])-number(raw[index]['parameters'][coordinate])
            row.append(str(abs(delta/scale)))  # Exact raw delta / existing scale, once.
        vectors[identity]=row
    landscape['drift_vectors']=vectors
    landscape['upstream_code_hashes']=upstream_codes
    return landscape

def metric_value(report, metric):
    value=report
    for part in metric['path']:
        if not isinstance(value,dict) or part not in value:
            raise MissingStatisticalEvidence('required metric support missing: '+metric['metric_id'])
        value=value[part]
    if value is None:
        raise MissingStatisticalEvidence('legitimately undefined metric: '+metric['metric_id'])
    number(value)  # Invalid/nonfinite required inputs FAIL.
    return value
