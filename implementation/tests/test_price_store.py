"""Price store v1 (Prices_D / Prices_M tabs in the user's own sheet): Python reference of the pure logic, checked against
the shared SYNTHETIC vectors and the device JS (web_assets/price-store.js)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
from investment_system.qgv import price_store as ps  # noqa: E402
from investment_system.qgv import virtual_trading_inputs as vi  # noqa: E402
from autonomy_gate_a_guard import contains_device_actual  # noqa: E402

FIXTURE = ROOT / 'tests/fixtures/price_store_v1.json'
MODULE = ROOT / 'src/investment_system/product/web_assets/price-store.js'


def data():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def test_vectors_are_current_synthetic_and_not_private():
    out = subprocess.run([sys.executable, str(ROOT / 'tools/price_store_reference.py'), '--check'], capture_output=True, text=True).stdout.strip()
    assert out == 'PRICE_STORE_REFERENCE_OK'
    d = data()
    assert d['synthetic'] is True and d['note'].startswith('SYNTHETIC')
    assert not contains_device_actual(FIXTURE.read_bytes(), 'implementation/tests/fixtures/price_store_v1.json')


def test_append_only_rules():
    stored = {'2026-10-01': 1.0, '2026-10-02': 2.0}
    plan = ps.append_plan(stored, {'2026-10-01': 1.5, '2026-10-02': 2.0, '2026-10-03': 3.0, '2026-09-30': 0.5}, '1d')
    assert plan == {'append': [['2026-09-30', 0.5], ['2026-10-03', 3.0]], 'revised_ignored': 1}
    assert all(day not in stored for day, _ in plan['append'])
    monthly = ps.append_plan({'2026-08': 9.0}, {'2026-08': ['2026-08-31', 9.0], '2026-09': ['2026-09-30', 10.0]}, '1mo')
    assert monthly == {'append': [['2026-09-30', 10.0]], 'revised_ignored': 0}
    # Month-end rows dedupe by month: a different last-session date in a stored month is not appended again.
    assert ps.index_rows([['A', '2026-09-30', 1.0], ['A', '2026-09-29', 2.0]], '1mo') == {'series': {'A': {'2026-09': 1.0}}, 'duplicates': 1}


def test_header_mismatch_and_missing_values():
    try:
        ps.parse_tab([['symbol', 'date', 'interval', 'close', 'source', 'fetched_at']], '1d')
        raise AssertionError('header accepted')
    except ps.StoreError as e:
        assert str(e) == 'SHEET_HEADER_MISMATCH'
    parsed = ps.parse_tab([list(ps.HEAD), ['SPY', '2026-10-01', ''], ['SPY', '2026-10-02', '0'], ['SPY', '2026-10-05', 'NOT_AVAILABLE']], '1d')
    assert parsed == {'header': True, 'rows': [], 'invalid': 3}, 'a missing or zero close is never stored as a value'


def test_month_end_selection_and_ranges():
    closes = {'2026-08-28': 1.0, '2026-08-31': 2.0, '2026-09-30': 3.0, '2026-10-12': 4.0}
    assert ps.month_ends(closes, '2026-10-13') == {'2026-08': ['2026-08-31', 2.0], '2026-09': ['2026-09-30', 3.0]}
    assert ps.next_month_range('2026-09', '2026-10-13') is None
    assert ps.next_month_range(None, '2026-10-13') == '5y'
    order = [name for name, _ in ps.RANGES]
    last = [ps.next_range(d, '2026-10-12', '2026-10-13') for d in ['2026-10-09', '2026-08-01', '2026-03-01', '2025-06-01', '2023-01-01', '2020-01-01']]
    assert [order.index(r) for r in last] == sorted(order.index(r) for r in last)


def test_runner_payload_round_trip():
    closes = {'2024-10-14': 1.0, '2025-01-02': 2.0, '2026-10-12': 3.0}
    p = ps.runner_payload(closes, 'SPY', '2026-10-13', '2026-10-13T12:00:00Z')
    assert vi.series_from_history(p, 'SPY', 'USD') == ({'2024-10-14': 1.0, '2025-01-02': 2.0, '2026-10-12': 3.0}, None)
    p = ps.runner_payload(closes, 'SPY', '2026-10-15', '2026-10-15T12:00:00Z')
    assert [b['session_date'] for b in p['bars']] == ['2025-01-02', '2026-10-12'], 'the runner window is 24 months'


def test_js_equals_python_on_vectors():
    script = r'''
const P=require(process.argv[1]),R=require(process.argv[1].replace('price-store.js','virtual-trading-runner.js'));
const d=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8')),plain=v=>JSON.parse(JSON.stringify(v));
const err=f=>{try{return plain(f());}catch(e){return{error:e.message};}};
const out={tabs:d.tabs.map(v=>err(()=>P.parseTab(v.values,v.interval))),indexes:d.indexes.map(v=>plain(P.indexRows(v.rows,v.interval))),
 histories:d.histories.map(v=>[plain(P.closesFromHistory(v.payload,v.symbol)),P.sourceOf(v.payload)]),month_ends:d.month_ends.map(v=>plain(P.monthEnds(v.closes,v.as_of))),
 due:d.due.map(v=>err(()=>P.dueDate(v.symbol,v.day,v.time))),daily_ranges:d.ranges.daily.map(v=>P.nextRange(v.last,v.due,v.today)),
 monthly_ranges:d.ranges.monthly.map(v=>[P.monthDue(v.today),P.nextMonthRange(v.last_month,v.today)]),plans:d.plans.map(v=>plain(P.appendPlan(v.stored,v.fetched,v.interval))),
 rows:d.rows.map(v=>P.sheetRows(v.symbol,v.rows,v.source,v.fetched_at)),merged:d.merged.map(v=>plain(P.monthEndClosesOf(v.daily,v.monthly,v.as_of))),
 runner:d.runner.map(v=>plain(P.runnerPayload(v.closes,v.symbol,v.today,v.read_at))),chunks:d.chunks.map(v=>P.chunkRows(v.rows,v.max_bytes)),universe:d.universe.map(v=>P.universeSymbol(v.code))};
process.stdout.write(JSON.stringify(out));
'''
    res = subprocess.run(['node', '-e', script, str(MODULE), str(FIXTURE)], capture_output=True, text=True, check=True)
    js, d = json.loads(res.stdout), data()
    assert js['tabs'] == [v['expected'] for v in d['tabs']]
    assert js['indexes'] == [v['expected'] for v in d['indexes']]
    assert js['histories'] == [[v['expected'], v['source']] for v in d['histories']]
    assert js['month_ends'] == [v['expected'] for v in d['month_ends']]
    assert js['due'] == [v['expected'] for v in d['due']]
    assert js['daily_ranges'] == [v['expected'] for v in d['ranges']['daily']]
    assert js['monthly_ranges'] == [[v['due'], v['expected']] for v in d['ranges']['monthly']]
    assert js['plans'] == [v['expected'] for v in d['plans']]
    assert js['rows'] == [v['expected'] for v in d['rows']]
    assert js['merged'] == [v['expected'] for v in d['merged']]
    assert js['runner'] == [v['expected'] for v in d['runner']]
    assert js['chunks'] == [v['expected'] for v in d['chunks']]
    assert js['universe'] == [v['expected'] for v in d['universe']]


def test_write_allowlist_covers_only_the_two_price_tabs():
    text = (ROOT / 'src/investment_system/product/web_assets/google-sheet-quotes.js').read_text(encoding='utf-8')
    assert "'Prices_D','Prices_M'];" in text
    assert "Prices_(?:D|M))'!A1$/" in text
    source = MODULE.read_text(encoding='utf-8')
    for banned in ('console.', 'sessionStorage.', 'indexedDB'):
        assert banned not in source, banned
    # The only device key the store writes is its on/off flag.
    assert source.count('localStorage.setItem(') == 1 and "setItem(FLAG_KEY,'1')" in source
