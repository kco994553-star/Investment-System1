#!/usr/bin/env python3
"""Offline retained-input classification -> QGV/technical/macro research handoff."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.sector_qgv import preview_qgv, save_user_config
from investment_system.research.sector_qgv_held import checked_bytes
from investment_system.research.sector_qgv_partial import assert_retained_preview, compare_axes
from investment_system.research.common_classification.catalog import dictionary
from investment_system.research.common_classification.records import from_sector_snapshot, resolve
from investment_system.research.common_classification.qgv import project_qgv, gate_comparison
from investment_system.research.common_classification.technical_macro import technical_groups, macro_projection


def run(job, output, *, synthetic=False):
    output=Path(output).resolve()
    if job.get('schema_version')!='common-classification-job/1': raise ValueError('JOB_VERSION_INVALID')
    kind='SYNTHETIC' if synthetic else 'RETAINED_INPUT'
    if job.get('data_kind')!=kind: raise ValueError('JOB_DATA_KIND_MISMATCH')
    if not synthetic and any((parent/'.git').exists() for parent in (output,*output.parents)):
        raise ValueError('PRIVATE_OUTPUT_OUTSIDE_CHECKOUT_REQUIRED')
    if output.exists(): raise ValueError('OUTPUT_ALREADY_EXISTS')
    read=lambda key:json.loads(checked_bytes(job[key]))
    snapshot=read('snapshot'); before=read('retained_preview'); saved=read('saved_config'); config=saved['config']
    assert_retained_preview(before,snapshot,config)
    if saved!=save_user_config(config,before,request_id=before['request_id'],expected_preview_id=before['preview_id']):
        raise ValueError('SAVED_CONFIG_REFERENCE_MISMATCH')
    if 'classification_store' in job:
        store=read('classification_store')
    else:
        store=from_sector_snapshot(snapshot,read('source_evidence'),source_sha256=job['snapshot']['sha256'],
                                   recorded_at=job['recorded_at'],data_kind=kind)
    if store['data_kind']!=kind: raise ValueError('STORE_DATA_KIND_MISMATCH')
    view=resolve(store,valuation_date=snapshot['valuation_date'],knowledge_as_of=job['knowledge_as_of'])
    projected=project_qgv(snapshot,view)
    after=preview_qgv(config,projected,job['request_id'])  # Only the new projection is calculated.
    qgv_links={'schema_version':'common-classification-qgv-links/1',
        'classification_hash':view['classification_hash'],'valuation_date':view['valuation_date'],
        'preview_identity':{k:after[k] for k in ('preview_id','input_hash','config_hash','cache_key','engine_version')},
        'rows':[{'company_id':r['company_id'],'issuer_id':r['issuer_id'],
                 'classification_record_id':r['record_id']} for r in view['rows']]}
    compared=compare_axes(before,after,config,config,job.get('comparison_id','CC-CLASSIFICATION-20261107-C1'),input_treatment=True)
    link_input=read('technical_input') if 'technical_input' in job else {'measurements':[],'security_links':[],'price_basis':'RAW'}
    technical=technical_groups(view,link_input['measurements'],link_input['security_links'],price_basis=link_input['price_basis'])
    macro=macro_projection(view,read('macro_source_links') if 'macro_source_links' in job else [])
    gate=gate_comparison(snapshot,view)
    original={r['company_id']:r for r in snapshot['rows']}
    rows=[]
    for r in view['rows']:
        old=original.get(r['company_id'],{})
        rows.append({'company_id':r['company_id'],'issuer_id':r['issuer_id'],
            'previous_sector':old.get('sector_id'),'sector':r['sector'],'industry':r['industry'],'accounting':r['accounting'],
            'sector_changed':old.get('sector_id')!=r['sector']['id'],
            'accounting_changed':old.get('accounting_template')!=r['accounting']['id'],
            'record_id':r['record_id'],'source_refs':r['source_refs']})
    raw_companies=sum(any(f['raw_value'] is not None for f in r['factors'].values()) for r in after['result_rows'])
    score_companies=sum(any(f['score'] is not None for f in r['factors'].values()) for r in after['result_rows'])
    summary={'schema_version':'common-classification-run/1','data_kind':kind,'valuation_date':snapshot['valuation_date'],
        'financial_as_of':snapshot['as_of'],'classification_knowledge_as_of':job['knowledge_as_of'],
        'classification_hash':view['classification_hash'],
        'universe_id':snapshot['universe_id'],'universe_version':snapshot['universe_version'],
        'classification':view['coverage'],'classification_failures':view['unresolved_reasons'],
        'sector_changes':sum(r['sector_changed'] for r in rows),'accounting_changes':sum(r['accounting_changed'] for r in rows),
        'raw_metric_codes':raw_companies,'factor_score_codes':score_companies,
        'raw_observations':sum(f['raw_valid'] for f in after['coverage']['factors'].values()),
        'price_availability':{'valid':None,'reason':'NOT_MEASURED_BY_CLASSIFICATION_ADAPTER'},
        'qgv_before':before['coverage']['axes'],'qgv_after':after['coverage']['axes'],
        'all_axes':after['coverage']['all_axes'],'total':after['coverage']['total'],
        'qg_comparison':compared['axes'],
        'official_gate_statuses':{s:sum(r['gate_status']==s for r in after['result_rows']) for s in ('PASS','VALUE_EXCLUDED','UNKNOWN')},
        'technical':{'requested_measurements':len(link_input['measurements']),
            'confirmed_company_links':sum(r['status']=='CONFIRMED' for r in technical['rows']),
            'verified_security_ids':len({sid for r in technical['rows'] for sid in r['security_ids']}),
            'confirmed_sector_groups':sum(g['membership_status']=='CONFIRMED' for g in technical['groups']),
            'actual_rank_rows':sum(r['rank'] is not None for g in technical['groups'] for m in g['board']['metrics'].values() for r in m['rows'])},
        'macro':{'source_sic_rows':view['coverage']['source_sic_available'],
            'common_industry_rows':view['coverage']['industry_confirmed'],
            'statistic_linked_rows':sum(r['statistic_mapping']['status']=='LINKED' for r in macro['rows']),
            'own_sector_returns':None,'rotation_probability':None},
        'gate_alternative':{'id':gate['comparison_id'],'transitions':gate['transitions'],'reasons':gate['reasons'],'applied':False},
        'performance':None,'historical_pit_certified':False,'deployment_state':'NOT_DEPLOYED'}
    files={'dictionary.json':dictionary(),'classification-store.json':store,'classification-view.json':view,
        'qgv-input.json':projected,'qgv-preview.json':after,'qgv-classification-links.json':qgv_links,'qg-comparison.json':compared,
        'classification-comparison.json':rows,'technical.json':technical,'macro.json':macro,
        'gate-comparison.json':gate,'summary.json':summary,'reference-saved-config.json':saved,
        'saved-config.json':save_user_config(config,after,request_id=after['request_id'],expected_preview_id=after['preview_id']),
        'replay-job.json':job}
    output.mkdir(parents=True,mode=0o700)
    manifest={'schema_version':'common-classification-manifest/1','data_kind':kind,
              'classification_hash':view['classification_hash'],'files':[],
              'source_files':{k:v for k,v in job.items() if isinstance(v,dict) and 'sha256' in v}}
    for name,data in files.items():
        body=(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
        path=output/name; path.write_bytes(body); path.chmod(0o600)
        manifest['files'].append({'path':name,'sha256':hashlib.sha256(body).hexdigest(),'size':len(body)})
    path=output/'manifest.json';path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--synthetic',action='store_true')
    args=parser.parse_args()
    try:
        summary=run(json.loads(Path(args.job).read_text()),args.output,synthetic=args.synthetic)
        print(json.dumps(summary,ensure_ascii=False,allow_nan=False))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        # No input payload, private company value or raw path in ordinary logs.
        print(json.dumps({'status':'FAILED','error_type':type(exc).__name__}),file=sys.stderr)
        raise SystemExit(1)
