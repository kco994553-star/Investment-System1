"""Synthetic technical runtime/capacity only; no acquisition or actual prices.

The QGV placeholder is NOT a computed score; use measured day1 QGV bytes when
estimating combined delivery costs. All generated price series are fictional.
"""
import argparse
from datetime import date,timedelta
from decimal import Decimal
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import time
import zlib

from investment_system.research._private_artifacts import digest,json_bytes
from investment_system.research.kis_price_bridge import normalize_page
from investment_system.research.private_kis_preprocess import calculate_and_project
from investment_system.research.private_kis_reference import reference_files
from investment_system.research.exp_deciles import schedule
from investment_system.research.pit_filings import session_close
from investment_system.research.kis_compact import compact,growth


def synthetic_contracts(count,n):
    end=date(2026,11,30);d=end;days=[]
    while len(days)<n:
        if schedule.is_session(d) and session_close(d).close_at is not None:days.append(d.isoformat())
        d-=timedelta(days=1)
    days.reverse();captured='2026-12-01T02:00:00Z'
    for i in range(count):
        symbol=f'S{i:04d}'
        rows=[]
        for j,day in enumerate(days):
            close=Decimal(10000+i*7+j*3+(j%17)*7)/100
            rows.append(dict(xymd=day.replace('-',''),open=str(close-Decimal('0.1')),
                high=str(close+Decimal('0.5')),low=str(close-Decimal('0.5')),clos=str(close),
                tvol=str(100000+i*83+j*29),tamt=str(close*(100000+i*83+j*29))))
        request=dict(SYMB=symbol,EXCD='NAS',MODP='0',GUBN='0',BYMD='20261130')
        body=json_bytes(dict(rt_cd='0',output1=dict(rsym='DNAS'+symbol),output2=rows))
        receipt=dict(sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),http_status=200,
                     fetched_at=captured,request=request)
        c=normalize_page(body,receipt=receipt,request=request,evidence=dict(currency='USD',
            currency_reference='SYNTHETIC_NOT_A_COMPANY',held_ranges=([
                dict(**{'from':days[0],'to':days[-1]},reason='SYNTHETIC_HOLD')
            ] if i<6 else [])))
        c['fixture_kind']='SYNTHETIC_NOT_A_COMPANY'
        yield c


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--series',type=int,default=517)
    p.add_argument('--sessions',type=int,default=1260)
    p.add_argument('--receipt',type=Path,required=True)
    args=p.parse_args();start=time.perf_counter()
    memory=io.BytesIO();old_bytes=old_git=old_chart_git=0
    with gzip.GzipFile(fileobj=memory,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w|') as t:
        for c in synthetic_contracts(args.series,args.sessions):
            f=reference_files(calculate_and_project(c,evaluation_day='2026-11-30',
                series_id='SYNTHETIC:'+c['symbol'],expected_contract_hash=digest(c)),c,'2026-11-30')
            for name,b in f.items():
                m=tarfile.TarInfo(name);m.size=len(b);m.mtime=0;t.addfile(m,io.BytesIO(b))
                old_bytes+=len(b);g=len(zlib.compress(b'blob '+str(len(b)).encode()+b'\0'+b,6));old_git+=g
                if name.startswith('chart/'):old_chart_git+=g
        b=json_bytes(dict(schema='SYNTHETIC_CAPACITY_PLACEHOLDER',rows={},private_raw_detail={}))
        m=tarfile.TarInfo('qgv/latest.json');m.size=len(b);m.mtime=0;t.addfile(m,io.BytesIO(b))
    calc_elapsed=time.perf_counter()-start
    variants={}
    for name,recent in [('B1','monthly'),('B2','daily')]:
        begin=time.perf_counter()
        with tarfile.open(fileobj=io.BytesIO(memory.getvalue())) as t:
            f=compact(((m.name,t.extractfile(m).read()) for m in t if m.isfile()),
                      evaluation_day='2026-11-30',recent=recent)
        manifest=json.loads(f['manifest.json']);pieces=manifest['pieces']
        def size(paths):
            paths=list(paths)
            return dict(raw=sum(len(f[x]) for x in paths),git_zlib6=sum(len(zlib.compress(
                b'blob '+str(len(f[x])).encode()+b'\0'+f[x],6)) for x in paths))
        mutable=['latest/indicators.json','qgv/latest.json','chart/index.json','manifest.json']
        if recent=='monthly':mutable.extend(x['path'] for x in pieces if x['kind']=='recent')
        days=[size([x['path']]) for x in pieces if x['kind']=='day']
        variants[name]=dict(files=len(f),max_file_bytes=max(map(len,f.values())),
            initial=size(f),mutable=size(mutable),
            maximum_daily_piece=dict(raw=max((x['raw'] for x in days),default=0),
                                     git_zlib6=max((x['git_zlib6'] for x in days),default=0)),
            latest_indicators=size(['latest/indicators.json']),qgv_placeholder=size(['qgv/latest.json']),
            sealed_year_total=size(x['path'] for x in pieces if x['kind']=='year'),
            sealed_month_total=size(x['path'] for x in pieces if x['kind']=='month'),
            piece_count=len(pieces),chart_reads_worst=1+len({(x['kind'],x['period']) for x in pieces}),
            projection_elapsed_seconds=time.perf_counter()-begin)
    out=dict(data_kind='SYNTHETIC_CAPACITY_NOT_A_COMPANY',series=args.series,sessions=args.sessions,
             technical_calculation_and_serialization_seconds=calc_elapsed,
             technical_legacy_total_bytes=old_bytes,technical_legacy_new_git_blob_bytes=old_git,
             chart_legacy_new_git_blob_bytes=old_chart_git,
             qgv_timing='NOT_MEASURED_PLACEHOLDER_NOT_CALCULATED',variants=variants)
    with args.receipt.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(dict(series=args.series,sessions=args.sessions,files=sum(v['files'] for v in variants.values()))))


if __name__=='__main__':main()
