"""3.5 tech filter join counterexamples (owner 2026-11-08, Codex #437 6714613662): the committed case file is exactly
Codex join_filtered_rows' output on inputs made from Codex's own fixture (tools/technical_filter_join_main_cases.py)."""
import copy
import json
import subprocess
import sys
from pathlib import Path

from investment_system.research.technical_filter_join import join_filtered_rows

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / 'tests/fixtures/technical_filter_join_main/cases.json'
TOOL = ROOT / 'tools/technical_filter_join_main_cases.py'


def load():
    return json.loads(CASES.read_text())


def test_committed_cases_are_exactly_the_codex_output():
    r = subprocess.run([sys.executable, str(TOOL), '--check'], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr


def test_case_outcomes_and_inputs_never_mutated():
    d = load(); c = d['cases']; codes = {k: v['codex'].get('code') for k, v in c.items()}
    assert codes['b_issuer_id_explicit_null'] == codes['c1_issuer_id_empty'] == codes['c2_issuer_id_other_issuer'] == codes['c3_issuer_id_number'] == 'ISSUER_LINK_MISMATCH'
    assert codes['f1_whole_population'] == 'SECURITY_ID_NOT_IN_BOARD' and codes['g1_member_link_missing'] == 'FIXED_SECURITY_LINK_MISSING'
    ranks = lambda k: [(r['rank_official'], r['rank_of']) for r in c[k]['codex']['kept']]
    for k in ('a_code_row_id_differs_from_issuer', 'd_legacy_rows_without_issuer_id', 'e_two_code_rows_one_issuer', 'f2_group_rows_only'):
        assert c[k]['codex']['ok'] and ranks(k) == [(4, 10), (9, 10)], k
    e = c['e_two_code_rows_one_issuer']['codex']['kept']
    assert len({r['id'] for r in e}) == 2 and {r['issuer_id'] for r in e} == {'SYNTHETIC:ISSUER:1'}
    # Codex sees only the rows it is given: an absent group member is not detected here (Main's groupRows refuses first).
    assert ranks('g2_member_row_absent') == [(9, 10)]
    population = copy.deepcopy(c['f2_group_rows_only']['population'])
    for k in ('f1_whole_population', 'f2_group_rows_only'):
        case = c[k]
        try:
            join_filtered_rows(d['board'], qgv_rows=case['qgv_rows'], security_links=case['security_links'], conditions=case['conditions'], data_kind='SYNTHETIC')
        except ValueError:
            pass
        assert case['population'] == population, 'out-of-group rows unchanged'
