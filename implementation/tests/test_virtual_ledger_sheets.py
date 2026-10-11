"""Virtual ledger sheet storage v1 (D-10): Python reference of the row format, replay verification and missing-session
plan, checked against the shared SYNTHETIC vectors and the device JS."""
import copy
import hashlib
import json
import random
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from investment_system.qgv import virtual_ledger_sheets as vls  # noqa: E402
from investment_system.qgv import virtual_trading as vt  # noqa: E402
import virtual_ledger_sheets_reference as ref  # noqa: E402

FIXTURE = ROOT / 'tests/fixtures/virtual_ledger_sheets_v1.json'
MODULE = ROOT / 'src/investment_system/product/web_assets/virtual-ledger-sheets.js'


def data():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def test_vectors_are_current_and_synthetic():
    out = subprocess.run([sys.executable, str(ROOT / 'tools/virtual_ledger_sheets_reference.py'), '--check'],
                         capture_output=True, text=True).stdout.strip()
    assert out == 'VIRTUAL_LEDGER_SHEETS_REFERENCE_OK'
    d = data()
    assert d['synthetic'] is True and d['note'].startswith('SYNTHETIC')


def test_python_reproduces_status_vectors():
    cfg, (base, _) = vt.load_config(), ref.base_input()
    for v in data()['statuses']:
        status, inp = vls.ledger_status(copy.deepcopy(v['ledger']), base, v['recorded'], cfg, v['through'])
        assert json.loads(json.dumps(status)) == v['expected'], v['name']
        if v['recorded_sha256']:
            assert hashlib.sha256(vls.inputs_text(inp, status['recorded_through']).encode()).hexdigest() == v['recorded_sha256']


def test_js_equals_python_on_vectors():
    script = r'''
const S=require(process.argv[1]),R=require(process.argv[1].replace('virtual-ledger-sheets.js','virtual-trading-runner.js')),VT=require(process.argv[1].replace('virtual-ledger-sheets.js','virtual-trading.js'));
const fs=require('fs'),crypto=require('crypto');const d=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),inp=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const base=R.assemble(inp.vectors.find(v=>v.name===d.base_vector).inputs).ledgers.SET_A.input,cfg=VT.defaultConfig(),sha=t=>crypto.createHash('sha256').update(t).digest('hex');
const err=f=>{try{return f();}catch(e){return{error:e.message};}};
process.stdout.write(JSON.stringify({
 statuses:d.statuses.map(v=>{const{status,input}=S.ledgerStatus(v.ledger,base,v.recorded,cfg,v.through);return[status,input&&status.recorded_through?sha(S.inputsText(input,status.recorded_through)):null];}),
 numbers:d.numbers.map(([x])=>S.numStr(x)),meta:d.meta.map(v=>S.parseMeta(v.rows)),tabs:d.tabs.map(v=>err(()=>S.parseTab(v.values,S.HEADS[v.tab]))),
 flags:d.flags.map(v=>err(()=>S.parseFlags(v.values))),weights:d.weights.map(v=>S.validateWeights(v.raw,R.IDS)),
 replace:d.replace.map(v=>S.replaceRows(v.meta,v.kind,v.now,cfg,v.payload,v.recorded_last,v.reason))}));
'''
    inputs = ROOT / 'tests/fixtures/virtual_trading_inputs_v1.json'
    out = json.loads(subprocess.run(['node', '-e', script, str(MODULE), str(FIXTURE), str(inputs)], capture_output=True, text=True, check=True).stdout)
    d = data()
    for v, (status, digest) in zip(d['statuses'], out['statuses']):
        assert status == v['expected'], v['name']
        assert digest == v['recorded_sha256'], v['name']
    assert out['numbers'] == [s for _, s in d['numbers']]
    assert out['meta'] == [v['expected'] for v in d['meta']]
    assert out['tabs'] == [v['expected'] for v in d['tabs']]
    assert out['flags'] == [v['expected'] for v in d['flags']]
    assert out['weights'] == [v['expected'] for v in d['weights']]
    assert out['replace'] == [v['expected'] for v in d['replace']]


def test_number_text_matches_js_on_random_doubles():
    rng = random.Random(20261019)
    values = [struct.unpack('<d', struct.pack('<Q', rng.getrandbits(64)))[0] for _ in range(3000)]
    values = [x for x in values if x == x and abs(x) != float('inf')]
    values += [rng.uniform(0, 1e7) for _ in range(2000)] + [round(rng.uniform(0, 5000), 4) * rng.uniform(1, 1500) for _ in range(2000)]
    script = 'const xs=JSON.parse(require("fs").readFileSync(0,"utf8"));process.stdout.write(JSON.stringify(xs.map(x=>String(x))))'
    js = json.loads(subprocess.run(['node', '-e', script], input=json.dumps(values), capture_output=True, text=True, check=True).stdout)
    assert [vls.num_str(x) for x in values] == js


def test_rows_never_write_zero_for_missing_and_respect_start_date():
    d = data()
    for v in d['statuses']:
        for r in v['expected']['append_rows']:
            assert r[1] >= vt.load_config()['start_date']
            if r[2] == 'SUMMARY' and r[6] == 'VALUATION_NOT_AVAILABLE':
                assert r[14] == 'NOT_AVAILABLE'
    fresh = next(v for v in d['statuses'] if v['name'] == 'set_a_fresh_capped')['expected']
    assert fresh['missing'][-1] == '2026-10-27' and fresh['missing'][0] == '2026-10-19'
    mismatch = next(v for v in d['statuses'] if v['name'] == 'set_a_tampered_cell')['expected']
    assert mismatch['state'] == 'LEDGER_REPLAY_MISMATCH' and mismatch['append_rows'] == [] and mismatch['missing'] == []
