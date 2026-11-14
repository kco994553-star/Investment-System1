#!/usr/bin/env python3
"""Offline owner-private price/QGV jobs. No source calls or public serializers."""
import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.kis_price_bridge import normalize_page,analyze,compare,value_positions,merge_update
from investment_system.research.private_layer_qgv import compute_private_qgv
from investment_system.research.private_technical_board import measure_contract, build_contract_board, board_reader_payload
from investment_system.research.technical_handoff import prepare_technical


def execute(job):
    mode=job['mode'];a=job['arguments']
    if mode=='normalize':return normalize_page(Path(job['body_path']).read_bytes(),**a)
    functions={'analyze':analyze,'compare':compare,'positions':value_positions,'update':merge_update,'qgv':compute_private_qgv,
               'technical-measures':measure_contract,'technical-board':build_contract_board,
               'technical-reader':board_reader_payload,'technical-handoff':prepare_technical}
    if mode not in functions:raise ValueError('UNSUPPORTED_OFFLINE_JOB')
    return functions[mode](**a)


def default(v):
    if isinstance(v,Decimal):return str(v)
    if isinstance(v,(date,datetime)):return v.isoformat()
    raise TypeError('UNSUPPORTED_PRIVATE_VALUE')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();out=a.output.resolve()
    if any((parent/'.git').exists() for parent in (out.parent,*out.parents)):p.error('OUTPUT_MUST_BE_OUTSIDE_GIT')
    try:
        result=execute(json.loads(a.job.read_bytes()));data=json.dumps(result,ensure_ascii=False,allow_nan=False,default=default,separators=(',',':')).encode()+b'\n'
        out.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        with os.fdopen(os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(data)
    except Exception:
        # Do not echo provider response, symbol, local path or input values.
        print('OFFLINE_PRIVATE_JOB_FAILED',file=sys.stderr);return 1
    print('OFFLINE_PRIVATE_JOB_WRITTEN');return 0


if __name__=='__main__':raise SystemExit(main())
