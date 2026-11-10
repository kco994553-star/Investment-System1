"""Research-only reference population adapter around the existing QGV engine."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .sector_qgv import (CATALOG, MIN_SAMPLE, digest, config_hash, preview_qgv,
    validate_config, _input_identity, _mapped, _validated_observation,
    scoring_representatives, rank_result_rows, timestamp)
from .sector_qgv_registry import ENGINE, MODEL, NORMALIZATION
from .sector_qgv_partial import assert_retained_preview

CONTRACT='sector-qgv-reference-study/1'
POLICY='research-reference-additive/1'
ADAPTER='sector-qgv-reference-adapter/0.1.0'


def _records(snapshot):
    members=snapshot['members'];rows=snapshot['rows']
    if len(set(members))!=len(members) or len({r['company_id'] for r in rows})!=len(rows):
        raise ValueError('REFERENCE_DUPLICATE_MEMBER')
    if any(r['company_id'] not in members for r in rows):raise ValueError('REFERENCE_OUTSIDE_MEMBER')
    # Missing input rows remain in the original denominator.
    by={r['company_id']:r for r in rows}
    return {k:by.get(k,{'company_id':k}) for k in sorted(members)}


def _identity(snapshot):
    rows=_records(snapshot)
    return dict(id=snapshot['universe_id'],version=snapshot['universe_version'],
        members_hash=digest(sorted(snapshot['members'])),valuation_date=snapshot['valuation_date'],
        as_of=snapshot['as_of'],code_rows=len(rows),issuers=len({r['issuer_id'] for r in rows.values() if r.get('issuer_id')}),
        input_hash=_input_identity(snapshot),snapshot_id=snapshot['snapshot_id'],
        classification_records_hash=digest([{k:r.get(k) for k in ('company_id','classification_record_id')}
            for r in rows.values()]),
        classification_context=deepcopy(snapshot.get('classification_context')))


def _bindings(config,ev,base,source,source_preview,plan):
    return dict(config_hash=config_hash(config),evaluation=_identity(ev),reference_source=_identity(source),
        retained_evaluation_preview_hash=digest(base),retained_reference_preview_hash=digest(source_preview),
        plan_hash=digest(plan),engine_version=ENGINE,model_version=MODEL,normalization_version=NORMALIZATION,
        reference_adapter_version=ADAPTER,reference_code_hash=digest({n:hashlib.sha256(Path(__file__).with_name(n).read_bytes()).hexdigest()
            for n in ('sector_qgv.py','sector_qgv_registry.py','sector_qgv_reference.py')}))


def _classification_ok(row,snapshot):
    if not _mapped(row,snapshot):return False
    ctx=snapshot.get('classification_context',{});m=row['mapping']
    if ctx.get('classification_hash'):
        if (not row.get('classification_record_id') or
            m.get('common_classification_hash')!=ctx['classification_hash'] or
            m.get('common_record_id')!=row['classification_record_id'] or
            m.get('common_dictionary_version')!=ctx.get('dictionary_version') or
            m.get('common_mapping_version')!=ctx.get('mapping_version') or
            m.get('knowledge_as_of')!=ctx.get('knowledge_as_of')):return False
    return True


def _validate_common_contexts(evaluation,source):
    required=any('classification_hash' in s.get('classification_context',{}) or
        str(s.get('classification_context',{}).get('dictionary_version','')).startswith('common-') or
        any(r.get('mapping',{}).get('common_classification_hash') or r.get('classification_record_id') for r in s['rows'])
        for s in (evaluation,source))
    if not required:return
    for s in (evaluation,source):
        ctx=s.get('classification_context',{})
        if any(not isinstance(ctx.get(k),str) or not ctx[k] for k in
            ('classification_hash','dictionary_version','mapping_version','knowledge_as_of')):
            raise ValueError('REFERENCE_CLASSIFICATION_CONTEXT_MISSING')
        try:timestamp(ctx['knowledge_as_of'])
        except (TypeError,ValueError):raise ValueError('REFERENCE_CLASSIFICATION_CONTEXT_TIME') from None


def run_reference_study(config,evaluation,baseline,source,source_preview,plan,*,request_id):
    """Append individually validated, declared-factor references; never replace targets."""
    validate_config(config)
    if (plan.get('schema_version')!='sector-qgv-reference-plan/1' or plan.get('policy')!=POLICY or
        plan.get('minimum')!=MIN_SAMPLE or any(not isinstance(plan.get(k),str) or not plan[k]
        for k in ('study_id','version','reference_id','reference_version'))):raise ValueError('REFERENCE_PLAN_INVALID')
    if any(evaluation.get(k)!=source.get(k) for k in ('valuation_date','as_of','mapping_version')):
        raise ValueError('REFERENCE_CONTEXT_MISMATCH')
    _validate_common_contexts(evaluation,source)
    for k in ('dictionary_version','mapping_version','knowledge_as_of'):
        if evaluation.get('classification_context',{}).get(k)!=source.get('classification_context',{}).get(k):
            raise ValueError('REFERENCE_CLASSIFICATION_CONTEXT_MISMATCH')
    for s,p in ((evaluation,baseline),(source,source_preview)):
        _records(s);assert_retained_preview(p,s,config)
        if any(p.get(k)!=v for k,v in [('engine_version',ENGINE),('model_version',MODEL),('normalization_version',NORMALIZATION)]):
            raise ValueError('REFERENCE_ENGINE_VERSION_MISMATCH')
    declared=[]
    for g in plan['eligible_groups']:
        key=(g['sector_id'],g['accounting_template'],g['variant_id'])
        if key in declared or key[2] not in CATALOG or CATALOG[key[2]]['axis'] not in ('Q','G'):
            raise ValueError('REFERENCE_GROUP_INVALID')
        declared.append(key)
    if not declared or plan['reference_id']==evaluation['universe_id']:raise ValueError('REFERENCE_GROUP_INVALID')
    evrows=_records(evaluation);srcrows=_records(source)
    eval_issuers={r['issuer_id'] for r in evrows.values() if r.get('issuer_id')}
    src_peers,_=scoring_representatives(srcrows)
    combined=deepcopy(evaluation);combined['rows']=list(deepcopy(evrows).values())
    additions=[];audit=[]
    for key,row in srcrows.items():
        rec=dict(company_id=key,issuer_id=row.get('issuer_id'),reason=None,reasons={},admitted_variants=[])
        group=(row.get('sector_id'),row.get('accounting_template'))
        variants=[v for s,t,v in declared if (s,t)==group]
        if row.get('issuer_id') in eval_issuers:rec['reason']='EVALUATION_ISSUER_RETAINED'
        elif not variants:rec['reason']='GROUP_NOT_TARGETED'
        elif not row.get('issuer_id'):rec['reason']='ISSUER_ID_MISSING'
        elif key not in src_peers:rec['reason']='ISSUER_REPRESENTATIVE_UNRESOLVED'
        elif not _classification_ok(row,source):rec['reason']='MAPPING_UNRESOLVED'
        else:
            if key in evrows:raise ValueError('REFERENCE_ROW_ID_CONFLICT')
            observations={}
            for v in sorted(variants):
                value,status,_,_=_validated_observation(row,v,source)
                if value is None:rec['reasons'][v]=status
                else:observations[v]=deepcopy(row['observations'][v])
            if observations:
                item=deepcopy(row);item['observations']=observations
                combined['rows'].append(item);additions.append(key)
                rec.update(reason='ADMITTED',admitted_variants=sorted(observations),
                    mapping=deepcopy(row['mapping']),observation_contexts={v:{k:o.get(k) for k in
                    ('formula_version','fiscal_period','source_available_at','retrieved_at','currency','provenance','validation_basis')}
                    for v,o in observations.items()})
            else:rec['reason']='NO_VALID_DECLARED_OBSERVATION'
        audit.append(rec)
    binding=_bindings(config,evaluation,baseline,source,source_preview,plan)
    combined.update(members=sorted([*evaluation['members'],*additions]),universe_id=plan['reference_id'],
        universe_version=plan['reference_version'],snapshot_id='reference-study:'+digest(binding),
        input_version=evaluation['input_version']+'+'+POLICY)
    combined['classification_context']={k:evaluation.get('classification_context',{}).get(k) for k in
        ('dictionary_version','mapping_version','knowledge_as_of')}
    combined['classification_context']['source_contexts']=[deepcopy(s.get('classification_context')) for s in (evaluation,source)]
    internal=preview_qgv(config,combined,request_id)
    target_set=set(evaluation['members'])
    result_rows=[deepcopy(r) for r in internal['result_rows'] if r['company_id'] in target_set]
    rank_result_rows(result_rows)
    cr=_records(combined);reps,_=scoring_representatives(cr);pools=defaultdict(list)
    for r in internal['result_rows']:
        if r['company_id'] not in reps or not r.get('selected_variants'):continue
        for v,f in r['factors'].items():
            if f['raw_value'] is not None:pools[(r['sector_id'],r['accounting_template'],v)].append(r['company_id'])
    pool_records=[dict(sector_id=k[0],accounting_template=k[1],variant_id=k[2],members=sorted(v),
        issuer_ids=sorted(cr[x]['issuer_id'] for x in v)) for k,v in sorted(pools.items())]
    actual_members=sorted({x for p in pool_records for x in p['members']})
    reference=dict(id=plan['reference_id'],version=plan['reference_version'],members_hash=digest(actual_members),
        group_members_hash=digest(pool_records),valuation_date=evaluation['valuation_date'],as_of=evaluation['as_of'],
        input_hash=_input_identity(combined),code_rows=len(actual_members),issuers=len(actual_members),
        candidate_code_rows=len(combined['members']),additional_issuers=len(additions),
        scope='FACTOR_VALID_RESEARCH_REFERENCES_NOT_LISTING_OR_SECURITY_ELIGIBILITY',
        source_population=_identity(source),classification_context=combined['classification_context'])
    groups=[]
    for s,t,v in sorted(declared):
        old=[r for r in baseline['result_rows'] if (r['sector_id'],r['accounting_template'])==(s,t)]
        members=pools.get((s,t,v),[])
        groups.append(dict(sector_id=s,accounting_template=t,variant_id=v,
            before_valid_n=sorted({r['factors'][v]['valid_n'] for r in old}),after_valid_n=len(members),
            reference_members=sorted(members),reference_issuers=sorted(cr[x]['issuer_id'] for x in members),
            additional_members=sorted(set(members)&set(additions)),minimum=MIN_SAMPLE))
    comparison=_compare_rows(baseline['result_rows'],result_rows)
    key=digest(dict(binding=binding,evaluation_population=_identity(evaluation),reference_population=reference))
    result=dict(schema_version=CONTRACT,study=deepcopy(plan),request_id=request_id,cache_key=key,
        result_id=digest({'cache':key,'request_id':request_id}),evaluation_population=_identity(evaluation),
        reference_population=reference,bindings=binding,result_rows=result_rows,comparison=comparison,groups=groups,
        admission={'rows':audit,'reason_counts':dict(Counter(x['reason'] for x in audit))},
        performance=None,whole_market_denominator=None,operating_adoption='NOT_ADOPTED',
        rank_scope='ORIGINAL_EVALUATION_POPULATION_ONLY',reference_snapshot=combined)
    return result


def _compare_rows(before,after):
    by={r['company_id']:r for r in before};rows=[];axes={};any_new=set();factor_counts=defaultdict(Counter)
    if set(by)!={r['company_id'] for r in after}:raise ValueError('REFERENCE_TARGETS_CHANGED')
    for axis in ('Q','G','V','joint','total'):
        counts=Counter();ids=defaultdict(set)
        for b in after:
            a=by[b['company_id']]
            def value(r):
                if axis=='joint':return 1 if all(r['axes'][x] is not None for x in 'QGV') else None
                return r['total'] if axis=='total' else r['axes'][axis]
            av,bv=value(a),value(b)
            for k,yes in [('before',av is not None),('after',bv is not None),('gained',av is None and bv is not None),
                          ('lost',av is not None and bv is None),('changed_common',av is not None and bv is not None and av!=bv)]:
                counts[k+'_rows']+=yes
                if yes and b['issuer_id']:ids[k].add(b['issuer_id'])
            if axis in 'QGV' and av is None and bv is not None:any_new.add(b['issuer_id'])
        axes[axis]={**counts,**{k+'_issuers':len(ids[k]) for k in ('before','after','gained','lost','changed_common')}}
    for b in after:
        a=by[b['company_id']]
        fs=[]
        for v in b.get('selected_variants',[]):
            x,y=a['factors'][v],b['factors'][v]
            for stage,field in [('raw','raw_value'),('score','score')]:
                fc=factor_counts[v+':'+stage]
                for k,yes in [('before',x[field] is not None),('after',y[field] is not None),
                    ('gained',x[field] is None and y[field] is not None),('lost',x[field] is not None and y[field] is None),
                    ('changed_common',x[field] is not None and y[field] is not None and x[field]!=y[field])]:fc[k+'_rows']+=yes
            if x!=y:fs.append(dict(variant_id=v,before=x,after=y,reason='REFERENCE_POPULATION_CHANGED'))
        rows.append(dict(company_id=b['company_id'],issuer_id=b['issuer_id'],before_axes=a['axes'],after_axes=b['axes'],
            before_total=a['total'],after_total=b['total'],before_rank=a['rank'],after_rank=b['rank'],factors=fs))
    return dict(denominator_code_rows=len(before),denominator_issuers=len({r['issuer_id'] for r in before if r['issuer_id']}),
        axes=axes,factors={k:dict(v) for k,v in factor_counts.items()},new_any_axis_issuers=len(any_new),rows=rows)


def project_reference_rows(result,visible_ids):
    if len(set(visible_ids))!=len(visible_ids) or not set(visible_ids)<={r['company_id'] for r in result['result_rows']}:
        raise ValueError('REFERENCE_DISPLAY_MEMBERS_INVALID')
    return dict(schema_version=CONTRACT,evaluation_population=deepcopy(result['evaluation_population']),
        reference_population=deepcopy(result['reference_population']),cache_key=result['cache_key'],
        result_rows=[deepcopy(r) for r in result['result_rows'] if r['company_id'] in set(visible_ids)])


def save_reference_settings(config,plan,result):
    if result['bindings']['config_hash']!=config_hash(config) or result['bindings']['plan_hash']!=digest(plan):
        raise ValueError('REFERENCE_SAVE_CONTEXT_MISMATCH')
    return dict(schema_version='sector-qgv-reference-saved/1',config=deepcopy(config),plan=deepcopy(plan),
        bindings=deepcopy(result['bindings']),evaluation_population=deepcopy(result['evaluation_population']),
        reference_population=deepcopy(result['reference_population']),cache_key=result['cache_key'],
        result_rows_hash=digest(result['result_rows']),result_payload_hash=_payload_hash(result))


def _payload_hash(result):
    return digest({k:result[k] for k in ('result_rows','comparison','groups','admission')})


def reference_view(result):
    """Small authenticated reader projection. Full admission evidence stays private."""
    view={k:deepcopy(result[k]) for k in ('study','request_id','cache_key','result_id','evaluation_population',
        'reference_population','bindings','comparison','groups','performance','whole_market_denominator',
        'operating_adoption','rank_scope')}
    view.update(schema_version='sector-qgv-reference-view/1',visibility='PRIVATE_RESEARCH',
        source_result_hash=digest({k:v for k,v in result.items() if k!='reference_snapshot'}))
    if len(json.dumps(view,ensure_ascii=False,indent=2,allow_nan=False).encode())+1>2_000_000:
        raise ValueError('REFERENCE_VIEW_SIZE_LIMIT')
    return view


def replay_reference_study(saved,evaluation,baseline,source,source_preview,*,request_id):
    if saved.get('schema_version')!='sector-qgv-reference-saved/1':raise ValueError('REFERENCE_REPLAY_SCHEMA')
    binding=_bindings(saved['config'],evaluation,baseline,source,source_preview,saved['plan'])
    if binding!=saved['bindings']:raise ValueError('REFERENCE_REPLAY_INPUT_MISMATCH')
    result=run_reference_study(saved['config'],evaluation,baseline,source,source_preview,saved['plan'],request_id=request_id)
    if (result['cache_key']!=saved['cache_key'] or digest(result['result_rows'])!=saved['result_rows_hash'] or
        _payload_hash(result)!=saved.get('result_payload_hash') or
        result['evaluation_population']!=saved['evaluation_population'] or result['reference_population']!=saved['reference_population']):
        raise ValueError('REFERENCE_REPLAY_RESULT_MISMATCH')
    return result
