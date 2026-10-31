"""Offline replay of the registered ABT ledger into a PRIVATE Lab candidate.

No network, shared guard changes, published files, or QGV stock selection.
Use existing private results directory pending Main's path/contract agreement.
"""
import argparse
from datetime import date
from decimal import Decimal, localcontext
import importlib
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from audit_v_ledger import actual_calendar, bootstrap, ledger_pilot
from github_alpaca_probe import normalize
from long_prices import dates
from pilot import RawDatasetStore, digest, encoded, put_once, private_dir
from lab_results import loads, require, summarize, validate

HERE=Path(__file__).resolve().parent
ENGINE_COMMIT='ca310378ba4fe40a1a971da30b475d9812c68a15'


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()


def abt_request(meta,start,end):
    if 'request' in meta and meta['request'].get('symbol')!='ABT':return None
    q=meta.get('arguments',meta.get('request',{}))
    if q.get('feed')!='sip' or q.get('adjustment')!='raw':return None
    if 'arguments' in meta:
        a,b=q['start'][:10],q['end'][:10]
        if a>end or b<start:return None
        return {'symbol':'ABT','feed':'sip','adjustment':'raw','days':dates(a,b)}
    return q


def replay_prices(root, calendar, start, end):
    """Reuse existing raw normalizer and compare every requested day's five fields."""
    expected=[s.day.isoformat()for s in calendar.sessions if start<=s.day.isoformat()<=end]
    observed={};inputs=[]
    folders=[root/'long-2016-20261030/restored/ABT',
             root/'github-alpaca-20261031/restored',root/'github-kis-cooldown-20261031/restored']
    for folder in folders:
        store=RawDatasetStore(folder/'store')
        for p in sorted((folder/'requests').glob('*.json')):
            meta=loads(p.read_bytes());r=meta.get('receipt',{});req=abt_request(meta,start,end)
            if req is None:continue
            require(bool(r.get('sha256')),'unacquired required response')
            body=store.get_bytes(r['artifact_id']);require(digest(body)==r['sha256'],'raw hash mismatch')
            data=loads(body)
            parsed=normalize(encoded(dict(data,next_page_token=None)),req)
            for row in parsed:
                day=row['session_date']
                if day not in expected:continue
                if day in observed:require(observed[day]['raw']==row['raw'],'conflicting source bars')
                observed[day]=row
            inputs.extend([p,folder/'store/blobs'/r['artifact_id']])
    require(sorted(observed)==expected,'raw price coverage incomplete')
    saved_path=root/'long-2016-20261030/restored/ABT/normalized.json'
    saved={r['session_date']:r for r in loads(saved_path.read_bytes())}
    for d in expected:require(saved[d]['raw']==observed[d]['raw'],'normalization changed')
    return saved,inputs+[saved_path]


def run(a):
    repo=Path(git(HERE,'rev-parse','--show-toplevel'))
    require(not git(repo,'status','--porcelain','--untracked-files=no'),'commit research changes before run')
    source_commit=git(repo,'rev-parse','HEAD')
    for name in ('export_lab_pilot.py','lab_results.py','LAB_PILOT_REGISTER_20261031.json'):
        git(repo,'cat-file','-e',source_commit+':'+str((HERE/name).relative_to(repo)))
    engine_root=Path(git(a.reviewed_src,'rev-parse','--show-toplevel'))
    require(git(engine_root,'rev-parse','HEAD')==ENGINE_COMMIT,'engine revision mismatch')
    require(not git(engine_root,'status','--porcelain','--untracked-files=no'),'engine worktree dirty')
    out=a.private_root/'v-ledger-audit/results'
    require(out.is_dir(),'reuse existing private results directory; do not create a new location')
    out=private_dir(out)
    bootstrap(a.reviewed_src)
    metrics=importlib.import_module('investment_system.research.qgv_backtest.metrics')
    plan_path=HERE/'LAB_PILOT_REGISTER_20261031.json';plan=loads(plan_path.read_bytes())
    start,end=(plan['period'][k]for k in ('start','end'))
    prices=a.private_root/'long-2016-20261030/restored'
    calendar=actual_calendar(prices)
    sip,inputs=replay_prices(a.private_root,calendar,start,end)
    source_root=a.private_root/'v-ledger-audit';sources=RawDatasetStore(source_root/'sources')
    history_store=RawDatasetStore(a.private_root/'pit-v-link/sources')
    history_id='abt-official-split-history';history_body=history_store.get_bytes(history_id)
    require(digest(history_body)==history_store.get_manifest(history_id)['sha256'],'issuer history hash changed')
    history=a.private_root/'pit-v-link/sources/blobs'/history_id
    prior=out/'ledger-private.json'
    # Temporary replay under the existing private location; original result preserved.
    with TemporaryDirectory(prefix='.lab-replay-',dir=out) as temp:
        ledger_pilot(calendar,sip,sources,history,source_root/'finra-17-19.txt',Path(temp))
        replay=(Path(temp)/'ledger-private.json').read_bytes()
    require(replay==prior.read_bytes(),'existing ledger regression mismatch')
    ledger=loads(replay);r=ledger['result'];snapshots=ledger['snapshots']
    require((r['start'],r['sell'])==(start,end),'registered dates changed')
    require(r['cost_bps_each_side']==plan['fee_bps'] and r['slots']==15 and r['occupied_slots']==1,
            'registered allocation or costs changed')
    # No after-the-fact corporate action is used to choose an order.
    require(r['start']<r['buy'] and r['sell_signal']<r['sell'],'noncausal execution dates')
    require(all(e['declared']<e['effective_date']<=e['pay_date'] for e in r['events']),
            'future declaration input')
    expected=[s.day for s in calendar.sessions if start<=s.day.isoformat()<=end]
    result=summarize(snapshots,expected,metrics)
    with localcontext() as ctx:
        ctx.prec=70
        fees=sum((Decimal(f['fee'])for f in r['fills']),Decimal(0))
        expected_fees=sum((Decimal(f['gross'])*Decimal('.001')for f in r['fills']),Decimal(0))
        require(abs(fees-expected_fees)<Decimal('1e-30'),'two-sided fee mismatch')
        gross_final=Decimal(r['final_nav'])+fees
        require(abs(gross_final-Decimal(r['final_nav'])-fees)<Decimal('1e-30'),'cost reconciliation')
    limitations=[
        'Single ABT security from fixed ten-company convenience sample; selection/survivorship bias; no historical market universe.',
        'Ledger diagnostic only: no QGV scoring/selection, no BT-01/02/03 replacement, OOS_NOT_ESTABLISHED.',
        'Retrospective registration of an existing unchanged ledger experiment; not newly untouched holdout data.',
        'One of fifteen slots invested, remainder cash; fractional quantity and zero cash interest are explicit model assumptions.',
        'Raw Alpaca SIP prices; one-way fee 10bps, modeled slippage 0bps (not measured execution quality). No adjusted price plus cash dividend double counting.',
        'Dividend amounts/record/payable schedule OBSERVED; ex dates DERIVED from historical FINRA rule. Exceptional exchange dates not independently excluded; no actual account receipt evidence.',
        'End-of-day signal bar available before next open is reconstructed timing assumption; historical vendor receipt/vintage unavailable; close time is not receipt time.',
        'No split in tested interval per issuer history; delisting/merger settlement not exercised; cannot validate ended securities.',
        'Benchmark is nominal cash without interest, not SPY, a market total-return series, or measured risk-free return.',
        'Daily sample standard deviation times sqrt(252); actual-day CAGR (365.25). Sharpe null: measured RF absent.',
        'Monthly chart first point is initial signal date; later points last available session of month, final month partial. Daily metrics use full daily ledger, not chart samples.',
        'REAL indicates real source inputs, not validated strategy performance. PRIVATE CANDIDATE: Main contract/path agreement and publication rights pending.'
    ]
    record={'id':plan['id'],'name':'ABT 단일 슬롯 장부 파일럿',
        'description':'기존 실제 SIP 원주가·배당 근거로 15칸 중 1칸 매수·보유·청산 장부 재생; QGV 선정 미사용',
        'run_type':'PILOT','data_status':'REAL','validation_status':'NOT_VALIDATED','qgv_version':'v2',
        'universe':{'definition':plan['sample'],'point_in_time':False,
                    'survivorship_note':'Convenience sample selected for input evidence; no PIT market population, no generalization.'},
        'period':plan['period'],'rebalance':'annual',
        'benchmark':{'name':'Nominal USD cash (0 interest diagnostic)','total_return':False},
        'costs':{'fee_bps':plan['fee_bps'],'slippage_bps':plan['slippage_bps']},
        **result,'limitations':limitations}
    doc={'schema_version':'lab-backtest-v1','generated_at':a.generated_at,'source_commit':source_commit,'runs':[record]}
    validate(doc)
    inputs.extend([prior,history,source_root/'finra-17-19.txt',plan_path,
                   a.private_root/'alpaca_terms.pdf',a.private_root/'alpaca_terms.txt'])
    source_receipts=[]
    for store in (sources,history_store,RawDatasetStore(prices/'summary/calendar')):
        for aid in store.list_ids():
            manifest=store.get_manifest(aid);body=store.get_bytes(aid)
            require(digest(body)==manifest['sha256'],'source manifest mismatch')
            source_receipts.append(manifest)
    evidence={'source_commit':source_commit,'engine_commit':ENGINE_COMMIT,'experiment_id':plan['id'],
        'generated_at':a.generated_at,'private_only':True,'contract_agreement':'PENDING_MAIN',
        'replay_command':['python','implementation/experiments/bt-data-pilot-v06/export_lab_pilot.py',
                          '--private-root',str(a.private_root),'--reviewed-src',str(a.reviewed_src),
                          '--generated-at',a.generated_at],
        'input_files':[{'path':str(p),'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size}for p in sorted(set(inputs))],
        'source_receipts':source_receipts,
        'source_files':[{'path':str(p),'sha256':digest(p.read_bytes())}for p in
                        [Path(metrics.__file__),a.reviewed_src/'investment_system/research/qgv_backtest/ledger.py',
                         a.reviewed_src/'investment_system/research/qgv_backtest/calendar_adapter.py',
                         HERE/'audit_v_ledger.py',HERE/'export_lab_pilot.py',HERE/'lab_results.py']],
        'rights':{'provider':'Alpaca Basic SIP','scope':'Personal non-commercial private research',
                  'terms':'https://s3.amazonaws.com/files.alpaca.markets/disclosures/library/TermsAndConditions.pdf',
                  'fee_added':0,'publication':'NOT_CONFIRMED_DO_NOT_PUBLISH'},
        'checks':{'raw_daily_ohlcv_cells':len(expected)*5,'ledger_regression_byte_equal':True,
                  'component_comparisons':r['component_comparisons'],'session_count':len(expected),
                  'source_declared_before_event':True,'prior_close_before_next_open':True,
                  'two_sided_cost_reconciliation':True,'formal_universe_verified':False,
                  'delisting_settlement_tested':False,'independent_ex_date_observation':False},
        'cost_reconciliation':{'fixed_fill_gross_final':str(gross_final),'fees':str(fees),
                               'net_final':r['final_nav'],'method':'FIXED_FILL_COST_ATTRIBUTION_NOT_RESIZED_ZERO_COST_STRATEGY'},
        'daily_snapshots':snapshots}
    result_path=out/'lab-backtest-v1.candidate.json'
    evidence['result_sha256']=digest(encoded(doc))
    put_once(result_path,encoded(doc))
    put_once(out/'lab-backtest-v1.evidence-private.json',encoded(evidence))
    # Never emit financial metrics, curves, raw hashes or prices into public logs.
    return {'private_candidate_runs':1,'run_type':'PILOT','data_status':'REAL',
            'validation_status':'NOT_VALIDATED','daily_sessions':len(expected),
            'result_metrics_nonnull':sum(v is not None for v in result['metrics'].values()),
            'formal_backtests':0,'publication_performed':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--private-root',type=Path,required=True)
    p.add_argument('--reviewed-src',type=Path,required=True)
    p.add_argument('--generated-at',required=True,help='Actual first run timestamp, reuse verbatim for byte-identical replay')
    print(json.dumps(run(p.parse_args()),sort_keys=True))
