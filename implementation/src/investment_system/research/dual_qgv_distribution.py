"""Complete, bounded factor distributions from saved dual results; no scoring.

Both explicit display policies preserve stored score/rank/decile. The reference
percentile policy is a display research candidate until its basis is confirmed.
"""
from collections import Counter,defaultdict
from copy import deepcopy
import hashlib,json,math
from .dual_qgv import json_bytes,_code_hash
from .dual_qgv_delivery import MAX_BYTES,require
from .sector_qgv import digest
from .sector_qgv_registry import CATALOG

STORED='stored-evaluation-deciles/1'
REFERENCE='reference-score-deciles/1'
BANDS=[dict(decile=d,top_percent_from=(10-d)*10,top_percent_to=(11-d)*10,
            label=f'상위 {(10-d)*10}–{(11-d)*10}%') for d in range(10,0,-1)]


def _display(f,policy):
    score=f['score']
    if score is None:return None,f['score_status']
    require(type(score) in (int,float) and math.isfinite(score) and 0<=score<=100,'FACTOR_SCORE')
    require(type(f['valid_n']) is int and f['valid_n']>=20,'REFERENCE_MINIMUM')
    if policy==STORED:return f['decile'],f['decile_status']
    # Score already follows the factor direction and midpoint tie percentile.
    # Never rank the filtered evaluation rows or reverse LOWER factors a second time.
    return min(10,int(score//10)+1),'VALID'


def distribution_artifacts(boards,*,scope,data_kind,display_policy,source_hashes=None,max_bytes=MAX_BYTES):
    require(display_policy in (STORED,REFERENCE),'DISPLAY_POLICY')
    require(scope in ('operating504','held1057') and data_kind in ('SYNTHETIC','PRIVATE'),'SCOPE')
    require(type(max_bytes) is int and 0<max_bytes<=MAX_BYTES,'SIZE_LIMIT')
    from .qgv_333 import IDS
    legacy={'U1','U2','S1'}
    require(bool(boards) and (set(boards)<=legacy or set(boards)<=set(IDS)),'BOARD_KEYS')
    expected=next(iter(boards.values()))['evaluation_population']
    original_ids=None;meta={};entries=[];out={};parts=[];seq=0;registry={}
    def payload(items):return dict(schema_version='qgv-dual-factor-distribution-part/1',parts=items)
    def flush():
        nonlocal parts,seq
        if parts:out[f'distribution-{seq:03}.json']=payload(parts);parts=[];seq+=1
    def append(gid,rows):
        if len(json_bytes(payload([dict(group_id=gid,rows=rows)])))>max_bytes:
            require(len(rows)>1,'ROW_SIZE');mid=len(rows)//2
            return append(gid,rows[:mid])+append(gid,rows[mid:])
        part=dict(group_id=gid,rows=rows)
        if len(json_bytes(payload(parts+[part])))>max_bytes:flush()
        name=f'distribution-{seq:03}.json';parts.append(part);return [name]
    for key,b in boards.items():
        require(b.get('schema_version')=='qgv-dual-board/1','SOURCE_SCHEMA')
        if key in IDS:require(b.get('model_id')==IDS[key],'BOARD_MODEL_ID')
        if data_kind=='PRIVATE':require(b['bindings'].get('code_hash')==_code_hash(b['configuration']),'SOURCE_CODE_VERSION')
        require(b['result_hash']==digest({k:v for k,v in b.items() if k not in ('request_id','result_hash')}),'RESULT_HASH')
        require(b['evaluation_population']==expected,'EVALUATION_MISMATCH')
        require(b['configuration']['minimum']==20,'REFERENCE_MINIMUM')
        require(digest(b['groups'])==b['reference_population']['factor_members_hash'],'REFERENCE_GROUP_HASH')
        ids=[r['company_id'] for r in b['rows']]
        require(len(ids)==len(set(ids))==expected['code_rows'],'EVALUATION_MEMBERS')
        if original_ids is None:original_ids=ids
        require(ids==original_ids,'EVALUATION_MEMBERS')
        meta[key]={f:deepcopy(b[f]) for f in ('model_id','model_version','evaluation_population','reference_population','bindings','result_hash','normalization_version','engine_version','adapter_version')}
        meta[key]['configuration_hash']=digest(b['configuration'])
        meta[key]['source_result_sha256']=(source_hashes or {}).get(key) or hashlib.sha256(json_bytes(b)).hexdigest()
        refs={(g['ranking_scope'],g['variant_id']):g for g in b['groups']}
        require(len(refs)==len(b['groups']),'DUPLICATE_REFERENCE_GROUP')
        grouped=defaultdict(list)
        for row in b['rows']:
            identity={f:row.get(f) for f in ('company_id','issuer_id','security_id')}
            require(row['company_id'] not in registry or registry[row['company_id']]==identity,'IDENTITY_MISMATCH')
            registry[row['company_id']]=identity
            rscope=row['ranking_scope']
            require(rscope=='COMMON' if key not in ('S1','S1-333') else rscope.startswith('SECTOR|'),'RANK_SCOPE')
            for variant,f in row['factors'].items():
                require(variant in CATALOG,'UNKNOWN_VARIANT')
                decile,status=_display(f,display_policy)
                grouped[(rscope,variant)].append(dict(company_id=row['company_id'],score=f['score'],rank=f['rank'],rank_n=f['rank_n'],
                    stored_decile=f['decile'],stored_decile_status=f['decile_status'],decile=decile,decile_status=status,
                    score_status=f['score_status'],raw_status=f['raw_status'],kind=f['kind'],reference_n=f['valid_n']))
        for (rscope,variant),rows in sorted(grouped.items()):
            source=refs.get((rscope,variant));ref_n=source['valid_n'] if source else 0
            require(all(r['reference_n']==ref_n for r in rows),'REFERENCE_GROUP_N')
            valid=[r for r in rows if r['score'] is not None];n=len(valid)
            require(sorted(r['rank'] for r in valid)==list(range(1,n+1)) and all(r['rank_n']==n for r in valid),'RANK_INTEGRITY')
            ordered=sorted(valid,key=lambda r:r['rank'])
            for i,r in enumerate(ordered):
                if i:
                    prev=ordered[i-1]
                    require((-prev['score'],prev['company_id'])<=(-r['score'],r['company_id']),'STORED_ORDER')
                require(r['stored_decile_status']==('VALID' if n>=10 else 'SAMPLE_LT_10'),'STORED_DECILE_STATUS')
                require((type(r['stored_decile']) is int and 1<=r['stored_decile']<=10) if n>=10 else r['stored_decile'] is None,'STORED_DECILE')
            require(all(r['rank'] is None and r['stored_decile'] is None for r in rows if r['score'] is None),'RANK_WITHOUT_SCORE')
            tie_splits=[dict(score=a['score'],last_rank=a['rank'],next_rank=z['rank'],from_decile=a['stored_decile'],to_decile=z['stored_decile'])
                        for a,z in zip(ordered,ordered[1:]) if a['score']==z['score'] and a['stored_decile']!=z['stored_decile']]
            counts=Counter(r['decile'] for r in rows if r['decile'] is not None)
            reasons=Counter(r['decile_status'] for r in rows if r['decile'] is None)
            gid=key+'|'+rscope+'|'+variant
            comparison=dict(role='FACTOR_REFERENCE' if display_policy==REFERENCE else 'EVALUATION_VALID',
                unit='REPRESENTATIVE_ISSUER' if display_policy==REFERENCE else 'EVALUATION_CODE_ROW',
                n=ref_n if display_policy==REFERENCE else n,
                members_hash=(source['members_hash'] if source else None) if display_policy==REFERENCE else digest(sorted(r['company_id'] for r in valid)))
            entry=dict(group_id=gid,board=key,ranking_scope=rscope,variant_id=variant,
                raw_direction=CATALOG[variant]['direction'],score_direction='HIGHER_IS_BETTER',
                evaluation_rows_in_scope=len(rows),evaluation_valid_n=n,reference_valid_n=ref_n,comparison_group=comparison,
                reference_members_hash=source['members_hash'] if source else None,
                reference_issuer_members_hash=source['issuer_members_hash'] if source else None,
                bins=[dict(decile=d,count=counts[d]) for d in range(10,0,-1)],
                unavailable_count=sum(reasons.values()),unavailable_reasons=dict(reasons),legacy_tie_splits=tie_splits)
            # Original company order retained; consumers filter, never re-rank.
            for r in rows:del r['reference_n']
            entry['files']=list(dict.fromkeys(append(gid,rows)));entries.append(entry)
    flush()
    out['distribution-index.json']=dict(schema_version='qgv-dual-factor-distribution/1',scope=scope,data_kind=data_kind,
        display_policy=display_policy,policy_state='EXISTING_RULE' if display_policy==STORED else 'RESEARCH_DISPLAY_CANDIDATE',
        bands=deepcopy(BANDS),boards=meta,companies=list(registry.values()),groups=entries,
        rank_policy='UNROUNDED_FACTOR_SCORE_DESC_COMPANY_ID_ASC_ORDINAL',
        minimum_reference_score_n=20,minimum_stored_evaluation_decile_n=10,
        complete_evaluation_rows=True,filter_changes_population=False,rank_recalculated=False,
        additional_factor_score_contribution=0,new_score_calculations=0,whole_market_denominator=None,whole_market_coverage=None)
    require(all(len(json_bytes(v))<=max_bytes for v in out.values()),'OUTPUT_SIZE')
    out['distribution-manifest.json']=dict(schema_version='qgv-dual-factor-distribution-manifest/1',scope=scope,data_kind=data_kind,
        display_policy=display_policy,source_results={k:dict(result_hash=m['result_hash'],sha256=m['source_result_sha256']) for k,m in meta.items()},
        files=[dict(path=name,size=len(json_bytes(value)),sha256=hashlib.sha256(json_bytes(value)).hexdigest()) for name,value in sorted(out.items())])
    require(len(json_bytes(out['distribution-manifest.json']))<=max_bytes,'OUTPUT_SIZE')
    return out


def select_rows(artifacts,group_id,deciles):
    """Reference consumer projection: exact stored rows and original N/context."""
    require(isinstance(deciles,list) and len(set(deciles))==len(deciles) and all(type(d) is int and 1<=d<=10 for d in deciles),'DECILE_FILTER')
    idx=artifacts['distribution-index.json'];matches=[g for g in idx['groups'] if g['group_id']==group_id]
    require(len(matches)==1,'GROUP_UNKNOWN');g=matches[0]
    rows=[r for name in g['files'] for p in artifacts[name]['parts'] if p['group_id']==group_id for r in p['rows']]
    require(len(rows)==g['evaluation_rows_in_scope'] and len({r['company_id'] for r in rows})==len(rows),'GROUP_ROWS')
    return deepcopy(dict(group=g,board=idx['boards'][g['board']],display_policy=idx['display_policy'],bands=idx['bands'],
                         rows=[r for r in rows if r['decile'] in deciles]))


def main(argv=None):
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    args=p.parse_args(argv);job=json.loads(args.job.read_bytes())
    require(job.get('schema_version')=='qgv-dual-factor-distribution-job/1','JOB_SCHEMA')
    if job.get('data_kind')!='SYNTHETIC':
        dest=args.output_dir.resolve();require(not any((x/'.git').exists() for x in (dest,*dest.parents)),'PRIVATE_OUTPUT_IN_CHECKOUT')
    boards={};pins={}
    for key,entry in job['board_results'].items():
        raw=Path(entry['path']).read_bytes();pins[key]=hashlib.sha256(raw).hexdigest()
        require(pins[key]==entry['sha256'],'SOURCE_FILE_HASH');boards[key]=json.loads(raw)
        require(boards[key]['result_hash']==entry['result_hash'],'SOURCE_RESULT_HASH')
    out=distribution_artifacts(boards,scope=job['scope'],data_kind=job['data_kind'],display_policy=job['display_policy'],source_hashes=pins)
    args.output_dir.mkdir(parents=True,exist_ok=False)
    for name,value in out.items():(args.output_dir/name).write_bytes(json_bytes(value))
    print(json.dumps(dict(status='PROJECTED_ALL_BINS',files=len(out),groups=len(out['distribution-index.json']['groups']),new_score_calculations=0)))


if __name__=='__main__':
    import re,sys
    try:main()
    except (ValueError,KeyError,TypeError,OSError) as error:
        code=str(error) if isinstance(error,ValueError) and re.fullmatch(r'[A-Z_]+',str(error)) else type(error).__name__
        print(json.dumps(dict(status='FAILED',error=code)),file=sys.stderr);raise SystemExit(1)
