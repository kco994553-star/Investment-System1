"""Virtual ledger sheet storage v1 (D-10): Python reference of the row format, continuation from the recorded state
(decision 2026-10-11), PRICE_REVISED and the missing-session plan, set definitions (B/C/D purpose + allowlisted members,
Set A versions, deletion = close), checked against the shared SYNTHETIC vectors and the device JS."""
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
        status, inp = vls.ledger_status(copy.deepcopy(v['ledger']), ref.revised(base, v['revise']), v['recorded'], cfg, v['through'])
        assert json.loads(json.dumps(status)) == v['expected'], v['name']
        if v['recorded_sha256']:
            assert hashlib.sha256(vls.inputs_text(inp, status['recorded_through']).encode()).hexdigest() == v['recorded_sha256']


def test_js_equals_python_on_vectors():
    script = r'''
const S=require(process.argv[1]),R=require(process.argv[1].replace('virtual-ledger-sheets.js','virtual-trading-runner.js')),VT=require(process.argv[1].replace('virtual-ledger-sheets.js','virtual-trading.js'));
const fs=require('fs'),crypto=require('crypto');const d=JSON.parse(fs.readFileSync(process.argv[2],'utf8')),inp=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const base=R.assemble(inp.vectors.find(v=>v.name===d.base_vector).inputs).ledgers.SET_A.input,cfg=VT.defaultConfig(),sha=t=>crypto.createHash('sha256').update(t).digest('hex');
const err=f=>{try{return f();}catch(e){return{error:e.message};}};
const revised=v=>{if(!v.revise)return base;const b=JSON.parse(JSON.stringify(base));b.companies[v.revise.company].closes[v.revise.date]=v.revise.close;return b;};
process.stdout.write(JSON.stringify({
 statuses:d.statuses.map(v=>{const{status,input}=S.ledgerStatus(v.ledger,revised(v),v.recorded,cfg,v.through);return[status,input&&status.recorded_through?sha(S.inputsText(input,status.recorded_through)):null];}),
 recorded:d.recorded_states.map(v=>err(()=>S.recordedState(v.rows))),sets:d.sets.map(v=>S.validateSet(v.raw,v.purpose,v.kind,Object.keys(R.MEMBERS))),
 setA:d.set_a_change.map(v=>S.setAChangeRows(v.meta,base,v.now,cfg,v.payload,v.recorded_last)),deletes:d.deletes.map(v=>err(()=>S.deleteRows(v.meta,v.kind,v.now,cfg,v.recorded_last))),
 ids:d.next_ids.map(v=>S.nextId(v.meta,v.kind)),members:Object.keys(R.MEMBERS).sort(),
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
    assert out['recorded'] == [v['expected'] for v in d['recorded_states']]
    assert out['sets'] == [v['expected'] for v in d['sets']]
    assert out['setA'] == [v['expected'] for v in d['set_a_change']]
    assert out['deletes'] == [v['expected'] for v in d['deletes']]
    assert out['ids'] == [v['expected'] for v in d['next_ids']]
    assert out['members'] == d['members']


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
    # Decision 2026-10-11: a recorded row that differs from the replay is not a stop: PRICE_REVISED, recording goes on.
    tampered = next(v for v in d['statuses'] if v['name'] == 'set_a_tampered_cell')['expected']
    assert tampered['state'] == 'OK' and 'PRICE_REVISED' in tampered['reason_codes'] and tampered['price_revised']['session'] == '2026-10-20'
    assert tampered['missing'] and tampered['append_rows']
    revised = next(v for v in d['statuses'] if v['name'] == 'set_a_bar_revised')['expected']
    assert revised['price_revised']['session'] == '2026-10-21' and revised['missing'][0] == '2026-10-26'
    for name in ('set_a_rows_missing_summary', 'set_a_rows_bad_number'):
        bad = next(v for v in d['statuses'] if v['name'] == name)['expected']
        assert bad['state'] == 'SHEET_ROWS_INVALID' and bad['append_rows'] == [], name


def test_continuation_from_recorded_state_equals_replay_when_nothing_was_revised():
    """Same inputs, recorded rows equal to the replay → the rows appended from the recorded state are exactly the replay's
    rows (cash, positions with KRW cost, pending orders and user flags round-trip through the sheet text)."""
    cfg, (base, _) = vt.load_config(), ref.base_input()
    d = data()
    checked = 0
    for v in d['statuses']:
        e = v['expected']
        if not v['recorded'] or e['price_revised'] or e['state'] != 'OK' or not e['missing'] or v['revise']:
            continue
        fresh, _ = vls.ledger_status(copy.deepcopy(v['ledger']), base, [], cfg, '2026-12-31')
        wanted = set(e['missing'])
        assert e['append_rows'] == [r for r in fresh['append_rows'] if r[1] in wanted], v['name']
        checked += 1
    assert checked >= 4


def test_recorded_state_is_the_engine_state():
    """recorded_state on the replayed rows reproduces the cash and positions the engine carries (resume == replay)."""
    cfg, (base, _) = vt.load_config(), ref.base_input()
    set_a = vls.set_a_ledger({'ledgers': []}, base, cfg)
    rows = vls.ledger_status(set_a, base, [], cfg, '2026-10-30')[0]['append_rows']
    state = vls.recorded_state([r for r in rows if r[1] <= '2026-10-23'])
    assert state['after'] == '2026-10-23' and state['cash'] >= 0 and all(p['quantity'] > 0 for p in state['positions'].values())
    for v in data()['recorded_states']:
        try:
            got = vls.recorded_state(v['rows'])
        except vls.SheetError as e:
            got = {'error': str(e)}
        assert json.loads(json.dumps(got)) == v['expected'], v['name']


def test_set_definitions_members_purpose_and_versions():
    d = data()
    members = sorted(vt_members())
    assert d['members'] == members and len(members) == 34
    assert not any(m.endswith('=x') for m in members)
    cases = {v['name']: v['expected'] for v in d['sets']}
    assert cases['purpose_missing']['reason_codes'] == ['PURPOSE_REQUIRED'] and cases['over_30']['reason_codes'] == ['SET_MEMBERS_OVER_30']
    assert cases['exactly_30']['state'] == 'OK' and cases['fx_symbol_rejected']['state'] == 'INVALID'
    first = next(v for v in d['set_a_change'] if v['name'] == 'first_change_stores_the_example')['expected']
    assert [(r[1], r[3]) for r in first] == [('set_a', 'LEDGER_START'), ('set_a', 'LEDGER_CLOSE'), ('set_a@v2', 'LEDGER_START')]
    assert json.loads(first[0][10])['target_basis'] == 'TARGET_V0' and json.loads(first[2][10])['target_basis'] == 'SET_A'
    deleted = next(v for v in d['deletes'] if v['name'] == 'delete_open_set_d')['expected']
    assert [r[3] for r in deleted] == ['LEDGER_CLOSE'] and json.loads(deleted[0][10]) == {'reason': 'SET_DELETED'}


def test_history_allowlist_extends_universe_without_expanding_virtual_set_members():
    """Universe504 price history is approved separately from virtual set allocation."""
    script = "const Q=require(process.argv[1]);process.stdout.write(JSON.stringify(Q.HISTORY_SYMBOLS))"
    js = json.loads(subprocess.run(['node', '-e', script, str(ROOT / 'src/investment_system/product/web_assets/google-sheet-quotes.js')],
                                   capture_output=True, text=True, check=True).stdout)
    from investment_system.qgv import virtual_trading_inputs as vi
    from investment_system.universe.universe_codes import source_codes
    universe = {code.split(':', 1)[1].replace('.', '-') for code in source_codes()}
    expected = universe | set(vi.MEMBERS.values()) | {'HYG', 'IEF', 'KRW=X', 'JPYKRW=X'}
    assert set(js) == expected
    assert set(vi.MEMBERS.values()) <= set(js)
    assert 'BRK-B' in js and 'BRK-B' not in vi.MEMBERS.values()


def vt_members():
    from investment_system.qgv import virtual_trading_inputs as vi
    return list(vi.MEMBERS)
