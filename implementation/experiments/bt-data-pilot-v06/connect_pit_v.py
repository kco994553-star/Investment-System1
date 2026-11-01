"""Actual fixed-ten factor-input audit. Unchanged canonical QGV v2 formulas.

No population ranks are inferred from the ten-name convenience sample. Raw
valuation metrics, basis validation and publication-time proof are separate.
All financial/price/output values and complete lineage are private artifacts.
"""
import argparse
from collections import Counter
from copy import deepcopy
import csv
from datetime import datetime, date, timezone
from decimal import Decimal
import hashlib
import html
import io
import json
from pathlib import Path
import re
import sys
import zipfile
from zoneinfo import ZoneInfo

from pilot import ROOT, encoded, private_dir, RawDatasetStore, digest
from github_kis_probe import FIXED
from investment_system.qgv import v2_factors, qgv_v2, qgv2_inputs
from investment_system.qgv import playbook
from investment_system.qgv.dcf_parameters import load_default_dcf_parameters

SIGNAL = '2016-04-01'
NY = ZoneInfo('America/New_York')
DEFINITIONS = {
 'v_earnings_yield': ('EBIT / (raw_close * weighted_average_diluted_shares + debt - cash)', ['ebit','diluted_shares','total_debt','cash'], 'ebit_yield'),
 'v_fcf_yield': ('(OCF - capex) / (raw_close * weighted_average_diluted_shares + debt - cash)', ['fcf','diluted_shares','total_debt','cash'], 'fcf_yield'),
 'v_vs_industry': ('percentile(EBIT/EV, eligible industry peers; canonical fallback)', ['ebit','diluted_shares','total_debt','cash','historical_peer_population'], None),
 'v_vs_own_history': ('percentile(current EBIT/share/price, >=3 historical fiscal-year-end month yields plus current)', ['ebit','diluted_shares','ebit_per_share_history','aligned_historical_month_prices'], 'own_history'),
 'v_expectation_check': ('reverse_DCF(FCF/diluted_shares,raw_close,approved_parameters) - revenue_CAGR_3y', ['fcf','diluted_shares','revenue_cagr_3y'], 'gap'),
}


def text_of(path):
    return ' '.join(html.unescape(re.sub('<[^>]+>', ' ', path.read_text())).split())


def filings_for(prior, cik):
    main = json.loads((prior/'store/blobs'/f'submissions__{cik:010d}').read_bytes())
    sources = [main['filings']['recent']]
    h = prior/'store/blobs'/f'history__{cik}'
    if h.exists(): sources.append(json.loads(h.read_bytes()))
    filings = {}
    for data in sources:
        for i, accn in enumerate(data['accessionNumber']):
            item = {k: data[k][i] for k in ('filingDate','acceptanceDateTime','form','primaryDocument')}
            if accn in filings and filings[accn] != item: raise ValueError('FILINGS_CONFLICT')
            filings[accn] = item
    return filings


def main(args):
    import investment_system, investment_system.research
    investment_system.__path__.append(str(args.reviewed_src/'investment_system'))
    investment_system.research.__path__.append(str(args.reviewed_src/'investment_system/research'))
    from investment_system.research.qgv_backtest.pit_adapter import filter_companyfacts, quotes_as_of
    from investment_system.research.qgv_backtest.calendar_adapter import Session, VerifiedSessionCalendar
    out = private_dir(args.output)
    for folder, ids in ((args.sources/'sources', ('abt-official-split-history','abt-2016-cusip')),
                        (args.abt_evidence/'store', ('abt_2015_10k','abt_2015_10k_index'))):
        store = RawDatasetStore(folder)
        for artifact_id in ids:
            assert digest(store.get_bytes(artifact_id)) == store.get_manifest(artifact_id)['sha256']
    cal_store = args.prices/'summary/calendar'
    cp = next((cal_store/'blobs').glob('*'))
    cal_data = json.loads(cp.read_bytes())
    sessions = [Session(r['date'],datetime.fromisoformat(r['date']+'T'+r['open']).replace(tzinfo=NY),
                        datetime.fromisoformat(r['date']+'T'+r['close']).replace(tzinfo=NY)) for r in cal_data]
    calendar = VerifiedSessionCalendar(sessions, coverage_start='2016-01-01',coverage_end='2026-10-30',source='ALPACA_READONLY_CALENDAR_ACTUAL_RESPONSE')
    decision = calendar.session(SIGNAL).close_at
    next_session = next(s for s in sessions if s.day > date.fromisoformat(SIGNAL))
    with zipfile.ZipFile(args.sec/'2016q1.zip') as z:
        subs = list(csv.DictReader(io.TextIOWrapper(z.open('sub.txt')),delimiter='\t'))
    sic = {}
    for row in sorted(subs,key=lambda r:(r['filed'],r['adsh'])):
        if row['filed'] < SIGNAL.replace('-',''): sic[int(row['cik'])] = row
    matrix, details, yearly = [], {}, []
    receipt_by_cik={int(r['cik']):r for r in json.loads((args.sec/'companyfacts-receipts.json').read_bytes())}
    for cik, symbol, exchange, historical in FIXED:
        assert hashlib.sha256((args.sec/f'companyfacts-{cik}.json').read_bytes()).hexdigest()==receipt_by_cik[cik]['stored_payload_sha256']
        original = json.loads((args.sec/f'companyfacts-{cik}.json').read_bytes())
        enriched = deepcopy(original)
        filings = filings_for(args.prior,cik)
        for tags in enriched['facts'].values():
            for node in tags.values():
                for rows in node.get('units',{}).values():
                    for row in rows:
                        filing = filings.get(row.get('accn'))
                        row['accepted'] = filing['acceptanceDateTime'] if filing else 'UNVERIFIED_ACCEPTANCE'
        filtered = filter_companyfacts(enriched,SIGNAL,decision_at=decision)
        diagnostic = {}
        profile, fy, currency, metrics, vi = v2_factors.compute(filtered.payload,sic=sic[cik]['sic'],cutoff=filtered.cutoff,diagnostics=diagnostic)
        inputs, periods = qgv2_inputs._v_inputs(vi)
        fact_reader = v2_factors._Facts(filtered.payload,'us-gaap',currency,filtered.cutoff)
        annual_lineage = {}
        for item in ('ebit','operating_cash_flow','capital_expenditure','diluted_shares','revenue'):
            for year in (2012,2015):
                at = date(year,12,31)
                hit = fact_reader.annual(item,at)
                origin = fact_reader.annual_filing(item,at)
                if hit:
                    annual_lineage[f'{item}:{year}'] = {'value':hit[0],'start':hit[1].isoformat(),'end':hit[2].isoformat(),
                        'accn':origin[0] if origin else None,'filed':origin[1].isoformat() if origin else None,
                        'acceptance':filings.get(origin[0],{}).get('acceptanceDateTime') if origin else None}
        source_rows = json.loads((args.prices/historical/'normalized.json').read_bytes())
        bar = next(r for r in source_rows if r['session_date']==SIGNAL)
        quote = {'price':bar['raw']['close'],'currency':'USD','month_closes':{}}
        company = {'profile':profile,'v_inputs':inputs}
        code = 'US:'+historical
        cyclical = qgv2_inputs.cyclical_basis({'records':{code:{'sic':sic[cik]['sic'],'metrics':metrics}}},playbook.load_config()).get(code)
        type_config = json.loads((ROOT/'src/investment_system/qgv/type_config_v1.json').read_bytes())
        years = type_config['value_basis']['normalized_years'] if cyclical else None
        raw = qgv_v2._metrics(company,quote,load_default_dcf_parameters(),years)
        # Trace only; never treat a raw yield as its population percentile score.
        selected = []
        needed_tags = set(t for item in ('ebit','operating_cash_flow','capital_expenditure','diluted_shares','cash_and_equivalents',
                                        'debt_total_long_term','debt_noncurrent','debt_short_term','revenue')
                          for t in v2_factors.CONCEPTS['us-gaap'].get(item,()))
        for tax,tags in filtered.payload['facts'].items():
            for tag,node in tags.items():
                if tag not in needed_tags: continue
                for unit,rows in node.get('units',{}).items():
                    for row in rows:
                        if row.get('end')==fy:
                            selected.append({'taxonomy':tax,'tag':tag,'unit':unit,**row})
        details[symbol] = {'cik':cik,'query_symbol':historical,'profile':profile,'signal':SIGNAL,'decision_at':decision.isoformat(),
            'next_tradable_open':next_session.open_at.isoformat(),'calc_version':v2_factors.CALC_VERSION,'fiscal_end':fy,
            'diagnostics':diagnostic,'v_inputs_v2':vi,'flat_inputs':inputs,'periods':periods,'actual_bar':bar,
            'raw_metrics':raw,'cyclical_basis':cyclical,'canonical_annual_lineage':annual_lineage,
            'selected_financial_candidates':selected,'pit_rejected_counts':filtered.rejected,
            'filing_acceptance_verified_count':len(filings),'original_financial_sha256':hashlib.sha256((args.sec/f'companyfacts-{cik}.json').read_bytes()).hexdigest()}
        for factor,(formula,required,key) in DEFINITIONS.items():
            required = list(required)
            if cyclical and factor in ('v_earnings_yield','v_vs_industry'):
                required.remove('ebit')
                required += ['revenue','operating_margin_history']
                formula = formula.replace('EBIT /','(revenue * mean(last_5_operating_margins)) /').replace('EBIT/EV','normalized_EBIT/EV')
            missing = [k for k in required if not inputs or inputs.get(k) is None or inputs.get(k)==[]]
            value = raw.get(key) if key else None
            matrix.append({'cik':cik,'symbol':symbol,'factor':factor,'formula':formula,'required_financial':required,
                'price_acquired':True,'price_basis':'RAW_SIP','requires_diluted_shares':True,
                'shares_basis':'LATEST_FILED_WEIGHTED_AVERAGE_DILUTED_NOT_OUTSTANDING',
                'shares_period_end':(vi.get('diluted_shares')or{}).get('period_end'),
                'shares_accession':diagnostic.get('diluted_shares',{}).get('accn'),
                'identity_status':'ABT_SINGLE_CLASS_EVIDENCE' if cik==1800 else 'COMPANY_SECURITY_MAPPING_PENDING',
                'financial_availability':'ACTUAL_SUBMISSIONS_ACCEPTANCE_FILTER',
                'price_publication_at':None,'price_event_time_convention':decision.isoformat(),
                'missing_inputs':missing,'raw_metric_calculated':value is not None,'raw_metric_value':value,
                'raw_reason':raw['reasons'].get(key) if key else 'HISTORICAL_PEER_POPULATION_NOT_VERIFIED',
                'official_percentile_score_calculated':False,'pit_eligible':False})
        # Annual financial availability, NOT eleven years of factor computation.
        all_fact_rows = [r for tags in enriched['facts'].values() for tag,n in tags.items() if tag in needed_tags
                         for rr in n.get('units',{}).values() for r in rr]
        for year in range(2015,2027):
            cutoff = f'{year}-12-31' if year<2026 else '2026-10-30'
            eligible = [r for r in all_fact_rows if r.get('filed','9999') < cutoff and r.get('end','9999')<=cutoff
                        and r.get('accepted')!='UNVERIFIED_ACCEPTANCE' and r['accepted'][:10]<=cutoff]
            year_filings = {r['accn'] for r in eligible if r.get('filed','')[:4]==str(year)}
            yearly.append({'cik':cik,'symbol':symbol,'year':year,'asof':cutoff,'accepted_facts':len(eligible),
                'accepted_filings_in_year':len(year_filings),'newest_financial_period':max((r.get('end','') for r in eligible),default=None),
                'full_year_v_computed':False,'formal_bt_eligible':False})
    # ABT independent arithmetic check and actual share-basis evidence.
    abt = details['ABT']; v=abt['flat_inputs']; p=abt['actual_bar']['raw']['close']
    ev = Decimal(str(p))*Decimal(str(v['diluted_shares']))+Decimal(str(v['total_debt']))-Decimal(str(v['cash']))
    for numerator,metric in (('ebit','ebit_yield'),('fcf','fcf_yield')):
        assert abs(float(Decimal(str(v[numerator]))/ev)-abt['raw_metrics'][metric]) < 1e-14
    split_text = text_of(args.sources/'sources/blobs/abt-official-split-history')
    tail = split_text.split('Stock Split History')[-1].split('Quick Links')[0]
    split_dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}',tail)
    assert split_dates and max(datetime.strptime(x,'%m/%d/%Y').date() for x in split_dates)==date(1998,5,29)
    annual = text_of(args.abt_evidence/'store/blobs/abt_2015_10k')
    assert 'Common Shares, Without Par Value New York Stock Exchange' in annual
    share_diag = abt['diagnostics']['diluted_shares']
    accn = share_diag['accn']; filing = filings_for(args.prior,1800)[accn]
    identity_text = text_of(args.sources/'sources/blobs/abt-2016-cusip')
    assert '002824100' in identity_text and 'Abbott Laboratories' in identity_text and 'Common Stock' in identity_text
    security = 'CUSIP:002824100'
    alignment = {'status':'VERIFIED','source':'ABT_2015_10K_PLUS_ISSUER_SPLIT_HISTORY',
        'signal_day':SIGNAL,'verified_through':SIGNAL,'shares_period_end':abt['v_inputs_v2']['diluted_shares']['period_end'],
        'shares_basis_date':filing['filingDate'],'shares_filing_accn':accn,'price_to_shares_factor':1.0,'split_events':[]}
    candidate = {'security_id':security,'date':SIGNAL,'close':p,'currency':'USD','price_basis':'RAW','shares_basis':'RAW',
        'basis_alignment':alignment,'known_at':None,'assumed_available_at':decision.isoformat()}
    accepted = quotes_as_of([candidate],SIGNAL,calendar=calendar)
    assert security in accepted
    abt['basis_check'] = {'price_to_shares_factor':1.0,'strict_adapter_accepted':True,'share_period_age_days':(date.fromisoformat(SIGNAL)-date.fromisoformat(alignment['shares_period_end'])).days,
        'filing_age_days':(date.fromisoformat(SIGNAL)-date.fromisoformat(filing['filingDate'])).days,'filing':filing,
        'point_security_id':security,'point_security_id_verified':True,'global_permanent_security_master_verified':False,
        'price_publication_timestamp_verified':False,'historical_quote_revision_policy_verified':False,
        'full_pit_eligible':False,'reason':'RECONSTRUCTED_INPUTS_PASS_ADAPTER_BUT_PRICE_PUBLICATION_AND_VINTAGE_NOT_PROVEN'}
    for row in matrix:
        row['research_pit_adapter_eligible']=row['symbol']=='ABT' and row['raw_metric_calculated']
        row['pit_scope']='RECONSTRUCTED_AS_OF_EXISTING_ADAPTER_NOT_VENDOR_VINTAGE_REPLAY'
        row['pit_blockers']=(['EXACT_PRICE_PUBLICATION_AND_REVISION_VINTAGE_UNVERIFIED'] if row['symbol']=='ABT' else
            ['SECURITY_ID_AND_SPLIT_BASIS_NOT_YET_VERIFIED','EXACT_PRICE_PUBLICATION_AND_REVISION_VINTAGE_UNVERIFIED'])
        if row['symbol']=='ABT': row['basis_adapter_accepted']=True
    (out/'factor-cell-matrix-private.json').write_bytes(encoded(matrix))
    (out/'company-lineage-private.json').write_bytes(encoded(details))
    (out/'financial-year-coverage.json').write_bytes(encoded(yearly))
    summary={'version':'BT-DATA-PILOT v0.6','signal':SIGNAL,'slots':50,
        'raw_metrics_calculated':sum(r['raw_metric_calculated']for r in matrix),'official_factor_scores_calculated':0,
        'fully_pit_eligible':0,'basis_adapter_accepted_companies':1,
        'research_pit_adapter_eligible_raw_metric_slots':sum(r['research_pit_adapter_eligible']for r in matrix),
        'by_company':{s:sum(r['raw_metric_calculated']for r in matrix if r['symbol']==s)for s in details},
        'formal_backtests':0,'synthetic_data_used':False,'population_ranks_generated':False}
    (out/'aggregate.json').write_bytes(encoded(summary))
    source_paths = [ROOT/'src/investment_system/qgv'/n for n in ('v2_factors.py','qgv_v2.py','qgv2_inputs.py','dcf_parameters_v1_1_default.json','type_config_v1.json','playbook.py')]
    source_paths += [args.reviewed_src/'investment_system/research/qgv_backtest'/n for n in ('pit_adapter.py','calendar_adapter.py')]
    source_paths += [Path(__file__).resolve()]
    source_paths += [cp,args.sec/'2016q1.zip',args.abt_evidence/'store/blobs/abt_2015_10k',args.abt_evidence/'store/blobs/abt_2015_10k_index']
    source_paths += list((args.sources/'sources/blobs').glob('*'))
    source_paths += [args.sec/f'companyfacts-{cik}.json' for cik,_,_,_ in FIXED]
    source_paths += [args.prior/'store/blobs'/f'submissions__{cik:010d}'for cik,_,_,_ in FIXED]
    source_paths += [args.prior/'store/blobs'/f'history__{cik}'for cik,_,_,_ in FIXED if (args.prior/'store/blobs'/f'history__{cik}').exists()]
    source_paths += [args.prices/'summary/reused-sources.json']
    source_paths += [args.prices/historical/'normalized.json'for _,_,_,historical in FIXED]
    (out/'provenance.json').write_bytes(encoded([{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in source_paths]))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('prices','sec','prior','sources','abt-evidence','reviewed-src','output'):p.add_argument('--'+n,type=Path,required=True)
    print(json.dumps(main(p.parse_args()),sort_keys=True))
