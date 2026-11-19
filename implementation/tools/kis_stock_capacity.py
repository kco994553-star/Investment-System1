"""Read-only C1-C3 measurement: saved day1 values plus NEW indicator series.

No collection, financial/old technical recalculation, data update or HTTP. New
series call existing GSQ015 kernels. Optional five-year capacity uses synthetic
prices and held metadata ONLY for sizes, never real-data adoption or an SLA.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import date,timedelta
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time

from investment_system.research._private_artifacts import json_bytes
from investment_system.research.kis_compact import assemble_chart,unpack_row,_git_bytes
from investment_system.research.kis_stock_bundle import stock_bundle,indicator_series,assemble_stock,FIELDS,INDICATORS
from investment_system.research.exp_deciles import schedule


def load(archive,pin):
    b=Path(archive).read_bytes()
    if hashlib.sha256(b).hexdigest()!=pin:raise ValueError('ARCHIVE_PIN')
    with tarfile.open(fileobj=io.BytesIO(b)) as t:
        return {m.name:t.extractfile(m).read() for m in t if m.isfile()}


def profile(legacy,*,evaluation_day,case):
    months=defaultdict(lambda:defaultdict(int));month_counts=defaultdict(set)
    changed_latest=0;symbols=[];last_differences=0;begin=time.perf_counter()
    def source():
        nonlocal last_differences
        for symbol,c,latest in legacy:
            symbols.append(symbol);s=indicator_series(c,evaluation_day=evaluation_day)
            for j,key in enumerate(INDICATORS):
                expected=latest['technical'].get('metrics',{}).get(key,{}).get('reference_value')
                if case=='HELD_DAY1_NEW_SERIES' and s['rows']:
                    last_differences+=s['rows'][-1][j]!=expected
            # Same selected rows as producer, reference vectors; active month is
            # rewritten once per session. No timestamp/header mutation scenario.
            grouped=defaultdict(list)
            for r,vs in zip(c['bars'],s['rows']):grouped[r['date'][:7]].append([r.get(f) for f in FIELDS]+vs)
            for month,rows in grouped.items():
                for i,row in enumerate(rows):
                    b=json_bytes(dict(schema='kis-stock-piece/1',publication_scope='OWNER_PRIVATE_ONLY',
                        symbol=symbol,kind='active',period=month,basis=c['basis'],currency=c['currency'],
                        fields=FIELDS+INDICATORS,rows=rows[:i+1]))
                    months[month][row[0]]+=_git_bytes(b);month_counts[month].add(row[0])
            yield 'chart/'+symbol+'.json',json_bytes(c)
            for k in ('technical','measures'):yield k+'/'+symbol+'.json',json_bytes(latest[k])
            yield 'indicator-series/'+symbol+'.json',json_bytes(s)
        yield 'qgv/latest.json',json_bytes(profile.qgv)
    files=stock_bundle(source(),evaluation_day=evaluation_day,annual_budget=260000000)
    elapsed=time.perf_counter()-begin
    writer=json.loads(files['writer-manifest.json'])
    mutable=[p for p in files if not p.startswith('stock/pieces/')]
    mutable_git=sum(_git_bytes(files[p]) for p in mutable)
    active_means={m:sum(byday.values())/len(byday) for m,byday in months.items() if len(byday)>=18}
    active_per_update=max(active_means.values()) if active_means else max(sum(v.values())/len(v) for v in months.values())
    # Use the newest complete year if present, otherwise scale observed months.
    year=evaluation_day[:4];selected=[m for m in months if m[:4]==year]
    if not selected:selected=list(months)
    sealed_row_year=sum(months[m][max(months[m])] for m in selected)*12/len(selected)
    # Conservatively charge monthly + quarter + year + era copies in rollover year.
    sealing=sealed_row_year*4
    bootstrap=sum(_git_bytes(b) for b in files.values())
    reads=[];responses=[];max_input=0;total_fetched=0
    sample=None
    for symbol in symbols:
        seen=[]
        def fetch(p):seen.append(p);return files[p]
        v=assemble_stock(fetch,symbol);b=json_bytes(v)
        reads.append(len(seen));responses.append((len(b),len(gzip.compress(b,mtime=0))))
        max_input=max(max_input,max(len(files[p]) for p in seen));total_fetched=max(total_fetched,sum(len(files[p]) for p in seen))
        if sample is None or len(b)>sample[0]:sample=(len(b),symbol,seen)
    raw_bootstrap=52662560;raw_new=105739*252
    parts=dict(view_mutable_and_active_updates_estimate=round((mutable_git+active_per_update)*252),
               view_sealing_allowance=round(sealing),view_bootstrap=bootstrap,
               raw_bootstrap_reused_estimate=raw_bootstrap,raw_new_rows_reused_estimate=raw_new,
               raw_summaries_allowance=1000000,git_other_reserve=40000000)
    result=dict(case=case,series=len(symbols),evaluation_day=evaluation_day,files=len(files),
        new_series_and_projection_seconds=elapsed,latest_value_differences=last_differences if case=='HELD_DAY1_NEW_SERIES' else None,
        max_file_bytes=max(map(len,files.values())),max_worker_parsed_file_bytes=max_input,
        max_worker_fetched_bytes=total_fetched,max_data_fetches=max(reads),
        max_response_json_bytes=max(x[0] for x in responses),max_response_gzip_bytes=max(x[1] for x in responses),
        min_response_json_bytes=min(x[0] for x in responses),mutable_git_per_capture=mutable_git,
        active_month_max_mean_git_per_update=active_per_update,monthly_active_mean_git=active_means,
        first_year_parts_estimate=parts,first_year_total_estimate=sum(parts.values()),
        headroom_below_300MB_estimate=300000000-sum(parts.values()),
        first_year_measured=False,old_qgv_recalculated=False,worker_cpu_verified=False,
        browser_open_time_measured=False,sample_symbol=sample[1],
        stock_latest_max_bytes=max(len(b) for p,b in files.items() if p.startswith('stock/latest/')),
        qgv_bucket_max_bytes=max(len(b) for p,b in files.items() if p.startswith('qgv/buckets/')),
        manifest_bytes=len(files['manifest.json']),writer_index_bytes=len(files['writer-manifest.json']),
        context_bytes=len(files['qgv/context.json']))
    return result,files


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--expected-sha256',required=True)
    p.add_argument('--receipt',type=Path,required=True);p.add_argument('--synthetic-sessions',type=int)
    p.add_argument('--synthetic-series',type=int,default=517)
    p.add_argument('--bundle',type=Path)
    a=p.parse_args();old=load(a.archive,a.expected_sha256)
    if a.bundle and a.synthetic_sessions:raise ValueError('CAPACITY_BUNDLE_NOT_A_REAL_DELIVERY')
    index=json.loads(old['chart/index.json']);latest=json.loads(old['latest/indicators.json'])
    q=json.loads(old['qgv/latest.json'])
    profile.qgv=dict(q['context'],rows={k:unpack_row(q,k) for k in q['rows']})
    if not a.synthetic_sessions:
        def legacy():
            for symbol in sorted(latest['rows']):
                c=assemble_chart(old,symbol)
                yield c['symbol'],c,unpack_row(latest,symbol)
        day=index['evaluation_day'];kind='HELD_DAY1_NEW_SERIES'
    else:
        day='2026-11-30';d=date.fromisoformat(day);days=[]
        while len(days)<a.synthetic_sessions:
            if schedule.is_session(d):days.append(d.isoformat())
            d-=timedelta(days=1)
        days.reverse();originals=sorted(latest['rows'])
        def legacy():
            for i in range(a.synthetic_series):
                original=originals[i%len(originals)]
                symbol=f'SYN{i:04d}';c=assemble_chart(old,original);c.update(symbol=symbol,basis='RAW',splits=[])
                meta=unpack_row(latest,original)
                for v in meta.values():v['symbol']=symbol
                c['display']=dict(state='AVAILABLE',validation_tier='UNVERIFIED_REFERENCE',official=False,label='SYNTHETIC_CAPACITY')
                c['bars']=[dict(date=d,open=f'{100+i*0.03+j*0.01:.2f}',high=f'{103+i*0.03+j*0.01:.2f}',
                    low=f'{99+i*0.03+j*0.01:.2f}',close=f'{100.2+i*0.03+j*0.01+(j%17)*0.07:.2f}',
                    volume=str(100000+i*83+j*29),amount=str(10000000+i*1111+j*101)) for j,d in enumerate(days)]
                c['raw_bars']=deepcopy(c['bars'])
                yield symbol,c,deepcopy(meta)
        kind='SYNTHETIC_PRICES_WITH_HELD_METADATA_CAPACITY_NOT_ADOPTION'
    result,files=profile(legacy(),evaluation_day=day,case=kind)
    result['source_archive_sha256']=a.expected_sha256
    with a.receipt.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    if a.bundle:
        with a.bundle.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w|') as t:
            for name,b in sorted(files.items()):
                m=tarfile.TarInfo(name);m.size=len(b);m.mtime=0;t.addfile(m,io.BytesIO(b))
    print(json.dumps({k:result[k] for k in ('series','files','max_data_fetches','latest_value_differences')}))


if __name__=='__main__':
    try:main()
    except Exception:
        print(json.dumps(dict(failures=1)))
        raise SystemExit(2) from None
