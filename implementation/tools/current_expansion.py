#!/usr/bin/env python3
"""Retained SEC ZIP -> current-expansion diagnostics; offline/private outputs only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.current_expansion import evaluate,read_held_archive


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--basis-date',required=True)
    p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--evidence',type=Path)
    a=p.parse_args();out=a.output_dir.resolve()
    if any((parent/'.git').exists() for parent in (out,*out.parents)):p.error('OUTPUT_MUST_BE_OUTSIDE_GIT')
    try:
        # A failed replay cannot replace a prior successful directory.
        out.mkdir(mode=0o700,parents=True,exist_ok=False)
        held=read_held_archive(a.archive,basis_date=a.basis_date)
        evidence=json.loads(a.evidence.read_bytes()) if a.evidence else {}
        result=evaluate(held['candidates'],financials=held['financials'],evidence=evidence,
                        source=held['source'],basis_date=a.basis_date)
        files={}
        for name,value in [('held-normalized.json',held),('current-expansion.json',result)]:
            body=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()+b'\n'
            with os.fdopen(os.open(out/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(body)
            files[name]={'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}
        manifest={'schema_version':'current-expansion-private-manifest/1','archive_name':a.archive.name,
                  'basis_date':a.basis_date,'files':files,'network_requests':0,'public_universe_changed':False}
        with os.fdopen(os.open(out/'manifest.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
            json.dump(manifest,f,indent=2)
    except Exception:
        print('CURRENT_EXPANSION_OFFLINE_FAILED',file=sys.stderr);return 1
    print('CURRENT_EXPANSION_PRIVATE_OUTPUT_WRITTEN');return 0


if __name__=='__main__':raise SystemExit(main())
