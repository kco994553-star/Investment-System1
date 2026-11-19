"""Chart prerequisite regressions: complete series, bounded reads and no formulas in JS."""
from copy import deepcopy
from datetime import date, timedelta
import importlib
import json
from pathlib import Path
import subprocess

import pytest

from investment_system.research._private_artifacts import json_bytes
from investment_system.research.exp_deciles import schedule


def api():
    assert importlib.util.find_spec('investment_system.research.kis_stock_bundle'), 'stock bundle producer missing'
    return importlib.import_module('investment_system.research.kis_stock_bundle')


def chart(n=140, *, held=False, start=date(2025, 1, 2)):
    days=[];d=start
    while len(days)<n:
        if schedule.is_session(d):days.append(d.isoformat())
        d+=timedelta(days=1)
    rows=[dict(date=d,open='10',high='11',low='9',close='10',volume='100',amount='1000') for d in days]
    return dict(schema='kis-bars/1',symbol='SYN',basis='RAW',currency='USD',splits=[],
                raw_bars=rows,bars=deepcopy(rows),dividend_adjustment='NONE',
                display=dict(state='WITHHELD' if held else 'AVAILABLE',validation_tier='UNVERIFIED_REFERENCE',
                             label='검증 전(참고)',official=False,hold_reasons=['SYNTHETIC_HOLD'] if held else []))


def latest():
    return dict(technical=dict(metrics={},display=chart()['display']),measures=dict(metrics={}))


def test_series_hand_values_warmup_undefined_rsi_and_full_history_seed():
    m=api();c=chart();s=m.indicator_series(c,evaluation_day=c['bars'][-1]['date'])
    by={k:i for i,k in enumerate(s['fields'])}
    assert len(s['rows'])==140 and len(by)==10
    assert s['rows'][18][by['SMA_20']] is None and s['rows'][19][by['SMA_20']]==10
    assert s['rows'][118][by['SMA_120']] is None and s['rows'][119][by['SMA_120']]==10
    assert s['rows'][-1][by['BOLL_UPPER_20_2']]==10
    assert s['rows'][-1][by['RSI_14']] is None  # zero total change is undefined, not 50
    assert s['rows'][32][by['MACD_SIGNAL_9']] is None
    assert s['rows'][33][by['MACD_SIGNAL_9']]==0
    assert s['validation_tier']=='UNVERIFIED_REFERENCE' and not s['adopted_values_included']


def test_series_holds_gap_volume_only_missing_and_no_future_leak():
    m=api();c=chart(held=True)
    s=m.indicator_series(c,evaluation_day=c['bars'][-1]['date'])
    assert all(v is None for row in s['rows'] for v in row)
    c=chart();c['bars'][30]['volume']=None;c['raw_bars'][30]['volume']=None
    s=m.indicator_series(c,evaluation_day=c['bars'][-2]['date'])
    assert len(s['rows'])==139 and s['rows'][30][0]==10
    del c['bars'][40];del c['raw_bars'][40]
    s=m.indicator_series(c,evaluation_day=c['bars'][-1]['date'])
    assert s['rows'][39][0]==10 and all(v is None for row in s['rows'][40:] for v in row)
    assert any(r['reason']=='PRICE_WINDOW_INCOMPLETE' for r in s['reason_runs'])


def source(c):
    m=api();end=c['bars'][-1]['date']
    yield 'chart/S/SYN.json',json_bytes(c)
    yield 'technical/S/SYN.json',json_bytes(latest()['technical'])
    yield 'measures/S/SYN.json',json_bytes(latest()['measures'])
    yield 'indicator-series/S/SYN.json',json_bytes(m.indicator_series(c,evaluation_day=end))
    yield 'qgv/latest.json',json_bytes(dict(schema='kis-qgv/1',calculated_at=end+'T23:00:00Z',
                    rows={'ROW':{'total':None}},population=['ROW'],private_raw_detail={}))


def test_one_symbol_load_covers_every_period_with_at_most_twelve_fetches():
    m=api();c=chart(1260,start=date(2020,11,2));day=c['bars'][-1]['date']
    files=m.stock_bundle(source(c),evaluation_day=day)
    fetched=[]
    def fetch(path):fetched.append(path);return files[path]
    view=m.assemble_stock(fetch,'SYN')
    assert len(fetched)<=12 and len(set(fetched))==len(fetched)
    assert len(view['rows'])==1260 and len(view['fields'])==17
    assert view['rows'][0][1]=='10'
    assert view['latest']==latest()
    assert view['rows'][-1][7]==10
    assert len(json_bytes(view))<2*1024*1024
    assert view['coverage']['scope']=='ALL_RETAINED_SESSIONS'


def test_all_is_not_silently_truncated_to_five_years_and_closed_pieces_immutable():
    m=api();c=chart(1600,start=date(2019,1,2));day=c['bars'][-1]['date']
    a=m.stock_bundle(source(c),evaluation_day=day)
    view=m.assemble_stock(a.__getitem__,'SYN')
    assert len(view['rows'])==1600 and view['coverage']['retained_sessions']==1600
    previous=json.loads(a['writer-manifest.json']);c['bars'][0]['close']='10.5';c['raw_bars'][0]['close']='10.5'
    with pytest.raises(ValueError,match='IMMUTABLE_PIECE_CHANGED'):
        m.stock_bundle(source(c),evaluation_day=day,previous=previous)
    revised=m.stock_bundle(source(c),evaluation_day=day,previous=previous,revision_reference='SYNTHETIC_REVIEW')
    assert json.loads(revised['writer-manifest.json'])['reviewed_revisions']['reference']=='SYNTHETIC_REVIEW'
    replay=m.stock_bundle(source(c),evaluation_day=day,previous=json.loads(revised['writer-manifest.json']))
    assert replay==revised


def test_mismatched_series_piece_hash_partial_and_previous_budget_are_rejected():
    m=api();c=chart();day=c['bars'][-1]['date'];a=m.stock_bundle(source(c),evaluation_day=day)
    manifest=json.loads(a['writer-manifest.json']);bad=deepcopy(a)
    item=next(x for x in manifest['files'] if x['path'].startswith('stock/pieces/'))
    bad[item['path']]+=b' '
    with pytest.raises(ValueError,match='STOCK_FILE_PIN'):m.assemble_stock(bad.__getitem__,'SYN')
    del bad[item['path']]
    with pytest.raises(KeyError):m.assemble_stock(bad.__getitem__,'SYN')
    with pytest.raises(ValueError,match='PREVIOUS_STOCK_CONTRACT'):
        m.stock_bundle(source(c),evaluation_day=day,previous={})
    previous=json.loads(a['writer-manifest.json']);previous['growth_ledger']['charged_bytes']=260000000
    c['bars'][-1]['close']='10.5';c['raw_bars'][-1]['close']='10.5'
    with pytest.raises(ValueError,match='ANNUAL_DATA_BUDGET'):
        m.stock_bundle(source(c),evaluation_day=day,previous=previous)


def test_series_split_basis_is_confirmed_only_and_matches_supplied_adjusted_rows():
    m=api();c=chart();split=c['bars'][70]['date']
    c['splits']=[dict(date=split,ratio='2',status='CONFIRMED',evidence='SYNTHETIC')]
    c['basis']='SPLIT_ADJUSTED'
    from investment_system.research.kis_price_bridge import price_rows
    c['bars']=price_rows(c,c['raw_bars'][-1]['date'])
    s=m.indicator_series(c,evaluation_day=c['bars'][-1]['date'])
    assert s['rows'][69][0]==5 and s['rows'][89][0]==10
    c['source_query']={'MODP':'1'}
    with pytest.raises(ValueError,match='RAW_DAILY_SOURCE_REQUIRED'):
        m.indicator_series(c,evaluation_day=c['bars'][-1]['date'])


def test_year_quarter_month_rollover_reuses_closed_bytes_and_identical_replay():
    m=api();c=chart(1260,start=date(2020,10,1));day=c['bars'][-1]['date']
    a=m.stock_bundle(source(c),evaluation_day=day)
    writer=json.loads(a['writer-manifest.json'])
    b=m.stock_bundle(source(c),evaluation_day=day,previous=writer)
    assert a==b
    # Every possible end-month in a six-calendar-year slice stays bounded.
    for month in range(1,13):
        dates=[f'{year}-{mo:02d}-15' for year in range(2020,2026) for mo in range(1,13)
               if f'{year}-{mo:02d}-15'<=f'2025-{month:02d}-15' and
               f'{year}-{mo:02d}-15'>=f'2020-{month:02d}-15']
        assert len({m._period(d,f'2025-{month:02d}-15') for d in dates})<=10


def test_node_reference_reads_same_single_response_and_rejects_pin_mismatch():
    m=api();c=chart();files=m.stock_bundle(source(c),evaluation_day=c['bars'][-1]['date'])
    module=(Path(__file__).parents[2]/'src/investment_system/research/kis_stock_reader.mjs').as_uri()
    assert Path(module.removeprefix('file://')).exists(), 'stock consumer reference missing'
    script='''import {readStock} from MODULE;
let raw='';for await(const c of process.stdin)raw+=c;
const files=JSON.parse(raw);let requests=0;
const fetch=async p=>{requests++;return new TextEncoder().encode(files[p]);};
const result=await readStock(fetch,'SYN');
const path=Object.keys(files).find(p=>p.startsWith('stock/pieces/'));
files[path]+=' ';let rejected=false;
try{await readStock(fetch,'SYN');}catch(e){rejected=e.message==='STOCK_FILE_PIN';}
console.log(JSON.stringify({result,requests,rejected}));
'''.replace('MODULE',json.dumps(module))
    run=subprocess.run(['node','--input-type=module','-e',script],input=json.dumps({k:v.decode() for k,v in files.items()}),
                       text=True,capture_output=True)
    assert run.returncode==0,run.stderr
    out=json.loads(run.stdout)
    assert out['result']==m.assemble_stock(files.__getitem__,'SYN') and out['rejected']


def test_storage_filename_is_not_a_provider_symbol_alias():
    m=api();c=chart();c['symbol']='SYN/A'
    def payloads():
        for p,b in source(c):
            v=json.loads(b)
            if p.startswith(('technical/','measures/')):v['symbol']='SYN/A';b=json_bytes(v)
            yield p,b
    files=m.stock_bundle(payloads(),evaluation_day=c['bars'][-1]['date'])
    assert m.assemble_stock(files.__getitem__,'SYN/A')['symbol']=='SYN/A'
    with pytest.raises((KeyError,StopIteration)):
        m.assemble_stock(files.__getitem__,'SYN_A')


def test_public_fixture_has_real_pins_and_hand_checked_chart_values():
    p=Path(__file__).parents[1]/'fixtures/kis-stock-wire-v1.json'
    fixture=json.loads(p.read_bytes());calls=[]
    def fetch(path):calls.append(path);return fixture['files'][path].encode()
    v=api().assemble_stock(fetch,'SYN')
    assert len(calls)==5 and len(v['rows'])==140 and len(v['fields'])==17
    assert v['rows'][-1][7]==10 and v['rows'][-1][-2]==0
    assert v['rows'][-1][13] is None

