"""Offline stock chart projection. Existing kernels only; no Worker or UI math.

Immutable completed eras/years/quarters/months plus one active month. All retained
sessions remain readable; a five-calendar-year window needs <=10 price+indicator
pieces, one small manifest and one bucket. Raw source retention is separate.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import date
import hashlib
import json

from ._private_artifacts import json_bytes, MAX_BYTES
from .kis_compact import pack, unpack_row, growth, _git_bytes, sha, need, FIELDS
from .kis_price_bridge import price_rows
from .technical_display import close_indicator_paths, _number
from .exp_deciles.technical_measures import sessions

BUCKETS=32
INDICATORS=['SMA_20','SMA_60','SMA_120','BOLL_MIDDLE_20','BOLL_UPPER_20_2',
            'BOLL_LOWER_20_2','RSI_14','MACD_12_26','MACD_SIGNAL_9','MACD_HISTOGRAM_12_26_9']
SCOPE='OWNER_PRIVATE_ONLY'
SCHEMA='kis-private-delivery/3'


def bucket(symbol):return f'{hashlib.sha256(symbol.encode()).digest()[0]%BUCKETS:02d}'


def indicator_series(chart, *, evaluation_day, start_index=0):
    """Full retained seed, snapshot price basis; reference values, never adoption.

    Warmup, missing sessions and explicit display holds stay null. A later gap
    cannot invalidate earlier prefixes. Missing volume alone never blocks prices.
    No split is inferred from a ratio or from provider MODP1.
    """
    need(chart.get('source_query',{}).get('MODP','0')=='0','RAW_DAILY_SOURCE_REQUIRED')
    need(chart['basis'] in ('RAW','SPLIT_ADJUSTED') and chart.get('dividend_adjustment','NONE')=='NONE',
         'RAW_OR_CONFIRMED_SPLITS_REQUIRED')
    need(all(s.get('status')=='CONFIRMED' and s.get('evidence') for s in chart['splits']),
         'SPLIT_EVIDENCE_REQUIRED')
    rows=price_rows(chart,evaluation_day);days=[r['date'] for r in rows]
    need(days==sorted(set(days)),'UNSORTED_OR_DUPLICATE_SESSION')
    expected=sessions(date.fromisoformat(days[0]),date.fromisoformat(days[-1])) if days else []
    expected=[d.isoformat() if isinstance(d,date) else d for d in expected]
    prices=[_number(r.get('close')) for r in rows]
    stop=next((i for i,p in enumerate(prices) if p is None or i>=len(expected) or days[i]!=expected[i]),len(rows))
    need(0<=start_index<=len(rows),'INDICATOR_SERIES_START')
    paths=close_indicator_paths(prices[:stop]) if stop and start_index<len(rows) else {}
    held=chart.get('display',{}).get('state')=='WITHHELD'
    values=[];runs=[]
    for j,key in enumerate(INDICATORS):
        series,reasons=paths.get(key,([],[]));column=[];last=None
        for i in range(start_index,len(rows)):
            reason='DISPLAY_WITHHELD' if held else 'PRICE_WINDOW_INCOMPLETE' if i>=stop else reasons[i]
            column.append(None if reason else series[i])
            if reason:
                if last is not None and last['reason']==reason and last['to']==i-1:last['to']=i
                else:last=dict(field=key,**{'from':i,'to':i},reason=reason);runs.append(last)
            else:last=None
        values.append(column)
    return dict(schema='kis-indicator-series/1',publication_scope=SCOPE,symbol=chart['symbol'],
                evaluation_day=evaluation_day,basis=chart['basis'],currency=chart['currency'],
                fields=INDICATORS,dates=days[start_index:],rows=[list(v) for v in zip(*values)],reason_runs=runs,
                validation_tier='UNVERIFIED_REFERENCE',adopted_values_included=False,
                seed='GSQ015_FULL_RETAINED_HISTORY',historical_pit_proven=False,
                clock_scope='LATEST_SNAPSHOT_RESTATED_BASIS_NOT_HISTORICAL_SIGNAL',
                display=deepcopy(chart.get('display',{})))


def _period(day,end):
    y,m=int(day[:4]),int(day[5:7]);ey,em=int(end[:4]),int(end[5:7]);era=ey//3*3
    if y<era:return 'era',f'{y//3*3:04d}-{y//3*3+2:04d}'
    if y<ey:return 'year',day[:4]
    if (m-1)//3<(em-1)//3:return 'quarter',f'{y:04d}-Q{(m-1)//3+1}'
    if m<em:return 'month',day[:7]
    return 'active',day[:7]


def _ref(path,b):return dict(path=path,bytes=len(b),sha256=sha(b))


def stock_bundle(legacy_files, *, evaluation_day, previous=None, revision_reference=None,
                 annual_budget=260000000):
    """No score computation; consume existing projected results + new series.

    `previous` is the offline writer-manifest, NOT the small Worker manifest.
    The 260MB view ledger leaves 40MB in the old view-only policy; combined RAW
    cost still requires Main's inclusive budget check before a data update.
    """
    if previous is not None:
        need(previous.get('schema')==SCHEMA and previous.get('kind')=='OFFLINE_WRITER_ONLY' and
             previous.get('publication_scope')==SCOPE,'PREVIOUS_STOCK_CONTRACT')
        ledger=previous.get('growth_ledger',{})
        need(ledger.get('annual_payload_budget')==annual_budget and type(ledger.get('charged_bytes')) is int,
             'PREVIOUS_GROWTH_LEDGER_REQUIRED')
        need(previous['evaluation_day']<=evaluation_day,'PREVIOUS_DATE_REGRESSION')
    files={};records={};qgv=None;pending={};pieces=[]
    prior={(x['symbol'],x['kind'],x['period']):x for x in (previous or {}).get('files',[]) if 'symbol' in x}
    corrections=[]
    for path,b in legacy_files:
        if path.startswith('manifests/'):continue
        obj=json.loads(b)
        if path=='qgv/latest.json':qgv=obj;continue
        symbol=obj.get('symbol') or path.rsplit('/',1)[-1][:-5]
        part=pending.setdefault(symbol,{})
        if path.startswith('chart/'):part['chart']=obj
        elif path.startswith('technical/'):part['technical']=obj
        elif path.startswith('measures/'):part['measures']=obj
        elif path.startswith('indicator-series/'):part['series']=obj
        else:raise ValueError('UNKNOWN_STOCK_INPUT')
        if set(part)!={'chart','technical','measures','series'}:continue
        c=part['chart'];s=part['series'];rows=price_rows(c,evaluation_day);dates=[r['date'] for r in rows]
        need(symbol not in records,'DUPLICATE_STOCK_SYMBOL')
        need(s['schema']=='kis-indicator-series/1' and s['symbol']==symbol and
             s['evaluation_day']==evaluation_day and s['basis']==c['basis'] and
             s['currency']==c['currency'] and s['fields']==INDICATORS and s['dates']==dates and
             len(s['rows'])==len(rows) and all(len(r)==10 for r in s['rows']), 'INDICATOR_SERIES_CONTEXT')
        need(s['display']==c.get('display',{}),'INDICATOR_DISPLAY_MISMATCH')
        grouped=defaultdict(list)
        for i,r in enumerate(rows):grouped[_period(r['date'],evaluation_day)].append(i)
        refs=[];raw={r['date']:r for r in c['raw_bars']}
        for (kind,period),indices in sorted(grouped.items()):
            value=dict(schema='kis-stock-piece/1',publication_scope=SCOPE,symbol=symbol,kind=kind,
                       period=period,basis=c['basis'],currency=c['currency'],fields=FIELDS+INDICATORS,
                       rows=[[rows[i].get(f) for f in FIELDS]+s['rows'][i] for i in indices])
            if c['basis']=='SPLIT_ADJUSTED':
                value['raw_rows']=[[raw[rows[i]['date']].get(f) for f in FIELDS] for i in indices]
            b=json_bytes(value);need(len(b)<=MAX_BYTES,'STOCK_PIECE_LIMIT')
            key=(symbol,kind,period);old=prior.get(key)
            if kind!='active' and old and old['sha256']!=sha(b):
                need(bool(isinstance(revision_reference,str) and revision_reference.strip()),'IMMUTABLE_PIECE_CHANGED')
                corrections.append(dict(symbol=symbol,kind=kind,period=period,prior_sha256=old['sha256'],new_sha256=sha(b)))
            code=hashlib.sha256(symbol.encode()).hexdigest()[:20]
            name=f'stock/pieces/{code}/{kind}/{period}-{sha(b)}.json';files[name]=b
            ref=dict(_ref(name,b),symbol=symbol,kind=kind,period=period)
            refs.append(ref);pieces.append(ref)
        # Five-year/full subsets have exactly the same precomputed seeds.
        series_meta={k:v for k,v in s.items() if k not in ('dates','rows')}
        header={k:v for k,v in c.items() if k not in ('raw_bars','bars')}
        header['row_source_scope']='DERIVED_VIEW_RETAINED_ORIGINALS_SEPARATE'
        records[symbol]=dict(chart=header,indicators=series_meta,latest={k:part[k] for k in ('technical','measures')},pieces=refs)
        del pending[symbol]
    need(not pending and records and qgv is not None,'COMPLETE_STOCK_INPUTS_REQUIRED')
    buckets=[]
    for slot in sorted({bucket(k) for k in records}):
        b=json_bytes(pack({k:v for k,v in records.items() if bucket(k)==slot},kind='STOCK',
                          context=dict(evaluation_day=evaluation_day)))
        name=f'stock/latest/{slot}.json';files[name]=b;buckets.append(dict(_ref(name,b),bucket=slot))
    context={k:v for k,v in qgv.items() if k not in ('rows','private_raw_detail')}
    context['raw_detail_state']='REBUILDABLE_NOT_IN_VIEW'
    b=json_bytes(context);files['qgv/context.json']=b;qcontext=_ref('qgv/context.json',b)
    qb=[]
    for slot in sorted({bucket(k) for k in qgv['rows']}):
        b=json_bytes(pack({k:v for k,v in qgv['rows'].items() if bucket(k)==slot},kind='QGV',context={}))
        name=f'qgv/buckets/{slot}.json';files[name]=b;qb.append(dict(_ref(name,b),bucket=slot))
    piece_map={x['path']:x for x in pieces}
    entries=[piece_map[n] if n in piece_map else _ref(n,b) for n,b in sorted(files.items())]
    writer=dict(schema=SCHEMA,kind='OFFLINE_WRITER_ONLY',publication_scope=SCOPE,
                evaluation_day=evaluation_day,files=entries)
    if corrections:writer['reviewed_revisions']=dict(reference=revision_reference,pieces=corrections)
    elif previous and previous.get('reviewed_revisions'):
        writer['reviewed_revisions']=deepcopy(previous['reviewed_revisions'])
    service=dict(schema=SCHEMA,publication_scope=SCOPE,layout='B2_STOCK_SERIES',
                 evaluation_day=evaluation_day,buckets=BUCKETS,bucket_rule='SHA256_UTF8_FIRST_BYTE_MOD_32',
                 stock_buckets=buckets,qgv_buckets=qb,qgv_context=qcontext,verification_promoted=False)
    same=previous and all(previous.get(k)==v for k,v in writer.items())
    year=(qgv.get('calculated_at') or evaluation_day)[:4]
    old=(previous or {}).get('growth_ledger',{})
    used=old.get('charged_bytes',0) if old.get('year')==year else 0
    writer['growth_ledger']=deepcopy(old) if same else dict(year=year,charged_bytes=used,annual_payload_budget=annual_budget,
        measure='GIT_ZLIB1_BLOBS_PLUS_UNCOMPRESSED_SMALL_MANIFEST_RESERVE',reserved_other_git_bytes=40000000)
    # Manifest is small; charge uncompressed +64 rather than a recursive hash.
    for _ in range(12):
        wb=json_bytes(writer);files['writer-manifest.json']=wb
        service['writer_manifest']=_ref('writer-manifest.json',wb)
        service['growth_ledger']=writer['growth_ledger'];files['manifest.json']=json_bytes(service)
        if same:break
        stats=growth(files,previous=previous)
        total=used+stats['new_git_loose_blob_bytes']-_git_bytes(files['manifest.json'])+len(files['manifest.json'])+64
        if writer['growth_ledger']['charged_bytes']==total:break
        writer['growth_ledger']['charged_bytes']=total
    need(writer['growth_ledger']['charged_bytes']<=annual_budget,'ANNUAL_DATA_BUDGET')
    need(all(len(b)<=MAX_BYTES for b in files.values()),'STOCK_FILE_LIMIT')
    return files


def _read(fetch, ref):
    b=fetch(ref['path']);need(len(b)==ref['bytes'] and sha(b)==ref['sha256'],'STOCK_FILE_PIN')
    return json.loads(b)


def assemble_stock(fetch, symbol):
    """Reference consumer only: fetch/verify/decode, no indicator calculations."""
    manifest=json.loads(fetch('manifest.json'))
    need(manifest.get('schema')==SCHEMA and manifest.get('layout')=='B2_STOCK_SERIES' and
         manifest.get('publication_scope')==SCOPE,'STOCK_MANIFEST_REQUIRED')
    ref=next(x for x in manifest['stock_buckets'] if x['bucket']==bucket(symbol))
    packet=_read(fetch,ref)
    need(packet['context']['evaluation_day']==manifest['evaluation_day'],'STOCK_DATE_MISMATCH')
    record=unpack_row(packet,symbol);raw=[];values=[]
    for r in record['pieces']:
        p=_read(fetch,r)
        need(p['symbol']==symbol and p['fields']==FIELDS+INDICATORS and p['basis']==record['chart']['basis'] and
             p['currency']==record['chart']['currency'],'STOCK_PIECE_CONTEXT')
        need(all(len(v)==17 for v in p['rows']),'STOCK_ROW_WIDTH')
        values.extend(p['rows'])
        if record['chart']['basis']=='SPLIT_ADJUSTED':
            need(len(p.get('raw_rows',[]))==len(p['rows']) and
                 all(len(v)==7 for v in p['raw_rows']),'STOCK_RAW_ROW_WIDTH')
            raw.extend(p['raw_rows'])
    raw.sort(key=lambda r:r[0]);values.sort(key=lambda r:r[0])
    days=[r[0] for r in values]
    need(days==sorted(set(days)) and all(d<=manifest['evaluation_day'] for d in days),'STOCK_SESSION_SET')
    out=dict(schema='kis-stock-view/1',publication_scope=SCOPE,symbol=symbol,evaluation_day=manifest['evaluation_day'],
             chart=dict(record['chart'],schema='kis-chart-metadata/1'),fields=FIELDS+INDICATORS,rows=values,
             indicators=record['indicators'],latest=record['latest'],
             coverage=dict(scope='ALL_RETAINED_SESSIONS',retained_sessions=len(days),
                           retained_start=days[0] if days else None,retained_end=days[-1] if days else None),
             additional_requests_for_toggle=0,additional_requests_for_retained_period=0)
    if record['chart']['basis']=='SPLIT_ADJUSTED':
        need([r[0] for r in raw]==days,'STOCK_RAW_SESSION_SET')
        out['raw_fields']=FIELDS;out['raw_rows']=raw
    need(len(json_bytes(out))<=MAX_BYTES,'STOCK_RESPONSE_LIMIT')
    return out
