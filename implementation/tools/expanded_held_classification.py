#!/usr/bin/env python3
"""Offline retained catalog -> common classification -> issuer-sample Q/G."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.expanded_held_classification import build


def run(job,output,*,synthetic=False):
    out=Path(output).resolve();kind='SYNTHETIC' if synthetic else 'RETAINED_INPUT'
    if job.get('data_kind')!=kind:raise ValueError('JOB_DATA_KIND_MISMATCH')
    if not synthetic and any((p/'.git').exists() for p in (out,*out.parents)):
        raise ValueError('PRIVATE_OUTPUT_OUTSIDE_CHECKOUT_REQUIRED')
    if out.exists():raise ValueError('OUTPUT_ALREADY_EXISTS')
    files=build(job)
    out.mkdir(parents=True,mode=0o700)
    manifest={'schema_version':'held-expanded-classification-manifest/1','data_kind':kind,
        'source_files':{k:v for k,v in job.items() if isinstance(v,dict) and 'sha256' in v},'files':[]}
    def write(name,body):
        p=out/name;p.write_bytes(body);p.chmod(0o600)
        manifest['files'].append({'path':name,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)})
    files['replay-job.json']=job
    for name,value in files.items():write(name,(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode())
    # Readable without unpacking any archive; no company raw values in stdout.
    values={r['company_id']:r for r in files['preview.json']['result_rows']}
    import io
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=['analysis_row_id','issuer_id','valuation_date','sector','accounting','industry','reasons','record_id','source_refs','Q','G','V','total'])
    writer.writeheader()
    for r in files['classification-view.json']['rows']:
        v=values[r['company_id']]
        writer.writerow({'analysis_row_id':r['company_id'],'issuer_id':r['issuer_id'],'valuation_date':job['as_of'][:10],
            **{k:r[k]['id'] for k in ('sector','accounting','industry')},'reasons':json.dumps({k:r[k]['reasons'] for k in ('sector','accounting','industry')}),
            'record_id':r['record_id'],'source_refs':json.dumps(r['source_refs']),**v['axes'],'total':v['total']})
    write('classification-summary.csv',stream.getvalue().encode('utf-8-sig'))
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');(out/'manifest.json').chmod(0o600)
    return files['summary.json']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',required=True);p.add_argument('--output',required=True);p.add_argument('--synthetic',action='store_true');a=p.parse_args()
    try:
        summary=run(json.loads(Path(a.job).read_text()),a.output,synthetic=a.synthetic)
        print(json.dumps(summary,ensure_ascii=False,allow_nan=False))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print(json.dumps({'status':'FAILED','error_type':type(exc).__name__}),file=sys.stderr);raise SystemExit(1)
