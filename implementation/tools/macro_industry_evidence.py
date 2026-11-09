#!/usr/bin/env python3
"""Offline company -> common industry -> source evidence query; no acquisition."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.classification_counts import load, reference, require
from investment_system.research.common_classification.macro_evidence import query_industry_evidence


def run(job, output, *, synthetic=False):
    require(job.get('schema_version')=='macro-industry-query-job/1','JOB_SCHEMA')
    kind='SYNTHETIC' if synthetic else 'RETAINED_INPUT'
    require(job.get('data_kind')==kind,'DATA_KIND_MISMATCH')
    out=Path(output).resolve()
    require(not out.exists(),'OUTPUT_ALREADY_EXISTS')
    if not synthetic:require(not any((p/'.git').exists() for p in (out,*out.parents)),'PRIVATE_OUTPUT_OUTSIDE_CHECKOUT_REQUIRED')
    view,links,cache=(load(job[k]) for k in ('view','mappings','macro_cache'))
    require(view['data_kind']==kind,'VIEW_DATA_KIND')
    result=query_industry_evidence(view,links,cache)
    result['source_files']={k:reference(job[k]) for k in ('view','mappings','macro_cache')}
    files={'query.json':result,'taxonomy.json':result['taxonomy']}
    body={k:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode() for k,v in files.items()}
    manifest={'schema_version':'macro-industry-query-manifest/1','data_kind':kind,
        'classification_context':result['classification_context'],'source_files':result['source_files'],
        'files':[{'path':k,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for k,b in body.items()]}
    body['manifest.json']=(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode()
    out.parent.mkdir(parents=True,exist_ok=True);tmp=Path(tempfile.mkdtemp(prefix='.'+out.name+'-',dir=out.parent))
    try:
        for k,b in body.items():
            f=tmp/k;f.write_bytes(b);f.chmod(0o600);assert f.read_bytes()==b;json.loads(f.read_bytes())
        tmp.rename(out)
    finally:
        if tmp.exists():shutil.rmtree(tmp)
    return {'status':'VERIFIED','counts':result['counts'],'new_source_requests':0,'historical_pit_certified':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',required=True);p.add_argument('--output',required=True);p.add_argument('--synthetic',action='store_true');a=p.parse_args()
    try:print(json.dumps(run(json.loads(Path(a.job).read_text()),a.output,synthetic=a.synthetic)))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print(json.dumps({'status':'FAILED','error_type':type(exc).__name__}),file=sys.stderr);raise SystemExit(1)
