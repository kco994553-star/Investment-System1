#!/usr/bin/env python3
"""Network-free 555/Top500 CLI. Input pins are supplied independently in the job."""
import argparse,hashlib,json
from pathlib import Path
from investment_system.research.qgv_555 import run,configuration,catalog,accounting_recipes,fixture
from investment_system.research.qgv_555_delivery import artifacts,validate
from investment_system.research.qgv_555_additional import attach
from investment_system.research.top500_selection import select_top500
from investment_system.research.dual_qgv import json_bytes


def read(desc):
    raw=Path(desc['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=desc['sha256']:raise ValueError('INPUT_FILE_HASH')
    return json.loads(raw)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',type=Path);p.add_argument('--synthetic',action='store_true');p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise ValueError('OUTPUT_ALREADY_EXISTS_PRESERVE_PRIOR')
    if a.synthetic:
        e,r=fixture();job=dict(data_kind='SYNTHETIC');configs={k:configuration(k) for k in ('U1-555','S1-555')}
    else:
        job=json.loads(a.job.read_bytes())
        if job.get('mode')=='central-v-input':
            from investment_system.research.qgv_555_central_v import bind_central_prices
            snapshot,audit=bind_central_prices(read(job['snapshot']),read(job['financial_records']),read(job['prices']),
                job['reviewed_at'],job['input_cutoff'])
            a.output.mkdir(parents=True)
            (a.output/'snapshot.json').write_bytes(json_bytes(snapshot))
            (a.output/'central-v-audit.json').write_bytes(json_bytes(audit))
            return
        if job.get('mode')=='preview':
            from investment_system.research.qgv_555_preview import preview,preview_page
            result=preview(job['request'],read(job['evaluation']),read(job['reference']),
                expected_evaluation=job['expected_evaluation'],expected_reference=job['expected_reference'],
                saved_before=read(job['saved_before']) if job.get('saved_before') else None)
            a.output.mkdir(parents=True)
            (a.output/'preview-result.json').write_bytes(json_bytes(result))
            (a.output/'preview-page.json').write_bytes(json_bytes(preview_page(result,**job.get('page',{}))))
            return
        if job.get('mode')=='top500':
            result=select_top500(read(job['input']),previous=read(job['previous']) if job.get('previous') else None)
            a.output.mkdir(parents=True);(a.output/'top500.json').write_bytes(json_bytes(result));return
        e=read(job['evaluation']);r=read(job['reference']);configs=job['configurations']
    boards={k:attach(run(c,e,r),e,r) for k,c in configs.items()}
    # Save reproducible calculation output before projection. A projection failure
    # can then resume through project_qgv_555_additional without recalculating QGV.
    a.output.mkdir(parents=True)
    for key,b in boards.items():(a.output/(key+'-result.json')).write_bytes(json_bytes(b))
    f=artifacts(boards,data_kind=job['data_kind'])
    pin=hashlib.sha256(json_bytes(f['manifest.json'])).hexdigest()
    validated=validate(f,manifest_sha256=pin,expected_evaluation=next(iter(boards.values()))['evaluation'],expected_references={k:b['reference'] for k,b in boards.items()})
    for name,value in f.items():(a.output/name).write_bytes(json_bytes(value))
    (a.output/'verification.json').write_bytes(json_bytes(validated))
    if a.synthetic:
        (a.output/'catalog.json').write_bytes(json_bytes(catalog()));(a.output/'accounting-recipes.json').write_bytes(json_bytes(accounting_recipes()))
        (a.output/'evaluation-input.json').write_bytes(json_bytes(e));(a.output/'reference-input.json').write_bytes(json_bytes(r))
    print(json.dumps({k:b['coverage'] for k,b in boards.items()}))


if __name__=='__main__':main()
