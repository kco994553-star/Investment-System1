"""Read-only scoped action probe; never import this into production.
Preserves prior raw probes and uses the existing fetch_real_data._get unchanged.
"""
import importlib.util, hashlib, json, traceback
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('_existing_fetch_real_data', ROOT/'tools/fetch_real_data.py')
f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)
SYMS = ['ASML','LRCX','KLAC','8035.T','042700.KS','NVDA','AMD','AVGO','QCOM','INTC','MSFT','GOOGL','AMZN','RTX','SYK','ETN','HUBB','GEV','ROK']
def now(): return datetime.now(timezone.utc).isoformat()
def probe(sym):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5y&events=div%2Csplits'
    r = dict(provider_symbol=sym, certified_security_identity=None, request_url=url, started_at=now(), historical_available_at=None, authentication='NONE', retries=0, method='existing tools/fetch_real_data.py _get unchanged')
    try:
        body, status, ctype = f._get(url, f.YAHOO_UA)
        r.update(acquisition_completed_at=now(), http_status=status, content_type=ctype, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        dest = OUT/f'actions_{sym.replace(".","_")}_5y_daily_original.json'
        with dest.open('xb') as h: h.write(body)
        r.update(raw_path=str(dest.relative_to(ROOT.parent)), persisted_at=now())
        data=json.loads(body); chart=data.get('chart') or {}; results=chart.get('result') or []; r['chart_error']=chart.get('error')
        if results:
            q=results[0]; events=q.get('events') or {}; r.update(returned_symbol=(q.get('meta') or {}).get('symbol'), interval=(q.get('meta') or {}).get('dataGranularity'), bar_count=len(q.get('timestamp') or []), event_categories=list(events), event_counts={k:len(v) for k,v in events.items()}, events=events)
    except Exception as e:
        r.update(acquisition_completed_at=now(), status='FAILED', exception_type=type(e).__name__, error=str(e))
    return r
with ThreadPoolExecutor(max_workers=3) as pool: rows=list(pool.map(probe,SYMS))
with (OUT/'ACTION_ACQUISITION_PROBES_v0.3.json').open('x') as h:
    json.dump(dict(kind='SCOPED_CURRENT_ACTION_SOURCE_ACQUISITION_NOT_PRODUCTION', generated_at=now(), range_requested='5y', interval_requested='1d', events_requested=['div','splits'], source_code_sha256=hashlib.sha256((ROOT/'tools/fetch_real_data.py').read_bytes()).hexdigest(), prior_raw_unchanged=True, rows=rows),h,indent=2,allow_nan=False)
print(json.dumps({'captured':sum('sha256' in x for x in rows),'requested':len(rows),'counts':[{'symbol':r['provider_symbol'],'status':r.get('http_status',r.get('status')), 'events':r.get('event_counts'), 'error':r.get('error')} for r in rows]},indent=2))
