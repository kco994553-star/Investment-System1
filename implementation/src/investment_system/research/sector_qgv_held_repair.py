"""Pinned source delta repair; preserves population, classification, gates and settings."""
from copy import deepcopy
from collections import Counter, defaultdict
import hashlib
import json
import tarfile
import zipfile
from .sector_qgv import digest, timestamp, VALID
from .sector_qgv_held import checked_bytes, held_observations, ADAPTER_VERSION


def source_code_hash():
    from pathlib import Path
    names=('sector_qgv.py','sector_qgv_held.py','sector_qgv_held_repair.py','financial_v.py')
    return digest({n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest() for n in names})


def repair(snapshot, plan):
    if plan.get('schema_version')!='sector-qgv-held-repair/1':raise ValueError('REPAIR_PLAN_SCHEMA')
    if plan.get('snapshot_hash')!=digest(snapshot):raise ValueError('REPAIR_SNAPSHOT_MISMATCH')
    out=deepcopy(snapshot);rows={r['company_id']:r for r in out['rows']};seen=set();audit=[];cache={};reused=0
    if plan.get('retained_repair'):
        prior=json.loads(checked_bytes(plan['retained_repair']))
        if prior.get('source_code_hash')!=source_code_hash() or prior['valuation_date']!=snapshot['valuation_date'] or prior['as_of']!=snapshot['as_of']:
            raise ValueError('REPAIR_CACHE_CONTEXT_MISMATCH')
        for r in prior['rows']:
            cache[(r['source']['sha256'],r['record_context_hash'],r['accounting_template'])]=(r['observations'],r['diagnostics'],r['components'])
    grouped=defaultdict(list)
    for item in plan['rows']:
        key=item['company_id']
        if key in seen or key not in rows:raise ValueError('REPAIR_MEMBER_MISMATCH')
        seen.add(key);grouped[item['archive_id']].append(item)
    for archive_id,items in sorted(grouped.items()):
        spec=plan['archives'][archive_id];checked_bytes(spec)
        opener=zipfile.ZipFile if spec['format']=='ZIP' else tarfile.open
        with opener(spec['path']) as archive:
            for item in items:
                row=rows[item['company_id']];record=item['record'];sha=item['sha256']
                if (row.get('issuer_id')!=record.get('cik') or record['source_sha256']['companyfacts']!=sha or
                    timestamp(record['acquired_at'])>timestamp(snapshot['as_of'])):raise ValueError('REPAIR_SOURCE_CONTEXT')
                # The original observation must point to this exact source, not a newer acquisition.
                refs={p for o in row['observations'].values() for p in o.get('provenance',[])}
                if item['reference'] not in refs or '#sha256='+sha not in item['reference']:
                    raise ValueError('REPAIR_ORIGINAL_SOURCE_MISMATCH')
                key=(sha,digest(record),row.get('accounting_template'))
                if key not in cache:
                    body=archive.read(item['member']) if spec['format']=='ZIP' else archive.extractfile(item['member']).read()
                    if hashlib.sha256(body).hexdigest()!=sha:raise ValueError('REPAIR_MEMBER_HASH')
                    payload=json.loads(body)
                    if str(payload['cik']).zfill(10)!=row['issuer_id']:raise ValueError('REPAIR_ISSUER_MISMATCH')
                    obs,diag,components=held_observations(payload,record,item['reference'],as_of=snapshot['as_of'],
                        valuation_date=snapshot['valuation_date'],accounting_template=row.get('accounting_template'),include_components=True)
                    cache[key]=(obs,diag,components)
                else:reused+=1
                obs,diag,components=deepcopy(cache[key]);old=deepcopy(row['observations'])
                # Only Q/G bridge outputs; existing V and independent observations survive.
                row['observations'].update(obs);row['input_diagnostics']['held_input_repair']=diag
                changes=[{'variant_id':v,'before':old.get(v),'after':o}
                         for v,o in obs.items() if old.get(v)!=o]
                audit.append({'company_id':row['company_id'],'issuer_id':row['issuer_id'],
                    'accounting_template':row.get('accounting_template'),'source':{k:item[k] for k in ('archive_id','member','sha256','reference')},
                    'record_context_hash':digest(record),'components':components,'observations':obs,'diagnostics':diag,'changes':changes})
    out['input_version']=snapshot['input_version']+'+'+ADAPTER_VERSION
    out['snapshot_id']=snapshot['snapshot_id']+':input-repair:'+digest(plan)[:16]
    report={'schema_version':'sector-qgv-held-repair-audit/1','treatment':'INPUT_CONNECTION_REPAIR',
        'original_snapshot_hash':digest(snapshot),'new_snapshot_hash':digest(out),'plan_hash':digest(plan),
        'valuation_date':snapshot['valuation_date'],'as_of':snapshot['as_of'],'source_code_hash':source_code_hash(),
        'original_denominator':len(snapshot['members']),
        'reviewed_rows':len(audit),'reused_source_contexts':reused,'new_source_contexts':len(audit)-reused,'rows':audit,
        'classification_changed':False,'settings_changed':False,'official_gate_changed':False}
    return out,report


def comparison(before, after):
    """Exact code-row transitions; axes never assembled across issuer classes."""
    if before['config_hash']!=after['config_hash']:raise ValueError('REPAIR_CONFIG_CHANGED')
    for k in ('valuation_date','as_of','universe_id','universe_version','model_version','normalization_version','mapping_version'):
        if before[k]!=after[k]:raise ValueError('REPAIR_CONTEXT_CHANGED:'+k)
    old={r['company_id']:r for r in before['result_rows']};new={r['company_id']:r for r in after['result_rows']}
    if old.keys()!=new.keys():raise ValueError('REPAIR_DENOMINATOR_CHANGED')
    factors=defaultdict(Counter);axes=defaultdict(Counter);changed=[]
    def count(c,a,b):
        c['before']+=a is not None;c['after']+=b is not None
        c['gained']+=a is None and b is not None;c['lost']+=a is not None and b is None
        c['changed_common']+=a is not None and b is not None and a!=b
    for key,a in old.items():
        b=new[key];delta=[]
        if any(a[k]!=b[k] for k in ('issuer_id','sector_id','accounting_template','gate_status')):raise ValueError('REPAIR_CLASSIFICATION_OR_GATE_CHANGED')
        for v,x in a['factors'].items():
            y=b['factors'][v]
            for stage,field in [('raw','raw_value'),('score','score')]:
                count(factors[v+':'+stage+':all'],x[field],y[field])
                if v in b.get('selected_variants',[]):count(factors[v+':'+stage+':selected'],x[field],y[field])
            if x!=y:delta.append({'variant_id':v,'before':x,'after':y})
        for axis in ('Q','G','V'):count(axes[axis],a['axes'][axis],b['axes'][axis])
        count(axes['joint'],1 if all(x is not None for x in a['axes'].values()) else None,
                              1 if all(x is not None for x in b['axes'].values()) else None)
        count(axes['total'],a['total'],b['total'])
        if delta:changed.append({'company_id':key,'issuer_id':b['issuer_id'],'factors':delta,
            'before_axes':a['axes'],'after_axes':b['axes'],'before_total':a['total'],'after_total':b['total']})
    groups=defaultdict(lambda:{'members':0,'raw_valid':0,'scoring_representatives':0,'valid_n':set()})
    for r in new.values():
        for v in r.get('selected_variants',[]):
            g=groups[(r['sector_id'],r['accounting_template'],v)];f=r['factors'][v]
            g['members']+=1;g['raw_valid']+=f['raw_value'] is not None
            g['scoring_representatives']+=f['raw_value'] is not None and f['score_status']!='ISSUER_REPRESENTATIVE_UNRESOLVED'
            g['valid_n'].add(f['valid_n'])
    return {'schema_version':'sector-qgv-input-repair-comparison/1','treatment':'INPUT_CONNECTION_REPAIR',
        'denominator':len(old),'valuation_date':before['valuation_date'],
        'before_input_hash':before['input_hash'],'after_input_hash':after['input_hash'],
        'axes':{k:dict(v) for k,v in axes.items()},'factors':{k:dict(v) for k,v in factors.items()},'rows':changed,
        'groups':[dict(sector_id=k[0],accounting_template=k[1],variant_id=k[2],**{q:z for q,z in g.items() if q!='valid_n'},
                       valid_n=sorted(g['valid_n']),minimum=20,
                       structural_shortfall=g['members']<20) for k,g in sorted(groups.items())],
        'whole_market_denominator':None,'performance':'NOT_MEASURED'}
