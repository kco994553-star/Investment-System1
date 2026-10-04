"""Immutable documentation/corporate-action captures outside the production package."""
import importlib.util,hashlib,json
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[4]; OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_fetch_primary',ROOT/'tools/fetch_real_data.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
SOURCES=[('lrcx_split_2024','https://newsroom.lamresearch.com/2024-05-21-Lam-Research-Corporation-Announces-10-Billion-Share-Repurchase-Authorization-and-a-10-for-1-Stock-Split'),('klac_split_2026_8k','https://ir.kla.com/sec-filings/all-sec-filings/content/0001193125-26-212093/d116682d8k.htm'),('avgo_split_2024','https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-second-quarter-fiscal-year-2024-financial'),('tokyo_split_2026_notice','https://www.tel.com/news/ir/2026/20260529_001.html'),('tiingo_eod_documentation','https://www.tiingo.com/documentation/end-of-day'),('yahoo_adjusted_close_help','https://help.yahoo.com/kb/SLN28256.html')]
def now():return datetime.now(timezone.utc).isoformat()
def probe(item):
 name,url=item;r={'name':name,'source_url':url,'started_at':now(),'historical_available_at':None,'authentication':'NONE','retries':0,'method':'existing fetch_real_data._get unchanged'}
 try:
  body,status,ctype=f._get(url,f.YAHOO_UA);r.update(acquisition_completed_at=now(),http_status=status,content_type=ctype,bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
  dest=OUT/(name+'_original.html')
  with dest.open('xb') as sink: sink.write(body)
  r.update(raw_path=str(dest.relative_to(ROOT.parent)),persisted_at=now())
 except Exception as e:r.update(acquisition_completed_at=now(),status='FAILED',exception_type=type(e).__name__,error=str(e))
 return r
with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(probe,SOURCES))
with (OUT/'PRIMARY_SOURCE_CAPTURES_v0.3.json').open('x') as h:json.dump({'kind':'PRIMARY_BASIS_ACTION_SOURCE_CANDIDATES_NOT_ADMISSION','rows':rows},h,indent=2)
print(json.dumps(rows,indent=2))
