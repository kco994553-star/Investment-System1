"""Universe Completeness Gate + Top-500 Sufficiency Gate (independent Promotion
Gate extensions). No network. All evidence here is synthetic/offline-computed."""
import importlib.util, json
from datetime import datetime, timezone
from pathlib import Path
from investment_system.ingestion.raw_store import RawDatasetStore
UTC = timezone.utc

def load_tool():
    p = Path(__file__).parents[1] / 'tools' / 'audit_mcap_store.py'
    s = importlib.util.spec_from_file_location('audit_mcap_store2', p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

AS_OF = '2024-12-31T00:00:00+00:00'


# ---------- Universe Completeness Gate ----------

def test_completeness_gate_requires_dated_matching_benchmark():
    m = load_tool()
    audit = {'as_of': AS_OF, 'companyfacts': 3500, 'rankable': 3000}
    g = m.build_universe_completeness_gate(audit, None)
    assert g['passed'] is False
    assert 'MISSING_BENCHMARK_SOURCE' in g['reasons']
    ref = {'source': 'WFE', 'source_vintage': '2025-01-15', 'as_of': '2025-06-30T00:00:00+00:00',
           'total_estimate_low': 3400, 'total_estimate_high': 3700}
    mismatched = m.build_universe_completeness_gate(audit, ref)
    assert 'BENCHMARK_AS_OF_MISMATCH' in mismatched['reasons']


def test_completeness_gate_never_true_from_count_alone_below_threshold():
    m = load_tool()
    ref = {'source': 'WFE Dec 2024', 'source_vintage': '2025-01-15', 'as_of': AS_OF,
           'total_estimate_low': 3400, 'total_estimate_high': 3700}
    thin = m.build_universe_completeness_gate({'as_of': AS_OF, 'companyfacts': 598, 'rankable': 297}, ref)
    assert thin['passed'] is False
    assert 'COMPANYFACTS_COVERAGE_BELOW_BENCHMARK_LOW_ESTIMATE' in thin['reasons']
    assert round(thin['coverage_ratio'], 3) == round(598 / 3400, 3)


def test_completeness_gate_can_pass_on_real_coverage_but_stays_separate_from_pool_complete():
    m = load_tool()
    ref = {'source': 'WFE Dec 2024', 'source_vintage': '2025-01-15', 'as_of': AS_OF,
           'total_estimate_low': 3400, 'total_estimate_high': 3700}
    full = m.build_universe_completeness_gate({'as_of': AS_OF, 'companyfacts': 3450, 'rankable': 3200}, ref)
    assert full['passed'] is True
    # The gate itself never emits candidate_pool_complete=True -- that stays the
    # v2 promotion gate's job, and only after combining with the base gate.
    assert 'candidate_pool_complete' not in full


# ---------- Top-500 Sufficiency Gate ----------

def _audit(rankable, cutoff=1e9):
    return {'as_of': AS_OF, 'rankable': rankable, 'top_cutoff_mcap_if_500_rankable': cutoff}


def test_sufficiency_gate_fails_with_no_reference():
    m = load_tool()
    g = m.build_top500_sufficiency_gate(_audit(600), [])
    assert g['passed'] is False
    assert 'NO_LARGE_CAP_REFERENCE_SUPPLIED' in g['reasons']


def test_sufficiency_gate_rejects_undated_current_roster_as_survivorship_risk():
    m = load_tool()
    ref = {'name': 'SP500', 'source': 'wikipedia', 'source_vintage': '2026-09-24', 'as_of': AS_OF,
           'membership_basis': 'UNDATED_ROSTER', 'members': ['AAPL'],
           'missing_from_pool': [], 'present_not_rankable': [], 'present_rankable_outside_top500': []}
    g = m.build_top500_sufficiency_gate(_audit(600), [ref])
    assert g['passed'] is False
    assert g['references'][0]['passed'] is False
    assert 'UNDATED_ROSTER_SURVIVORSHIP_RISK' in g['references'][0]['reasons']


def test_sufficiency_gate_flags_missing_and_unranked_large_caps():
    m = load_tool()
    ref = {'name': 'SP500-asof', 'source': 'fja05680/sp500', 'source_vintage': '2026-09-24', 'as_of': AS_OF,
           'membership_basis': 'RECONSTRUCTED_LATER_VINTAGE', 'members': ['AAPL', 'GOOGL', 'MSFT'],
           'missing_from_pool': ['ZZZZ'], 'present_not_rankable': ['GOOGL'], 'present_rankable_outside_top500': []}
    g = m.build_top500_sufficiency_gate(_audit(600), [ref])
    assert g['passed'] is False
    r = g['references'][0]
    assert 'MISSING_LARGE_CAP_NAMES' in r['reasons'] and r['missing_from_pool'] == ['ZZZZ']
    assert 'REFERENCE_MEMBERS_PRESENT_BUT_NOT_RANKABLE' in r['reasons'] and r['present_not_rankable'] == ['GOOGL']


def test_sufficiency_gate_passes_only_when_a_reference_is_fully_clean_and_rankable_ge_500():
    m = load_tool()
    clean = {'name': 'SP500-asof', 'source': 'fja05680/sp500', 'source_vintage': '2026-09-24', 'as_of': AS_OF,
              'membership_basis': 'RECONSTRUCTED_LATER_VINTAGE', 'members': ['AAPL', 'MSFT'],
              'missing_from_pool': [], 'present_not_rankable': [], 'present_rankable_outside_top500': []}
    under500 = m.build_top500_sufficiency_gate(_audit(499), [clean])
    assert under500['passed'] is False and 'FEWER_THAN_500_RANKABLE' in under500['reasons']
    g = m.build_top500_sufficiency_gate(_audit(600), [clean])
    assert g['passed'] is True
    assert g['n_references_usable'] == 1
    # One dirty and one clean reference: still passes on the strength of the clean one.
    dirty = {**clean, 'name': 'Russell1000-asof', 'missing_from_pool': ['FOO']}
    mixed = m.build_top500_sufficiency_gate(_audit(600), [dirty, clean])
    assert mixed['passed'] is True and mixed['n_references_usable'] == 1
    assert mixed['references'][0]['passed'] is False and mixed['references'][1]['passed'] is True


def test_sufficiency_gate_needs_a_cutoff_even_with_a_clean_reference():
    m = load_tool()
    clean = {'name': 'SP500-asof', 'source': 'fja05680/sp500', 'source_vintage': '2026-09-24', 'as_of': AS_OF,
              'membership_basis': 'RECONSTRUCTED_LATER_VINTAGE', 'members': ['AAPL'],
              'missing_from_pool': [], 'present_not_rankable': [], 'present_rankable_outside_top500': []}
    g = m.build_top500_sufficiency_gate(_audit(600, cutoff=None), [clean])
    assert g['passed'] is False and 'NO_CUTOFF_MCAP_COMPUTED' in g['reasons']


# ---------- evaluate_reference_coverage: real store-driven identity check ----------

def test_evaluate_reference_coverage_classifies_by_store_presence(tmp_path):
    m = load_tool()
    store = RawDatasetStore(tmp_path / 'raw')
    cf = {'facts': {'dei': {'EntityCommonStockSharesOutstanding': {'units': {'shares': [
        {'filed': '2024-11-01', 'val': 100}]}}}}}
    store.put('companyfacts:0000000001', json.dumps(cf).encode(), 'u', 'SEC', 'application/json', 't', 200)
    chart = {'chart': {'result': [{'timestamp': [int(datetime(2024, 12, 1, tzinfo=UTC).timestamp())],
              'indicators': {'quote': [{'close': [12.0]}]}}], 'error': None}}
    store.put('yahoo_chart:AAA:5y', json.dumps(chart).encode(), 'u', 'YAHOO', 'application/json', 't', 200)
    # BBB: companyfacts present but no usable shares/price -> present_not_rankable.
    store.put('companyfacts:0000000002', json.dumps({'facts': {}}).encode(), 'u', 'SEC', 'application/json', 't', 200)
    listings = {'a': {'cik': '1', 'yahoo': 'AAA'}, 'b': {'cik': '2', 'yahoo': 'BBB'}}
    ref = {'name': 'X', 'source': 's', 'source_vintage': 'v', 'as_of': AS_OF,
           'membership_basis': 'DATED_INTERVALS', 'members': ['AAA', 'BBB', 'ZZZ']}
    out = m.evaluate_reference_coverage(store, listings, ranked_top500_tickers=set(), reference=ref)
    assert out['missing_from_pool'] == ['ZZZ']
    assert out['present_not_rankable'] == ['BBB']
    assert out['present_rankable_outside_top500'] == ['AAA']
    # AAA already in the ranked top-500 set -> neither missing nor flagged.
    in_top500 = m.evaluate_reference_coverage(store, listings, ranked_top500_tickers={'AAA'}, reference=ref)
    assert in_top500['present_rankable_outside_top500'] == []


# ---------- Combined v2 Promotion Gate ----------

def test_v2_gate_requires_base_gate_and_one_of_completeness_or_sufficiency():
    m = load_tool()
    ev = {'as_of': AS_OF, 'source': 'dated-us-listing-snapshot', 'source_vintage': '2025-01-02', 'eligibility_complete': True}
    audit = {'as_of': AS_OF, 'listings': 600, 'rankable': 600, 'top_cutoff_mcap_if_500_rankable': 1e9}
    # No sub-gates at all: base passes numerically, but neither independent path passed.
    g = m.build_promotion_gate_v2(audit, ev, None, None)
    assert g['passed'] is False
    assert 'NEITHER_COMPLETENESS_NOR_SUFFICIENCY_GATE_PASSED' in g['reasons']
    # A passing sufficiency gate alone is enough, even with a failing/absent completeness gate.
    clean = {'name': 'SP500-asof', 'source': 'fja05680/sp500', 'source_vintage': '2026-09-24', 'as_of': AS_OF,
              'membership_basis': 'RECONSTRUCTED_LATER_VINTAGE', 'members': ['AAPL'],
              'missing_from_pool': [], 'present_not_rankable': [], 'present_rankable_outside_top500': []}
    suf = m.build_top500_sufficiency_gate(audit, [clean])
    g2 = m.build_promotion_gate_v2(audit, ev, None, suf)
    assert g2['passed'] is True and g2['candidate_pool_complete'] is True and g2['justified_official_top500'] is True
    assert g2['completeness_gate_passed'] is False and g2['sufficiency_gate_passed'] is True


def test_v2_gate_still_fails_closed_if_base_numeric_checks_fail_even_with_clean_sufficiency():
    m = load_tool()
    ev = {'as_of': AS_OF, 'source': 's', 'source_vintage': 'v', 'eligibility_complete': True}
    audit = {'as_of': AS_OF, 'listings': 600, 'rankable': 400, 'top_cutoff_mcap_if_500_rankable': 1e9}  # not all rankable, <500
    clean = {'name': 'X', 'source': 's', 'source_vintage': 'v', 'as_of': AS_OF,
              'membership_basis': 'DATED_INTERVALS', 'members': ['AAPL'],
              'missing_from_pool': [], 'present_not_rankable': [], 'present_rankable_outside_top500': []}
    suf = m.build_top500_sufficiency_gate(audit, [clean])
    g = m.build_promotion_gate_v2(audit, ev, None, suf)
    assert g['passed'] is False
    assert g['base_gate']['passed'] is False


def test_cli_v2_gate_end_to_end_fail_closed(tmp_path, monkeypatch):
    m = load_tool()
    store = RawDatasetStore(tmp_path / 'raw')
    listings_path = tmp_path / 'listings.json'
    listings_path.write_text(json.dumps({}), encoding='utf-8')
    ev_path = tmp_path / 'ev.json'
    ev_path.write_text(json.dumps({'as_of': AS_OF, 'source': 'x', 'source_vintage': 'v', 'eligibility_complete': True}), encoding='utf-8')
    out = tmp_path / 'gate2.json'
    monkeypatch.setattr('sys.argv', ['audit_mcap_store.py', '--store', str(tmp_path / 'raw'), '--listings', str(listings_path),
                                      '--as-of', AS_OF, '--eligibility-evidence', str(ev_path), '--gate-v2-out', str(out)])
    m.main()
    g = json.loads(out.read_text(encoding='utf-8'))
    assert g['passed'] is False
    assert 'NEITHER_COMPLETENESS_NOR_SUFFICIENCY_GATE_PASSED' in g['reasons']
