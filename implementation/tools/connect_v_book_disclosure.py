#!/usr/bin/env python3
"""Attach a reviewed stored book-value claim; no quote acquisition or ratio call."""
import argparse,json
from pathlib import Path
from investment_system.research.sector_qgv_held import checked_bytes
from investment_system.research.v_book_disclosure import connect
from investment_system.research.dual_qgv import json_bytes


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('PRESERVE_PREVIOUS_INPUT')
    job=json.loads(a.job.read_bytes());pack=json.loads(checked_bytes(job['resume']));claim=json.loads(checked_bytes(job['claim']))
    body=checked_bytes(job['body']);receipt=json.loads(checked_bytes(job['receipt']))
    req=[r for r in receipt['requests'] if r.get('sha256')==claim['document_sha256']]
    if len(req)!=1 or req[0]['acquired_at']!=claim['acquired_at'] or req[0]['http_status']!=200:raise ValueError('ACQUISITION_RECEIPT_MISMATCH')
    out,ready=connect(pack,claim,body,input_cutoff=job['input_cutoff'])
    a.output.mkdir(parents=True);(a.output/'v-resume-input.json').write_bytes(json_bytes(out));(a.output/'readiness.json').write_bytes(json_bytes(ready))
    (a.output/'source-job.json').write_bytes(json_bytes(job))
    print(json.dumps({k:ready[k] for k in ('valuation_date','real_raw_calculated','V_scored','total_scored')}))


if __name__=='__main__':main()
