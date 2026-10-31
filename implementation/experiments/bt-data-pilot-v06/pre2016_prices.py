"""Bounded pre-2016 KIS backfill using explicit BYMD, never a new pricing engine.

Actual aliases are kept separate. Requests are not evidence of listing dates.
One authentication; stop on provider rejection, no session/token retry.
"""
import argparse
from datetime import date, timedelta
import json
import os
from pathlib import Path

from github_kis_probe import KIS, FIXED, choose_keys, kis_normalize
from long_prices import safe_extract, checkpoint
from pilot import private_dir, RawDatasetStore, encoded, digest
from github_alpaca_probe import release, RAW_REPO


def run(output, archive, resume=None, phase='all'):
    if os.environ.get('GITHUB_ACTIONS') != 'true': raise ValueError('RUNNER_REQUIRED')
    code, _, data = release.http('GET',f'{release.API}/repos/{RAW_REPO}')
    if code != 200 or json.loads(data).get('private') is not True: raise ValueError('PRIVATE_DESTINATION_REQUIRED')
    root=private_dir(output); (root/'requests').mkdir(exist_ok=True)
    old=root.parent/'prior-kis';safe_extract(archive,old)
    if resume:
        safe_extract(resume,root)
        (root/'previous-aggregate.json').write_bytes((root/'aggregate.json').read_bytes())
    oldstore=RawDatasetStore(old/'store');store=RawDatasetStore(root/'store')
    aliases=[(s,h,'NAS' if h=='CECE' else ex)for _,s,ex,h in FIXED]
    series={h:{} for _,h,_ in aliases}; reused=[]
    for p in (old/'requests').glob('*.json'):
        m=json.loads(p.read_bytes());q=m['request'];r=m.get('receipt',{})
        if q.get('SYMB') not in series or q.get('MODP')!='0' or not r.get('sha256'):continue
        body=oldstore.get_bytes(r['artifact_id']);assert digest(body)==r['sha256']
        if json.loads(body).get('rt_cd')!='0':continue
        for row in kis_normalize(body,q['SYMB'],'0',q['BYMD']):
            if row['session_date']<'2016-01-01':series[q['SYMB']][row['session_date']]=row
        reused.append({'request':q,'receipt':r})
    (root/'reused-sources.json').write_bytes(encoded(reused))
    cursors={h:(date.fromisoformat(min(series[h]))-timedelta(days=1)).strftime('%Y%m%d')
             if series[h] else '20151231' for _,h,_ in aliases}
    # Restore actual old responses, but do not let disconnected era-probe islands
    # advance the contiguous backfill cursor.
    if resume:
        for p in (root/'requests').glob('*.json'):
            m=json.loads(p.read_bytes());q=m['request'];r=m.get('receipt',{})
            if q.get('SYMB') not in series or not r.get('sha256'):continue
            body=store.get_bytes(r['artifact_id']);assert digest(body)==r['sha256']
            if json.loads(body).get('rt_cd')!='0':continue
            for row in kis_normalize(body,q['SYMB'],'0',q['BYMD']):
                series[q['SYMB']][row['session_date']]=row
    report={'version':'BT-DATA-PILOT v0.6','targets':['2010-01-01','2000-01-01','1990-01-01'],
            'requests':[],'auth':None,'formal_backtests':0,'local_request_cap':240,
            'historical_security_identity_verified':False,'joined_to_sip':False,'phase':phase,
            'resume_archive_sha256':release.file_sha(resume) if resume else None}
    keys,status=choose_keys(os.environ)
    client=KIS(root,store,keys,max_calls=240) if keys else None
    if client:
        client.pause_seconds=2.0;client.request_label='PRE2016_EXPLICIT_BYMD'
        report['auth']=client.authenticate()
    else:report['auth']={'status':status}
    tag='bt-data-pilot-v06-pre2016-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1')

    def save(name):
        report['market_requests']=client.calls if client else 0
        report['coverage']=[{'company':s,'alias':h,'rows':len(series[h]),'first':min(series[h],default=None),
            'last':max(series[h],default=None),'requested_targets':report['targets'],
            'identity_status':'UNVERIFIED_DO_NOT_STITCH','ledger_ready':False}for s,h,_ in aliases]
        (root/'normalized.json').write_bytes(encoded(series));(root/'aggregate.json').write_bytes(encoded(report))
        checkpoint(root,tag,name)

    def page(alias,ex,bymd,purpose):
        if client.stopped or client.calls>=client.max_calls:return None
        calls_before=client.calls
        body,m=client.page(alias,ex,bymd,'0','')
        result={'alias':alias,'exchange':ex,'bymd':bymd,'purpose':purpose,'http_status':m.get('http_status'),
                'retrieved_at':m.get('retrieved_at'),'response_tr_cont':m.get('response_tr_cont'),
                'cache_hit':client.calls==calls_before}
        report['requests'].append(result)
        if not body:
            result['status']=m.get('status','NETWORK_REQUEST_FAILED');client.stopped=True;return None
        obj=json.loads(body)
        if obj.get('rt_cd')!='0':
            result.update(status='API_REJECTED',provider_code=obj.get('msg_cd'))
            client.stopped=True;return None
        try:rows=kis_normalize(body,alias,'0',bymd)
        except (ValueError,KeyError,TypeError):
            result['status']='RESPONSE_QUALITY_FAILED';client.stopped=True;return None
        result.update(status='ACQUIRED' if rows else 'EMPTY_RESPONSE_NOT_HISTORY_START_PROOF',rows=len(rows),
                      first=min((r['session_date']for r in rows),default=None),last=max((r['session_date']for r in rows),default=None))
        for row in rows:
            d=row['session_date']
            if d in series[alias] and series[alias][d]['raw']!=row['raw']:raise ValueError('OVERLAP_CONFLICT')
            if d<'2016-01-01':series[alias][d]=row
        (root/'aggregate.json').write_bytes(encoded(report))
        return rows

    if client and report['auth']['status']=='AUTHENTICATED':
        # Probe the old 100-row edge first, then three explicit older anchors.
        for d in (('20151105','20100401','20000403','19900402') if phase=='all' else ()):
            if page('ABT','NYS',d,'ABT_BOUNDARY_AND_ERA_PROBE') is None:break
        save('anchor-checkpoint')
        if not client.stopped and phase=='all':
            for company,alias,ex in aliases:
                if alias!='ABT':
                    page(alias,ex,'20100401','FIXED10_2010_PROBE')
                    if client.stopped:break
                    page(alias,ex,'20000403','FIXED10_2000_PROBE')
                if client.stopped:break
        # 2010 first for each fixed alias. Earlier anchor islands do not count as a contiguous backfill.
        targets=[('2010-01-01',aliases)]
        if phase=='all':targets += [('2000-01-01',[aliases[0]]),('1990-01-01',[aliases[0]])]
        for target, cohort in targets:
            for company,alias,ex in cohort:
                if not client or client.stopped or client.calls>=client.max_calls:break
                cursor=cursors[alias];visited=set()
                while cursor>=target.replace('-','') and not client.stopped and client.calls<client.max_calls:
                    if cursor in visited:raise ValueError('REPEATED_CURSOR')
                    visited.add(cursor)
                    rows=page(alias,ex,cursor,'BACKFILL_TO_'+target)
                    if not rows:break
                    earliest=min(r['session_date']for r in rows)
                    nxt=(date.fromisoformat(earliest)-timedelta(days=1)).strftime('%Y%m%d')
                    if nxt>=cursor:raise ValueError('NO_BACKWARD_PROGRESS')
                    cursor=nxt
                    cursors[alias]=cursor
                    (root/'checkpoint.json').write_bytes(encoded({'cursors':cursors,'target':target,'calls':client.calls}))
                save(company+'-'+target)
    save('final')
    return {'version':report['version'],'private_release_tag':tag,'auth':report['auth'],
            'market_requests':report.get('market_requests',0),'coverage':report['coverage'],
            'last_request_status':report['requests'][-1] if report['requests'] else None}


def response_state(http,obj):
    if http in (401,403,429) or obj.get('msg_cd')=='EGW00201':return 'BLOCKED'
    if http is None or http>=500 or obj.get('msg_cd')=='OPSQ1002':return 'RETRYABLE_ERROR'
    if http!=200 or obj.get('rt_cd')!='0':return 'BLOCKED'
    return 'FETCHED' if obj.get('output2') else 'EMPTY_RESPONSE'


def year_tasks(expected,acquired):
    tasks=[]
    for company,days in expected.items():
        for year in sorted({int(d[:4])for d in days},reverse=True):
            missing=sorted(d for d in days if int(d[:4])==year and d not in acquired.get(company,set()))
            if missing:tasks.append({'company':company,'year':year,'cursor':missing[-1].replace('-',''),'state':'PENDING'})
    return tasks


def stable_run(output,archive,resume,plan_path):
    """Serial per-company/year queue; bounded retry receipts never overwrite originals."""
    import csv,time
    from datetime import datetime,timezone
    from pilot import acquire
    if os.environ.get('GITHUB_ACTIONS')!='true':raise ValueError('RUNNER_REQUIRED')
    code,_,data=release.http('GET',f'{release.API}/repos/{RAW_REPO}')
    if code!=200 or json.loads(data).get('private')is not True:raise ValueError('PRIVATE_DESTINATION_REQUIRED')
    root=private_dir(output);old=root.parent/'prior-kis';safe_extract(archive,old)
    safe_extract(resume,root);store=RawDatasetStore(root/'store');plan=json.loads(plan_path.read_bytes())
    prior_state=json.loads((root/'stable-state.json').read_bytes())if(root/'stable-state.json').exists()else None
    run_id=os.environ['GITHUB_RUN_ID']+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1')
    if prior_state:(root/('stable-state-before-'+run_id+'.json')).write_bytes(encoded(prior_state))
    series={};cache={};conflicts=[]
    for folder in (old,root):
        source=RawDatasetStore(folder/'store')
        for p in sorted((folder/'requests').glob('*.json')):
            m=json.loads(p.read_bytes());q=m['request'];r=m.get('receipt',{})
            if q.get('MODP')!='0' or not r.get('sha256'):continue
            b=source.get_bytes(r['artifact_id']);assert digest(b)==r['sha256'];o=json.loads(b)
            key=(q['SYMB'],q['EXCD'],q['BYMD'])
            if response_state(m['http_status'],o)in('FETCHED','EMPTY_RESPONSE'):
                cache[key]=(b,m)
                for row in kis_normalize(b,q['SYMB'],'0',q['BYMD']):
                    if row['session_date']>='2016-01-01':continue
                    sid=q['SYMB'];d=row['session_date'];series.setdefault(sid,{})
                    if d in series[sid]and series[sid][d]['raw']!=row['raw']:
                        conflicts.append({'symbol':sid,'date':d,'reason':'ROUTING_OR_VINTAGE_CONFLICT'});continue
                    series[sid][d]=row
    before={s:set(rows)for s,rows in series.items()}
    acquire(store,'stable-calendar',plan['calendar']['url'],'PUBLIC_EXCHANGE_CALENDAR_FIXTURE')
    body=store.get_bytes('stable-calendar');assert digest(body)==plan['calendar']['sha256']
    calendar=[r[''][:10]for r in csv.DictReader(body.decode().splitlines())]
    routes={r['company']:r for r in plan['routes']}
    expected={c:{d for d in calendar if max('2010-01-01',r['start'])<=d<=min('2015-12-31',r['end'])}for c,r in routes.items()}
    acquired={c:set(series.get(r['alias'],{}))for c,r in routes.items()}
    tasks=year_tasks(expected,acquired)
    # ABT's exact gap first, then rotate companies each year; a rejection is not a global completion.
    tasks.sort(key=lambda t:(0 if t['company']=='ABT'else 1,-t['year'],list(routes).index(t['company'])))
    report={'version':'BT-DATA-PILOT v0.6','run_id':run_id,'token_issuances':0,'token_refreshes':0,'workers':1,
        'requests':[],'tasks':tasks,'conflicts':conflicts,'formal_backtests':0,'plan':plan,'old_snapshot_preserved':True,
        'started_at':datetime.now(timezone.utc).isoformat(),'all_key_users_observable':False,'max_new_calls':210}
    keys,status=choose_keys(os.environ);client=KIS(root,store,keys,max_calls=210)if keys else None
    if client:
        client.pause_seconds=3.0;client.request_label='STABLE_'+run_id
        report['auth']=client.authenticate();report['token_issuances']=1
    else:report['auth']={'status':status}
    tag='bt-data-pilot-v06-kis-stable-'+run_id
    failures={};started=time.monotonic();calls_checkpoint=0
    def save(upload=False):
        report['market_requests']=client.calls if client else 0
        report['elapsed_seconds']=round(time.monotonic()-started,3)
        report['coverage']=[]
        for company,r in routes.items():
            dates=set(series.get(r['alias'],{}));visible=sorted(d for d in dates if r['start']<=d<=r['end'])
            missing=sorted(expected[company]-dates)
            report['coverage'].append({'company':company,'alias':r['alias'],'first':min(visible,default=None),'last':max(visible,default=None),
                'rows':len(visible),'new_rows':len(set(visible)-before.get(r['alias'],set())),
                'expected_sessions':len(expected[company]),'missing_sessions':len(missing),'missing_dates':missing,
                'identity_status':r['identity_status'],'formal_eligible':False})
        (root/'stable-normalized.json').write_bytes(encoded(series));(root/'stable-state.json').write_bytes(encoded(report))
        if upload:checkpoint(root,tag,'stable-'+str(report['market_requests']))
    def request(company,alias,exchange,cursor,purpose):
        nonlocal calls_checkpoint
        key=(alias,exchange,cursor)
        if key in cache:return cache[key],response_state(cache[key][1]['http_status'],json.loads(cache[key][0]))
        for attempt in range(2):
            if client.stopped or client.calls>=210 or time.monotonic()-started>1500:return (None,None),'PENDING'
            if attempt:time.sleep(30)
            b,m=client.page(alias,exchange,cursor,'0',attempt=attempt)
            try:obj=json.loads(b)if b else {}
            except ValueError:obj={}
            state=response_state(m.get('http_status'),obj)
            event={k:m.get(k)for k in ('http_status','retrieved_at','elapsed_seconds','response_tr_cont','receipt')}
            event.update(company=company,alias=alias,exchange=exchange,bymd=cursor,purpose=purpose,attempt=attempt,state=state,
                provider_code=obj.get('msg_cd'),provider_message=obj.get('msg1'),token_instance=1)
            report['requests'].append(event);save()
            if state in ('FETCHED','EMPTY_RESPONSE'):
                cache[key]=(b,m);return (b,m),state
            if state=='BLOCKED':
                if obj.get('msg_cd')=='EGW00201':client.stopped=True
                return (b,m),state
            failures[company]=failures.get(company,0)+1
            if failures[company]>=2:return (b,m),state
        return (b,m),state
    def add_rows(company,alias,b,m,cursor):
        rows=kis_normalize(b,alias,'0',cursor);group=series.setdefault(alias,{})
        for row in rows:
            d=row['session_date']
            if d>='2016-01-01':continue
            if d in group and group[d]['raw']!=row['raw']:
                conflicts.append({'symbol':alias,'date':d,'reason':'OVERLAP_CONFLICT'});raise ValueError('OVERLAP_CONFLICT')
            group[d]=row
        return rows
    if client and report['auth']['status']=='AUTHENTICATED':
        for task in tasks:
            c=task['company'];r=routes[c];alias=r['alias'];year=task['year']
            if failures.get(c,0)>=2:task.update(state='BLOCKED',reason='COMPANY_RETRY_LIMIT');continue
            if client.stopped or client.calls>=210 or time.monotonic()-started>1500:break
            seen=set();cursor=task['cursor']
            while True:
                missing=sorted(d for d in expected[c]if int(d[:4])==year and d not in series.get(alias,{}))
                if not missing:task.update(state='VALIDATED',validation='RAW_ROWS_AND_REFERENCE_CALENDAR_ONLY');break
                cursor=min(cursor,missing[-1].replace('-',''));task['cursor']=cursor
                if cursor in seen:task.update(state='BLOCKED',reason='REPEATED_CURSOR');break
                seen.add(cursor)
                (b,m),state=request(c,alias,r['exchange'],cursor,'YEAR_'+str(year));task['state']=state
                if state=='EMPTY_RESPONSE' and r.get('fallback_exchange'):
                    (b,m),state=request(c,alias,r['fallback_exchange'],cursor,'EXCHANGE_ROUTING_CONTROL');task['state']=state
                if state!='FETCHED':break
                try:rows=add_rows(c,alias,b,m,cursor)
                except (ValueError,KeyError,TypeError):task.update(state='BLOCKED',reason='QUALITY_OR_OVERLAP_FAILED');break
                earliest=min(x['session_date']for x in rows);nxt=(date.fromisoformat(earliest)-timedelta(days=1)).strftime('%Y%m%d')
                if nxt>=cursor:task.update(state='BLOCKED',reason='NO_BACKWARD_PROGRESS');break
                cursor=nxt;task['cursor']=cursor
                if cursor<str(year)+'0101':
                    missing=expected[c]-set(series.get(alias,{}));within=[d for d in missing if int(d[:4])==year]
                    task.update(state='VALIDATED'if not within else 'BLOCKED',reason=None if not within else 'INTERNAL_SESSION_GAPS');break
                save()
            save(upload=True)
        # Intermediate anchors only after every company has had a queue opportunity.
        for bymd in ('20091231','20051230','20001229','19951229'):
            for c,r in routes.items():
                if r['start']>'2000-01-01' or failures.get(c,0)>=2:continue
                if client.stopped or client.calls>=210 or time.monotonic()-started>1500:break
                if bymd=='19951229' and c!='ABT':continue
                (b,m),state=request(c,r['alias'],r['exchange'],bymd,'HISTORY_BOUNDARY_PROBE')
                if state=='FETCHED':
                    try:add_rows(c,r['alias'],b,m,bymd)
                    except (ValueError,KeyError,TypeError):report['requests'][-1]['state']='BLOCKED'
                save()
    save();checkpoint(root,tag,'final')
    return {'version':report['version'],'private_release_tag':tag,'auth':report['auth'],'market_requests':report['market_requests'],
        'states':{s:sum(t['state']==s for t in tasks)for s in sorted({t['state']for t in tasks})},
        'coverage':[{k:v for k,v in c.items()if k!='missing_dates'}for c in report['coverage']]}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private-dir',type=Path,required=True);p.add_argument('--prior-zip',type=Path,required=True)
    p.add_argument('--resume-zip',type=Path);p.add_argument('--phase',choices=('all','2010','stable'),default='all')
    p.add_argument('--plan',type=Path)
    a=p.parse_args()
    try:print(json.dumps(stable_run(a.private_dir,a.prior_zip,a.resume_zip,a.plan) if a.phase=='stable' else run(a.private_dir,a.prior_zip,a.resume_zip,a.phase)))
    except (ValueError,KeyError,TypeError,OSError,release.ReleaseError):
        print('{"status":"STOPPED_CHECK_PRIVATE_CHECKPOINT"}');raise SystemExit(2) from None
