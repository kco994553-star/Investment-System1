from copy import deepcopy
import pytest
from investment_system.research.private_technical_board import board_reader_payload
from test_private_technical_board import board_input


def test_checked_in_screen_fixtures_match_real_reader_and_expected_filters():
    import json,subprocess
    from pathlib import Path
    from investment_system.research.technical_screen_fixtures import fixtures
    root=Path(__file__).parents[2]; folder=Path(__file__).parent/'fixtures/technical_screen_v1'
    cases,expectations=fixtures()
    assert json.loads((folder/'expectations.json').read_text())==expectations
    for name,payload in cases.items():assert json.loads((folder/(name+'.json')).read_text())==payload
    script=r'''const fs=require('fs'),T=require(process.argv[1]);const dir=process.argv[2],E=JSON.parse(fs.readFileSync(dir+'/expectations.json'));let count=0;
for(const [name,e]of Object.entries(E.cases)){const p=JSON.parse(fs.readFileSync(dir+'/'+e.file));if(name==='failed'){if(p!==null)throw Error('failure not null');continue;}
const v=T.validate(p);if(!v.ok)throw Error(JSON.stringify(v));const b=v.value.boards[0].board;
const order=b.metrics.momentum_3m.rows.map(r=>r.security_id);if(JSON.stringify(order)!==JSON.stringify(e.expected_order))throw Error('order '+name);
const r=T.evaluate(b,e.filter),ids=[...r.rows].filter(([,v])=>v.state==='PASS').map(([k])=>k).sort();
if(JSON.stringify(ids)!==JSON.stringify(e.expected_selected_ids))throw Error('filter '+name);for(const k of ['PASS','FAIL','UNKNOWN'])if(r.counts[k]!==e.expected_filter_counts[k])throw Error('counts '+name);
if(b.metrics.volatility_6m.n_valid!==e.valid_volatility_n)throw Error('N '+name);count++;}console.log(count);'''
    r=subprocess.run(['node','-e',script,str(root/'src/investment_system/product/web_app/tech-screen.js'),str(folder)],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert r.stdout.strip()=='5'


def test_regression_february_30_saved_result_is_not_exported():
    from investment_system.research.private_technical_board import build_contract_board
    series,links,group=board_input(1)
    result=build_contract_board(series,group=group,security_links=links)
    result['signal_day']=result['board']['signal_day']='2017-02-30'
    with pytest.raises(ValueError):board_reader_payload(result)

