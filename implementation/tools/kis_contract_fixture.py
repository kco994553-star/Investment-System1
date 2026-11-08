#!/usr/bin/env python3
"""Generate deterministic SYNTHETIC owner-private contract fixtures outside Git."""
from pathlib import Path
import argparse,hashlib,json,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investment_system.research.kis_price_bridge import normalize_page


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


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args();out=a.output_dir.resolve()
    if any((d/'.git').exists() for d in (out,*out.parents)):p.error('OUTPUT_MUST_BE_OUTSIDE_GIT')
    out.mkdir(parents=True,exist_ok=True,mode=0o700);manifest=[]
    for name,data in fixtures().items():
        b=json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
        with os.fdopen(os.open(out/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(b)
        manifest.append({'file':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    print(json.dumps({'synthetic_only':True,'files':manifest}))
if __name__=='__main__':main()
