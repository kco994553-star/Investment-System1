"""Build tests/fixtures/virtual_ledger_sheets_v1.json: SYNTHETIC vectors for the virtual ledger sheet storage (D-10).

The ledger inputs are the SYNTHETIC 'full_synthetic' runner vector of tests/fixtures/virtual_trading_inputs_v1.json
(assembled again here and on the device, so the closes are not repeated). Each vector holds the expected Python
reference output (qgv/virtual_ledger_sheets.py): text form of numbers, sheet rows, replay verification, missing
sessions, inputs hashes, tab/meta/flag parsing, weight validation and new-ledger meta rows; decision 2026-10-11:
continuation from the recorded state (recorded rows are canonical), PRICE_REVISED, user sets B/C/D with purpose and
allowlisted members, Set A versions and set deletion (closed only).
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


def ledger(lid, kind, begin, end=None, weights=None, basis=None, snapshot=None, purpose=None):
    return {'id': lid, 'kind': kind, 'begin': begin, 'end': end,
            'target_basis': basis or {'SET_A': 'TARGET_V0', 'SET_B': 'SET_B', 'SET_C': 'SET_C', 'SET_D': 'SET_D', 'SHADOW': 'USER_TARGET'}[kind],
            'target_weights': weights, 'snapshot': snapshot, 'config_version': 'virtual_trading/v1-provisional',
            'engine_version': 'virtual_trading_rules/v1', 'reason': 'INITIAL', 'purpose': purpose, 'close_reason': None}


def revised(base, revise):
    """A revised daily bar (SYNTHETIC): the same input with one close changed after it was recorded."""
    if not revise:
        return base
    out = copy.deepcopy(base)
    out['companies'][revise['company']]['closes'][revise['date']] = revise['close']
    return out


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
    rows_resume = [r for r in rows if r[1] <= '2026-10-23']
    nvda_close = base['companies']['nvda']['closes']['2026-10-21']
    revise = {'company': 'nvda', 'date': '2026-10-21', 'close': round(nvda_close * 1.0625, 4)}
    cases = [
        ('set_a_fresh_capped', set_a, [], '2026-10-27'),
        ('set_a_resume_mid', set_a, rows_resume, '2026-10-30'),
        ('set_a_bar_revised', set_a, rows_resume, '2026-10-30', revise),
        ('set_a_rows_missing_summary', set_a, [r for r in first3 if not (r[1] == '2026-10-21' and r[2] == 'SUMMARY')], '2026-10-30'),
        ('set_a_rows_bad_number', set_a, [r if r[2] != 'SUMMARY' or r[1] != '2026-10-20' else r[:13] + ['1,000'] + r[14:] for r in first3], '2026-10-30'),
        ('set_c_purpose_etf_member', ledger('set_c-1', 'SET_C', '2026-10-21', None, {'nvda': 30, 'smh': 20, 'msft': 25}, purpose='반도체 집중 비교'), [], '2026-10-30'),
        ('set_a_v2_closed_v1', ledger('set_a@v2', 'SET_A', '2026-10-22', None, {'amd': 40, 'googl': 30}, 'SET_A'), [], '2026-10-30'),
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
    for case in cases:
        name, led, recorded, through = case[:4]
        rev = case[4] if len(case) > 4 else None
        status, inp = vls.ledger_status(led, revised(base, rev), recorded, cfg, through)
        last = status['missing'][-1] if status['missing'] else status['recorded_through']
        out.append({'name': name, 'ledger': led, 'recorded': recorded, 'through': through, 'revise': rev, 'expected': status,
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
    sets = [vls.start_row(NOW, {'id': 'set_c-1', 'kind': 'SET_C', 'begin': '2026-10-22'}, cfg, {'reason': 'INITIAL', 'target_basis': 'SET_C', 'target_weights': {'smh': 30, 'nvda': 20}, 'purpose': '반도체 ETF와 비교'}),
            vls.close_row(NOW, {'id': 'set_c-1', 'kind': 'SET_C'}, '2026-10-27', {'reason': 'SET_DELETED'}),
            vls.close_row(NOW, {'id': 'set_a', 'kind': 'SET_A'}, '2026-10-23', {'next': 'set_a@v2', 'reason': 'SET_A_CHANGED'}),
            vls.start_row(NOW, {'id': 'set_a@v2', 'kind': 'SET_A', 'begin': '2026-10-23'}, cfg, {'reason': 'SET_A_CHANGED', 'previous': 'set_a', 'target_basis': 'SET_A', 'target_weights': {'amd': 40, 'xlk': 10}}),
            vls.start_row(NOW, {'id': 'set_d-1', 'kind': 'SET_D', 'begin': '2026-10-26'}, cfg, {'reason': 'INITIAL', 'target_basis': 'SET_D', 'target_weights': {'msft': 50}, 'purpose': '단일 종목 기준선'})]
    many = {cid: 3 for cid in list(vi.MEMBERS)[:31]}
    cases = [('full_history', good), ('sets_versions_and_deletion', good[:1] + sets)]
    bad = [('duplicate_start', good[:2] + [good[1]]), ('unknown_event', good[:1] + [[NOW, '', 'TARGET', 'NOTE', '', '', '', '', '', '', '{}']]),
           ('close_unknown', [good[3]]), ('record_bad_sha', good[:1] + [good[6][:9] + ['xyz', good[6][10]]]),
           ('weights_over_100', [vls.target_row(NOW, {'nvda': 60, 'amd': 50})]), ('payload_not_json', [good[0][:10] + ['{x']]),
           ('kind_prefix_mismatch', [vls.start_row(NOW, {'id': 'shadow-1', 'kind': 'SET_B', 'begin': '2026-10-22'}, cfg, {'target_basis': 'SET_B', 'target_weights': weights})]),
           ('shadow_without_snapshot', [vls.start_row(NOW, {'id': 'shadow-1', 'kind': 'SHADOW', 'begin': '2026-10-22'}, cfg, {'target_basis': 'TARGET_V0', 'target_weights': weights})]),
           ('purpose_with_line_break', [vls.start_row(NOW, {'id': 'set_c-1', 'kind': 'SET_C', 'begin': '2026-10-22'}, cfg, {'target_basis': 'SET_C', 'target_weights': weights, 'purpose': '두 줄\n목적'})]),
           ('set_a_v1_suffix_invalid', [vls.start_row(NOW, {'id': 'set_a@v1', 'kind': 'SET_A', 'begin': '2026-10-22'}, cfg, {'target_basis': 'SET_A', 'target_weights': weights})]),
           ('over_30_members', [vls.start_row(NOW, {'id': 'set_d-1', 'kind': 'SET_D', 'begin': '2026-10-22'}, cfg, {'target_basis': 'SET_D', 'target_weights': many, 'purpose': '많은 종목'})]),
           ('unknown_member', [vls.start_row(NOW, {'id': 'set_d-1', 'kind': 'SET_D', 'begin': '2026-10-22'}, cfg, {'target_basis': 'SET_D', 'target_weights': {'zzz': 5}, 'purpose': '알 수 없는 종목'})])]
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
        ('set_c_first', 'SET_C', '2026-10-21T01:00:00Z', {'target_basis': 'SET_C', 'target_weights': {'smh': 30, 'nvda': 20}, 'purpose': '반도체 ETF와 비교'}, None, 'INITIAL', meta),
    ]:
        replace.append({'name': name, 'meta': m, 'kind': kind, 'now': now, 'payload': payload, 'recorded_last': last, 'reason': reason,
                        'expected': vls.replace_rows(m, kind, now, cfg, payload, last, reason)})
    sets_meta = vls.parse_meta([r + [''] * (len(vls.META_HEAD) - len(r)) for r in good[:1] + sets])
    set_a_change = []
    for name, m, now, payload, last in [
        ('first_change_stores_the_example', {'ledgers': [], 'records': {}, 'user_target': None}, '2026-10-12T01:00:00Z', {'target_weights': {'amd': 40, 'xlk': 10}}, None),
        ('example_recorded_then_changed', meta, '2026-10-26T01:00:00Z', {'target_weights': {'msft': 60}, 'purpose': '대형 기술주 하나'}, '2026-10-23'),
        ('second_version', sets_meta, '2026-10-29T01:00:00Z', {'target_weights': {'qual': 50, 'vug': 50}}, '2026-10-28'),
    ]:
        set_a_change.append({'name': name, 'meta': m, 'now': now, 'payload': payload, 'recorded_last': last,
                             'expected': vls.set_a_change_rows(m, base, now, cfg, payload, last)})
    deletes = []
    for name, m, kind, now, last in [('delete_open_set_d', sets_meta, 'SET_D', '2026-10-29T01:00:00Z', '2026-10-28'),
                                     ('delete_closed_set_c', sets_meta, 'SET_C', '2026-10-29T01:00:00Z', None)]:
        try:
            expected = vls.delete_rows(m, kind, now, cfg, last)
        except vls.SheetError as e:
            expected = {'error': str(e)}
        deletes.append({'name': name, 'meta': m, 'kind': kind, 'now': now, 'recorded_last': last, 'expected': expected})
    next_ids = [{'kind': k, 'meta': sets_meta, 'expected': vls.next_id(sets_meta, k)} for k in vls.KINDS] + \
        [{'kind': 'SET_A', 'meta': {'ledgers': []}, 'expected': vls.next_id({'ledgers': []}, 'SET_A')}]
    status = {'id': 'set_a', 'kind': 'SET_A', 'missing': ['2026-10-22', '2026-10-23']}
    record = {'expected': vls.record_row(NOW, status, cfg, 'b' * 64, 44), 'status': status, 'sha256': 'b' * 64, 'rows': 44}
    begins = [{'now': n, 'previous_last': p, 'expected': vls.begin_for(n, cfg, p)} for n, p in [
        ('2026-10-12T01:00:00Z', None), ('2026-10-20T03:59:59Z', None), ('2026-10-20T04:00:00Z', None), ('2026-10-22T08:00:00+09:00', None),
        ('2026-10-22T08:00:00+09:00', '2026-10-21'), ('2026-10-22T08:00:00+09:00', '2026-10-30')]]
    return out, replace, record, begins, set_a_change, deletes, next_ids


def input_vectors():
    allowed = list(vi.IDS)
    weights = [('empty', {}), ('blank_strings', {'nvda': ' ', 'amd': ''}), ('texts', {'nvda': '40', 'msft': '35.5', 'hanmi': '24.5', 'amd': '0'}),
               ('numbers', {'nvda': 12.25, 'avgo': 7}), ('over_100', {'nvda': '60', 'amd': '40.0001'}), ('exactly_100', {'nvda': '60', 'amd': '40'}),
               ('negative', {'nvda': '-1'}), ('exponent', {'nvda': '1e1'}), ('too_precise', {'nvda': '1.23456'}), ('above_100', {'nvda': '100.5'}),
               ('unknown_company', {'nvda': '10', 'spy': '5'}), ('bool', {'nvda': True}), ('not_object', ['nvda'])]
    w = [{'name': n, 'raw': raw, 'expected': vls.validate_weights(raw, allowed)} for n, raw in weights]
    members = list(vi.MEMBERS)
    many = {cid: '3' for cid in members[:31]}
    set_cases = [('set_b_ok', {'nvda': '40', 'smh': '20'}, ' 반도체 비교 ', 'SET_B'), ('purpose_missing', {'nvda': '40'}, '', 'SET_C'),
                 ('purpose_none', {'nvda': '40'}, None, 'SET_D'), ('purpose_line_break', {'nvda': '40'}, '두 줄\n목적', 'SET_B'),
                 ('purpose_too_long', {'nvda': '40'}, '가' * 121, 'SET_B'), ('set_a_without_purpose', {'amd': '40', 'xlk': '10'}, None, 'SET_A'),
                 ('over_30', many, '많은 종목', 'SET_C'), ('exactly_30', {cid: '3' for cid in members[:30]}, '서른 종목', 'SET_C'),
                 ('fx_symbol_rejected', {'krw=x': '10'}, '환율', 'SET_B'), ('unknown_symbol', {'tsla': '10'}, '허용 목록 밖', 'SET_B'),
                 ('sum_over_100', {'nvda': '60', 'smh': '41'}, '합계 초과', 'SET_D'), ('empty', {}, '빈 구성', 'SET_D')]
    sets = [{'name': n, 'raw': raw, 'purpose': purpose, 'kind': kind, 'expected': vls.validate_set(raw, purpose, kind, members)}
            for n, raw, purpose, kind in set_cases]
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
    return w, flags, sets


def build():
    cfg = vt.load_config()
    base, holdings = base_input()
    tabs, groups = tab_vectors()
    meta, replace, record, begins, set_a_change, deletes, next_ids = meta_vectors(base, holdings, cfg)
    weights, flags, sets = input_vectors()
    canon = {'b': [1.5, None, True, 'x"y'], 'a': {'z': 1e-7, 'k': 'é'}, 'c': 100.0}
    return {'schema_version': 1, 'note': NOTE, 'synthetic': True, 'base_vector': BASE_VECTOR,
            'recordable_through': vls.recordable_through(base),
            'numbers': [[x, vls.num_str(x)] for x in NUMBERS], 'canonical': {'value': canon, 'expected': vls.canonical(canon)},
            'statuses': status_vectors(base, holdings, cfg), 'tabs': tabs, 'groups': groups, 'meta': meta, 'replace': replace,
            'record_row': record, 'begin_for': begins, 'weights': weights, 'flags': flags, 'sets': sets,
            'set_a_change': set_a_change, 'deletes': deletes, 'next_ids': next_ids, 'recorded_states': recorded_state_vectors(base, cfg),
            'members': sorted(vi.MEMBERS)}


def recorded_state_vectors(base, cfg):
    """recorded_state on synthetic recorded rows: a valid history (equals the engine state) and malformed variants."""
    holdings = next(x for x in json.loads(INPUTS.read_text(encoding='utf-8'))['vectors'] if x['name'] == BASE_VECTOR)['inputs']['holdings']
    snap = {'effective_at': '2026-10-20T13:00:00Z', 'source_effective_at': holdings['effective_at'], 'positions': holdings['positions']}
    shadow = ledger('shadow-1', 'SHADOW', '2026-10-20', None, {'nvda': 30, 'hanmi': 20, 'tokyo_electron': 10, 'msft': 20}, 'USER_TARGET', snap)
    shadow_rows = vls.ledger_status(shadow, base, [], cfg, '2026-10-30')[0]['append_rows']
    set_a_rows = vls.ledger_status(vls.set_a_ledger({'ledgers': []}, base, cfg), base, [], cfg, '2026-10-30')[0]['append_rows']
    upto = [r for r in shadow_rows if r[1] <= '2026-10-26']
    sell = next((i for i, r in enumerate(upto) if r[2] == 'EXECUTED' and r[8] == 'SELL'), None)
    cases = [('shadow_through_10_26', upto), ('set_a_all', set_a_rows),
             ('row_after_summary', upto + [upto[-2]]),
             ('sell_unheld', [r if i != sell else r[:3] + ['amd'] + r[4:] for i, r in enumerate(upto)] if sell is not None else upto[:1]),
             ('order_bad_side', [r if r[2] != 'ORDER' else r[:8] + ['HOLD'] + r[9:] for r in upto]),
             ('negative_cash', [r if r[2] != 'SUMMARY' else r[:13] + ['-5'] + r[14:] for r in upto]), ('empty', [])]
    out = []
    for name, rows in cases:
        try:
            expected = vls.recorded_state(rows)
        except vls.SheetError as e:
            expected = {'error': str(e)}
        out.append({'name': name, 'rows': rows, 'expected': expected})
    return out


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
