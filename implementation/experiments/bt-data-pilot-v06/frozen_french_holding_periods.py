"""Private complete-window analysis of frozen curves; no stock/price/ledger engine."""
import argparse, hashlib, json, math, subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
HORIZONS=(12,36,60,120)
TIE_TOLERANCE=1e-12

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validated_curve(curve):
 dates=[]; nav=[]; prev=None
 for row in curve:
  k=row['date']; d=datetime.strptime(k,'%Y-%m'); serial=d.year*12+d.month
  if d.strftime('%Y-%m')!=k: raise ValueError('MONTH_FORMAT')
  if prev is not None and serial!=prev+1: raise ValueError('NONCONTIGUOUS_MONTHS')
  v=row['value']
  if type(v) not in (float,int) or not math.isfinite(v) or v<=0: raise ValueError('POSITIVE_NAV_REQUIRED')
  dates.append(k);nav.append(v);prev=serial
 if not nav: raise ValueError('EMPTY_CURVE')
 return dates,nav

def holding_windows(curve,benchmark,months):
 if months not in HORIZONS: raise ValueError('UNREGISTERED_HORIZON')
 dates,nav=validated_curve(curve);bd,bnav=validated_curve(benchmark)
 if dates!=bd: raise ValueError('BENCHMARK_DATE_MISMATCH')
 windows=[]
 for i in range(len(nav)-months):
  j=i+months;t=nav[j]/nav[i]-1;b=bnav[j]/bnav[i]-1
  a=(1+t)**(12/months)-1;ba=(1+b)**(12/months)-1;peak=nav[i];dd=0.0
  for v in nav[i:j+1]: peak=max(peak,v);dd=min(dd,v/peak-1)
  windows.append(dict(start_nav_month=dates[i],first_return_month=dates[i+1],end_month=dates[j],cumulative_return=t,annualized_return=a,max_drawdown=dd,benchmark_cumulative_return=b,benchmark_annualized_return=ba,cumulative_difference=t-b,annualized_difference=a-ba))
 if not windows: return dict(months=months,window_count=0,summary=None,null_reason='INSUFFICIENT_COMPLETE_MONTHS',windows=[])
 summary={}
 for f in ('cumulative_return','annualized_return','max_drawdown','cumulative_difference','annualized_difference'):
  vs=[w[f] for w in windows];summary[f]=dict(mean=mean(vs),median=median(vs),worst=min(vs))
 summary.update(loss_fraction=sum(w['cumulative_return'] < -TIE_TOLERANCE for w in windows)/len(windows),market_win_fraction=sum(w['cumulative_difference'] > TIE_TOLERANCE for w in windows)/len(windows),market_tie_fraction=sum(abs(w['cumulative_difference'])<=TIE_TOLERANCE for w in windows)/len(windows),worst_return_window=min(windows,key=lambda w:w['cumulative_return']),group_benchmark=None,group_benchmark_null_reason='NO_MATCHED_FULL_GROUP_SERIES_IN_FROZEN_OUTPUT')
 return dict(months=months,window_count=len(windows),summary=summary,null_reason=None,windows=windows)

def run(root):
 originals={}
 for file in ('EXP_B_FROZEN_MANIFEST_v1.json','BBOOK_OUTPUT_MANIFEST_v1_private.json'):
  for f in json.loads((root/file).read_bytes())['files']:
   p=root/f['path']
   if sha(p)!=f['sha256']: raise ValueError('FROZEN_SOURCE_CHANGED')
   originals[str(p)]=f['sha256']
 inputs=[root/'EXP_B_results_private.json',root/'BBOOK_RESULTS_private.json'];old,book=[json.loads(p.read_bytes()) for p in inputs]
 cfg=dict(id='EXP-FRENCH-FROZEN-HOLDING-v1',horizons=list(HORIZONS),source_sha256={str(p):sha(p) for p in inputs},scope='ALL_FROZEN_B_AND_BOOK_FRENCH_COMMON_AND_LONGEST',tolerance=TIE_TOLERANCE,monthly_start_windows='COMPLETE_ONLY_OVERLAPPING',registered_at=datetime.now(timezone.utc).isoformat(),stock_decile_experiment=False,frozen_strategy_settings_unchanged=True)
 conf=root/'FRENCH_HOLDING_CONFIG_v1_private.json'
 if conf.exists():
  saved=json.loads(conf.read_bytes())
  if any(saved[k]!=v for k,v in cfg.items() if k!='registered_at'): raise ValueError('FROZEN_CONFIG_DIFFERS')
  cfg=saved
 else: conf.write_text(json.dumps(cfg,indent=2));conf.chmod(0o400)
 sources=[(r,old['benchmark'],'FROZEN_B') for r in old['runs']]+[(r,book['benchmarks'][r['benchmark_key']],'BOOK_FRENCH') for r in book['runs']]
 runs=[]
 for r,b,f in sources:
  statistics=[]
  for n in HORIZONS:
   item=holding_windows(r['equity_curve'],b['equity_curve'],n)
   # All complete windows are evaluated; persist summaries and worst-window trace.
   item.pop('windows');statistics.append(item)
  runs.append(dict(id=r['id'],source_family=f,scope=r.get('scope','COMMON'),preset=r.get('preset'),strategy_family=r['family'],weighting=r.get('weighting'),favorable_rank=r.get('favorable_rank'),benchmark=r.get('benchmark_key','FF5/1963-07/2026-09'),windows=statistics))
 for p,s in originals.items():
  if sha(p)!=s: raise ValueError('SOURCE_MUTATED')
 result=dict(id=cfg['id'],code_sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),config_sha256=sha(conf),inputs=cfg['source_sha256'],source_files_unchanged=len(originals),runs=runs,limitations=['Overlapping windows are not independent trials or future success probabilities.','French market is not S&P500; group-EW reference unavailable.','Costs unobserved: gross only; no FX or stock execution.','Frozen B monthly mixture and French formation rules unchanged; not annual stock reselection.','PILOT / REAL / NOT_VALIDATED; not QGV itself or OOS.'])
 p=root/'FRENCH_HOLDING_RESULTS_private.json';p.write_text(json.dumps(result,separators=(',',':')));p.chmod(0o600)
 print(json.dumps(dict(runs=len(runs),horizon_rows=len(runs)*4,source_files_unchanged=len(originals),private_result=str(p))))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private',type=Path,required=True);run(p.parse_args().private)
