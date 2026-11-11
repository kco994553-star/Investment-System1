"""Bounded projections of existing dual QGV deliveries. Never scores or re-ranks."""
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import math
import re
from .dual_qgv import json_bytes

MAX_BYTES = 1_800_000
SOURCE_FILE = re.compile(r'^(summary|index)\.json$|^detail-\d{3}\.json$')


def require(condition, code):
    if not condition:
        raise ValueError(code)


def delivery_manifest(files, *, scope, data_kind):
    """The existing real-delivery manifest format; no synthetic data regenerated."""
    require(scope in ('operating504', 'held1057'), 'SCOPE')
    require(data_kind in ('SYNTHETIC', 'PRIVATE'), 'DATA_KIND')
    return dict(schema_version='qgv-dual-delivery-manifest/1', scope=scope, data_kind=data_kind,
        files=[dict(path=n,size=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in sorted(files.items()) if SOURCE_FILE.fullmatch(n)])


def factor_leaders_artifacts(files, *, expected_manifest_sha256, top_n=20, max_bytes=MAX_BYTES):
    require(type(top_n) is int and 1 <= top_n <= 100, 'TOP_N')
    require(type(max_bytes) is int and 0 < max_bytes <= MAX_BYTES, 'SIZE_LIMIT')
    manifest_raw = files.get('manifest.json')
    require(isinstance(manifest_raw, bytes) and hashlib.sha256(manifest_raw).hexdigest()==expected_manifest_sha256, 'MANIFEST_HASH')
    manifest = json.loads(manifest_raw)
    require(manifest.get('schema_version')=='qgv-dual-delivery-manifest/1', 'MANIFEST_SCHEMA')
    require(manifest.get('scope') in ('operating504','held1057') and manifest.get('data_kind') in ('PRIVATE','SYNTHETIC'), 'MANIFEST_SCOPE')
    docs, seen = {}, set()
    for item in manifest['files']:
        name=item['path']
        require(isinstance(name,str) and SOURCE_FILE.fullmatch(name) and name not in seen, 'FILE_NAME')
        seen.add(name)
        require(name in files, 'FILE_MISSING')
        raw=files[name]
        require(len(raw)==item['size'] and hashlib.sha256(raw).hexdigest()==item['sha256'], 'FILE_HASH')
        require(len(raw)<=2_000_000, 'SOURCE_SIZE')
        docs[name]=json.loads(raw)
    require({'summary.json','index.json'} <= set(docs), 'FILE_MISSING')
    summary,index=docs['summary.json'],docs['index.json']
    require(summary.get('schema_version')=='qgv-dual-delivery/1' and index.get('schema_version')=='qgv-dual-index/1', 'SOURCE_SCHEMA')
    boards=summary['boards'];require(bool(boards) and set(boards)<= {'U1','U2','S1'}, 'BOARD_KEYS')
    population=index['evaluation_population']
    require(all(b['evaluation_population']==population for b in boards.values()), 'POPULATION_MISMATCH')
    heads={r['company_id']:r for r in index['rows']}
    require(len(heads)==len(index['rows'])==population['code_rows'], 'INDEX_MEMBERS')
    used=set();groups=defaultdict(list);fields=('missing_factors','nominal_axis_weights','nominal_effective_weights','post_gate_axis_weights','post_gate_effective_weights')
    presence={k:{f:dict(present=0,absent=0,absent_statuses={}) for f in fields} for k in boards}
    for name,detail in sorted(docs.items()):
        if not name.startswith('detail-'):continue
        require(detail.get('schema_version')=='qgv-dual-detail/1', 'DETAIL_SCHEMA')
        for row in detail['rows']:
            cid=row['company_id'];require(cid in heads and cid not in used and heads[cid]['detail_file']==name, 'DETAIL_MEMBER')
            used.add(cid);require(set(row['boards'])==set(boards), 'BOARD_KEYS')
            for key,body in row['boards'].items():
                require(body['company_id']==cid and body['issuer_id']==heads[cid]['issuer_id'] and body['security_id']==heads[cid]['security_id'], 'DETAIL_IDENTITY')
                scope=body['ranking_scope'];require(isinstance(scope,str) and (scope=='COMMON' if key!='S1' else scope.startswith('SECTOR|')), 'RANK_SCOPE')
                for field in fields:
                    p=presence[key][field];p['present' if field in body else 'absent']+=1
                    if field not in body:p['absent_statuses'][body['status']]=p['absent_statuses'].get(body['status'],0)+1
                for variant,f in body['factors'].items():
                    require('raw_value' not in f, 'RAW_VALUE')
                    value=f['score'];require(value is None or type(value) in (float,int) and math.isfinite(value), 'SCORE')
                    if value is None:require(f['rank'] is None and f['decile'] is None, 'RANK_WITHOUT_SCORE')
                    groups[(key,scope,variant)].append(dict(company_id=cid,issuer_id=body['issuer_id'],security_id=body['security_id'],
                        score=value,rank=f['rank'],rank_n=f['rank_n'],decile=f['decile'],decile_status=f['decile_status'],valid_n=f['valid_n'],kind=f['kind']))
    require(used==set(heads), 'DETAIL_MISSING')
    meta={k:{f:deepcopy(b[f]) for f in ('model_id','model_version','evaluation_population','reference_population','bindings','result_hash','configuration_hash')} for k,b in boards.items()}
    out={};entries=[];chunk=[];seq=0
    def flush():
        nonlocal chunk,seq
        if chunk:
            out[f'factor-leaders-{seq:03}.json']=dict(schema_version='qgv-dual-factor-leaders-detail/1',groups=chunk)
            chunk=[];seq+=1
    for (key,scope,variant),rows in sorted(groups.items()):
        valid=[r for r in rows if r['score'] is not None];n=len(valid)
        require(all(type(r['rank']) is int and r['rank_n']==n for r in valid) and sorted(r['rank'] for r in valid)==list(range(1,n+1)), 'RANK_INTEGRITY')
        ordered=sorted(valid,key=lambda r:r['rank'])  # Existing producer rank only; never sort scores or recompute ties.
        reference_n={r['valid_n'] for r in rows};require(len(reference_n)==1, 'REFERENCE_N_MISMATCH')
        ref_n=next(iter(reference_n))
        require(ref_n is None or type(ref_n) is int and ref_n>=0, 'REFERENCE_N')
        bounds=[]
        if n>=10:
            require(all(r['decile_status']=='VALID' and type(r['decile']) is int and 1<=r['decile']<=10 for r in ordered), 'DECILE_INTEGRITY')
            require([r['decile'] for r in ordered]==sorted((r['decile'] for r in ordered),reverse=True), 'DECILE_INTEGRITY')
            for decile in range(10,0,-1):
                members=[r for r in ordered if r['decile']==decile]
                if members:bounds.append(dict(decile=decile,count=len(members),first_rank=members[0]['rank'],last_rank=members[-1]['rank'],first_score=members[0]['score'],last_score=members[-1]['score']))
        else:require(all(r['decile'] is None and r['decile_status']=='SAMPLE_LT_10' for r in ordered), 'DECILE_INTEGRITY')
        gid=key+'|'+scope+'|'+variant
        item=dict(group_id=gid,board=key,ranking_scope=scope,variant_id=variant,evaluation_rows_in_scope=len(rows),
                  evaluation_valid_n=n,reference_valid_n=ref_n,rank_unit='EVALUATION_CODE_ROW',
                  top_n=top_n,leaders=[{k:r[k] for k in ('company_id','issuer_id','security_id','score','rank','rank_n','decile','kind')} for r in ordered[:top_n]],
                  decile_status='VALID' if n>=10 else 'SAMPLE_LT_10' if n else 'NO_VALID_SCORE',decile_boundaries=bounds)
        if len(json_bytes(dict(schema_version='qgv-dual-factor-leaders-detail/1',groups=chunk+[item])))>max_bytes:flush()
        require(len(json_bytes(dict(schema_version='qgv-dual-factor-leaders-detail/1',groups=[item])))<=max_bytes, 'GROUP_SIZE')
        entries.append(dict(group_id=gid,board=key,ranking_scope=scope,variant_id=variant,evaluation_valid_n=n,reference_valid_n=ref_n,file=f'factor-leaders-{seq:03}.json'))
        chunk.append(item)
    flush()
    out['factor-leaders.json']=dict(schema_version='qgv-dual-factor-leaders/1',scope=manifest['scope'],data_kind=manifest['data_kind'],
        source_delivery_manifest_sha256=expected_manifest_sha256,boards=meta,groups=entries,optional_detail_fields=presence,
        projection_only=True,rank_recalculated=False,whole_market_denominator=None,whole_market_coverage=None)
    require(all(len(json_bytes(v))<=max_bytes for v in out.values()), 'OUTPUT_SIZE')
    out['factor-leaders-manifest.json']=dict(schema_version='qgv-dual-factor-leaders-manifest/1',scope=manifest['scope'],data_kind=manifest['data_kind'],
        source_delivery_manifest_sha256=expected_manifest_sha256,files=[dict(path=n,size=len(json_bytes(v)),sha256=hashlib.sha256(json_bytes(v)).hexdigest()) for n,v in sorted(out.items())])
    require(len(json_bytes(out['factor-leaders-manifest.json']))<=max_bytes, 'OUTPUT_SIZE')
    return out


def main(argv=None):
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--top-n',type=int,default=20)
    args=parser.parse_args(argv)
    raw=(args.source_dir/'manifest.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==args.manifest_sha256,'MANIFEST_HASH')
    manifest=json.loads(raw);files={'manifest.json':raw}
    for item in manifest['files']:
        require(isinstance(item['path'],str) and SOURCE_FILE.fullmatch(item['path']), 'FILE_NAME')
        files[item['path']]=(args.source_dir/item['path']).read_bytes()
    if manifest['data_kind']!='SYNTHETIC':
        destination=args.output_dir.resolve()
        require(not any((p/'.git').exists() for p in (destination,*destination.parents)), 'PRIVATE_OUTPUT_IN_CHECKOUT')
    out=factor_leaders_artifacts(files,expected_manifest_sha256=args.manifest_sha256,top_n=args.top_n)
    args.output_dir.mkdir(parents=True,exist_ok=False)
    for name,value in out.items():(args.output_dir/name).write_bytes(json_bytes(value))
    print(json.dumps(dict(status='PROJECTED',files=len(out),groups=len(out['factor-leaders.json']['groups']),score_calculations=0)))


if __name__=='__main__':
    import sys
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        code=str(error) if isinstance(error, ValueError) and re.fullmatch(r'[A-Z_]+',str(error)) else type(error).__name__
        print(json.dumps(dict(status='FAILED',error=code)),file=sys.stderr)
        raise SystemExit(1)
