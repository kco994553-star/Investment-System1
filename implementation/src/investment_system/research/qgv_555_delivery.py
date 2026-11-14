"""Bounded projections of saved 555 results; does not recompute scores or deciles."""
from collections import defaultdict, Counter
from copy import deepcopy
import hashlib,json
from .dual_qgv import json_bytes
from .dual_qgv_delivery import MAX_BYTES,require
from .qgv_555 import IDS,SPECS,configuration,validate_configuration
from .sector_qgv import digest


def artifacts(boards,*,data_kind,max_bytes=MAX_BYTES):
    require(not any(b.get('namespace') in ('PERSONAL_SHEET_V','OWNER_PRIVATE_KIS_V') for b in boards.values()),'PERSONAL_RESULT_NOT_RESEARCH_DELIVERY')
    require(all(b.get('schema_version')=='qgv-555-result/1' for b in boards.values()),'RESEARCH_RESULT_SCHEMA')
    require(data_kind in ('SYNTHETIC','PRIVATE'),'DATA_KIND')
    require(0<max_bytes<=MAX_BYTES,'SIZE_LIMIT')
    require(set(boards)<=set(IDS) and bool(boards),'BOARDS')
    files={};groups=[];models={};evaluation=None
    def bounded(name,rows,header):
        out=[];part=[];seq=0;empty_size=len(json_bytes(dict(header,rows=[])));estimate=empty_size
        def flush():
            nonlocal part,seq,estimate
            value=dict(header,rows=part);path=f'{name}-{seq:04}.json'
            require(len(json_bytes(value))<=max_bytes,'ROW_SIZE')
            files[path]=value;out.append(path);part=[];seq+=1;estimate=empty_size
        for row in rows:
            # Conservative accounting avoids repeatedly serializing the growing
            # part; actual bytes are still checked in flush before publication.
            cost=2*len(json_bytes(row))+256
            if part and estimate+cost>max_bytes:flush()
            part.append(row);estimate+=cost
        if part:flush()
        return out
    for key,b in boards.items():
        config=validate_configuration(b['configuration'])
        require(config['candidate']==key and b['model_id']==configuration(key,version=config['version'])['model_id'],'MODEL_ID')
        require(b['result_hash']==digest({k:v for k,v in b.items() if k!='result_hash'}),'RESULT_HASH')
        if evaluation is None:evaluation=b['evaluation']
        require(b['evaluation']==evaluation,'EVALUATION_CONTEXT')
        paths=bounded(key+'-detail',b['rows'],dict(schema_version='qgv-555-detail/1',model_id=b['model_id'],result_hash=b['result_hash']))
        models[key]=dict(model_id=b['model_id'],result_hash=b['result_hash'],bindings=b['bindings'],coverage=b['coverage'],
            calculated_at=b['calculated_at'],configuration=b['configuration'],files=paths)
        fields=[('roles',role) for role in SPECS]+[('factors',key) for key in (b['rows'][0].get('factors',{}) if b['rows'] else {})]
        for field,role in fields:
            scopes=defaultdict(list)
            for r in b['rows']:
                f=r[field][role]
                scopes[r['ranking_scope']].append(dict(company_id=r['company_id'],issuer_id=r['issuer_id'],
                    score=f['score'],rank=f['rank'],rank_n=f['rank_n'],decile=f['decile'],decile_status=f['decile_status'],
                    reference_counts={x['metric']:x['reference_n'] for x in f['metrics']} if field=='roles' else {role:f['reference_n']},
                    missing_metrics=[dict(metric=x['metric'],reason=x['reason']) for x in f['metrics'] if x['score'] is None] if field=='roles' else ([dict(metric=role,reason=f['reason'])] if f['score'] is None else [])))
            for scope,rows in sorted(scopes.items()):
                gid=digest([key,role,scope])[:24];valid=[r for r in rows if r['score'] is not None]
                n=len(valid);counts=Counter(r['decile'] for r in valid)
                require(sorted(r['rank'] for r in valid)==list(range(1,n+1)),'STORED_RANK')
                if n>=10:require(sum(counts[d] for d in range(1,11))==n,'ALL_DECILES')
                paths=bounded('distribution-'+gid,rows,dict(schema_version='qgv-555-distribution-part/1',group_id=gid,result_hash=b['result_hash']))
                ordered=sorted(valid,key=lambda r:r['rank'])
                tie_splits=[dict(score=a['score'],last_rank=a['rank'],next_rank=z['rank'],from_decile=a['decile'],to_decile=z['decile']) for a,z in zip(ordered,ordered[1:]) if a['score']==z['score'] and a['decile']!=z['decile']]
                groups.append(dict(group_id=gid,model=key,role=role,kind=field,ranking_scope=scope,evaluation_valid_n=n,
                    original_code_rows=len(rows),unit='CODE_ROW',reference_n=None,reference_n_reason='COMPOSITE_SUBMETRIC_COUNTS_IN_MEMBERS',
                    bins=[dict(decile=d,count=counts[d],top_percent_from=(10-d)*10,top_percent_to=(11-d)*10) for d in range(10,0,-1)],
                    minimum_decile_n=10,tie_splits=tie_splits,members_hash=digest(rows),files=paths))
    index=dict(schema_version='qgv-555-delivery/1',data_kind=data_kind,evaluation=evaluation,models=models,groups=groups,
        rank_policy='STORED_DUAL_ORDINAL_SCORE_DESC_CODE_ASC',tie_policy='EXISTING_FIXED_COUNT_BINS_WITH_REPORTED_TIE_SPLITS',
        official=False,whole_market_denominator=None,filter_recalculates=False,additional_factor_contribution=0,
        groups_layout='INLINE',groups_count=len(groups),group_files=[])
    if len(json_bytes(index))>max_bytes:
        index['group_files']=bounded('group-index',groups,dict(schema_version='qgv-555-groups-part/1',evaluation_input_hash=evaluation['input_hash']))
        index['groups']=[];index['groups_layout']='SHARDED'
    require(len(json_bytes(index))<=max_bytes,'INDEX_SIZE');files['index.json']=index
    files['manifest.json']=dict(schema_version='qgv-555-delivery-manifest/1',data_kind=data_kind,
        files=[dict(path=p,size=len(json_bytes(v)),sha256=hashlib.sha256(json_bytes(v)).hexdigest()) for p,v in sorted(files.items())])
    return files


def read_groups(files):
    index=files['index.json']
    if index.get('groups_layout','INLINE')=='INLINE':return index['groups']
    require(index.get('groups_layout')=='SHARDED' and not index['groups'],'GROUP_INDEX_LAYOUT')
    groups=[]
    for path in index['group_files']:
        p=files[path];require(p['schema_version']=='qgv-555-groups-part/1' and p['evaluation_input_hash']==index['evaluation']['input_hash'],'GROUP_INDEX_CONTEXT')
        groups.extend(p['rows'])
    require(len(groups)==index['groups_count'] and len({g['group_id'] for g in groups})==len(groups),'GROUP_INDEX_MEMBERS')
    return groups


def validate(files,*,manifest_sha256,expected_evaluation,expected_references):
    require(hashlib.sha256(json_bytes(files['manifest.json'])).hexdigest()==manifest_sha256,'MANIFEST_HASH')
    listed=files['manifest.json']['files']
    require(len({f['path'] for f in listed})==len(listed),'DUPLICATE_MEMBER')
    for f in listed:
        require(f['path'] in files,'MISSING_MEMBER');raw=json_bytes(files[f['path']])
        require(len(raw)==f['size']<=MAX_BYTES and hashlib.sha256(raw).hexdigest()==f['sha256'],'MEMBER_HASH')
    idx=files['index.json'];require(idx['evaluation']==expected_evaluation,'EVALUATION_ANCHOR')
    require(set(expected_references)==set(idx['models']),'REFERENCE_MODELS')
    for key,m in idx['models'].items():
        require(m['bindings']['reference']==expected_references[key],'REFERENCE_ANCHOR')
    groups=read_groups(files)
    for g in groups:
        rows=[]
        for path in g['files']:
            p=files[path];require(p['group_id']==g['group_id'],'GROUP_SCOPE');rows.extend(p['rows'])
        require(len(rows)==g['original_code_rows'] and len({r['company_id'] for r in rows})==len(rows),'GROUP_MEMBERS')
        require(digest(rows)==g['members_hash'],'GROUP_MEMBER_HASH')
        counts=Counter(r['decile'] for r in rows if r['score'] is not None)
        require(all(counts[x['decile']]==x['count'] for x in g['bins']),'BIN_COUNT')
    return dict(status='VALIDATED',groups=len(groups),files=len(files),independent_pins_required=True)
