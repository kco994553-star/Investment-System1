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
from investment_system.research.macro_observed_timeline import current_query, timeline


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    source=ap.add_mutually_exclusive_group(required=True)
    source.add_argument('--archive',type=Path)
    source.add_argument('--timeline-cache',type=Path,help='reuse a previously verified timeline for current reading; no calculation replay')
    ap.add_argument('--cache-sha256',help='required pinned hash when using --timeline-cache')
    ap.add_argument('--at',required=True,action='append',help='UTC timestamp; repeat in increasing order')
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    output=args.output.resolve()
    if any((p/'.git').exists() for p in (output.parent,*output.parents)):
        ap.error('output must be outside Git worktrees')
    body=(args.archive or args.timeline_cache).read_bytes()
    digest=hashlib.sha256(body).hexdigest()
    if args.timeline_cache:
        if len(args.at)!=1 or args.cache_sha256!=digest:
            ap.error('current query requires one --at and the matching --cache-sha256')
        result=current_query(json.loads(body),el.parse_iso(args.at[0]))
        result['timeline_cache_sha256']=digest
    else:
        if args.cache_sha256:
            ap.error('--cache-sha256 requires --timeline-cache')
        result=timeline(json.loads(body),[el.parse_iso(x) for x in args.at])
        result['archive_sha256']=digest
    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with os.fdopen(os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    summary={'schema_version':result['schema_version']}
    summary.update({'snapshots':len(result['snapshots'])} if 'snapshots' in result else {'counts':result['counts']})
    print(json.dumps(summary))


if __name__=='__main__':main()
