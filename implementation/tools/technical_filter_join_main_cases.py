#!/usr/bin/env python3
"""Counterexample cases for the 3.5 tech-filter QGV join (owner 2026-11-08 「공통 분류 계약 인수와 기술 필터 소비 오류 수정」,
Codex #437 comment 6714613662): Codex's expected result for each case is the OUTPUT of Codex's own
research.technical_filter_join.join_filtered_rows (#516, explicit issuer_id); Main never writes an expected result by hand.

Every case starts from Codex's public fixture tests/research/fixtures/technical_filter_join_v1/inputs.json
(cases.original_board, join_inputs.same_date_same_security) and changes only the QGV rows / links handed in:
  a  code-row id != issuer_id (id = 'COMPANY:' + old id, issuer_id = old id)                    -> join
  b  issuer_id explicitly null on one row                                                        -> refused
  c  issuer_id wrong: '' / another issuer / a number                                             -> refused
  d  legacy rows without the issuer_id field (id = issuer)                                       -> join (old rule)
  e  two code rows of one issuer (two securities, two links, one issuer_id)                      -> two rows kept
  f  board group smaller than the population: whole population -> refused; the group's rows only -> join;
     the population's rows are not changed by the call (inputs compared before / after)
  g  a group member missing: its link missing -> refused; its row absent -> Codex joins the rest (Codex does not know
     the group; Main's IS2.classification.groupRows refuses that input with MEMBER_NOT_MAPPED before any join)
Result per case: {ok: true, kept: [{id, issuer_id, security_id, rank_official, rank_of, total}]} or {ok: false, code}.
SYNTHETIC only. Run from the repository root:
  python implementation/tools/technical_filter_join_main_cases.py [--check]
writes (or with --check compares byte for byte) implementation/tests/fixtures/technical_filter_join_main/cases.json."""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from investment_system.research.technical_filter_join import join_filtered_rows  # noqa: E402

CODEX = ROOT / 'tests/research/fixtures/technical_filter_join_v1/inputs.json'
CODEX_SHA256 = '8411e823440b913f3a3e67cd44f0e7c8ce160f88e86fd6c0c844b32911788db6'
OUT = ROOT / 'tests/fixtures/technical_filter_join_main/cases.json'


def text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1, allow_nan=False) + '\n'


def split(rows):
    """Common-record rows: id = the company code row, issuer_id = the issuer (the old id)."""
    return [{**r, 'id': 'COMPANY:' + r['id'], 'issuer_id': r['id']} for r in rows]


def extra_rows():
    """Population rows outside the board group: own securities, scores and ranks (never on the board)."""
    return [{'id': 'COMPANY:OUTSIDE:%d' % i, 'issuer_id': 'SYNTHETIC:ISSUER:OUT%d' % i, 'ticker': 'SYNTHETIC:SYMBOL:OUT%d' % i,
             'code': 'SYNTHETIC:CODE:OUT%d' % i, 'signal_day': '2017-01-06', 'security_id': 'SYNTHETIC:OUT%d' % i,
             'score': {'total': t, 'q': t, 'g': t, 'v': t}, 'rank': {'official': k, 'personal': None, 'of': 10}}
            for i, (t, k) in enumerate([(85, 2), (75, 5)])]


def cases(inputs):
    base = inputs['join_inputs']['same_date_same_security']
    rows, links, conditions = base['qgv_rows'], base['security_links'], base['conditions']
    out = {}
    def put(name, what, qgv_rows, security_links=links, population=None):
        out[name] = {'what': what, 'qgv_rows': qgv_rows, 'security_links': security_links, 'conditions': conditions,
                     **({'population': population} if population is not None else {})}
    a = split(rows)
    put('a_code_row_id_differs_from_issuer', 'id = company code row, issuer_id = issuer', a)
    put('b_issuer_id_explicit_null', 'one row issuer_id null (never falls back to id)', [dict(a[0], issuer_id=None)] + a[1:])
    put('c1_issuer_id_empty', "one row issuer_id ''", [dict(a[0], issuer_id='')] + a[1:])
    put('c2_issuer_id_other_issuer', 'one row issuer_id of another issuer', [dict(a[0], issuer_id='SYNTHETIC:ISSUER:3')] + a[1:])
    put('c3_issuer_id_number', 'one row issuer_id a number', [dict(a[0], issuer_id=1)] + a[1:])
    put('d_legacy_rows_without_issuer_id', 'legacy rows: no issuer_id field, id = issuer', copy.deepcopy(rows))
    # e: securities 001 and 003 belong to one issuer (ISSUER:1): two code rows, two links, one issuer_id.
    e_id = {'SYNTHETIC:001': 'COMPANY:SYNTHETIC:CODE:1A', 'SYNTHETIC:003': 'COMPANY:SYNTHETIC:CODE:1B'}
    e_rows = [dict(r, id=e_id.get(r['security_id'], 'COMPANY:' + r['id']),
                   issuer_id='SYNTHETIC:ISSUER:1' if r['security_id'] in ('SYNTHETIC:001', 'SYNTHETIC:003') else r['id']) for r in rows]
    e_links = [dict(l, issuer_id='SYNTHETIC:ISSUER:1') if l['security_id'] in ('SYNTHETIC:001', 'SYNTHETIC:003') else dict(l) for l in links]
    put('e_two_code_rows_one_issuer', 'two securities of one issuer kept as two rows', e_rows, e_links)
    population = a[:1] + extra_rows()[:1] + a[1:] + extra_rows()[1:]
    put('f1_whole_population', 'board group smaller than the population: every population row passed', population, population=population)
    put('f2_group_rows_only', 'board group smaller than the population: exactly the group rows passed', a, population=population)
    put('g1_member_link_missing', 'a group member\'s link missing', a, [l for l in links if l['security_id'] != 'SYNTHETIC:001'])
    put('g2_member_row_absent', 'a group member\'s row absent (Codex cannot see the group; Main groupRows refuses first)',
        [r for r in a if r['security_id'] != 'SYNTHETIC:001'])
    return out


def run(board, case):
    before = copy.deepcopy(case)
    try:
        kept = join_filtered_rows(board, qgv_rows=case['qgv_rows'], security_links=case['security_links'],
                                  conditions=case['conditions'], data_kind='SYNTHETIC')
        result = {'ok': True, 'kept': [{'id': r['id'], 'issuer_id': r.get('issuer_id'), 'security_id': r['security_id'],
                                        'rank_official': r['rank']['official'], 'rank_of': r['rank']['of'], 'total': r['score']['total']} for r in kept]}
    except ValueError as exc:
        result = {'ok': False, 'code': str(exc)}
    if case != before:
        raise SystemExit('CODEX_JOIN_MUTATED_INPUT')
    return result


def build():
    if hashlib.sha256(CODEX.read_bytes()).hexdigest() != CODEX_SHA256:
        raise SystemExit('CODEX_JOIN_FIXTURE_PIN_MISMATCH')
    inputs = json.loads(CODEX.read_text())
    board = inputs['cases']['original_board']
    made = cases(inputs)
    return {'schema_version': 'main-technical-filter-join-cases/1', 'data_kind': 'SYNTHETIC',
            'made_by': 'implementation/tools/technical_filter_join_main_cases.py (Codex join_filtered_rows output only)',
            'codex_fixture': {'path': 'implementation/tests/research/fixtures/technical_filter_join_v1/inputs.json', 'sha256': CODEX_SHA256},
            'board': board, 'cases': {name: {**c, 'codex': run(board, c)} for name, c in made.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    body = text(build())
    if args.check:
        if not OUT.exists() or OUT.read_text() != body:
            print('MAIN_JOIN_CASES_DIFFER_FROM_CODEX_OUTPUT', file=sys.stderr); return 1
        print('OK ' + hashlib.sha256(body.encode()).hexdigest()); return 0
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(body)
    print('WROTE ' + hashlib.sha256(body.encode()).hexdigest())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
