#!/usr/bin/env python3
"""Read a held macro archive at explicit cutoffs; no network or operating side effects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.macro import evidence_lines as el
from investment_system.research.macro_observed_timeline import timeline


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive',required=True,type=Path)
    ap.add_argument('--at',required=True,action='append',help='UTC timestamp; repeat in increasing order')
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    output=args.output.resolve()
    if any((p/'.git').exists() for p in (output.parent,*output.parents)):
        ap.error('output must be outside Git worktrees')
    body=args.archive.read_bytes()
    result=timeline(json.loads(body),[el.parse_iso(x) for x in args.at])
    result['archive_sha256']=hashlib.sha256(body).hexdigest()
    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with os.fdopen(os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'schema_version':result['schema_version'],'snapshots':len(result['snapshots'])}))


if __name__=='__main__':main()
