"""Offline actual-response audit; calendar validity is not investment eligibility."""
import argparse,csv,json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from pilot import RawDatasetStore,digest,encoded,private_dir


def intervals(observed,calendar):
    result=[];current=[]
    for d in calendar:
        if d in observed:current.append(d)
        elif current:result.append({'first':current[0],'last':current[-1],'sessions':len(current)});current=[]
    if current:result.append({'first':current[0],'last':current[-1],'sessions':len(current)})
    return result


def verify(root,baseline,old,output):
    out=private_dir(output);state=json.loads((root/'stable-state.json').read_bytes());plan=state['plan']
    store=RawDatasetStore(root/'store');calbody=store.get_bytes('stable-calendar');assert digest(calbody)==plan['calendar']['sha256']
    calendar=[x[''][:10]for x in csv.DictReader(calbody.decode().splitlines())];market=set(calendar)
    baseline_rows=json.loads((baseline/'normalized.json').read_bytes());series=json.loads((root/'stable-normalized.json').read_bytes())
    observed={};source_hashes=set();field_checks=0;request_dates=[]
    for folder in (old,root):
        raw=RawDatasetStore(folder/'store')
        for p in (folder/'requests').glob('*.json'):
            m=json.loads(p.read_bytes());q=m['request'];receipt=m.get('receipt',{})
            if q.get('MODP')!='0' or not receipt.get('sha256'):continue
            body=raw.get_bytes(receipt['artifact_id']);assert digest(body)==receipt['sha256'];source_hashes.add(receipt['sha256'])
            obj=json.loads(body)
            if obj.get('rt_cd')!='0':continue
            for row in obj.get('output2',[]):
                d=row['xymd'];d=d[:4]+'-'+d[4:6]+'-'+d[6:];symbol=q['SYMB']
                if d>='2016-01-01':continue
                values={f:Decimal(row[k])for f,k in zip(('open','high','low','close','volume'),('open','high','low','clos','tvol'))}
                key=(symbol,d)
                if key in observed:assert observed[key]==values,'CONFLICTING_RAW_DUPLICATE'
                observed[key]=values
    companies=[];rejections=[]
    for route in plan['routes']:
        alias=route['alias'];c=route['company'];rows=series.get(alias,{})
        for d,row in rows.items():
            assert (alias,d)in observed
            for f,v in row['raw'].items():
                if f in observed[(alias,d)]:assert Decimal(str(v))==observed[(alias,d)][f];field_checks+=1
        dates={d for d in rows if route['start']<=d<=route['end']};sessions=dates&market
        previous=set(baseline_rows.get(alias,{}));new=dates-previous
        excluded=sorted(dates-market)
        for d in excluded:rejections.append({'company':c,'date':d,'reason':'REFERENCE_CALENDAR_CLOSED','volume_zero':rows[d]['raw']['volume']==0,'ohlc_flat':len({rows[d]['raw'][f]for f in ('open','high','low','close')})==1})
        expected={d for d in calendar if max(plan.get('target_start','2010-01-01'),route['start'])<=d<=min('2015-12-31',route['end'])}
        requests=[x for x in state['requests']if x['company']==c]
        tasks=[x for x in state['tasks']if x['company']==c]
        clean={d:rows[d]for d in sorted(sessions)}
        (out/(c+'-calendar-filtered-private.json')).write_bytes(encoded(clean))
        companies.append({'company':c,'alias':alias,'requested_start':plan.get('target_start','2010-01-01'),'expected_sessions':len(expected),
            'raw_rows_in_identity_window':len(dates),'calendar_rows':len(sessions),'new_raw_rows':len(new),'new_calendar_rows':len(new&market),
            'off_calendar_rows':len(excluded),'continuous_blocks':intervals(sessions,calendar),'missing_target_blocks':intervals(expected-sessions,calendar),
            'target_acquired':len(sessions&expected),'request_states':dict(Counter(x['state']for x in requests)),
            'actual_calls':len(requests),'task_states':dict(Counter(x['state']for x in tasks)),
            'next_positions':[{'year':t['year'],'cursor':t['cursor'],'state':t['state'],'reason':t.get('reason')}for t in tasks if t['state']!='VALIDATED'],
            'identity_status':route['identity_status'],'not_ipo_or_delisting_inferred':True,'formal_eligible_period':None})
    # Exact original ABT gap, independently derived from the preserved calendar.
    gap={d for d in calendar if '2010-04-05'<=d<='2011-01-31'}
    assert len(gap)==210
    report={'version':'BT-DATA-PILOT v0.6','run_id':state['run_id'],'companies':companies,'abt_gap_expected':210,
        'abt_gap_acquired':len(gap&set(series['ABT'])),'raw_hashes_reopened':len(source_hashes),'field_checks':field_checks,
        'off_calendar_rejections':rejections,'auth':state['auth'],'token_issuances':state['token_issuances'],'token_refreshes':state['token_refreshes'],
        'workers':1,'market_calls':state['market_requests'],'elapsed_seconds':state['elapsed_seconds'],
        'errors':[x for x in state['requests']if x['state']in('RETRYABLE_ERROR','BLOCKED')],
        'raw_normalizer_replay':'PASS','calendar_filter':'PASS_REFERENCE_FIXTURE_NOT_FULL_SECURITY_SESSION_PROOF',
        'corporate_actions':'NOT_VALIDATED_BY_PRICE_COVERAGE','formal_backtests':0}
    (out/'actual-audit-private.json').write_bytes(encoded(report))
    # Excludes receipts, price hashes, prices, and derived valuation numbers.
    public={k:v for k,v in report.items()if k not in ('errors','off_calendar_rejections')}
    public['error_summary']=[{k:x.get(k)for k in ('company','bymd','http_status','provider_code','provider_message','state','attempt','retrieved_at')}for x in report['errors']]
    public['off_calendar_rows_excluded']=len(rejections)
    unique_bad={(x['symbol'],x['date'],x['reason']) for x in state.get('quality_rejections',[])}
    public['quality_rejected_symbol_dates']=[{'symbol':s,'date':d,'reason':reason}for s,d,reason in sorted(unique_bad)]
    (out/'aggregate.json').write_bytes(encoded(public));return public

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('root','baseline','old','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.root,a.baseline,a.old,a.output),sort_keys=True))
