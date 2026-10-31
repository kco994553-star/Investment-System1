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


def run(output, archive):
    if os.environ.get('GITHUB_ACTIONS') != 'true': raise ValueError('RUNNER_REQUIRED')
    code, _, data = release.http('GET',f'{release.API}/repos/{RAW_REPO}')
    if code != 200 or json.loads(data).get('private') is not True: raise ValueError('PRIVATE_DESTINATION_REQUIRED')
    root=private_dir(output); (root/'requests').mkdir(exist_ok=True)
    old=root.parent/'prior-kis';safe_extract(archive,old)
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
    report={'version':'BT-DATA-PILOT v0.6','targets':['2010-01-01','2000-01-01','1990-01-01'],
            'requests':[],'auth':None,'formal_backtests':0,'local_request_cap':240,
            'historical_security_identity_verified':False,'joined_to_sip':False}
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
        body,m=client.page(alias,ex,bymd,'0','')
        result={'alias':alias,'exchange':ex,'bymd':bymd,'purpose':purpose,'http_status':m.get('http_status'),
                'retrieved_at':m.get('retrieved_at'),'response_tr_cont':m.get('response_tr_cont')}
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
        for d in ('20151105','20100401','20000403','19900402'):
            if page('ABT','NYS',d,'ABT_BOUNDARY_AND_ERA_PROBE') is None:break
        save('anchor-checkpoint')
        if not client.stopped:
            for company,alias,ex in aliases:
                if alias!='ABT':
                    page(alias,ex,'20100401','FIXED10_2010_PROBE')
                    if client.stopped:break
                    page(alias,ex,'20000403','FIXED10_2000_PROBE')
                if client.stopped:break
        # 2010 first for each fixed alias. Earlier anchor islands do not count as a contiguous backfill.
        for target, cohort in [('2010-01-01',aliases),('2000-01-01',[aliases[0]]),('1990-01-01',[aliases[0]])]:
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


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private-dir',type=Path,required=True);p.add_argument('--prior-zip',type=Path,required=True)
    a=p.parse_args()
    try:print(json.dumps(run(a.private_dir,a.prior_zip)))
    except (ValueError,KeyError,TypeError,OSError,release.ReleaseError):
        print('{"status":"STOPPED_CHECK_PRIVATE_CHECKPOINT"}');raise SystemExit(2) from None
