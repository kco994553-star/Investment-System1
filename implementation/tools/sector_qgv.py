#!/usr/bin/env python3
"""Offline JSON job -> sector-QGV preview, comparisons and saved configuration.

No network or collection hooks. Real results require a directory outside the checkout;
synthetic fixtures may use --synthetic with an explicitly synthetic job.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.sector_qgv import (default_config,preview_qgv,comparison_configs,
    compare_previews,save_user_config,list_factors)
from investment_system.research.sector_qgv_held import checked_bytes,build_held_snapshot


def run(job,output,synthetic=False):
    output=Path(output).resolve();root=Path(__file__).resolve().parents[2]
    if synthetic and job.get('data_kind')!='SYNTHETIC':raise ValueError('SYNTHETIC_LABEL_REQUIRED')
    if not synthetic and output.is_relative_to(root):raise ValueError('PRIVATE_OUTPUT_OUTSIDE_CHECKOUT_REQUIRED')
    if not synthetic and any((parent/'.git').exists() for parent in (output,*output.parents)):
        raise ValueError('PRIVATE_OUTPUT_OUTSIDE_CHECKOUT_REQUIRED')
    if output.exists():raise ValueError('OUTPUT_ALREADY_EXISTS')
    mode=job.get('mode','normalized')
    config=job.get('config',default_config());audit=None
    if mode=='held-sec':
        spec=job['sec_snapshot'];sec=json.loads(checked_bytes(spec))
        mappings=json.loads(checked_bytes(job['mapping'])) if job.get('mapping') else {}
        snapshot,audit=build_held_snapshot(sec,job['archives'],snapshot_hash=spec['sha256'],mapping_rows=mappings)
    elif mode=='normalized':snapshot=json.loads(checked_bytes(job['snapshot']))
    elif mode=='held-sec-classification':
        from investment_system.research.sector_qgv_classification import connect_held_classification
        spec=job['sec_snapshot'];sec=json.loads(checked_bytes(spec))
        retained=json.loads(checked_bytes(job['snapshot']))
        snapshot,audit=connect_held_classification(retained,sec,job['archives'],spec['sha256'])
    else:raise ValueError('JOB_MODE_UNSUPPORTED')
    main_response=None
    if job.get('main_request'):
        from investment_system.research.sector_qgv_main import run_preview_request
        request=json.loads(checked_bytes(job['main_request']))
        if request['request_id']!=job['request_id']:raise ValueError('MAIN_REQUEST_JOB_MISMATCH')
        main_response=run_preview_request(snapshot,request)
        preview=main_response['after'];config=main_response['after_config']
    else:preview=preview_qgv(config,snapshot,job['request_id'])
    saved=save_user_config(config,preview,request_id=job['request_id'],expected_preview_id=preview['preview_id'])
    comparisons=[]
    if job.get('comparisons'):
        # Preregistered treatments always compare to the pinned default, not a caller's custom baseline.
        if config!=default_config():raise ValueError('COMPARISON_DEFAULT_BASE_REQUIRED')
        for cid,candidate in comparison_configs().items():
            result=preview_qgv(candidate,snapshot,cid)
            comparisons.append(compare_previews(preview,result,cid))
    axis_comparison=None
    if job.get('axis_comparison'):
        from investment_system.research.sector_qgv_partial import assert_retained_preview,compare_axes
        spec=job['axis_comparison']
        retained=json.loads(checked_bytes(spec['before_preview']))
        before_config=spec.get('before_config',default_config())
        reference_snapshot=json.loads(checked_bytes(spec['before_snapshot'])) if spec.get('input_treatment') else snapshot
        assert_retained_preview(retained,reference_snapshot,before_config)
        axis_comparison=compare_axes(retained,preview,before_config,config,spec['comparison_id'],
                                     input_treatment=spec.get('input_treatment',False))
    baseline=json.loads(checked_bytes(job['official_baseline_coverage'])) if job.get('official_baseline_coverage') else None
    artifacts={'preview.json':preview,'saved-config.json':saved,'snapshot.json':snapshot,
        'catalog.json':list_factors(config,'INFORMATION_TECHNOLOGY','GENERAL'),
        'comparisons.json':comparisons,'connection-audit.json':audit,
        'official-baseline-reference.json':baseline}
    if main_response:artifacts['main-response.json']=main_response
    if axis_comparison:artifacts['axis-comparison.json']=axis_comparison
    output.mkdir(parents=True,mode=0o700)
    manifest={'schema_version':'sector-qgv-run/1','data_kind':job.get('data_kind','PRIVATE'),
              'request_id':job['request_id'],'input_job':job,'files':[]}
    for name,data in artifacts.items():
        body=(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
        p=output/name;p.write_bytes(body);p.chmod(0o600)
        manifest['files'].append({'path':name,'size':len(body),'sha256':hashlib.sha256(body).hexdigest()})
    p=output/'manifest.json';p.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n');p.chmod(0o600)
    return {'schema_version':'sector-qgv-run-summary/1','denominator':len(snapshot['members']),
            'axes':preview['coverage']['axes'],'all_axes':preview['coverage']['all_axes'],
            'total':preview['coverage']['total'],'performance':'NOT_MEASURED'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--synthetic',action='store_true');args=parser.parse_args()
    try:summary=run(json.loads(Path(args.job).read_text()),args.output,args.synthetic)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        # No raw inputs, company results or exception repr in stdout/stderr.
        code=str(exc)
        reason=code if re.fullmatch(r'[A-Z][A-Z_]+',code) else 'INPUT_VALIDATION_FAILED'
        print(json.dumps({'status':'FAILED','reason_type':type(exc).__name__,'reason':reason}));return 2
    print(json.dumps(summary));return 0


if __name__=='__main__':raise SystemExit(main())
