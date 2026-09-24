"""KRX OPEN API -> RawDatasetStore network runner.

Secret handling: KRX_AUTH_KEY is read only from the process environment and is
never persisted in blobs, manifests, reports, URLs, or logs.

The KRX OPEN API documents AUTH_KEY as a request header. This runner keeps KRX
network I/O outside the analysis engine, matching the existing SEC/Yahoo
network-runner -> RawDatasetStore -> offline replay architecture.
"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from investment_system.ingestion.raw_store import RawDatasetStore

FETCHER='tools/fetch_krx_data.py v1'
BASE='https://data-dbg.krx.co.kr/svc/apis'
ENDPOINTS={
 'kospi_daily': ('sto/stk_bydd_trd','KRX_KOSPI_DAILY'),
 'kosdaq_daily': ('sto/ksq_bydd_trd','KRX_KOSDAQ_DAILY'),
 'kospi_basic': ('sto/stk_isu_base_info','KRX_KOSPI_BASIC'),
 'kosdaq_basic': ('sto/ksq_isu_base_info','KRX_KOSDAQ_BASIC'),
}

def _get(url,key):
    req=Request(url,headers={'AUTH_KEY':key,'Accept':'application/json','User-Agent':'Investment-System1/0.2'})
    with urlopen(req,timeout=30) as r:
        return r.read(),r.status,r.headers.get('Content-Type','application/json')

def run(store_dir:Path,bas_dd:str,kinds:list[str],refresh=False):
    key=os.environ.get('KRX_AUTH_KEY','').strip()
    if not key: raise RuntimeError('KRX_AUTH_KEY environment variable is required')
    if len(bas_dd)!=8 or not bas_dd.isdigit(): raise ValueError('bas_dd must be YYYYMMDD')
    store=RawDatasetStore(store_dir); log=[]
    for kind in kinds:
        if kind not in ENDPOINTS: raise ValueError(f'unknown kind: {kind}')
        path,source_kind=ENDPOINTS[kind]
        aid=f'krx:{kind}:{bas_dd}'
        if store.has(aid) and not refresh:
            log.append({'artifact_id':aid,'status':'SKIPPED_ALREADY_PRESENT'}); continue
        url=f'{BASE}/{path}?{urlencode({"basDd":bas_dd})}'
        try: body,status,ctype=_get(url,key)
        except HTTPError as e:
            snippet=e.read()[:180].decode('utf-8','replace')
            code=None
            try: code=json.loads(snippet).get('respCode')
            except Exception: code=None
            log.append({'artifact_id':aid,'status':f'HTTP_{e.code}','resp_code':code}); continue
        except (URLError,TimeoutError,OSError) as e:
            log.append({'artifact_id':aid,'status':f'ERROR_{type(e).__name__}'}); continue
        # Reject HTML/error pages before they can masquerade as real KRX data.
        try:
            parsed=json.loads(body.decode('utf-8'))
        except Exception:
            log.append({'artifact_id':aid,'status':'INVALID_NON_JSON','bytes':len(body)}); continue
        store.put(aid,body,url,source_kind,ctype,FETCHER,http_status=status,notes='KRX statistical information; AUTH_KEY not persisted')
        rows=len(parsed.get('OutBlock_1',[])) if isinstance(parsed,dict) else 0
        log.append({'artifact_id':aid,'status':'OK','bytes':len(body),'rows':rows})
        time.sleep(.12)
    report={'kind':'KRX_REAL_DATA_INGEST_RUN','as_of':bas_dd,'n_requested':len(log),'n_ok':sum(x['status'] in ('OK','SKIPPED_ALREADY_PRESENT') for x in log),'n_failed':sum(x['status'] not in ('OK','SKIPPED_ALREADY_PRESENT') for x in log),'log':log,'real_data_verified':False,'note':'Raw KRX ingest only; downstream PIT/eligibility verification remains required.'}
    (store_dir/f'krx_ingest_run_{int(time.time())}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--store',default=str(ROOT/'data'/'raw')); p.add_argument('--date',required=True); p.add_argument('--kinds',default='kospi_daily,kosdaq_daily,kospi_basic,kosdaq_basic'); p.add_argument('--refresh',action='store_true'); a=p.parse_args()
    print(json.dumps(run(Path(a.store),a.date,[x.strip() for x in a.kinds.split(',') if x.strip()],a.refresh),ensure_ascii=False,indent=2))
