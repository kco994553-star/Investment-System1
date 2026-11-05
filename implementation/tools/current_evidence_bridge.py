#!/usr/bin/env python3
"""Verified held crosswalk/cache -> staged evidence -> existing evaluate; no network."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.current_evidence_bridge import link_and_evaluate


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args();out=a.output_dir.resolve()
    if any((parent/'.git').exists() for parent in (out,*out.parents)):p.error('OUTPUT_MUST_BE_OUTSIDE_GIT')
    try:
        job=json.loads(a.job.read_bytes());inputs={};refs={}
        for key in ('held','crosswalk','covers','sources','links'):
            ref=job['inputs'][key];body=Path(ref['path']).read_bytes()
            if hashlib.sha256(body).hexdigest()!=ref['sha256']:raise ValueError('INPUT_HASH_MISMATCH')
            inputs[key]=json.loads(body);refs[key]={**ref,'bytes':len(body)}
        links=inputs['links'] if isinstance(inputs['links'],list) else [inputs['links']]
        result=link_and_evaluate(held=inputs['held'],crosswalk=inputs['crosswalk'],cover_evidence=inputs['covers'],
                                 source_evidence=inputs['sources'],document_links=links,basis_date=job['basis_date'])
        evaluation=result.pop('evaluation');pipeline_inputs=result.pop('pipeline_inputs')
        pipeline_inputs['financials_ref']=refs['held']
        out.mkdir(mode=0o700,parents=True,exist_ok=False);files={}
        for name,value in [('staged-evidence.json',result),('pipeline-inputs.json',pipeline_inputs),('current-expansion.json',evaluation)]:
            body=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()+b'\n'
            with os.fdopen(os.open(out/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(body)
            files[name]=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
        manifest=dict(schema_version='current-evidence-private-manifest/1',basis_date=job['basis_date'],inputs=refs,files=files,
                      financial_records_recomputed=0,new_source_requests=0,public_population_changed=False)
        with os.fdopen(os.open(out/'manifest.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(manifest,f,indent=2)
    except Exception:
        print('CURRENT_EVIDENCE_BRIDGE_FAILED',file=sys.stderr);return 1
    print('CURRENT_EVIDENCE_BRIDGE_WRITTEN');return 0


if __name__=='__main__':raise SystemExit(main())
