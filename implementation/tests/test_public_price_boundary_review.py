"""Final-review regressions use invented SEC rows and deny all external transport."""
from copy import deepcopy
from datetime import datetime, timezone
import inspect
import json
import zipfile

import pytest

from investment_system.ingestion.raw_store import RawDatasetStore
from investment_system.providers.sec_m1 import build_input
from investment_system.providers.sec_vintage import resolve_vintages, select_latest
from investment_system.public_price_boundary import PublicPriceBoundaryError, project_companyfacts
from tests.test_public_price_boundary import tool, prohibit_network
from tests.test_sec_m1_provider import payloads, fact, CIK, ACQUIRED


def ingest(tmp_path, monkeypatch, kind, facts):
    store = RawDatasetStore(tmp_path / 'store')
    if kind == 'network':
        module = tool('fetch_real_data')
        class Response:
            status = 200
            headers = {'Content-Type': 'application/json'}
            def read(self): return json.dumps(facts).encode()
            def __enter__(self): return self
            def __exit__(self, *args): return False
        monkeypatch.setattr(module, 'urlopen', lambda *args, **kwargs: Response())
        module._fetch_one(store, 'companyfacts:' + CIK, module.SEC_FACTS_URL.format(cik=CIK),
                          'SEC_COMPANYFACTS', '', [])
    else:
        archive = tmp_path / 'facts.zip'
        with zipfile.ZipFile(archive, 'w') as handle:
            handle.writestr('CIK' + CIK + '.json', json.dumps(facts))
        result = tool('import_bulk_real_data').import_sec(store, archive, False)
        if not result['imported']:
            assert result['bad'] == 1
            raise PublicPriceBoundaryError('PUBLIC_PRICE_BOUNDARY: route withheld under GSQ-010')
    return store


@pytest.mark.parametrize('kind', ['network', 'bulk'])
def test_admitted_financial_ingestion_retains_identity_and_existing_m1_result(tmp_path, monkeypatch, kind):
    facts, submissions = payloads()
    original = build_input('nvda', facts, submissions, ACQUIRED, ACQUIRED)
    assert original['status'] == 'READY'
    store = ingest(tmp_path, monkeypatch, kind, facts)
    projected = json.loads(store.get_bytes('companyfacts:' + CIK))
    assert projected['cik'] == CIK
    result = build_input('nvda', projected, submissions, ACQUIRED, ACQUIRED)
    assert result['status'] == 'READY'
    assert result['selected_input_facts'] == original['selected_input_facts']
    assert result['raw_fundamentals']['revenue'] == original['raw_fundamentals']['revenue']


@pytest.mark.parametrize('kind', ['network', 'bulk'])
@pytest.mark.parametrize('cik', [None, True, 1045810.0, ' 1045810', '١٠٤٥٨١٠', '00001045810', 789019, {'renamed': 1}])
def test_invalid_or_mismatched_cik_never_reaches_store(tmp_path, monkeypatch, kind, cik):
    facts, _ = payloads()
    facts['cik'] = cik
    with pytest.raises(PublicPriceBoundaryError):
        ingest(tmp_path, monkeypatch, kind, facts)
    assert RawDatasetStore(tmp_path / 'store').list_ids() == []


def test_unsupported_form_cannot_become_unlabeled_eligible_fact():
    facts, _ = payloads(rows=[fact(form='S-1')])
    original = resolve_vintages(facts, 'us-gaap', 'Revenues', 'USD', ACQUIRED, '10-K')
    assert original == []
    projected = project_companyfacts(facts)
    assert resolve_vintages(projected, 'us-gaap', 'Revenues', 'USD', ACQUIRED, '10-K') == []


@pytest.mark.parametrize('change', [
    {'form': 'S-1'}, {'form': None}, {'form': ''}, {'form': []},
    {'fy': 'UNREVIEWED'}, {'fy': True}, {'fy': []}, {'fp': 'UNREVIEWED'}, {'fp': []},
    {'accn': 'UNREVIEWED'}, {'accn': None}, {'frame': 'UNREVIEWED'},
    {'filed': '2025-99-99'}, {'start': '2024-99-99'}, {'end': '2024-99-99'},
])
def test_invalid_selection_metadata_excludes_whole_row(change):
    facts, _ = payloads(rows=[fact(**change)])
    projected = project_companyfacts(facts)
    assert projected['facts']['us-gaap']['Revenues']['units']['USD'] == []


@pytest.mark.parametrize('fy', [2024, '2024'])
def test_valid_selection_metadata_and_amendment_order_are_preserved_exactly(fy):
    rows = [fact(fy=fy, frame='CY2024'), fact(fy=fy, form='10-K/A', val=101, filed='2025-02-02',
              accn='0001045810-25-000002', frame='CY2024')]
    facts, _ = payloads(rows=rows)
    before = deepcopy(facts)
    projected = project_companyfacts(facts)
    assert facts == before
    assert projected['facts']['us-gaap']['Revenues']['units']['USD'] == rows
    before_vintages = resolve_vintages(facts, 'us-gaap', 'Revenues', 'USD', ACQUIRED, '10-K')
    after_vintages = resolve_vintages(projected, 'us-gaap', 'Revenues', 'USD', ACQUIRED, '10-K')
    assert after_vintages == before_vintages
    assert select_latest(after_vintages) == select_latest(before_vintages)


STORE_PRICE_ENTRYPOINTS = {
    'run_top500_gate_chain': [
        'eligibility_filter', '_as_of_price', 'share_scale_overrides', '_as_of_bar',
        'gate_audited_candidates', 'gate_snapshot_consistency', 'registration_share_count_overrides',
        'cover_mcap_overrides', 'apply_nport_reported_prices',
        'apply_corporate_action_share_counts', 'apply_corporate_action_prices',
    ],
    'audit_mcap_store': ['build_pit_gap_plan', 'evaluate_reference_coverage'],
    'fetch_stooq_prices': ['target_symbols'],
}


class UnreadableStore:
    def __getattr__(self, name):
        raise AssertionError('stored input must not be accessed')


@pytest.mark.parametrize('module_name,function', [(m, f) for m, fs in STORE_PRICE_ENTRYPOINTS.items() for f in fs])
def test_all_exposed_stored_price_paths_block_before_dependencies(module_name, function, monkeypatch):
    module = tool(module_name)
    def forbidden(*args, **kwargs):
        raise AssertionError('stored price dependency reached')
    for name in ('load_price_bars', 'load_companyfacts', 'load_submissions', 'official_mcap500_snapshot_from_store', '_load'):
        if hasattr(module, name): monkeypatch.setattr(module, name, forbidden)
    fn = getattr(module, function)
    args = [UnreadableStore() if p.name == 'store' else None
            for p in inspect.signature(fn).parameters.values() if p.default is inspect.Parameter.empty]
    with pytest.raises(PublicPriceBoundaryError):
        fn(*args)
