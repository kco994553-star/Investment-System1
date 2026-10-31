"""Offline V-contract audit and an actual-input, non-strategy ledger replay.

Reuses canonical QGV functions and the reviewed research ledger/calendar/PIT
adapter. Raw prices and every numerical valuation/ledger result stay private.
"""
import argparse
from copy import deepcopy
import csv
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal, localcontext
from fractions import Fraction
import html
import json
from pathlib import Path
import re
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from connect_pit_v import main as baseline_replay, filings_for, text_of
from pilot import ROOT, RawDatasetStore, digest, encoded, private_dir
from github_kis_probe import kis_normalize
from investment_system.qgv import v2_factors,qgv2_inputs,qgv_v2
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters


def bootstrap(reviewed):
    import investment_system,investment_system.research
    investment_system.__path__.append(str(reviewed/'investment_system'))
    investment_system.research.__path__.append(str(reviewed/'investment_system/research'))


def actual_calendar(prices):
    from investment_system.research.qgv_backtest.calendar_adapter import Session,VerifiedSessionCalendar
    store=RawDatasetStore(prices/'summary/calendar');aid=store.list_ids()[0]
    body=store.get_bytes(aid);assert digest(body)==store.get_manifest(aid)['sha256']
    tz=ZoneInfo('America/New_York')
    sessions=[Session(x['date'],datetime.fromisoformat(x['date']+'T'+x['open']).replace(tzinfo=tz),
        datetime.fromisoformat(x['date']+'T'+x['close']).replace(tzinfo=tz))for x in json.loads(body)]
    return VerifiedSessionCalendar(sessions,coverage_start='2016-01-01',coverage_end='2026-10-30',source='ACTUAL_ALPACA_CALENDAR')


def replay_kis(folders):
    series={};count=0;hashes=set()
    for folder in folders:
        store=RawDatasetStore(folder/'store')
        for p in sorted((folder/'requests').glob('*.json')):
            meta=json.loads(p.read_bytes());q=meta['request'];r=meta.get('receipt',{})
            if q.get('MODP')!='0' or not r.get('sha256'):continue
            body=store.get_bytes(r['artifact_id']);assert digest(body)==r['sha256'];hashes.add(r['sha256'])
            obj=json.loads(body)
            if obj.get('rt_cd')!='0':continue
            originals={x['xymd']:x for x in obj['output2']}
            for row in kis_normalize(body,q['SYMB'],'0',q['BYMD']):
                original=originals[row['session_date'].replace('-','')]
                for field,key in zip(('open','high','low','close','volume'),('open','high','low','clos','tvol')):
                    assert Decimal(str(row['raw'][field]))==Decimal(original[key]);count+=1
                key=(q['SYMB'],row['session_date'])
                if key in series:assert series[key]['raw']==row['raw']
                series[key]={**row,'source_sha256':r['sha256'],'source_url':r['source_url'],
                    'retrieved_at':meta.get('retrieved_at'),'query':q}
    return series,{'unique_raw_hashes':len(hashes),'numeric_replays_including_reused_pages':count}


def enriched_facts(sec,prior,cik):
    receipts={int(x['cik']):x for x in json.loads((sec/'companyfacts-receipts.json').read_bytes())}
    body=(sec/f'companyfacts-{cik}.json').read_bytes();assert digest(body)==receipts[cik]['stored_payload_sha256']
    facts=json.loads(body);filings=filings_for(prior,cik)
    for tags in facts['facts'].values():
        for node in tags.values():
            for rows in node.get('units',{}).values():
                for row in rows:row['accepted']=filings.get(row.get('accn'),{}).get('acceptanceDateTime','UNVERIFIED_ACCEPTANCE')
    return facts,filings


def revenue_trace(payload,filings,fy,currency,cutoff,decision):
    f=v2_factors._Facts(payload,'us-gaap',currency,cutoff);end=date.fromisoformat(fy)
    result=[]
    for year in (end.year-3,end.year):
        at=end.replace(year=year);hit=f.annual('revenue',at);origin=f.annual_filing('revenue',at)
        if not hit or not origin:return {'status':'MISSING_REVENUE_LEG','legs':result}
        filing=filings[origin[0]];accepted=datetime.fromisoformat(filing['acceptanceDateTime'].replace('Z','+00:00'))
        assert origin[1].isoformat()<decision.date().isoformat() and accepted<=decision and hit[2]<=decision.date()
        result.append({'value':hit[0],'start':hit[1].isoformat(),'end':hit[2].isoformat(),
            'accession':origin[0],'filed':origin[1].isoformat(),'accepted':filing['acceptanceDateTime']})
    growth=(result[1]['value']/result[0]['value'])**(1/3)-1 if result[0]['value']>0 and result[1]['value']>0 else None
    return {'status':'TRAILING_PUBLIC_BEFORE_SIGNAL','legs':result,'unrounded_cagr':growth,'future_realized_sales_used':False}


def abt_point(day,calendar,facts,filings,headers,sources,sip,kis):
    from investment_system.research.qgv_backtest.pit_adapter import filter_companyfacts,quotes_as_of
    decision=calendar.session(day).close_at
    header=headers[day];body=sources.get_bytes(header['artifact_id']);assert digest(body)==header['sha256']
    t=' '.join(html.unescape(re.sub('<[^>]+>',' ',body.decode())).split())
    sic=re.search(r'STANDARD INDUSTRIAL CLASSIFICATION:.*?\[(\d{4})\]',t).group(1)
    assert header['filing']['filingDate']<day and sic=='2834'
    pit=filter_companyfacts(facts,day,decision_at=decision);diag={}
    profile,fy,currency,metrics,vi=v2_factors.compute(pit.payload,sic=sic,cutoff=pit.cutoff,diagnostics=diag)
    v,periods=qgv2_inputs._v_inputs(vi);share=diag['diluted_shares'];accn=share.get('accn')
    assert accn and vi['diluted_shares']['value'] is not None
    # Issuer's complete split table: last split 1998; no factor guessed from prices.
    # 2012/pre-spin-off historical observations are excluded, not adjusted synthetically.
    accepted=[];history=[]
    candidates=[(day,sip[day],'ALPACA_SIP')]
    for h in v.get('ebit_per_share_history')or[]:
        month=h['period_end'][:7]
        if month<'2013-01':continue
        pool=kis if month<'2016-01' else sip
        matching=[d for d in pool if d[:7]==month and d<=day]
        if matching:
            d=max(matching);candidates.append((d,pool[d],'KIS_RAW' if month<'2016-01' else 'ALPACA_SIP'))
    for d,bar,provider in candidates:
        alignment={'status':'VERIFIED','source':'ABT_SINGLE_COMMON_CLASS_AND_ISSUER_NO_SPLITS_AFTER_1998',
            'signal_day':day,'verified_through':day,'shares_period_end':vi['diluted_shares']['period_end'],
            'shares_basis_date':filings[accn]['filingDate'],'shares_filing_accn':accn,
            'price_to_shares_factor':1.0,'split_events':[]}
        accepted.append({'security_id':'CUSIP:002824100','date':d,'close':bar['raw']['close'],
            'currency':'USD','price_basis':'RAW','shares_basis':'RAW','basis_alignment':alignment,
            'known_at':None,'assumed_available_at':calendar.session(d).close_at.isoformat() if d>='2016-01-01' else None,
            'is_month_end':d!=day})
        if d!=day:history.append({'date':d,'provider':provider,'close':bar['raw']['close']})
    # Pre-2016 month-end status is independently checked using the preserved XNYS fixture below.
    # quotes_as_of's supplied calendar begins in 2016; it does not infer older sessions.
    # Separate old month-end evidence is passed via is_month_end with calendar=None.
    quote=quotes_as_of(accepted,day)['CUSIP:002824100']
    raw=qgv_v2._metrics({'profile':profile,'v_inputs':v},quote,load_default_dcf_parameters())
    trace=revenue_trace(pit.payload,filings,fy,currency,pit.cutoff,decision)
    if trace.get('unrounded_cagr') is not None:
        assert float(format(trace['unrounded_cagr'],'.6g'))==v['revenue_cagr_3y']
    return {'signal_day':day,'decision_at':decision.isoformat(),'next_open':calendar.next_session(day).open_at.isoformat(),
        'fiscal_end':fy,'v_inputs':v,'periods':periods,'share_diagnostics':share,'raw_metrics':raw,
        'v5_trace':trace,'historical_prices':history,'quote':quote,'as_filed_sic':header,
        'reconstruction_status':'RECONSTRUCTED_AS_OF','vendor_snapshot_replay':'NOT_ESTABLISHED',
        'provider_publication_at':None,'receipt_at_decision_asserted':False,
        'price_availability':'RESEARCH_S_COMPLETED_BAR_FOR_T_OPEN_ASSUMPTION',
        'pre2013_history':'EXCLUDED_SPINOFF_ECONOMIC_BASIS_NOT_BRIDGED'}


def ledger_pilot(calendar,sip,sources,issuer_history,rule_text,out):
    from investment_system.research.qgv_backtest.calendar_adapter import rebalance_schedule
    from investment_system.research.qgv_backtest.ledger import Ledger,Dividend
    a,b=rebalance_schedule(calendar,date(2016,1,1),date(2017,12,31),rebalance='ANNUAL_FEBRUARY')
    record_sources={'2016-04-15':('abt-declare-20160219','2016-02-19'),
        '2016-07-15':('abt-declare-20160610','2016-06-10'),
        '2016-10-14':('abt-declare-20160915','2016-09-15'),
        '2017-01-13':('abt-declare-20161209','2016-12-09')}
    table=issuer_history.read_text();events=[]
    for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',table,re.S|re.I):
        text=' '.join(html.unescape(re.sub('<[^>]+>',' ',tr)).split())
        m=re.fullmatch(r'(\d\d/\d\d/\d{4}) (\d\d/\d\d/\d{4}) \$(\d+\.\d+) Regular Cash',text)
        if not m:continue
        record=datetime.strptime(m[1],'%m/%d/%Y').date();pay=datetime.strptime(m[2],'%m/%d/%Y').date()
        if record.isoformat() not in record_sources:continue
        aid,declared=record_sources[record.isoformat()];body=sources.get_bytes(aid)
        assert digest(body)==sources.get_manifest(aid)['sha256']
        declaration=' '.join(html.unescape(re.sub('<[^>]+>',' ',body.decode())).split())
        assert 'Abbott' in declaration and Decimal(m[3])*100 in [Decimal(x) for x in re.findall(r'(\d+(?:\.\d+)?) cents per share',declaration)]
        months={'Apr':'April','Jul':'July','Oct':'Oct.','Jan':'Jan.','May':'May','Aug':'Aug.','Nov':'Nov.','Feb':'Feb.'}
        def published_date(d):return months[d.strftime('%b')]+' '+str(d.day)+', '+str(d.year)
        assert published_date(record) in declaration and published_date(pay) in declaration
        # Normal cash <25%; pre-2017-09-05 Rule 11140: second business day before record.
        assert record.weekday()==4 and record<date(2017,9,5)
        ex=calendar.previous_session(calendar.previous_session(record).day).day
        assert ex.weekday()==2 and declared<ex.isoformat()
        event=Dividend('ABT:'+record.isoformat(),ex,'CUSIP:002824100',Decimal(m[3]),pay)
        events.append((event,{'record':record.isoformat(),'declared':declared,'source':aid,
            'ex_date_basis':'DERIVED_FROM_ACTUAL_RECORD_DATE_AND_HISTORICAL_FINRA_11140',
            'pay_date_basis':'ISSUER_PUBLISHED_PAYABLE_DATE_NOT_ACCOUNT_RECEIPT'}))
    assert len(events)==4
    assert re.search(r'\[second\]first\s+business day preceding the record date',rule_text.read_text())
    pdf=sources.get_bytes('finra-17-19-pdf')
    assert digest(pdf)==sources.get_manifest('finra-17-19-pdf')['sha256']
    book=Ledger(initial_cash=100000,cost_bps=10);sid='CUSIP:002824100'
    # One occupied slot out of the unchanged N15 allocation; 14 slots remain cash.
    # Frozen ledger test orders, not a QGV selection or strategy return.
    start=a.signal_day;end=b.execution_day
    refcash=Fraction(100000);refqty=Fraction(0);claims={};fees=Fraction(0);paid=Fraction(0)
    target=Fraction(100000)/(15*Fraction(str(sip[start.isoformat()]['raw']['close'])))
    states=[];checks=0;event_checks=0
    def close(x,y):
        with localcontext() as c:
            c.prec=70;expected=Decimal(y.numerator)/Decimal(y.denominator)
            assert abs(x-expected)<Decimal('1e-30')
    for session in calendar.sessions:
        day=session.day
        if not start<=day<=end:continue
        px=sip[day.isoformat()]['raw'];before=book.cash
        for event,evidence in events:
            if event.effective_date==day:
                assert Fraction(str(event.cash_per_share))/Fraction(str(px['close']))<Fraction(1,4)
                book.apply_event(event,day);claims[event.event_id]=refqty*Fraction(event.cash_per_share)
                assert book.cash==before;event_checks+=1
                # Identical event replay must not duplicate entitlement.
                old=dict(book.receivables);book.apply_event(event,day);assert book.receivables==old
        for event,_ in events:
            if event.pay_date==day:
                amount=claims.pop(event.event_id);refcash+=amount;paid+=amount
        book.settle_events(day)
        if day==a.execution_day:
            gross=target*Fraction(str(px['open']));fee=gross/Fraction(1000)
            refcash-=gross+fee;fees+=fee;refqty=target
        if day==b.execution_day:
            gross=refqty*Fraction(str(px['open']));fee=gross/Fraction(1000)
            refcash+=gross-fee;fees+=fee;refqty=Fraction(0)
        if day in (a.execution_day,b.execution_day):
            book.execute_open(day,{sid:px['open']});count=len(book.fills)
            book.execute_open(day,{sid:px['open']});assert len(book.fills)==count
        snap=book.nav(day,{sid:px['close']});assert snap.status=='COMPLETE'
        close(book.cash,refcash);close(book.holdings.get(sid,Decimal(0)),refqty)
        close(snap.receivables,sum(claims.values(),Fraction(0)))
        close(snap.nav,refcash+refqty*Fraction(str(px['close']))+sum(claims.values(),Fraction(0)));checks+=4
        states.append(asdict(snap))
        if day==a.signal_day:book.rebalance(day,[sid],15,{sid:px['close']})
        if day==b.signal_day:book.rebalance(day,[],15,{sid:px['close']})
    with localcontext() as context:
        context.prec=70
        fee_total=sum((x.fee for x in book.fills),Decimal(0))
        dividend_total=Decimal(paid.numerator)/Decimal(paid.denominator)
    close(fee_total,fees)
    assert len(book.fills)==2 and not book.holdings and not book.receivables
    result={'scope':'ACTUAL_INPUT_LEDGER_DIAGNOSTIC_NOT_QGV_STRATEGY','capital':100000,'slots':15,'occupied_slots':1,
        'cost_bps_each_side':10,'cash_interest':'EXPLICIT_ZERO_DIAGNOSTIC_NOT_PRIMARY',
        'start':start.isoformat(),'buy':a.execution_day.isoformat(),'sell_signal':b.signal_day.isoformat(),'sell':end.isoformat(),
        'daily_snapshots':len(states),'component_comparisons':checks,'events':[{**asdict(e),**v}for e,v in events],
        'fills':[asdict(x)for x in book.fills],'final_nav':states[-1]['nav'],'fees':str(fee_total),
        'dividends_received':str(dividend_total),
        'duplicate_event_and_fill_checks':event_checks+2,'all_component_reconciliations_passed':True,
        'actual_account_trades':False,'formal_backtest':False,'oos_established':False}
    (out/'ledger-private.json').write_text(json.dumps({'result':result,'snapshots':states},default=str,sort_keys=True))
    return {k:result[k]for k in ('scope','start','buy','sell_signal','sell','daily_snapshots','component_comparisons','duplicate_event_and_fill_checks','all_component_reconciliations_passed','formal_backtest')}


def main(a):
    bootstrap(a.reviewed_src);out=private_dir(a.output);calendar=actual_calendar(a.prices)
    baseline_replay(SimpleNamespace(prices=a.prices,sec=a.sec,prior=a.prior,sources=a.previous_sources,
        abt_evidence=a.abt_evidence,reviewed_src=a.reviewed_src,output=out/'baseline-replay'))
    base=json.loads((out/'baseline-replay/company-lineage-private.json').read_bytes())
    cells=json.loads((out/'baseline-replay/factor-cell-matrix-private.json').read_bytes())
    sources=RawDatasetStore(a.sources/'sources');headers=json.loads((a.sources/'abt-headers.json').read_bytes())
    from investment_system.research.qgv_backtest.calendar_adapter import rebalance_schedule
    annual=rebalance_schedule(calendar,date(2016,1,1),date(2026,10,30),rebalance='ANNUAL_FEBRUARY')
    quarterly=rebalance_schedule(calendar,date(2016,1,1),date(2016,12,31),rebalance='QUARTERLY')
    assert set(headers)=={x.signal_day.isoformat()for x in annual+quarterly}|{'2016-04-01'}
    sip={r['session_date']:r for r in json.loads((a.prices/'ABT/normalized.json').read_bytes())}
    kis_all,kis_checks=replay_kis([a.old_kis,a.pre2016]);kis={d:r for (s,d),r in kis_all.items()if s=='ABT'}
    overlaps=[d for d in kis if d in sip]
    assert overlaps and all(kis[d]['raw']['close']==sip[d]['raw']['close']for d in overlaps)
    facts,filings=enriched_facts(a.sec,a.prior,1800)
    points={d:abt_point(d,calendar,facts,filings,headers,sources,sip,kis)for d in sorted(headers)}
    # Check every historical month close used, independently of its source's row labels.
    fixture=list(csv.DictReader(a.calendar_fixture.open()));fixture_days=[r[''][:10]for r in fixture]
    for point in points.values():
        for h in point['historical_prices']:
            month=h['date'][:7]
            expected=max((s.day.isoformat()for s in calendar.sessions if s.day.isoformat().startswith(month)),default=None) if month>='2016-01' else max(d for d in fixture_days if d.startswith(month))
            assert h['date']==expected
    traces={}
    for symbol,record in base.items():
        if record['raw_metrics'].get('gap') is None:continue
        from investment_system.research.qgv_backtest.pit_adapter import filter_companyfacts
        f,fl=enriched_facts(a.sec,a.prior,record['cik']);p=filter_companyfacts(f,'2016-04-01',decision_at=calendar.session('2016-04-01').close_at)
        traces[symbol]=revenue_trace(p.payload,fl,record['fiscal_end'],record['flat_inputs']['currency'],p.cutoff,calendar.session('2016-04-01').close_at)
        assert float(format(traces[symbol]['unrounded_cagr'],'.6g'))==record['flat_inputs']['revenue_cagr_3y']
    mapping={'v_earnings_yield':'ebit_yield','v_fcf_yield':'fcf_yield','v_vs_own_history':'own_history','v_expectation_check':'gap'}
    for cell in cells:
        key=mapping.get(cell['factor']);value=cell['raw_metric_value']
        if cell['symbol']=='ABT' and key:value=points['2016-04-01']['raw_metrics'][key]
        cell['calculation_completed']=value is not None;cell['calculated_value_private']=value
        cell['input_admissibility']='CONTRACT_CONFORMANT_RESEARCH_INPUT' if cell['symbol']=='ABT' and value is not None else 'PENDING_CELL_EVIDENCE'
        cell['reconstructed_pit']='PASS_UNDER_EXISTING_RECONSTRUCTED_AS_OF_CONTRACT' if cell['symbol']=='ABT' and value is not None else 'NOT_PASSED'
        cell['contemporaneous_snapshot_replay']='NOT_ESTABLISHED_ADDITIONAL_QUALITY_TIER_NOT_RECONSTRUCTION_GATE'
        cell['population_score']='NOT_CALCULATED'
        cell['self_history_score_calculated']=cell['symbol']=='ABT' and key=='own_history' and value is not None
        cell['vintage_absence_blocks_reconstructed_research']=False
        for legacy in ('pit_eligible','raw_metric_value','raw_metric_computed','pit_blockers','raw_metric_calculated','research_pit_adapter_eligible'):
            cell.pop(legacy,None)
        if cell['symbol']=='ABT' and value is not None:
            cell['missing_inputs']=[]
            cell['raw_reason']=None
        if cell['symbol']=='ABT' and key=='own_history':
            cell['price_basis']='RAW_SIP_CURRENT_KIS_PRE2016_HISTORY_NO_AUTOMATIC_STITCH'
    # Earlier observations remain in baseline-replay; avoid conflicting legacy statuses here.
    (out/'v-cell-audit-private.json').write_bytes(encoded(cells));(out/'abt-points-private.json').write_bytes(encoded(points))
    (out/'v5-traces-private.json').write_bytes(encoded(traces))
    ledger=ledger_pilot(calendar,sip,sources,a.previous_sources/'sources/blobs/abt-official-split-history',a.sources/'finra-17-19.txt',out)
    summary={'version':'BT-DATA-PILOT v0.6','baseline_date':'2016-04-01','baseline_cells':50,
        'baseline_calculation_completed':sum(c['calculation_completed']for c in cells),
        'baseline_reconstructed_pit_pass':sum(c['reconstructed_pit'].startswith('PASS')for c in cells),
        'market_population_scores':0,'contemporaneous_snapshot_replays':0,'actual_abt_evaluation_dates':len(points),
        'abt_calculation_slots':len(points)*5,'abt_calculated_cells':sum(sum(p['raw_metrics'][k]is not None for k in mapping.values())for p in points.values()),
        'abt_ev_shares_changed':False,'v5_future_sales_used':False,'v5_baseline_traces_checked':len(traces),
        'kis_sip_overlap_close_matches':len(overlaps),
        'kis_sip_overlap_field_matches':{f:sum(abs(Decimal(str(kis[d]['raw'][f]))-Decimal(str(sip[d]['raw'][f])))<=Decimal('0.01') for d in overlaps) for f in ('open','high','low','close','volume')},'kis_replay':kis_checks,'ledger':ledger,'formal_backtests':0}
    (out/'aggregate.json').write_bytes(encoded(summary));return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('prices','sec','prior','previous-sources','abt-evidence','reviewed-src','sources','old-kis','pre2016','calendar-fixture','output'):p.add_argument('--'+n,type=Path,required=True)
    print(json.dumps(main(p.parse_args()),sort_keys=True))
