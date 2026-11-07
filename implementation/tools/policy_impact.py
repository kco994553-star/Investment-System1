#!/usr/bin/env python3
"""Offline policy-impact build. stdout contains aggregate counts/error paths only."""
import argparse
import json
import os
import tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.policy_impact import build,Invalid

def main():
    p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    target=Path(a.output).resolve();tmp=None
    try:
        j=json.loads(Path(a.job).read_text());b=j['bundle']
        if b['data_kind']!='SYNTHETIC' and any((d/'.git').exists() for d in [target.parent,*target.parents]):raise Invalid('PRIVATE_OUTPUT_REQUIRED','$')
        result=build(b,j['company_ids'],j['as_of'],public=j.get('public',False),public_macro_ids=j.get('public_macro_ids',[]),previous=j.get('previous'),query_timezone=j.get('query_timezone','UTC'))
        target.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix=target.name+'.',dir=target.parent);tmp=Path(name)
        with os.fdopen(fd,'w') as f:json.dump(result,f,ensure_ascii=False,allow_nan=False,indent=2);f.write('\n')
        os.replace(tmp,target)
        print(json.dumps({'status':'BUILT','counts':{g:len(result['bundle'][g]) for g in ('sources','policies','exposures','hypotheses')},'historical_pit_eligible':False}));return 0
    except (Invalid,ValueError,KeyError,TypeError,OSError) as e:
        if tmp is not None and tmp.exists():tmp.unlink()
        print(json.dumps({'status':'FAILED','code':e.code if isinstance(e,Invalid) else 'INPUT_INVALID','path':e.path if isinstance(e,Invalid) else '$'}));return 2
if __name__=='__main__':raise SystemExit(main())
