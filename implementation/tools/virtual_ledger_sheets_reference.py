"""Build tests/fixtures/virtual_ledger_sheets_v1.json: SYNTHETIC vectors for the virtual ledger sheet storage (D-10).

The ledger inputs are the SYNTHETIC 'full_synthetic' runner vector of tests/fixtures/virtual_trading_inputs_v1.json
(assembled again here and on the device, so the closes are not repeated). Each vector holds the expected Python
reference output (qgv/virtual_ledger_sheets.py): text form of numbers, sheet rows, replay verification, missing
sessions, inputs hashes, tab/meta/flag parsing, weight validation and new-ledger meta rows.
Usage: python tools/virtual_ledger_sheets_reference.py [--check]
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.qgv import virtual_ledger_sheets as vls  # noqa: E402
from investment_system.qgv import virtual_trading as vt  # noqa: E402
from investment_system.qgv import virtual_trading_inputs as vi  # noqa: E402

OUT = ROOT / 'tests/fixtures/virtual_ledger_sheets_v1.json'
INPUTS = ROOT / 'tests/fixtures/virtual_trading_inputs_v1.json'
BASE_VECTOR = 'full_synthetic'
NOTE = 'SYNTHETIC test vectors: ledger inputs come from the synthetic runner vector; no market data, no real holdings.'
NOW = '2026-10-21T23:30:00Z'
NUMBERS = [0.1 + 0.2, 1e21, 1e-7, 123e-20, 5e-324, 1.7976931348623157e308, 1e20, 123456789012345680000.0, 0.000001,
           1.5, 100.0, 2.5e-7, 1234.5678e10, 1000000, 999999.9999999999, 1 / 3, 12.5 * 101.25 * 1381.2345, -0.0, -42.75]


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def base_input():
    v = next(x for x in json.loads(INPUTS.read_text(encoding='utf-8'))['vectors'] if x['name'] == BASE_VECTOR)
    out = vi.assemble(**copy.deepcopy(v['inputs']))
    return out['ledgers']['SET_A']['input'], v['inputs']['holdings']


def ledger(lid, kind, begin, end=None, weights=None, basis=None, snapshot=None):
    return {'id': lid, 'kind': kind, 'begin': begin, 'end': end, 'target_basis': basis or {'SET_A': 'TARGET_V0', 'SET_B': 'SET_B', 'SHADOW': 'USER_TARGET'}[kind],
            'target_weights': weights, 'snapshot': snapshot, 'config_version': 'virtual_trading/v1-provisional',
            'engine_version': 'virtual_trading_rules/v1', 'reason': 'INITIAL'}


def status_vectors(base, holdings, cfg):
    empty = {'ledgers': [], 'records': {}, 'user_target': None}
    set_a = vls.set_a_ledger(empty, base, cfg)
    fresh, _ = vls.ledger_status(set_a, base, [], cfg, '2026-10-30')
    rows = fresh['append_rows']
    first3 = [r for r in rows if r[1] <= '2026-10-21']
    tampered = copy.deepcopy(first3)
    k = next(i for i, r in enumerate(tampered) if r[1] == '2026-10-20' and r[2] == 'SUMMARY')
    tampered[k][13] = vls.num_str(float(tampered[k][13]) + 1)
    gap = [r for r in rows if r[1] in ('2026-10-19', '2026-10-21')]
    beyond = first3 + [[r[0], '2026-11-02'] + r[2:] for r in rows if r[1] == '2026-10-22']
    snap = {'effective_at': '2026-10-20T13:00:00Z', 'source_effective_at': holdings['effective_at'], 'positions': holdings['positions']}
    user = {'nvda': 30, 'hanmi': 20, 'tokyo_electron': 10, 'msft': 20}
    shadow = ledger('shadow-1', 'SHADOW', '2026-10-20', None, user, 'USER_TARGET', snap)
    shadow_rows = vls.ledger_status(shadow, base, [], cfg, '2026-10-30')[0]['append_rows']
    bad_snap = copy.deepcopy(snap)
    bad_snap['positions']['nvda']['average_cost'] = None
    set_b = ledger('set_b-1', 'SET_B', '2026-10-19', '2026-10-23', {'nvda': 40, 'msft': 35.5, 'hanmi': 24.5})
    set_b_rows = vls.ledger_status(set_b, base, [], cfg, '2026-10-30')[0]['append_rows']
    cases = [
        ('set_a_fresh_capped', set_a, [], '2026-10-27'),
        ('set_a_resume', set_a, first3, '2026-10-30'),
        ('set_a_tampered_cell', set_a, tampered, '2026-10-30'),
        ('set_a_gap', set_a, gap, '2026-10-30'),
        ('set_a_beyond_replay', set_a, beyond, '2026-10-30'),
        ('set_a_waiting_for_qg', set_a, first3, None),
        ('set_b_late_begin', ledger('set_b-2', 'SET_B', '2026-10-22', None, {'nvda': 40, 'msft': 35.5, 'hanmi': 24.5}), [], '2026-10-30'),
        ('set_b_closed', set_b, [r for r in set_b_rows if r[1] == '2026-10-19'], '2026-10-30'),
        ('shadow_segment', shadow, [], '2026-10-30'),
        ('shadow_resume', shadow, [r for r in shadow_rows if r[1] <= '2026-10-22'], '2026-10-28'),
        ('shadow_no_actual', ledger('shadow-2', 'SHADOW', '2026-10-20', None, user, 'USER_TARGET', {'effective_at': NOW, 'positions': {}}), [], '2026-10-30'),
        ('shadow_invalid_with_rows', ledger('shadow-1', 'SHADOW', '2026-10-20', None, user, 'USER_TARGET', bad_snap),
         [r for r in shadow_rows if r[1] == '2026-10-20'], '2026-10-30'),
        ('shadow_not_started', ledger('shadow-3', 'SHADOW', '2026-11-02', None, user, 'TARGET_V0', snap), [], '2026-10-30'),
    ]
    out = []
    for name, led, recorded, through in cases:
        status, inp = vls.ledger_status(led, base, recorded, cfg, through)
        last = status['missing'][-1] if status['missing'] else status['recorded_through']
        out.append({'name': name, 'ledger': led, 'recorded': recorded, 'through': through, 'expected': status,
                    'recorded_sha256': sha(vls.inputs_text(inp, status['recorded_through'])) if inp and status['recorded_through'] else None,
                    'next_sha256': sha(vls.inputs_text(inp, last)) if inp and last else None})
    return out


def tab_vectors():
    head = list(vls.LEDGER_HEAD)
    row = ['set_a', '2026-10-19', 'SUMMARY', '', '', '', '', '', '', '1000000', '', '', '', '1000000', '1000000']
    cases = [
        ('empty_tab', [], 'VirtualA'),
        ('header_only', [head], 'VirtualA'),
        ('trailing_cells_omitted', [head, row[:10], row], 'VirtualA'),
        ('header_differs', [head[:-1] + ['total']], 'VirtualA'),
        ('header_short', [head[:-1]], 'VirtualA'),
        ('number_cell', [head, row[:9] + [1000000]], 'VirtualA'),
        ('too_many_cells', [head, row + ['x']], 'VirtualA'),
        ('blank_row', [head, []], 'VirtualA'),
        ('meta_header', [list(vls.META_HEAD)], 'VirtualMeta'),
    ]
    out = []
    for name, values, tab in cases:
        try:
            expected = vls.parse_tab(values, vls.HEADS[tab])
        except vls.SheetError as e:
            expected = {'error': str(e)}
        out.append({'name': name, 'tab': tab, 'values': values, 'expected': expected})
    groups = []
    for name, rows in [('ordered', [row, row[:1] + ['2026-10-20'] + row[2:], ['set_b-1'] + row[1:]]),
                       ('date_goes_back', [row[:1] + ['2026-10-20'] + row[2:], row]),
                       ('bad_id', [['set_c'] + row[1:]]), ('bad_type', [row[:2] + ['NOTE'] + row[3:]])]:
        try:
            expected = vls.group_ledger_rows(rows)
        except vls.SheetError as e:
            expected = {'error': str(e)}
        groups.append({'name': name, 'rows': rows, 'expected': expected})
    return out, groups


def meta_vectors(base, holdings, cfg):
    weights = {'nvda': 40, 'msft': 35.5, 'hanmi': 24.5}
    set_a = vls.set_a_ledger({'ledgers': []}, base, cfg)
    snap = {'effective_at': '2026-10-20T13:00:00Z', 'source_effective_at': holdings['effective_at'], 'positions': holdings['positions']}
    good = [vls.start_row(NOW, set_a, cfg, {'reason': 'INITIAL', 'target_basis': 'TARGET_V0', 'target_weights': set_a['target_weights']}),
            vls.start_row(NOW, {'id': 'set_b-1', 'kind': 'SET_B', 'begin': '2026-10-22'}, cfg, {'reason': 'INITIAL', 'target_basis': 'SET_B', 'target_weights': weights}),
            vls.target_row(NOW, {'nvda': 50, 'hanmi': 25}),
            vls.close_row(NOW, {'id': 'set_b-1', 'kind': 'SET_B'}, '2026-10-26', {'next': 'set_b-2', 'reason': 'SET_B_REDEFINED'}),
            vls.start_row(NOW, {'id': 'set_b-2', 'kind': 'SET_B', 'begin': '2026-10-26'}, cfg, {'reason': 'SET_B_REDEFINED', 'previous': 'set_b-1', 'target_basis': 'SET_B', 'target_weights': {'amd': 100}}),
            vls.start_row(NOW, {'id': 'shadow-1', 'kind': 'SHADOW', 'begin': '2026-10-20'}, cfg, {'reason': 'INITIAL', 'target_basis': 'USER_TARGET', 'target_weights': {'nvda': 50, 'hanmi': 25}, 'snapshot': snap}),
            [NOW, 'set_a', 'SET_A', 'RECORD', '', '', 'virtual_trading/v1-provisional', 'virtual_trading_rules/v1', '2026-10-21', 'a' * 64, '{"rows":3,"sessions":3}'],
            vls.target_row(NOW, None)]
    cases = [('full_history', good)]
    bad = [('duplicate_start', good[:2] + [good[1]]), ('unknown_event', good[:1] + [[NOW, '', 'TARGET', 'NOTE', '', '', '', '', '', '', '{}']]),
           ('close_unknown', [good[3]]), ('record_bad_sha', good[:1] + [good[6][:9] + ['xyz', good[6][10]]]),
           ('weights_over_100', [vls.target_row(NOW, {'nvda': 60, 'amd': 50})]), ('payload_not_json', [good[0][:10] + ['{x']]),
           ('kind_prefix_mismatch', [vls.start_row(NOW, {'id': 'shadow-1', 'kind': 'SET_B', 'begin': '2026-10-22'}, cfg, {'target_basis': 'SET_B', 'target_weights': weights})]),
           ('shadow_without_snapshot', [vls.start_row(NOW, {'id': 'shadow-1', 'kind': 'SHADOW', 'begin': '2026-10-22'}, cfg, {'target_basis': 'TARGET_V0', 'target_weights': weights})])]
    out = []
    for name, rows in cases + bad:
        padded = [r + [''] * (len(vls.META_HEAD) - len(r)) for r in rows]
        out.append({'name': name, 'rows': padded, 'expected': vls.parse_meta(padded)})
    meta = vls.parse_meta([r + [''] * (len(vls.META_HEAD) - len(r)) for r in good])
    replace = []
    for name, kind, now, payload, last, reason, m in [
        ('set_b_first', 'SET_B', '2026-10-12T01:00:00Z', {'target_basis': 'SET_B', 'target_weights': weights}, None, 'INITIAL', {'ledgers': []}),
        ('set_b_redefine_after_recorded', 'SET_B', '2026-10-27T00:30:00Z', {'target_basis': 'SET_B', 'target_weights': {'qcom': 10}}, '2026-10-27', 'SET_B_REDEFINED', meta),
        ('shadow_resync', 'SHADOW', '2026-10-28T15:00:00+09:00', {'target_basis': 'USER_TARGET', 'target_weights': {'nvda': 50}, 'snapshot': snap}, '2026-10-22', 'RESYNC', meta),
    ]:
        replace.append({'name': name, 'meta': m, 'kind': kind, 'now': now, 'payload': payload, 'recorded_last': last, 'reason': reason,
                        'expected': vls.replace_rows(m, kind, now, cfg, payload, last, reason)})
    status = {'id': 'set_a', 'kind': 'SET_A', 'missing': ['2026-10-22', '2026-10-23']}
    record = {'expected': vls.record_row(NOW, status, cfg, 'b' * 64, 44), 'status': status, 'sha256': 'b' * 64, 'rows': 44}
    begins = [{'now': n, 'previous_last': p, 'expected': vls.begin_for(n, cfg, p)} for n, p in [
        ('2026-10-12T01:00:00Z', None), ('2026-10-20T03:59:59Z', None), ('2026-10-20T04:00:00Z', None), ('2026-10-22T08:00:00+09:00', None),
        ('2026-10-22T08:00:00+09:00', '2026-10-21'), ('2026-10-22T08:00:00+09:00', '2026-10-30')]]
    return out, replace, record, begins


def input_vectors():
    allowed = list(vi.IDS)
    weights = [('empty', {}), ('blank_strings', {'nvda': ' ', 'amd': ''}), ('texts', {'nvda': '40', 'msft': '35.5', 'hanmi': '24.5', 'amd': '0'}),
               ('numbers', {'nvda': 12.25, 'avgo': 7}), ('over_100', {'nvda': '60', 'amd': '40.0001'}), ('exactly_100', {'nvda': '60', 'amd': '40'}),
               ('negative', {'nvda': '-1'}), ('exponent', {'nvda': '1e1'}), ('too_precise', {'nvda': '1.23456'}), ('above_100', {'nvda': '100.5'}),
               ('unknown_company', {'nvda': '10', 'spy': '5'}), ('bool', {'nvda': True}), ('not_object', ['nvda'])]
    w = [{'name': n, 'raw': raw, 'expected': vls.validate_weights(raw, allowed)} for n, raw in weights]
    flags_values = [list(vls.FLAGS_HEAD), ['', '2026-10-22', 'googl', 'HOLD'], ['2026-10-21T00:00:00Z', 46317, 'NVDA', 'exclude'],
                    ['', '2026-10-23', '8035.T', 'CONFIRMED_TEMPORARY'], ['', '2026-10-23', 'XYZ', 'HOLD'], ['', 'yesterday', 'amd', 'HOLD'],
                    ['', '2026-10-24', 'amd', 'SELL'], [], ['', '', '', ''], ['', 46318.5, 'amd', 'HOLD'], ['', '2026-10-25 ', ' rok ', ' clear ']]
    flags = [{'name': 'mixed', 'values': flags_values, 'expected': vls.parse_flags(flags_values)}, {'name': 'empty', 'values': [], 'expected': vls.parse_flags([])}]
    try:
        vls.parse_flags([['date', 'company', 'kind']])
        bad = None
    except vls.SheetError as e:
        bad = str(e)
    flags.append({'name': 'header_differs', 'values': [['date', 'company', 'kind']], 'expected': {'error': bad}})
    return w, flags


def build():
    cfg = vt.load_config()
    base, holdings = base_input()
    tabs, groups = tab_vectors()
    meta, replace, record, begins = meta_vectors(base, holdings, cfg)
    weights, flags = input_vectors()
    canon = {'b': [1.5, None, True, 'x"y'], 'a': {'z': 1e-7, 'k': 'é'}, 'c': 100.0}
    return {'schema_version': 1, 'note': NOTE, 'synthetic': True, 'base_vector': BASE_VECTOR,
            'recordable_through': vls.recordable_through(base),
            'numbers': [[x, vls.num_str(x)] for x in NUMBERS], 'canonical': {'value': canon, 'expected': vls.canonical(canon)},
            'statuses': status_vectors(base, holdings, cfg), 'tabs': tabs, 'groups': groups, 'meta': meta, 'replace': replace,
            'record_row': record, 'begin_for': begins, 'weights': weights, 'flags': flags}


def text():
    return json.dumps(build(), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'


def main(argv):
    if '--check' in argv:
        print('VIRTUAL_LEDGER_SHEETS_REFERENCE_OK' if OUT.read_text(encoding='utf-8') == text() else 'VIRTUAL_LEDGER_SHEETS_REFERENCE_STALE')
        return 0
    OUT.write_text(text(), encoding='utf-8')
    print('wrote', OUT.relative_to(ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
