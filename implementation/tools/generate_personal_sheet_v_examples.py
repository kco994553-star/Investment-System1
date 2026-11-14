#!/usr/bin/env python3
"""Developer-only, network-free synthetic examples. No real-data input mode."""
import argparse,hashlib,json,runpy
from pathlib import Path
from investment_system.research.personal_sheet_v import prepare_personal,personal_result,personal_page
from investment_system.research.qgv_555 import configuration,identity
from investment_system.research.dual_qgv import json_bytes
from investment_system.research.dual_qgv_delivery import MAX_BYTES


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--synthetic',action='store_true',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('PRESERVE_EXISTING_EXAMPLES')
    root=Path(__file__).resolve().parents[1]
    fixture=runpy.run_path(str(root/'tests/research/test_personal_sheet_v.py'))['fixture']
    files={};states=[]
    for model in ('U1-555','S1-555'):
        req,e,r,f,prices=fixture();req['configuration']=configuration(model,version='0.4.0')
        assert all(x['company_id'].startswith('SYN:') for x in e['rows'])
        prepared=prepare_personal(req,e,r,f,prices,expected_evaluation=identity(e),expected_reference=identity(r))
        out=personal_result(prepared);key=model.lower()
        files[key+'-request.json']=json_bytes(req)
        files[key+'-result.json']=json_bytes(out)
        if model=='U1-555':
            for name,value in [('evaluation',e),('reference',r),('financial-records',f),('prices',prices)]:
                files['input-'+name+'.json']=json_bytes(value)
        files[key+'-packet.json']=prepared['packet_text'].encode()
        files[key+'-page.json']=json_bytes(personal_page(out,limit=23))
        files[key+'-groups.json']=json_bytes(dict(schema_version='personal-sheet-v-groups/1',namespace='PERSONAL_SHEET_V',
            result_hash=out['result_hash'],groups=out['groups']))
        files[key+'-expected.json']=json_bytes(dict(data_kind='SYNTHETIC',counts=out['counts'],counts_unit=out['counts_unit'],
            denominator=out['denominator'],expected_payload_sha256=prepared['payload_sha256'],
            expected_evaluation=identity(e),expected_reference=identity(r),expected_configuration_hash=prepared['packet']['configuration_hash']))
    for label in ('UNCONFIRMED_TIME','DELAYED','ADJUSTMENT_UNKNOWN','READ_FAILED','NONPRICE_UNCONFIRMED','NO_PRICE','GATE_UNKNOWN'):
        req,e,r,f,prices=fixture(10)
        if label=='UNCONFIRMED_TIME':prices[0].update(price_timestamp=None,time_status='UNCONFIRMED')
        elif label=='DELAYED':prices[0]['price_timestamp']='2026-11-13T20:00:00Z'
        elif label=='ADJUSTMENT_UNKNOWN':prices[0]['adjustment_status']='UNKNOWN'
        elif label=='READ_FAILED':prices[0].update(status='READ_FAILED',price=None)
        elif label=='NONPRICE_UNCONFIRMED':f[e['rows'][0]['company_id']]['basis_evidence']['share_basis']['status']='UNKNOWN'
        elif label=='NO_PRICE':prices=[]
        elif label=='GATE_UNKNOWN':e['rows'][0]['gate']=None
        out=personal_result(prepare_personal(req,e,r,f,prices,expected_evaluation=identity(e),expected_reference=identity(r)))
        row=out['rows'][0];states.append(dict(state=label,expected_counts=out['counts'],row=row))
    files['states.json']=json_bytes(dict(data_kind='SYNTHETIC',schema_version='personal-sheet-v-states/1',states=states,
        real_sheet_connected=False,real_price_calculation_executed=False,performance_verified=False))
    a.output.mkdir(parents=True)
    entries=[]
    for name,raw in sorted(files.items()):
        assert len(raw)<=MAX_BYTES
        (a.output/name).write_bytes(raw);assert (a.output/name).read_bytes()==raw
        entries.append(dict(path=name,size=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    (a.output/'manifest.json').write_bytes(json_bytes(dict(schema_version='personal-sheet-v-example-manifest/1',data_kind='SYNTHETIC',files=entries)))
    print(json.dumps(dict(data_kind='SYNTHETIC',files=len(entries),largest=max(x['size'] for x in entries))))


if __name__=='__main__':main()
