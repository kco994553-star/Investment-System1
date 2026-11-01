"""Replay pre-2016 originals; audit gaps, quarantined CSV, and older SEC items.

All numerical prices and financial extracts are private. No provider requests,
price stitching, universe substitution, or strategy execution occur here.
"""
import argparse,csv,html,json,re
from collections import Counter
from pathlib import Path
from audit_v_ledger import replay_kis
from pilot import RawDatasetStore,digest,encoded,private_dir


def blocks(missing,calendar):
    groups=[]
    for day in calendar:
        if day not in missing:continue
        if groups and calendar.index(day)==calendar.index(groups[-1][-1])+1:groups[-1].append(day)
        else:groups.append([day])
    return [{'first':g[0],'last':g[-1],'sessions':len(g)}for g in groups]


def run(root,prior,output):
    out=private_dir(output)
    rows,checks=replay_kis([root/'github-kis-cooldown-20261031/restored',root/'pre2016-2010/restored'])
    calendar=[r[''][:10]for r in csv.DictReader((prior/'github/gerrymanoim__exchange_calendars/tests__resources__xnys.csv').open())]
    expected=[d for d in calendar if '2010-01-01'<=d<='2015-12-31']
    companies=[('ABT','ABT'),('ACU','ACU'),('AE','AE'),('BKTI','RWC'),('AMD','AMD'),('CECO','CECE'),('MATX','MATX'),('ALX','ALX'),('LNG','LNG'),('IDSA','IDSA')]
    coverage=[]
    for company,alias in companies:
        dates=sorted(d for s,d in rows if s==alias and d<'2016-01-01')
        missing=set(expected)-set(dates)
        coverage.append({'company':company,'alias':alias,'target_start':'2010-01-01',
            'pre2016_rows':len(dates),'first':dates[0]if dates else None,'last':dates[-1]if dates else None,
            'expected_reference_sessions_2010_2015':len(expected),'acquired_in_target':len(set(dates)&set(expected)),
            'missing_reference_sessions':len(missing),'missing_blocks':blocks(missing,expected),
            'new_2010_request_executed':company=='ABT','reason':'SESSION_FULL_HALTED' if company=='ABT' else 'NOT_ATTEMPTED_AFTER_GLOBAL_STOP',
            'missing_is_not_ipo_or_delisting_inference':True,'formal_eligible_period':None})
    store=RawDatasetStore(root/'v-ledger-audit/sources')
    body=store.get_bytes('github-abt-price-quarantine');assert digest(body)==store.get_manifest('github-abt-price-quarantine')['sha256']
    sample=list(csv.DictReader(body.decode().splitlines()));counts=Counter(r['Date']for r in sample)
    invalid=[];missing=0
    from decimal import Decimal
    for r in sample:
        try:
            o,h,l,c,v=[Decimal(r[k])for k in ('Open','High','Low','Close','Volume')]
            if not all(x.is_finite()for x in (o,h,l,c,v)) or min(o,h,l,c)<=0 or v<0 or not l<=min(o,c)<=max(o,c)<=h:invalid.append(r['Date'])
        except Exception:missing+=1
    pairs=[(r,rows[('ABT',r['Date'])])for r in sample if ('ABT',r['Date'])in rows]
    quarantine={'repository':'https://github.com/wmhbrown121/trade-datasets','commit':'c2a1af916490810bc01866deefbd509620225846',
        'file':'Kaggle/Data/Stocks/abt.us.txt','rows':len(sample),'first':min(counts),'last':max(counts),
        'duplicate_dates':sum(n-1 for n in counts.values()),'invalid_ohlcv':len(invalid),'missing_or_non_numeric_rows':missing,
        'kis_overlap_rows':len(pairs),'close_equal_within_one_cent':sum(abs(Decimal(r['Close'])-Decimal(str(k['raw']['close'])))<=Decimal('.01')for r,k in pairs),
        'original_supplier':'NOT_VERIFIED','data_license':'NOT_VERIFIED','adjustment':'NOT_VERIFIED','currency_and_identity':'NOT_VERIFIED',
        'adopted':False,'reason':'AUDIT_ONLY_NOT_EXECUTION_OR_VALUATION_INPUT'}
    # Extract original current-year columns; preserve source and normalized-text offsets.
    # Earlier years restated in later reports are not substituted for their original vintages.
    filings={1998:('1999-03-09',None),2000:('2001-02-15',None),2008:('2009-02-20','2009-02-20T21:44:22Z'),2009:('2010-02-19','2010-02-19T21:05:52Z')}
    extracts=[]
    for year,(filed,accepted) in filings.items():
        aid=f'abt-{year}-10k';body=store.get_bytes(aid);manifest=store.get_manifest(aid);assert digest(body)==manifest['sha256']
        text=' '.join(html.unescape(re.sub('<[^>]+>',' ',body.decode())).split())
        anchor=re.search(r'(?i)CONSOLIDATED STATEMENT OF EARNINGS(?: and Comprehensive Income)? \(dollars and shares in thousands except per share data\)',text)
        assert anchor;section=text[anchor.start():anchor.start()+4000];assert str(year) in section[:300]
        items={}
        for key,label in [('revenue','Net Sales'),('operating_earnings','Operating Earnings')]:
            m=re.search(label+r'[ .]*\$?\s*([\d,]+)',section,re.I);assert m
            raw=int(m[1].replace(',',''));assert raw>0
            items[key]={'reported_value':raw,'reported_unit':'USD_THOUSANDS','multiplier':1000,'value_usd':raw*1000,
                'normalized_text_offset':anchor.start()+m.start(),'original_statement_label':label}
        extracts.append({'source_id':aid,'source_manifest':manifest,'fiscal_year':year,'period_end':f'{year}-12-31',
            'filed':filed,'accepted':accepted,'timestamp_status':'EXACT_SUBMISSIONS' if accepted else 'DATE_ONLY_PENDING_ORIGINAL_HEADER',
            'items':items,'full_qgv_ready':False,'no_use_before_publication':True})
    intervals=list(csv.DictReader((prior/'github/fja05680__sp500/sp500_ticker_start_end.csv').open()))
    universe=[]
    for d in ('1990-01-02','2000-01-03','2010-01-04','2016-04-01','2026-10-30'):
        eligible=[r for r in intervals if r['start_date']<=d and(not r['end_date']or d<r['end_date'])]
        universe.append({'date':d,'candidate_interval_rows':len(eligible),'unique_tickers':len({r['ticker']for r in eligible}),
            'verified_historical_members':0,'end_boundary_convention':'ASSUMED_HALF_OPEN_NOT_VERIFIED',
            'reason':'MISSING_AUTHORITATIVE_EFFECTIVE_DATES_AND_DATA_RIGHTS','iex_membership_verified':False})
    (out/'older-financial-extracts-private.json').write_bytes(encoded(extracts))
    result={'version':'BT-DATA-PILOT v0.6','coverage':coverage,'quarantined_csv':quarantine,'raw_replay':checks,
        'older_sec_originals':[{k:r[k]for k in ('source_id','fiscal_year','filed','timestamp_status','full_qgv_ready')}for r in extracts],
        'universe':universe,'universe_source_rows':len(intervals),'formal_backtests':0}
    (out/'period-aggregate.json').write_bytes(encoded(result));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('root','prior','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.root,a.prior,a.output),sort_keys=True))
