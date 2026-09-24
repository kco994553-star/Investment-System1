"""Candidate hygiene heuristic: flags, never deletes; pattern-based only."""
import importlib.util
from pathlib import Path

def load_tool():
    p = Path(__file__).parents[1] / 'tools' / 'audit_candidate_hygiene.py'
    s = importlib.util.spec_from_file_location('audit_candidate_hygiene', p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def test_classifies_preferred_and_otc_adr_shapes_and_leaves_the_rest_clean():
    m = load_tool()
    listings = {
        'a': {'yahoo': 'AAPL'}, 'b': {'yahoo': 'BAC-PL'}, 'c': {'yahoo': 'ALL-PH'},
        'd': {'yahoo': 'AEMRF'}, 'e': {'yahoo': 'BBAAY'}, 'f': {'yahoo': 'MSFT'},
        'g': {'yahoo': 'GOOGL'},  # 5 letters but doesn't end in F/Y -> clean
    }
    r = m.audit_hygiene(listings)
    assert r['n_total'] == 7 and r['n_flagged'] == 4 and r['n_clean'] == 3
    assert r['flagged']['PREFERRED_SHARE_SUFFIX'] == ['b', 'c']
    assert r['flagged']['FIVE_LETTER_F_OR_Y_OTC_ADR_SHAPE'] == ['d', 'e']
    assert set(r['clean_company_ids']) == {'a', 'f', 'g'}


def test_never_mutates_input_or_claims_authority():
    m = load_tool()
    listings = {'x': {'yahoo': 'BAC-PL', 'cik': '123'}}
    before = dict(listings)
    r = m.audit_hygiene(listings)
    assert listings == before  # untouched
    assert 'heuristic' in r['note'].lower() or 'HEURISTIC' in r['kind']


def test_missing_or_empty_ticker_is_not_flagged_or_crashed_on():
    m = load_tool()
    r = m.audit_hygiene({'a': {}, 'b': {'yahoo': ''}})
    assert r['n_flagged'] == 0 and r['n_clean'] == 2


def test_cli_writes_report(tmp_path):
    m = load_tool()
    listings_path = tmp_path / 'listings.json'
    import json
    listings_path.write_text(json.dumps({'a': {'yahoo': 'BAC-PL'}}), encoding='utf-8')
    out = tmp_path / 'out.json'
    import sys
    old_argv = sys.argv
    try:
        sys.argv = ['audit_candidate_hygiene.py', '--listings', str(listings_path), '--out', str(out)]
        m.main()
    finally:
        sys.argv = old_argv
    r = json.loads(out.read_text(encoding='utf-8'))
    assert r['n_flagged'] == 1
