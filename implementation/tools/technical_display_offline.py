#!/usr/bin/env python3
"""Connect retained normalized daily bars to existing display kernels; no network."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.technical_display import measure_display,SCHEMA


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    if any((p/'.git').exists() for p in (output.parent,*output.parents)):
        parser.error('output must be outside Git working trees')
    payload=json.loads(args.input.read_bytes())
    result={'schema':SCHEMA,'signal_day':payload['signal_day'],'series':[
        measure_display(s['rows'],signal_day=payload['signal_day'],series_id=s['series_id'],symbol=s['symbol'],evidence=s['evidence'],source_kind=s.get('source_kind'))
        for s in payload['series']]}
    output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with os.fdopen(os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'schema':SCHEMA,'series_count':len(result['series'])}))


if __name__=='__main__':main()
