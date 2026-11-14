#!/usr/bin/env python3
"""Generate deterministic SYNTHETIC owner-private contract fixtures outside Git."""
from pathlib import Path
from datetime import date
from decimal import Decimal
import argparse,hashlib,json,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.kis_price_bridge import normalize_page
from investment_system.research.technical_handoff import prepare_technical
from investment_system.research.exp_deciles.technical_measures import sessions


def fixtures():
    days=['2026-10-19','2026-10-20','2026-10-21','2026-10-22','2026-10-23']
    body=json.dumps({'rt_cd':'0','output1':{'rsym':'DNASSYN'},'output2':[dict(xymd=d.replace('-',''),open='10',high='12',low='9',clos='11',tvol='100',tamt='1100') for d in days]},sort_keys=True).encode()
    receipt={'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'fetched_at':'2026-10-24T04:00:00Z','http_status':200}
    request={'SYMB':'SYN','EXCD':'NAS','MODP':'0','GUBN':'0','BYMD':'20261023'}
    evidence={'currency':'USD','currency_reference':'SYNTHETIC','identity_status':'CONFIRMED','identity_reference':'SYNTHETIC','identity_start':days[0],'identity_end':days[-1],'security_id':'SYNTHETIC-SECURITY-1','confirmed_ranges':[{'from':days[0],'to':days[-1],'evidence':'SYNTHETIC'}],'held_ranges':[],'splits':[]}
    raw=normalize_page(body,receipt=receipt,request=request,evidence=evidence)
    evidence['splits']=[{'date':'2026-10-22','ratio':'2','evidence':'SYNTHETIC','status':'CONFIRMED'}]
    evidence['held_ranges']=[{'from':'2026-10-20','to':'2026-10-20','reason':'SYNTHETIC_HELD_SESSION'}]
    adjusted=normalize_page(body,receipt=receipt,request=request,evidence=evidence,basis='SPLIT_ADJUSTED')
    for r in (raw,adjusted):r['fixture_kind']='SYNTHETIC_NOT_A_COMPANY'
    return {'synthetic-raw.json':raw,'synthetic-split-held.json':adjusted}


def handoff_fixtures():
    """Main can generate the exact jobs/results; every company and price is invented."""
    days=sessions(date(2026,5,1),date(2026,11,13))[-100:]
    event=days[50];out={};expected=[]
    for name in ('normal','split','missing-session','missing-evidence','stale'):
        rows=[]
        for i,d in enumerate(days):
            if (name=='missing-session' and i==50) or (name=='stale' and i==99):continue
            factor=2 if name=='split' and d<event else 1
            value=Decimal(100)+Decimal(i)/10
            rows.append(dict(xymd=d.replace('-',''),open=str(value*factor),high=str((value+1)*factor),
                low=str((value-1)*factor),clos=str(value*factor),tvol=str(100//factor),tamt='10000'))
        body=json.dumps({'rt_cd':'0','output1':{'rsym':'DNASSYN'},'output2':rows},sort_keys=True).encode()
        receipt=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),
                     fetched_at='2026-11-14T04:00:00Z',http_status=200)
        request=dict(SYMB='SYN',EXCD='NAS',MODP='0',GUBN='0',BYMD='20261113')
        evidence=dict(currency='USD',currency_reference='SYNTHETIC_CURRENCY',
            identity_status='UNKNOWN' if name=='missing-evidence' else 'CONFIRMED',
            identity_reference='SYNTHETIC_LISTING',identity_start=days[0],identity_end=days[-1],
            security_id='SYNTHETIC:SECURITY:1',issuer_id='SYNTHETIC:ISSUER:1',
            confirmed_ranges=[dict(**{'from':days[0],'to':days[-1]},evidence='SYNTHETIC_ACTION_RANGE')],
            held_ranges=[],splits=[dict(date=event,ratio='2',status='CONFIRMED',
                evidence='SYNTHETIC_SPLIT_NOT_ACTUAL_EVENT')] if name=='split' else [])
        c=normalize_page(body,receipt=receipt,request=request,evidence=evidence,
                         basis='SPLIT_ADJUSTED' if name=='split' else 'RAW')
        c['fixture_kind']='SYNTHETIC_NOT_A_COMPANY'
        job=dict(mode='technical-handoff',arguments=dict(c=c,evaluation_day=days[-1],series_id='SYNTHETIC:REQUEST:1'))
        result=prepare_technical(**job['arguments'])
        out[name+'-job.json']=job;out[name+'-result.json']=result
        expected.append(dict(case=name,signal_day=result['context']['signal_day'],
            chart_observation_day=result['context']['chart_observation_day'],
            missing_sessions=result['sessions']['missing'],
            component_raw=result['components']['raw_count'],component_adopted=result['components']['adopted_count'],
            measure_raw=result['measures']['raw_count'],measure_adopted=result['measures']['adopted_count'],
            pattern_state=result['patterns']['state'],pattern_reasons=result['patterns']['reasons'],
            group_status=result['group']['state'],rank=None,decile=None))
    out['expectations.json']=dict(schema='kis-technical-handoff-expectations/1',data_kind='SYNTHETIC',cases=expected)
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--technical-handoff',action='store_true',help='Generate five synthetic Main handoff cases')
    a=p.parse_args();out=a.output_dir.resolve()
    if any((d/'.git').exists() for d in (out,*out.parents)):p.error('OUTPUT_MUST_BE_OUTSIDE_GIT')
    out.mkdir(parents=True,exist_ok=True,mode=0o700);manifest=[]
    for name,data in (handoff_fixtures() if a.technical_handoff else fixtures()).items():
        b=json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
        with os.fdopen(os.open(out/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(b)
        manifest.append({'file':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    result=dict(schema='kis-synthetic-manifest/1',synthetic_only=True,files=manifest)
    if a.technical_handoff:
        data=json.dumps(result,sort_keys=True,separators=(',',':')).encode()+b'\n'
        with os.fdopen(os.open(out/'manifest.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(data)
    print(json.dumps(result))
if __name__=='__main__':main()
