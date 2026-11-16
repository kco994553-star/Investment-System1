"""Compact private views, not new indicators/scoring or an archival source store."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import zlib

from ._private_artifacts import canonical_bytes, digest, json_bytes, MAX_BYTES
from .kis_price_bridge import price_rows

FIELDS=['date','open','high','low','close','volume','amount']
BUCKETS=32
GROWTH_MEASURE='GIT_ZLIB1_BLOBS_PLUS_UNCOMPRESSED_MANIFEST_RESERVE'


def need(ok,reason):
    if not ok:raise ValueError(reason)


def sha(b):return hashlib.sha256(b).hexdigest()


def pack(records,*,kind,context=None):
    """Lossless repeated-object/key-layout sharing; JSON stays ordinary JSON.

    Tagged containers: [0,key-layout,values], [1,array], [2,shared-id]. Native
    scalars stay native, so null, false, zero and negative values remain distinct.
    Rows can be decoded individually; Worker need not expand every issuer.
    """
    counts=Counter();layouts=set()
    def count(v):
        if isinstance(v,dict):
            layouts.add(tuple(sorted(v)))
            for x in v.values():count(x)
        elif isinstance(v,list):
            for x in v:count(x)
        if isinstance(v,(dict,list,str)):
            b=canonical_bytes(v)
            if len(b)>=14:counts[b]+=1
    for v in records.values():count(v)
    keys=sorted(layouts);key_ids={k:i for i,k in enumerate(keys)}
    selected=sorted((b for b,n in counts.items() if n>=2 and (len(b)-8)*(n-1)>20),key=lambda b:(len(b),b))
    shared_ids={b:i for i,b in enumerate(selected)}
    def encode(v,skip=None):
        if isinstance(v,(dict,list,str)):
            b=canonical_bytes(v)
            if b!=skip and b in shared_ids:return [2,shared_ids[b]]
        if isinstance(v,dict):
            k=tuple(sorted(v));return [0,key_ids[k],[encode(v[x]) for x in k]]
        if isinstance(v,list):return [1,[encode(x) for x in v]]
        return v
    out=dict(schema='kis-record-pack/2',kind=kind,publication_scope='OWNER_PRIVATE_ONLY',
             layouts=[list(k) for k in keys],shared=[encode(json.loads(b),skip=b) for b in selected],
             rows={k:encode(v) for k,v in sorted(records.items())},context=context or {})
    need(len(json_bytes(out))<=MAX_BYTES,'PACK_FILE_LIMIT')
    return out


def unpack_row(packet,key):
    need(packet.get('schema')=='kis-record-pack/2','PACK_SCHEMA')
    active=set();nodes=0
    def decode(v,depth=0):
        nonlocal nodes
        nodes+=1;need(depth<100 and nodes<200000,'PACK_EXPANSION_LIMIT')
        if not isinstance(v,list):return v
        need(bool(v) and type(v[0]) is int,'PACK_TAG')
        if v[0]==0:
            need(len(v)==3 and type(v[1]) is int and 0<=v[1]<len(packet['layouts']),'PACK_LAYOUT')
            ks=packet['layouts'][v[1]];need(isinstance(v[2],list) and len(ks)==len(v[2]),'PACK_WIDTH')
            return {k:decode(x,depth+1) for k,x in zip(ks,v[2])}
        if v[0]==1:
            need(len(v)==2 and isinstance(v[1],list),'PACK_ARRAY')
            return [decode(x,depth+1) for x in v[1]]
        need(v[0]==2 and len(v)==2 and type(v[1]) is int and 0<=v[1]<len(packet['shared']),'PACK_REF')
        i=v[1];need(i not in active,'PACK_CYCLE');active.add(i)
        out=decode(packet['shared'][i],depth+1);active.remove(i);return out
    value=decode(packet['rows'][key]);need(len(json_bytes(value))<=MAX_BYTES,'PACK_ROW_LIMIT')
    return value


def _git_bytes(b):
    return len(zlib.compress(b'blob '+str(len(b)).encode()+b'\0'+b,1))


def growth(files,*,previous=None):
    old={r['path']:r for r in (previous or {}).get('files',[])}
    changed=[]
    for name,b in files.items():
        if name=='manifest.json' and previous:
            if json.loads(b)==previous:continue
        elif name in old and old[name]['sha256']==sha(b):continue
        changed.append((name,b))
    return dict(changed_files=len(changed),changed_payload_bytes=sum(len(b) for _,b in changed),
                new_git_loose_blob_bytes=sum(_git_bytes(b) for _,b in changed),
                git_compression_level=1,delta_savings_assumed=0)


def compact(legacy_files,*,evaluation_day,previous=None,revision_reference=None,
            daily_budget=None,annual_budget=260000000,recent='daily'):
    need(recent in ('daily','monthly'),'RECENT_LAYOUT')
    if previous is not None:
        need(isinstance(previous,dict) and previous.get('schema')=='kis-private-delivery/2' and
             previous.get('publication_scope')=='OWNER_PRIVATE_ONLY','PREVIOUS_COMPACT_CONTRACT')
        need(previous['evaluation_day']<=evaluation_day,'PREVIOUS_DATE_REGRESSION')
        ledger=previous.get('growth_ledger') or {}
        need(ledger.get('annual_payload_budget')==annual_budget and type(ledger.get('charged_bytes')) is int and
             ledger.get('measure')==GROWTH_MEASURE,
             'PREVIOUS_GROWTH_LEDGER_REQUIRED')
    records={};charts={};qgv=None
    for name,b in legacy_files:
        if name.startswith('manifests/'):continue
        obj=json.loads(b)
        if name=='qgv/latest.json':qgv=obj;continue
        symbol=name.rsplit('/',1)[-1][:-5]
        row=records.setdefault(symbol,{})
        if name.startswith('chart/'):
            need(symbol not in charts,'DUPLICATE_CHART_SYMBOL')
            need(obj['basis'] in ('RAW','SPLIT_ADJUSTED') and obj.get('dividend_adjustment','NONE')=='NONE',
                 'RAW_OR_CONFIRMED_SPLITS_REQUIRED')
            need(obj.get('currency')=='USD','CHART_CURRENCY')
            charts[symbol]=obj['raw_bars']
            row['chart']={k:v for k,v in obj.items() if k not in ('bars','raw_bars')}
            row['chart']['row_source_scope']='DERIVED_VIEW_RETAINED_ORIGINALS_SEPARATE'
        elif name.startswith('technical/'):row['technical']=obj
        elif name.startswith('measures/'):row['measures']=obj
    need(qgv is not None and records and all(set(r)=={'chart','technical','measures'} for r in records.values()),
         'COMPLETE_LATEST_INPUTS_REQUIRED')
    headers={k:r.pop('chart') for k,r in records.items()}
    state=pack(records,kind='INDICATORS',context=dict(evaluation_day=evaluation_day))
    context={k:v for k,v in qgv.items() if k not in ('rows','private_raw_detail')}
    q=pack(qgv['rows'],kind='QGV',context=context)
    q['raw_detail_state']='REBUILDABLE_NOT_IN_VIEW'
    files={'latest/indicators.json':json_bytes(state),'qgv/latest.json':json_bytes(q)}
    parts=defaultdict(dict);year=int(evaluation_day[:4]);month=evaluation_day[:7]
    for symbol,rows in sorted(charts.items()):
        bucket=f'{hashlib.sha256(symbol.encode()).digest()[0]%BUCKETS:02d}'
        for row in rows:
            day=row['date'];need(day<=evaluation_day,'FUTURE_CHART_ROW')
            if int(day[:4])<year-5:continue
            if day[:4]<evaluation_day[:4]:kind,period,slot='year',day[:4],bucket
            elif day[:7]<month:kind,period,slot='month',day[:7],bucket
            elif recent=='monthly':kind,period,slot='recent',month,bucket
            else:kind,period,slot='day',day,'all'
            parts[(kind,period,slot)].setdefault(symbol,[]).append([row.get(f) for f in FIELDS])
    pieces=[];corrections=[]
    prior={(x['kind'],x['period'],x['bucket']):x for x in (previous or {}).get('pieces',[])}
    for (kind,period,bucket),rows in sorted(parts.items()):
        for r in rows.values():r.sort(key=lambda x:x[0])
        payload=dict(schema='kis-chart-piece/2',publication_scope='OWNER_PRIVATE_ONLY',basis='RAW',
                     currency='USD',fields=FIELDS,period=period,rows=rows)
        b=json_bytes(payload);h=sha(b);need(len(b)<=MAX_BYTES,'CHART_PIECE_LIMIT')
        key=(kind,period,bucket)
        if kind!='recent' and key in prior and prior[key]['sha256']!=h:
            need(isinstance(revision_reference,str) and bool(revision_reference.strip()),'IMMUTABLE_PIECE_CHANGED')
            corrections.append(dict(kind=kind,period=period,bucket=bucket,
                prior_sha256=prior[key]['sha256'],new_sha256=h))
        path=f'chart/{kind}/{period}/{bucket}-{h}.json'
        files[path]=b
        pieces.append(dict(kind=kind,period=period,bucket=bucket,path=path,bytes=len(b),sha256=h))
    index=dict(schema='kis-chart-index/2',publication_scope='OWNER_PRIVATE_ONLY',
               evaluation_day=evaluation_day,buckets=BUCKETS,bucket_rule='SHA256_UTF8_FIRST_BYTE_MOD_32',
               row_source_scope='DERIVED_VIEW_RETAINED_ORIGINALS_SEPARATE',fields=FIELDS,
               headers=pack(headers,kind='CHART_HEADERS'),
               pieces=pieces)
    files['chart/index.json']=json_bytes(index)
    entries=[dict(path=n,bytes=len(b),sha256=sha(b)) for n,b in sorted(files.items())]
    manifest=dict(schema='kis-private-delivery/2',publication_scope='OWNER_PRIVATE_ONLY',
                  layout='COMPACT_DAILY' if recent=='daily' else 'COMPACT_RECENT_MONTH',
                  evaluation_day=evaluation_day,files=entries,pieces=pieces,
                  sources_recalculated_by='CANONICAL_KERNELS',raw_detail='REBUILDABLE_NOT_IN_VIEW',
                  verification_promoted=False)
    if corrections:manifest['reviewed_revisions']=dict(reference=revision_reference,pieces=corrections)
    # A repeat of identical service bytes is not a new annual charge.
    if previous and all(previous.get(k)==v for k,v in manifest.items()):
        files['manifest.json']=json_bytes(previous);return files
    year_key=evaluation_day[:4]
    used=(previous or {}).get('growth_ledger',{})
    carried=used.get('charged_bytes',0) if used.get('year')==year_key else 0
    manifest['growth_ledger']=dict(year=year_key,charged_bytes=carried,
        measure=GROWTH_MEASURE,
        reserved_other_git_bytes=40000000,annual_payload_budget=annual_budget)
    # Charge the manifest conservatively as uncompressed bytes, avoiding a
    # self-referential compressed-length checksum/length oscillation.
    for _ in range(8):
        files['manifest.json']=json_bytes(manifest)
        stats=growth(files,previous=previous)
        total=carried+stats['new_git_loose_blob_bytes']-_git_bytes(files['manifest.json'])+len(files['manifest.json'])+64
        if manifest['growth_ledger']['charged_bytes']==total:break
        manifest['growth_ledger']['charged_bytes']=total
    files['manifest.json']=json_bytes(manifest)
    need(total<=annual_budget,'ANNUAL_DATA_BUDGET')
    if daily_budget is not None:need(stats['changed_payload_bytes']<=daily_budget,'DAILY_DATA_BUDGET')
    need(all(len(b)<=MAX_BYTES for b in files.values()),'COMPACT_FILE_LIMIT')
    return files


def assemble_chart(files,symbol):
    """Reference consumer for Main: select one bucket, preserve RAW and claims."""
    index=json.loads(files['chart/index.json'])
    header=unpack_row(index['headers'],symbol);raw=[]
    bucket=f'{hashlib.sha256(symbol.encode()).digest()[0]%BUCKETS:02d}'
    for item in index['pieces']:
        if item['bucket'] not in (bucket,'all'):continue
        b=files[item['path']];need(sha(b)==item['sha256'] and len(b)==item['bytes'],'CHART_PIECE_PIN')
        p=json.loads(b)
        for values in p['rows'].get(symbol,[]):
            need(len(values)==len(FIELDS),'CHART_ROW_WIDTH')
            raw.append(dict(zip(FIELDS,values)))
    raw.sort(key=lambda r:r['date'])
    need(len({r['date'] for r in raw})==len(raw),'DUPLICATE_CHART_DAY')
    out=deepcopy(header);out.update(schema='kis-chart-view/2',raw_bars=raw)
    out['bars']=price_rows(dict(out,raw_bars=raw),index['evaluation_day'])
    return out
