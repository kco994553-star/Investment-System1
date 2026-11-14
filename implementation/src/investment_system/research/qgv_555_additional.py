"""Add zero-contribution catalog factor views to saved 555 results, not scores."""
from copy import deepcopy
from collections import defaultdict
from datetime import datetime,timezone
from .qgv_555 import catalog,identity,_usable
from .sector_qgv import digest
from .dual_qgv import _rank_factors
from .sector_qgv_registry import CATALOG
from ..qgv.v2_scoring import _Pool,percentile


def attach(result,evaluation,reference):
    if result['evaluation']!=identity(evaluation) or result['reference']!=identity(reference):raise ValueError('INPUT_ANCHORS')
    if result['result_hash']!=digest({k:v for k,v in result.items() if k!='result_hash'}):raise ValueError('SOURCE_RESULT_HASH')
    out=deepcopy(result);cats=catalog();c=result['configuration'];points={};rmap={}
    for r in sorted(reference['rows'],key=lambda x:x['company_id']):
        if not r.get('issuer_id') or r.get('accounting_template')!='GENERAL':continue
        if r['issuer_id'] in points:continue
        points[r['issuer_id']]={m:_usable(r,m,reference)[0] for m in cats};rmap[r['issuer_id']]=r
    pools={('all',):_Pool(points)}
    for f in (lambda r:('industry',r.get('industry_group')),lambda r:('sector',r.get('sector_id'),r.get('accounting_template'))):
        groups=defaultdict(dict)
        for issuer,r in rmap.items():groups[f(r)][issuer]=points[issuer]
        pools.update({k:_Pool(v) for k,v in groups.items()})
    lookup={r['company_id']:r for r in evaluation['rows']}
    for outrow in out['rows']:
        r=lookup[outrow['company_id']];outrow['factors']={}
        selected={x['metric']:x for role in reversed(list(outrow['roles'].values())) for x in role['metrics']}
        for m,spec in cats.items():
            if m in selected:
                node=deepcopy(selected[m]);node.update(kind='CORE_INPUT_VIEW',core_contribution='ALREADY_COUNTED_IN_ROLE')
            else:
                raw,reason=_usable(r,m,evaluation);score=None;n=0;basis=None
                if outrow['status']=='READY' and raw is not None:
                    keys=[('sector',r.get('sector_id'),r.get('accounting_template'))] if c['candidate']=='S1-555' else ([('industry',r.get('industry_group')),('all',)] if spec['axis']=='Q' else [('all',)])
                    for key in keys:
                        p=pools.get(key,_Pool({}));less,equal,n=p.rank(m,spec['direction'],raw,r['issuer_id']);basis='|'.join(str(v) for v in key)
                        if n>=c['minimum']:score=percentile(less,equal,n);break
                    if score is None:reason='PEER_SAMPLE_SMALL'
                elif outrow['status']!='READY':reason='ACCOUNTING_RECIPE_PREPARING'
                node=dict(metric=m,raw=raw,raw_status=reason,score=score,reason=None if score is not None else reason,
                    reference_n=n,reference_scope=basis,kind='ADDITIONAL',core_contribution=0)
            node['extra_score_contribution']=0;outrow['factors'][m]=node
    # Reuse the same stored rank/decile function with an internal slot mapping.
    # Slot names never appear in the exported factor identity.
    slots=list(CATALOG);names=list(cats)
    for start in range(0,len(names),len(slots)):
        keys=names[start:start+len(slots)];mapping=dict(zip(slots,keys))
        bridge=[dict(company_id=r['company_id'],ranking_scope=r['ranking_scope'],
            factors={slot:dict(score=r['factors'][mapping[slot]]['score'] if slot in mapping else None) for slot in slots}) for r in out['rows']]
        _rank_factors(bridge)
        for r,b in zip(out['rows'],bridge):
            for slot,key in mapping.items():r['factors'][key].update({k:b['factors'][slot][k] for k in ('rank','rank_n','decile','decile_status')})
    out['source_core_result_hash']=result['result_hash']
    import hashlib
    from pathlib import Path
    out['additional_code_hash']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out['additional_calculated_at']=datetime.now(timezone.utc).isoformat()
    out['core_scores_recomputed']=False
    out['result_hash']=digest({k:v for k,v in out.items() if k!='result_hash'})
    return out
