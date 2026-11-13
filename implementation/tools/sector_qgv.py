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
    if mode=='dual-study':
        from investment_system.research.dual_qgv import run_board,save_board,replay_board,delivery_artifacts,json_bytes
        if any(k in job for k in ('config','main_request','saved_config','reference_plan','comparisons')):
            raise ValueError('DUAL_JOB_CONFLICT')
        evaluation,reference=[json.loads(checked_bytes(job[k])) for k in ('evaluation_snapshot','reference_snapshot')]
        if job.get('dual_saved'):
            if 'dual_config' in job:raise ValueError('DUAL_JOB_CONFLICT')
            saved=json.loads(checked_bytes(job['dual_saved']));config=saved['configuration']
            result=replay_board(saved,evaluation,reference,job['request_id'])
        else:
            config=json.loads(checked_bytes(job['dual_config']))
            result=run_board(config,evaluation,reference,request_id=job['request_id'])
            saved=save_board(config,result)
        artifacts={'dual-result.json':result,'dual-saved.json':saved}
        artifacts.update(delivery_artifacts({config['model_id']:result}))
        output.mkdir(parents=True,mode=0o700)
        manifest={'schema_version':'qgv-dual-run/1','data_kind':'SYNTHETIC' if synthetic else 'PRIVATE','input_job':job,'files':[]}
        for name,data in artifacts.items():
            body=json_bytes(data);p=output/name;p.write_bytes(body);p.chmod(0o600)
            manifest['files'].append({'path':name,'size':len(body),'sha256':hashlib.sha256(body).hexdigest()})
        (output/'manifest.json').write_bytes(json_bytes(manifest))
        return {'schema_version':'qgv-dual-run-summary/1','model_id':config['model_id'],'coverage':result['coverage'],'performance':'NOT_MEASURED'}
    if mode=='reference-study':
        from investment_system.research.sector_qgv_reference import run_reference_study,save_reference_settings,replay_reference_study,reference_view
        if any(k in job for k in ('main_request','saved_config','retained_preview','comparisons','axis_comparison')):
            raise ValueError('REFERENCE_JOB_CONFLICT')
        ev,base,source,source_preview=[json.loads(checked_bytes(job[k])) for k in
            ('evaluation_snapshot','evaluation_preview','reference_snapshot','reference_preview')]
        if job.get('reference_saved'):
            if 'config' in job or 'reference_plan' in job:raise ValueError('REFERENCE_JOB_CONFLICT')
            saved=json.loads(checked_bytes(job['reference_saved']))
            result=replay_reference_study(saved,ev,base,source,source_preview,request_id=job['request_id'])
            config,plan=saved['config'],saved['plan']
        else:
            config=job.get('config',default_config());plan=json.loads(checked_bytes(job['reference_plan']))
            result=run_reference_study(config,ev,base,source,source_preview,plan,request_id=job['request_id'])
        saved=save_reference_settings(config,plan,result)
        reference_snapshot=result.pop('reference_snapshot')
        artifacts={'reference-result.json':result,'reference-settings.json':saved,'reference-snapshot.json':reference_snapshot,
                   'reference-view.json':reference_view(result)}
        output.mkdir(parents=True,mode=0o700)
        manifest={'schema_version':'sector-qgv-reference-run/1','data_kind':job.get('data_kind','PRIVATE'),'input_job':job,'files':[]}
        for name,data in artifacts.items():
            body=(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
            p=output/name;p.write_bytes(body);p.chmod(0o600)
            manifest['files'].append({'path':name,'size':len(body),'sha256':hashlib.sha256(body).hexdigest()})
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        return {'schema_version':'sector-qgv-reference-run-summary/1','evaluation_denominator':len(ev['members']),
            'reference_issuers':result['reference_population']['issuers'],'comparison':result['comparison']['axes'],
            'performance':'NOT_MEASURED'}
    restoring='saved_config' in job or 'retained_preview' in job
    if restoring and (not all(k in job for k in ('saved_config','retained_preview')) or
                      mode!='normalized' or any(k in job for k in ('config','main_request')) or
                      job.get('comparisons') or job.get('axis_comparison')):
        raise ValueError('SAVED_REPLAY_JOB_CONFLICT')
    config=job.get('config',default_config());audit=None
    if mode=='held-sec':
        spec=job['sec_snapshot'];sec=json.loads(checked_bytes(spec))
        mappings=json.loads(checked_bytes(job['mapping'])) if job.get('mapping') else {}
        snapshot,audit=build_held_snapshot(sec,job['archives'],snapshot_hash=spec['sha256'],mapping_rows=mappings)
    elif mode=='normalized':snapshot=json.loads(checked_bytes(job['snapshot']))
    elif mode=='held-input-repair':
        from investment_system.research.sector_qgv_held_repair import repair
        original=json.loads(checked_bytes(job['snapshot']))
        snapshot,audit=repair(original,json.loads(checked_bytes(job['repair_plan'])))
    elif mode=='held-sec-classification':
        from investment_system.research.sector_qgv_classification import connect_held_classification
        spec=job['sec_snapshot'];sec=json.loads(checked_bytes(spec))
        retained=json.loads(checked_bytes(job['snapshot']))
        snapshot,audit=connect_held_classification(retained,sec,job['archives'],spec['sha256'])
    elif mode=='v-resume':
        from investment_system.research.sector_qgv_v import resume
        pack=json.loads(checked_bytes(job['v_pack']));market=json.loads(checked_bytes(job['market_inputs']))
        expected_kind='SYNTHETIC' if synthetic else 'PRIVATE'
        if any(x.get('data_kind')!=expected_kind for x in (job,pack,market)):raise ValueError('V_DATA_KIND_MISMATCH')
        if config!=default_config():raise ValueError('V_RESUME_DEFAULT_CONFIG_REQUIRED')
        if not synthetic:
            evidence_hashes={spec['sha256'] for spec in job.get('market_evidence',[]) if checked_bytes(spec) is not None}
            def verify_refs(value):
                if isinstance(value,dict):
                    for k,v in value.items():
                        if k in ('evidence_refs','provenance','capital_scope_evidence'):
                            if not isinstance(v,list) or not v:raise ValueError('V_MARKET_EVIDENCE_REQUIRED')
                            for ref in v:
                                match=re.search(r'#sha256=([0-9a-f]{64})(?:$|[&#/])',ref) if isinstance(ref,str) else None
                                if not match or match[1] not in evidence_hashes:raise ValueError('V_MARKET_EVIDENCE_FILE_REQUIRED')
                        else:verify_refs(v)
                elif isinstance(value,list):
                    for v in value:verify_refs(v)
            verify_refs(market['records'])
        snapshot,resumed_preview=resume(pack,market,job['request_id'])
    elif mode=='v-prepare':
        from investment_system.research.sector_qgv_v import prepare
        if synthetic or job.get('data_kind')!='PRIVATE':raise ValueError('V_PREPARATION_PRIVATE_REQUIRED')
        snapshot=json.loads(checked_bytes(job['snapshot']));sec=json.loads(checked_bytes(job['sec_snapshot']))
        cache=json.loads(checked_bytes(job['financial_cache'])) if job.get('financial_cache') else {}
        pack,report=prepare(snapshot,sec,job['archives'],cache)
        output.mkdir(parents=True,mode=0o700)
        manifest={'schema_version':'sector-qgv-v-preparation-run/1','files':[]}
        for name,data in [('v-resume-input.json',pack),('readiness.json',report)]:
            body=(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode();path=output/name;path.write_bytes(body);path.chmod(0o600)
            manifest['files'].append({'path':name,'sha256':hashlib.sha256(body).hexdigest(),'size':len(body)})
        p=output/'manifest.json';p.write_text(json.dumps(manifest,indent=2)+'\n');p.chmod(0o600)
        return {k:v for k,v in report.items() if k!='rows'}
    else:raise ValueError('JOB_MODE_UNSUPPORTED')
    main_response=None
    if restoring:
        from investment_system.research.sector_qgv_restore import replay_saved_config
        restored=replay_saved_config(json.loads(checked_bytes(job['saved_config'])),
            json.loads(checked_bytes(job['retained_preview'])),snapshot,job['request_id'])
        config=restored['config'];preview=restored['preview']
    elif job.get('main_request'):
        from investment_system.research.sector_qgv_main import run_preview_request
        request=json.loads(checked_bytes(job['main_request']))
        if request['request_id']!=job['request_id']:raise ValueError('MAIN_REQUEST_JOB_MISMATCH')
        main_response=run_preview_request(snapshot,request)
        preview=main_response['after'];config=main_response['after_config']
    else:preview=resumed_preview if mode=='v-resume' else preview_qgv(config,snapshot,job['request_id'])
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
    if mode=='held-input-repair':
        from investment_system.research.sector_qgv_partial import assert_retained_preview
        from investment_system.research.sector_qgv_held_repair import comparison
        retained=json.loads(checked_bytes(job['before_preview']))
        assert_retained_preview(retained,original,config)
        artifacts['input-repair-comparison.json']=comparison(retained,preview)
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
