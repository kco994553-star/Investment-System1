"""Fixed-core dual research adapter. No fetch, price reconstruction or new scorer."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from .sector_qgv import (CATALOG,SECTORS,TEMPLATES,FINANCIAL,MODEL,ENGINE,NORMALIZATION,
    default_config,preset,_roles,_validate_preset,validate_config,effective_weights,
    _preview_core,_mapped,digest,scoring_representatives,rank_result_rows,timestamp)
from .sector_qgv_reference import _records,_identity,_classification_ok,_compare_rows

VERSION='dual-qgv-research/0.1.0'
SCHEMA='qgv-dual-board/1'


def candidate_configs():
    base=dict(schema_version='qgv-dual-config/1',version='0.1.0',minimum=20,
        missing_policy='strict/1',gate_policy='official-q-percentile-required/1',
        research_knowledge_cutoff='2026-11-10T12:03:13Z',execution_version=VERSION,study_id='DUAL-QGV-20261110-01',additional_policy='CATALOG_ZERO_CORE_WEIGHT')
    common=preset(default_config(),'INFORMATION_TECHNOLOGY','GENERAL')
    common.update(sector_id=None,accounting_template=None,preset_id='unified-roa-core/0.1.0',scope='COMMON')
    common['axis_weights']={'Q':1,'G':1,'V':1}
    common['axes']={'Q':_roles([('roa_ttm',100)]),'G':_roles([('roa_improvement_3y',100)]),
                   'V':_roles([('ep_ttm_diluted',50),('common_bp',50)])}
    u1=dict(base,model_id='unified-roa-core/0.1.0',kind='COMMON',uniform_preset=common)
    u2=deepcopy(u1);u2['model_id']='unified-sales-core/0.1.0';u2['uniform_preset']['preset_id']=u2['model_id']
    u2['uniform_preset']['axes']['G']=_roles([('revenue_cagr_3y',100)])
    sector=default_config()
    for s in SECTORS:
        for t in TEMPLATES:
            p=preset(sector,s,t)
            q=('roa_ttm','common_equity_assets') if t in FINANCIAL else ('cfo_assets_ttm','debt_assets') if t=='EQUITY_REIT' else ('operating_margin_ttm','debt_assets')
            p['axes']['Q']=_roles([(q[0],70),(q[1],30)])
            p['axes']['G']=_roles([('cfo_assets_improvement_3y' if t=='EQUITY_REIT' else 'roa_improvement_3y',100)])
            # Financial/asset-manager V already has the fixed two earnings/book roles.
            if len(p['axes']['V'])>2:
                kept={k:deepcopy(v) for k,v in p['axes']['V'].items() if k in ('earnings','cash')}
                total=sum(x['weight'] for x in kept.values())
                first=next(iter(kept));w=round(kept[first]['weight']*10000/total)
                kept[first]['weight']=w
                for k in kept:
                    if k!=first:kept[k]['weight']=10000-w
                p['axes']['V']=kept
            sector['scoped_overrides'][s+'|'+t]=p
    return {'U1':u1,'U2':u2,'S1':dict(base,model_id='sector-reduced-core/0.1.0',kind='SECTOR',sector_config=sector)}


def validate_model(config):
    required={'schema_version':'qgv-dual-config/1','version':'0.1.0','minimum':20,
        'missing_policy':'strict/1','gate_policy':'official-q-percentile-required/1',
        'execution_version':VERSION,'additional_policy':'CATALOG_ZERO_CORE_WEIGHT'}
    if any(config.get(k)!=v for k,v in required.items()) or not config.get('model_id') or not config.get('study_id'):
        raise ValueError('DUAL_CONFIG_INVALID')
    try:timestamp(config['research_knowledge_cutoff'])
    except (ValueError,TypeError,KeyError,AttributeError):raise ValueError('DUAL_RESEARCH_CUTOFF_INVALID') from None
    if config.get('kind')=='COMMON':
        if 'sector_config' in config:raise ValueError('DUAL_CONFIG_CONFLICT')
        p=deepcopy(config['uniform_preset']);w=p['axis_weights']
        if set(w)!=set('QGV') or any(type(x)!=int or x<=0 for x in w.values()):raise ValueError('DUAL_AXIS_WEIGHTS_INVALID')
        p['axis_weights']={'Q':3400,'G':3300,'V':3300};_validate_preset(p)
    elif config.get('kind')=='SECTOR':
        if 'uniform_preset' in config:raise ValueError('DUAL_CONFIG_CONFLICT')
        validate_config(config['sector_config'])
    else:raise ValueError('DUAL_KIND_INVALID')


def _code_files():
    return [Path(__file__).with_name(n) for n in
        ('dual_qgv.py','sector_qgv.py','sector_qgv_registry.py','sector_qgv_reference.py')] + [Path(__file__).parent.parent/'qgv/qgv_v2.py']


def _code_hash():
    return digest({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in _code_files()})


def _binding(config,evaluation,reference):
    return dict(model_hash=digest(config),evaluation=_identity(evaluation),reference=_identity(reference),
        code_hash=_code_hash(),engine_version=ENGINE,adapter_version=VERSION)


def _classification_valid(row,snapshot):
    ctx=snapshot.get('classification_context') or {}
    sources=ctx.get('source_contexts')
    if sources:
        match=[x for x in sources if x.get('classification_hash')==(row.get('mapping') or {}).get('common_classification_hash')]
        if len(match)!=1:return False
        snapshot=dict(snapshot,classification_context=match[0])
    elif row.get('classification_record_id') and not ctx.get('classification_hash'):return False
    return _classification_ok(row,snapshot)


def _validate_contexts(evaluation,reference,cutoff):
    contexts=[]
    for snapshot in (evaluation,reference):
        ctx=snapshot.get('classification_context') or {}
        cs=ctx.get('source_contexts') or ([ctx] if ctx else [])
        required=any(r.get('classification_record_id') or (r.get('mapping') or {}).get('common_classification_hash') for r in snapshot['rows']) or str(ctx.get('dictionary_version','')).startswith('common-')
        if required:
            if not cs or any(not all(isinstance(c.get(k),str) and c[k] for k in
                ('classification_hash','dictionary_version','mapping_version','knowledge_as_of')) for c in cs):
                raise ValueError('DUAL_CLASSIFICATION_CONTEXT_MISSING')
        contexts.extend(cs)
    for c in contexts:
        if c.get('knowledge_as_of'):
            try:
                if timestamp(c['knowledge_as_of'])>timestamp(cutoff):raise ValueError('FUTURE_KNOWLEDGE')
            except (ValueError,TypeError,AttributeError):raise ValueError('DUAL_CLASSIFICATION_TIME_INVALID') from None
    for key in ('dictionary_version','mapping_version','knowledge_as_of'):
        if len({c.get(key) for c in contexts})>1:raise ValueError('DUAL_CLASSIFICATION_CONTEXT_MISMATCH')


def _scope(row,kind):
    return 'COMMON' if kind=='COMMON' else 'SECTOR|'+str(row.get('sector_id'))+'|'+str(row.get('accounting_template'))


def _rank_factors(rows):
    """Existing total sorter reused on factor scores; issuer-factor research scopes."""
    for v in CATALOG:
        groups=defaultdict(list)
        for r in rows:
            f=r['factors'][v];f.update(rank=None,rank_n=0,decile=None,decile_status='NO_VALID_SCORE')
            if f['score'] is not None:groups[r['ranking_scope']].append(r)
        for group in groups.values():
            ranked=rank_result_rows([dict(company_id=r['company_id'],total=r['factors'][v]['score']) for r in group]);n=len(ranked)
            bins=[]
            if n>=10:
                k=n//10;q,rem=divmod(n-2*k,8)
                bins=[10]*k+[d for i,d in enumerate(range(9,1,-1)) for _ in range(q+(i<rem))]+[1]*k
            order={r['company_id']:i for i,r in enumerate(ranked)}
            for r in group:
                i=order[r['company_id']];r['factors'][v].update(rank=i+1,rank_n=n,decile=bins[i] if bins else None,
                    decile_status='VALID' if bins else 'SAMPLE_LT_10')


def _coverage(rows,evaluation):
    def count(sub):return {'code_rows':len(sub),'issuers':len({r['issuer_id'] for r in sub if r.get('issuer_id')})}
    den=count(rows);den['security_ids_present']=len({r['security_id'] for r in rows if r.get('security_id')})
    stages={}
    for stage,valid in [('core_inputs',lambda r:bool(r['selected_variants']) and all(r['factors'][v]['raw_components_available'] or r['factors'][v]['verified_external_available'] for v in r['selected_variants'])),
        ('core_raw',lambda r:bool(r['selected_variants']) and all(r['factors'][v]['raw_value'] is not None for v in r['selected_variants'])),
        ('core_scores',lambda r:bool(r['selected_variants']) and all(r['factors'][v]['score'] is not None for v in r['selected_variants'])),
        *[(a,lambda r,a=a:r['axes'][a] is not None) for a in 'QGV'],
        ('joint',lambda r:all(r['axes'][a] is not None for a in 'QGV')),('total',lambda r:r['total'] is not None)]:
        stages[stage]=count([r for r in rows if valid(r)])
    factors={};causes=defaultdict(list)
    for r in rows:
        reasons=set()
        if not r['selected_variants']:reasons.add(r['status'])
        for v in r['selected_variants']:
            f=r['factors'][v]
            if f['score'] is None:reasons.add(f['score_status'])
        if r['gate_status']=='UNKNOWN':reasons.add('GATE_UNKNOWN')
        for reason in reasons:causes[reason].append(r)
    for v in CATALOG:
        selected=[r for r in rows if v in r['selected_variants']]
        factors[v]={'selected':count(selected),'raw':count([r for r in selected if r['factors'][v]['raw_value'] is not None]),
                    'score':count([r for r in selected if r['factors'][v]['score'] is not None])}
    blocked=[r for r in rows if any(r['factors'][v]['score_status']=='PEER_SAMPLE_SMALL' for v in r['selected_variants'])]
    target={k:math.ceil(.95*den[k]) for k in ('code_rows','issuers')}
    return dict(denominator=den,target95=target,stages=stages,selected_factors=factors,
        causes_overlap=True,causes={k:count(v) for k,v in sorted(causes.items())},
        incomplete_unique=count([r for r in rows if r['total'] is None]),
        current_sample_barrier=count(blocked),
        gap95={stage:{k:max(0,target[k]-stages[stage][k]) for k in target} for stage in ('joint','total')},
        whole_market_denominator=None,whole_market_coverage=None)


def run_board(config,evaluation,reference,*,request_id):
    validate_model(config)
    if any(evaluation.get(k)!=reference.get(k) for k in ('schema_version','mapping_version','valuation_date','as_of')):
        raise ValueError('DUAL_CONTEXT_MISMATCH')
    _validate_contexts(evaluation,reference,config['research_knowledge_cutoff'])
    ev,refs=_records(evaluation),_records(reference)
    if any(k not in refs or refs[k]!=v for k,v in ev.items()):raise ValueError('DUAL_TARGET_INPUT_MISMATCH')
    if any(_mapped(r,evaluation) and not _classification_valid(r,evaluation) for r in ev.values()):
        raise ValueError('DUAL_EVALUATION_CLASSIFICATION_INVALID')
    # One retained context; invalid classification is not promoted, raw observations survive.
    clean=deepcopy(reference)
    for r in clean['rows']:
        if not _classification_valid(r,reference):r['mapping']=None
    cfg=default_config() if config['kind']=='COMMON' else config['sector_config']
    internal=_preview_core(cfg,clean,request_id,execution=config)
    peers,_=scoring_representatives(_records(clean));rows=[];pool=defaultdict(list)
    for r in internal['result_rows']:
        if r['company_id'] in peers and _mapped(refs[r['company_id']],clean) and _classification_valid(refs[r['company_id']],reference):
            for v,f in r['factors'].items():
                if f['raw_value'] is not None:pool[(_scope(r,config['kind']),v)].append(r['company_id'])
        if r['company_id'] not in ev:continue
        r=deepcopy(r);r['ranking_scope']=_scope(r,config['kind']);r['rank']=None;r['rank_n']=0
        r['selected_variants']=r.get('selected_variants',[]);r['scoring_representative']=r['company_id'] in peers
        for v,f in r['factors'].items():f['kind']='CORE' if v in r['selected_variants'] else 'ADDITIONAL'
        rows.append(r)
    groups=[]
    for (scope,v),members in sorted(pool.items()):
        groups.append(dict(ranking_scope=scope,variant_id=v,valid_n=len(members),members_hash=digest(sorted(members)),
            issuer_members_hash=digest(sorted(refs[k]['issuer_id'] for k in members))))
    scopes=defaultdict(list)
    for r in rows:scopes[r['ranking_scope']].append(r)
    for group in scopes.values():
        n=len(rank_result_rows(group))
        for r in group:r['rank_n']=n
    _rank_factors(rows)
    active=sorted({k for members in pool.values() for k in members})
    candidate_identity=_identity(reference)
    identity=dict(candidate_identity,id=candidate_identity['id']+':'+config['kind']+'_FACTOR_REFERENCES',
        members_hash=digest(active),code_rows=len(active),issuers=len({refs[k]['issuer_id'] for k in active}),
        factor_members_hash=digest(groups),candidate_population=candidate_identity,
        scope='FACTOR_INPUT_ELIGIBILITY_NOT_LISTING_OR_INVESTMENT_ELIGIBILITY')
    binding=_binding(config,evaluation,reference);key=digest(binding)
    result=dict(schema_version=SCHEMA,model_id=config['model_id'],model_version=config['version'],configuration=deepcopy(config),
        engine_version=ENGINE,adapter_version=VERSION,normalization_version='common-midrank-strict20/1' if config['kind']=='COMMON' else NORMALIZATION,
        evaluation_population=_identity(evaluation),reference_population=identity,groups=groups,
        bindings=binding,cache_key=key,request_id=request_id,rows=rows,coverage=_coverage(rows,evaluation),
        classification_mode='RETROSPECTIVE_RECONSTRUCTION' if any(timestamp(c['knowledge_as_of'])>timestamp(evaluation['as_of']) for c in
            (reference.get('classification_context',{}).get('source_contexts') or [reference.get('classification_context',{})]) if c.get('knowledge_as_of')) else 'AS_OF_CLASSIFICATION_NOT_SYSTEM_PIT_PROOF',
        performance_state='NOT_MEASURED',operating_adoption='NOT_ADOPTED',deployment_state='NOT_STARTED',visibility='PRIVATE_RESEARCH')
    result['result_hash']=digest({k:v for k,v in result.items() if k!='request_id'})
    return result


def project_board(result,visible_ids):
    if len(set(visible_ids))!=len(visible_ids) or not set(visible_ids)<={r['company_id'] for r in result['rows']}:raise ValueError('DUAL_DISPLAY_INVALID')
    out=deepcopy(result);out['rows']=[r for r in out['rows'] if r['company_id'] in set(visible_ids)]
    out['projection_only']=True;return out


def save_board(config,result):
    if digest(config)!=result['bindings']['model_hash']:raise ValueError('DUAL_SAVE_CONFIG_MISMATCH')
    return dict(schema_version='qgv-dual-saved/1',configuration=deepcopy(config),bindings=deepcopy(result['bindings']),result_hash=result['result_hash'])


def replay_board(saved,evaluation,reference,request_id):
    if saved.get('schema_version')!='qgv-dual-saved/1':raise ValueError('DUAL_REPLAY_SCHEMA')
    if _binding(saved['configuration'],evaluation,reference)!=saved['bindings']:raise ValueError('DUAL_REPLAY_INPUT_MISMATCH')
    r=run_board(saved['configuration'],evaluation,reference,request_id=request_id)
    if r['result_hash']!=saved['result_hash']:raise ValueError('DUAL_REPLAY_RESULT_MISMATCH')
    return r


def compare_boards(before,after,comparison_id,cause):
    a=before.get('rows',before.get('result_rows'));b=after['rows']
    result=_compare_rows(a,b)
    for r in result['rows']:
        for f in r['factors']:f['reason']=cause
    result.update(comparison_id=comparison_id,cause=cause,
        common_total_company_ids=[r['company_id'] for r in result['rows'] if r['before_total'] is not None and r['after_total'] is not None],
        rank_changes_comparable=cause!='WHOLE_MODEL_DIFFERENCE',performance=None)
    return result


def evidence_catalog():
    return {'schema_version':'qgv-dual-evidence/1','candidates':candidate_configs(),
        'factors':deepcopy(CATALOG),'evidence_class':'CONCEPT_REFERENCE_SYSTEM_VARIANT',
        'source':'DUAL_QGV.md','performance':'NOT_MEASURED'}


def json_bytes(value):
    return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()


def delivery_artifacts(boards,*,max_bytes=1_800_000):
    """Static authenticated summary/index/detail shards; no frontend recomputation."""
    if not boards:raise ValueError('DUAL_DELIVERY_EMPTY')
    first=next(iter(boards.values()));context=first['evaluation_population']
    ids=[r['company_id'] for r in first['rows']]
    if any(b['evaluation_population']!=context or [r['company_id'] for r in b['rows']]!=ids for b in boards.values()):
        raise ValueError('DUAL_DELIVERY_CONTEXT_MISMATCH')
    meta={k:{f:deepcopy(b[f]) for f in ('model_id','model_version','configuration','engine_version','adapter_version',
        'normalization_version','evaluation_population','reference_population','bindings','cache_key','result_hash',
        'coverage','classification_mode','performance_state','operating_adoption','deployment_state')} for k,b in boards.items()}
    # The sector config is a registered shared preset; hash plus model id in a small summary.
    for m in meta.values():
        m['configuration_hash']=digest(m.pop('configuration'))
        m['coverage'].pop('selected_factors',None)
    summary=dict(schema_version='qgv-dual-delivery/1',visibility='PRIVATE_RESEARCH',boards=meta)
    parts={'summary.json':summary};index=[];detail_rows=[];shard=0
    def flush():
        nonlocal shard,detail_rows
        if detail_rows:parts[f'detail-{shard:03}.json']={'schema_version':'qgv-dual-detail/1','rows':detail_rows};shard+=1;detail_rows=[]
    for i,key in enumerate(ids):
        detail={'company_id':key,'boards':{}}
        head={'company_id':key,'issuer_id':first['rows'][i]['issuer_id'],'security_id':first['rows'][i]['security_id'],'boards':{}}
        for name,b in boards.items():
            row=b['rows'][i];view=deepcopy(row)
            for f in view['factors'].values():f.pop('raw_value',None)
            detail['boards'][name]=view
            head['boards'][name]={k:row.get(k) for k in ('axes','total','rank','rank_n','ranking_scope','status','gate_status')}
        if len(json_bytes({'schema_version':'qgv-dual-detail/1','rows':detail_rows+[detail]}))>max_bytes:flush()
        if len(json_bytes({'schema_version':'qgv-dual-detail/1','rows':[detail]}))>max_bytes:raise ValueError('DUAL_DETAIL_TOO_LARGE')
        head['detail_file']=f'detail-{shard:03}.json';index.append(head);detail_rows.append(detail)
    flush();parts['index.json']={'schema_version':'qgv-dual-index/1','evaluation_population':context,'rows':index}
    if any(len(json_bytes(v))>max_bytes for v in parts.values()):raise ValueError('DUAL_DELIVERY_SIZE_LIMIT')
    return parts
