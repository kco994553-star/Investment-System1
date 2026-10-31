"""Offline verification of actual annual SIP pages, calendars and alias boundaries."""
import argparse
import csv
from datetime import datetime
from decimal import Decimal
import json
import html
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from long_prices import SYMBOLS, dates, START, END, RawDatasetStore, digest, encoded
from github_alpaca_probe import normalize
from github_kis_probe import FIXED


def run(root, old_alpaca, old_kis, calendar_fixture, events, output):
    evidence_store=RawDatasetStore(events/'sources')
    evidence={}
    for aid in ('rwc-bkti','ceco-ticker-official','ae-merger','idsa-form25','idsa-jan3'):
        body=evidence_store.get_bytes(aid);assert digest(body)==evidence_store.get_manifest(aid)['sha256']
        evidence[aid]=' '.join(html.unescape(re.sub('<[^>]+>',' ',body.decode())).split())
    assert all(t in evidence['rwc-bkti']for t in ('June 5, 2018','09180A100','continue to be valid'))
    assert all(t in evidence['ceco-ticker-official']for t in ('Nov. 7, 2022','CUSIP will remain unchanged'))
    assert 'February 5, 2025' in evidence['ae-merger']
    assert '12-30-2019' in evidence['idsa-form25'] and 'January 13, 2020' in evidence['idsa-jan3']
    reused = {}
    for old in (old_alpaca, old_kis):
        store=RawDatasetStore(old/'store')
        for p in (old/'requests').glob('*.json'):
            meta=json.loads(p.read_bytes());request=meta.get('request',{});receipt=meta.get('receipt',{})
            if request.get('symbol') not in SYMBOLS or request.get('feed')!='sip' or request.get('adjustment')!='raw' or not receipt.get('sha256'):continue
            body=store.get_bytes(receipt['artifact_id']);assert digest(body)==receipt['sha256']
            for r in normalize(body,request):reused[(r['symbol'],r['session_date'])]=r
    hashes=numeric=pages=terminal_pages=0;by_symbol={};details=[]
    for symbol in SYMBOLS:
        folder=root/symbol;store=RawDatasetStore(folder/'store');replayed={d:r for (s,d),r in reused.items()if s==symbol}
        for p in sorted((folder/'requests').glob('*.json')):
            meta=json.loads(p.read_bytes());receipt=meta['receipt'];params=meta['arguments']
            if not receipt.get('sha256'):raise ValueError('UNACQUIRED_REQUEST')
            body=store.get_bytes(receipt['artifact_id']);assert digest(body)==receipt['sha256'];hashes+=1
            source=json.loads(body,parse_float=Decimal);data=json.loads(body)
            terminal_pages += not bool(data.get('next_page_token'))
            a,b=params['start'][:10],params['end'][:10]
            request={'symbol':symbol,'feed':'sip','adjustment':'raw','days':dates(a,b)}
            parsed=normalize(encoded(dict(data,next_page_token=None)),request)
            original={r['t'][:10]:r for r in source['bars'] or []}
            for row in parsed:
                for field,key in zip(('open','high','low','close','volume'),('o','h','l','c','v')):
                    assert Decimal(str(row['raw'][field]))==Decimal(str(original[row['session_date']][key]));numeric+=1
                if row['session_date'] in replayed:
                    assert replayed[row['session_date']]['raw']==row['raw']
                replayed[row['session_date']]=row
            pages+=1
        saved=json.loads((folder/'normalized.json').read_bytes())
        assert encoded(saved)==encoded([replayed[d]for d in sorted(replayed)])
        by_symbol[symbol]=replayed
        details.append(json.loads((folder/'aggregate.json').read_bytes()))
    cal=RawDatasetStore(root/'summary/calendar');aid=cal.list_ids()[0]
    body=cal.get_bytes(aid);assert digest(body)==cal.get_manifest(aid)['sha256']
    calendar=json.loads(body);expected={r['date']for r in calendar}
    fixture={r[''][:10]:r for r in csv.DictReader(calendar_fixture.open())}
    matched=0
    for r in calendar:
        if r['date'] not in fixture:continue
        for field in ('open','close'):
            observed=datetime.fromisoformat(r['date']+'T'+r[field]).replace(tzinfo=ZoneInfo('America/New_York'))
            reference=datetime.fromisoformat(fixture[r['date']][field].replace('Z','+00:00'))
            assert observed==reference
        matched+=1
    # Boundaries supported by original issuer/SEC documents; preserve all originals.
    # Cross-sectional universe membership and split/cash ledgers are not established here.
    rules={'BKTI':[('RWC',START,'2018-06-04'),('BKTI','2018-06-05',END)],
           'CECO':[('CECE',START,'2022-11-04'),('CECO','2022-11-07',END)]}
    coverage=[]
    for cik,symbol,_,historical in FIXED:
        parts=rules.get(symbol,[(symbol,START,END)])
        observations={}
        for alias,a,b in parts:
            for day,row in by_symbol[alias].items():
                if a<=day<=b:
                    assert day not in observations
                    observations[day]=row
        actual=set(observations);missing=sorted(expected-actual)
        rec={'cik':cik,'symbol':symbol,'request_start':START,'request_end':END,'rows':len(actual),
             'first':min(actual,default=None),'last':max(actual,default=None),'expected_market_days':len(expected),
             'missing_market_days':len(missing),'missing_dates':missing,'internal_missing_dates':[d for d in missing if min(actual)<=d<=max(actual)],
             'pagination_complete':all(next(x for x in details if x['symbol']==a)['pagination_complete']for a,_,_ in parts),
             'alias_intervals':parts,'terminal_cash_settlement_verified':False,'formal_bt_eligible':False}
        if symbol=='AE':rec['absence_reason']='MERGER_TRADING_CEASED_BEFORE_2025_02_05_OPEN_SEC_8K'
        elif symbol=='IDSA':rec['absence_reason']='DISSOLUTION_AND_FORM25_CONFIRMED_EXACT_TRADING_STOP_AND_FINAL_DISTRIBUTIONS_PENDING'
        else:rec['absence_reason']='NONE_IN_REQUESTED_MARKET_CALENDAR'
        coverage.append(rec)
    overlap=by_symbol['CECE'].keys()&by_symbol['CECO'].keys()
    quarantine=[d for d in by_symbol['CECO']if d<'2022-11-07']
    report={'new_raw_hashes_verified':hashes,'actual_pages_verified':pages,'numeric_cells_verified':numeric,
            'terminal_pages':terminal_pages,'pages_with_continuation':pages-terminal_pages,
            'normalized_alias_rows':sum(len(r)for r in by_symbol.values()),'reused_rows':len(reused),
            'calendar_sessions':len(expected),'calendar_cross_source_sessions_checked':matched,
            'ceco_pre_change_quarantined_rows':len(quarantine),'cece_ceco_overlap_rows':len(overlap),
            'cece_ceco_identical_overlap_ohlcv':sum(by_symbol['CECE'][d]['raw']==by_symbol['CECO'][d]['raw']for d in overlap),
            'issuer_window_rows':sum(r['rows']for r in coverage),'coverage':coverage,'formal_backtests':0}
    output.write_bytes(encoded(report))
    return {k:v for k,v in report.items()if k!='coverage'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('restored','old-alpaca','old-kis','calendar-fixture','events','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.restored,a.old_alpaca,a.old_kis,a.calendar_fixture,a.events,a.output),sort_keys=True))
