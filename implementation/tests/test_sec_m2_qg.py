"""Independent synthetic M1 receipts exercise the offline M2 admission boundary."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from investment_system.contracts.raw import RawFundamentals
from investment_system.ingestion import sec_m1
from investment_system.markets.us import US_LISTINGS
from investment_system.producers.adapters import leaderboard_section, qgv_section
from investment_system.producers.serialization import canonical_bytes, canonical_sha256, to_jsonable
from investment_system.qgv.analysis import AnalysisEngine
from investment_system.qgv.factors import G_WEIGHTS, Q_WEIGHTS, V_INITIAL_PRIOR
from investment_system.qgv.g_horizon import GHorizonConfig, assess_horizon
from investment_system.qgv.leaderboard import LeaderboardEngine
from investment_system.qgv.raw_map import map_raw

AT = datetime(2025, 3, 1, 10, tzinfo=timezone.utc)
FINANCIAL = ('revenue', 'revenue_prev', 'ebit', 'ebit_prev', 'fcf', 'net_income', 'equity',
             'invested_capital', 'cash', 'total_debt', 'shares', 'eps', 'eps_prev')
METRICS = {
    'Revenues': (250, 100, 'USD'), 'OperatingIncomeLoss': (75, None, 'USD'),
    'FreeCashFlow': (50, None, 'USD'), 'CashAndCashEquivalentsAtCarryingValue': (150, None, 'USD'),
    'LongTermDebt': (10, None, 'USD'), 'StockholdersEquity': (20, None, 'USD'),
    'EarningsPerShareDiluted': (5, 2, 'USD/shares'), 'NetIncomeLoss': (30, None, 'USD'),
    'CommonStockSharesOutstanding': (10, None, 'shares'),
}
INSTANT = {'CashAndCashEquivalentsAtCarryingValue', 'LongTermDebt', 'StockholdersEquity',
           'CommonStockSharesOutstanding'}


def m2():
    try:
        return import_module('investment_system.qgv.sec_m2')
    except ModuleNotFoundError:
        pytest.fail('The offline SEC M2 candidate API has not been implemented')


def payloads(company='nvda', metrics=None, *, form='10-K'):
    """Fresh facts authored for this boundary, rather than production fixture copies."""
    metrics = METRICS if metrics is None else metrics
    cik = US_LISTINGS[company]['cik']
    facts = {'cik': int(cik), 'facts': {'us-gaap': {}}}
    accn = f'{cik}-25-000777'
    for concept, (current, previous, unit) in metrics.items():
        rows = []
        for year, value in ((2024, current), (2023, previous)):
            if value is None:
                continue
            row = {'end': f'{year}-12-31', 'val': value, 'filed': '2025-02-01',
                   'form': form, 'accn': accn, 'fy': year, 'fp': 'FY'}
            if concept not in INSTANT:
                row['start'] = f'{year}-01-01' if form == '10-K' else f'{year}-10-01'
            rows.append(row)
        facts['facts']['us-gaap'][concept] = {'units': {unit: rows}}
    submissions = {'cik': cik, 'filings': {'recent': {
        'form': [form], 'filingDate': ['2025-02-01'], 'accessionNumber': [accn],
        'acceptanceDateTime': ['2025-02-01T21:00:00Z']}}}
    return facts, submissions


def retain(store, company='nvda', metrics=None, *, acquired_at=AT, as_of=AT, form='10-K', bodies=None):
    facts, submissions = payloads(company, metrics, form=form) if bodies is None else bodies
    return sec_m1.retain_input(store, company, json.dumps(facts).encode(), json.dumps(submissions).encode(),
                               acquired_at, as_of, form_filter=form)


def analyze(store, receipts, *, as_of=AT, evaluated_at=AT, synthetic=True):
    return m2().analyze_receipts(store, [r['receipt_id'] if isinstance(r, dict) else r for r in receipts],
                                 as_of, evaluated_at=evaluated_at, synthetic_inputs=synthetic)


def direct(receipt, as_of=AT, synthetic=True):
    normalized = receipt['input']['raw_fundamentals']
    stamp = SimpleNamespace(data_stamp_id=normalized['stamp']['data_stamp_id'], synthetic=synthetic)
    raw = RawFundamentals(company_id=receipt['input']['company_id'], stamp=stamp,
                          source_kind='OBSERVED_RAW_INPUT', **{k: normalized[k] for k in FINANCIAL})
    observations = map_raw(raw)
    snapshot = AnalysisEngine().analyze(raw.company_id, as_of, observations, synthetic=synthetic,
        data_stamp_refs=(stamp.data_stamp_id,), g_horizon=to_jsonable(assess_horizon(GHorizonConfig(), 0)))
    return observations, snapshot


def test_native_fixed_weights_and_adapters_are_reused_with_all_twenty_observations(tmp_path):
    receipt = retain(tmp_path)
    result = analyze(tmp_path, [receipt])
    record = result['companies']['nvda']
    actual = result['candidate_data']['qgv']['data']['nvda']
    observations, expected = direct(receipt)
    expected = replace(expected, qgv_snapshot_id=actual['qgv_snapshot_id'])
    assert actual == qgv_section([expected])[1]['nvda']
    assert (actual['Q_score'], actual['G_score'], actual['V_score'], actual['total_score']) == (35, 75, None, 55)
    assert actual['attractiveness_10'] == expected.attractiveness_10
    assert actual['type_adjusted_score_100'] == 55
    assert actual['standard'] == 'v1' and actual['calibration'] == 'UNCALIBRATED'
    assert actual['confidence'] == 'MEDIUM'
    assert len(record['factors']) == 20
    for fid, observation in observations.items():
        factor = record['factors'][fid]
        assert factor['observation'] == to_jsonable(observation)
        assert factor['weight'] == {**Q_WEIGHTS, **G_WEIGHTS, **V_INITIAL_PRIOR}[fid]
        assert factor['source_references']['receipt_id'] == receipt['receipt_id']
        assert factor['source_references']['selected_input_facts'] == receipt['input']['selected_input_facts']
        assert factor['source_trace_basis'] == 'SUPPORTING_SELECTED_FACT_POOL_NOT_EXACT_FIELD_EXTRACTION'
    assert record['coverage']['Q_observed_weight'] == pytest.approx(.35)
    assert record['coverage']['G_observed_weight'] == pytest.approx(.75)
    assert record['score_basis'] == 'LEGACY_QG_ONLY'
    native_lb = LeaderboardEngine().build('SEC_M2_EXPLICIT_SUBSET', AT, [expected])
    native_lb = replace(native_lb, leaderboard_snapshot_id=result['candidate_data']['leaderboard']['data']['leaderboard_snapshot_id'])
    assert result['candidate_data']['leaderboard']['data'] == leaderboard_section(native_lb)[1]
    assert result['candidate_data']['leaderboard']['rank_basis'] == 'EXPLICIT_SUBSET_LEGACY_QG_ONLY_CANDIDATE'
    assert result['research_state']['status'] == 'PROVISIONAL_RESEARCH'
    assert result['contract'] == 'OFFLINE_SEC_QG_CANDIDATE'
    assert result['candidate_only'] and not result['prices_used'] and not result['publication_approved']
    assert not result['full_pit_historical'] and not result['real_data_verified']
    assert canonical_bytes(result)


def test_v_reasons_and_empty_context_cannot_be_backfilled_from_arbitrary_sec_concepts(tmp_path):
    bodies = payloads()
    bodies[0]['facts']['us-gaap']['SectorContextScore'] = {'units': {'pure': []}}
    receipt = retain(tmp_path, bodies=bodies)
    record = analyze(tmp_path, [receipt])['companies']['nvda']
    factors = record['factors']
    for fid in V_INITIAL_PRIOR:
        assert factors[fid]['status'] == 'NOT_AVAILABLE'
        assert factors[fid]['observation']['score_0_100'] is None
        assert factors[fid]['observation']['quality'] == 'MISSING_DATA'
    assert factors['fundamental_value']['reason_codes'] == ['MISSING_PRICE_AND_VALUATION_INPUTS']
    assert factors['margin_of_safety']['reason_codes'] == ['MISSING_PRICE_AND_VALUATION_INPUTS']
    assert factors['reverse_dcf']['reason_codes'] == ['MISSING_PRICE_OR_INDEPENDENT_IMPLIED_GROWTH_INPUT']
    assert factors['sector_context']['reason_codes'] == ['MISSING_SECTOR_CONTEXT_SOURCE']
    assert factors['theme_premium_discount']['reason_codes'] == ['MISSING_THEME_CONTEXT_SOURCE']
    assert factors['peer_relative_value']['reason_codes'] == ['MISSING_PEER_VALUATION_SOURCE']
    assert factors['historical_valuation']['reason_codes'] == ['MISSING_VALUATION_HISTORY_SOURCE']
    assert set(record['normalized_financial_fields']) == set(FINANCIAL)
    for field in ('price', 'wacc', 'dcf_value', 'own_multiple', 'sector_context_score', 'growth_durability_rubric'):
        assert field not in record['normalized_financial_fields']


@pytest.mark.parametrize('metrics,q,g,expected_status', [
    ({'Revenues': (100, 100, 'USD'), 'FreeCashFlow': (0, None, 'USD')}, 7.5, 20, 'CALCULATED'),
    ({'Revenues': (100, 100, 'USD'), 'FreeCashFlow': (-15, None, 'USD')}, 0, 20, 'CALCULATED'),
    ({'Revenues': (100, 100, 'USD')}, None, 20, 'NOT_AVAILABLE'),
    ({'Revenues': (100, None, 'USD'), 'OperatingIncomeLoss': (25, None, 'USD')}, 10, None, 'NOT_AVAILABLE'),
    ({'Revenues': (0, 100, 'USD'), 'EarningsPerShareDiluted': (0, 1, 'USD/shares')}, None, 0, 'NOT_AVAILABLE'),
])
def test_partial_zero_and_one_sided_scores_keep_native_arithmetic(tmp_path, metrics, q, g, expected_status):
    receipt = retain(tmp_path, metrics=metrics)
    result = analyze(tmp_path, [receipt])
    record = result['companies']['nvda']
    assert record['status'] == expected_status
    payload = (result['candidate_data']['qgv']['data'] if expected_status == 'CALCULATED'
               else result['unavailable_snapshots'])['nvda']
    observations, native = direct(receipt)
    assert payload['Q_score'] == q and payload['G_score'] == g
    assert payload['total_score'] == native.total_score
    assert record['factors']['fcf_quality']['observation'] == to_jsonable(observations['fcf_quality'])
    assert len(result['candidate_data']['leaderboard']['data']['rows']) == int(expected_status == 'CALCULATED')
    assert record['normalized_financial_fields']['fcf'] == receipt['input']['raw_fundamentals']['fcf']


def test_no_supported_fields_is_unavailable_without_using_previous_pointer(tmp_path):
    ready = retain(tmp_path)
    empty = retain(tmp_path, metrics={}, acquired_at=AT + timedelta(minutes=1), as_of=AT + timedelta(minutes=1))
    assert sec_m1.load_latest(tmp_path, 'nvda')['receipt_id'] == ready['receipt_id']
    result = analyze(tmp_path, [empty], as_of=AT + timedelta(minutes=1), evaluated_at=AT + timedelta(minutes=1))
    assert result['companies']['nvda']['reason_codes'] == ['M1_NOT_AVAILABLE']
    assert not result['candidate_data']['qgv']['data']
    assert not result['candidate_data']['leaderboard']['data']['rows']


def test_acquisition_boundary_offsets_unknown_publication_and_horizon_are_preserved(tmp_path):
    receipt = retain(tmp_path)
    early = analyze(tmp_path, [receipt], as_of=AT - timedelta(microseconds=1))
    assert early['companies']['nvda']['reason_codes'] == ['ACQUISITION_AFTER_CUTOFF']
    offset = AT.astimezone(timezone(timedelta(hours=9)))
    result = analyze(tmp_path, [receipt], as_of=offset)
    record = result['companies']['nvda']
    assert record['status'] == 'CALCULATED'
    source = record['source']
    assert source['original_availability'] == receipt['input']['availability']
    assert source['original_stamp'] == receipt['input']['raw_fundamentals']['stamp']
    assert source['original_stamp']['published_at'] is None
    assert source['original_stamp']['estimated'] is True
    assert source['original_availability']['basis'] == 'OBSERVED_PUBLIC_API_UPPER_BOUND'
    assert source['acquired_at'] == AT.isoformat() and source['stored_as_of'] == AT.isoformat()
    assert source['source_freshness'] == source['original_stamp']['freshness_status']
    snapshot = result['candidate_data']['qgv']['data']['nvda']
    assert snapshot['as_of'] == AT.isoformat() and snapshot['analyzed_at'] == AT.isoformat()
    assert snapshot['g_horizon'] == to_jsonable(assess_horizon(GHorizonConfig(), 0))
    assert snapshot['g_horizon']['available_quarters'] == 0
    assert record['factors']['next_3_5y_growth']['observation']['notes'].endswith('proxy: last yoy; not a 3-5y forecast')


def test_quarterly_receipt_is_explicitly_unavailable_and_20f_remains_annual(tmp_path):
    quarterly = retain(tmp_path / 'q', form='10-Q')
    assert analyze(tmp_path / 'q', [quarterly])['companies']['nvda']['reason_codes'] == ['ANNUAL_FORM_REQUIRED']
    facts, subs = payloads('asml')
    for node in facts['facts']['us-gaap'].values():
        for rows in node['units'].values():
            for row in rows:
                row['form'] = '20-F'
    subs['filings']['recent']['form'] = ['20-F']
    annual = retain(tmp_path / 'annual', 'asml', bodies=(facts, subs))
    assert analyze(tmp_path / 'annual', [annual])['companies']['asml']['status'] == 'CALCULATED'


@pytest.mark.parametrize('as_of,evaluated_at', [(AT.replace(tzinfo=None), AT), (AT, AT.replace(tzinfo=None)),
                                              (AT + timedelta(seconds=1), AT)])
def test_invalid_clocks_fail_before_receipt_reads(tmp_path, monkeypatch, as_of, evaluated_at):
    receipt = retain(tmp_path)
    monkeypatch.setattr(sec_m1, 'load_receipt', lambda *args: pytest.fail('invalid clock reached storage'))
    with pytest.raises(ValueError, match='INVALID_CLOCK'):
        analyze(tmp_path, [receipt], as_of=as_of, evaluated_at=evaluated_at)


@pytest.mark.parametrize('receipt_ids', [[], ['x'], ['a' * 64] * 2, ['a' * 64] * 18, 'a' * 64, None])
def test_invalid_request_shape_is_rejected_without_creating_store(tmp_path, receipt_ids):
    absent = tmp_path / 'absent'
    with pytest.raises(ValueError, match='INVALID_RECEIPT_REQUEST'):
        m2().analyze_receipts(absent, receipt_ids, AT, evaluated_at=AT, synthetic_inputs=True)
    assert not absent.exists()


def test_store_must_exist_and_synthetic_flag_must_be_explicit_bool(tmp_path):
    absent = tmp_path / 'absent'
    with pytest.raises(ValueError, match='STORE_NOT_AVAILABLE'):
        analyze(absent, ['a' * 64])
    assert not absent.exists()
    receipt = retain(tmp_path / 'store')
    with pytest.raises(ValueError, match='INVALID_INPUT_KIND'):
        analyze(tmp_path / 'store', [receipt], synthetic='true')


def rewrite_receipt(store, receipt, mutate):
    modified = json.loads(json.dumps(receipt))
    mutate(modified)
    modified['receipt_id'] = canonical_sha256({k: modified[k] for k in sec_m1.CORE})
    modified.pop('receipt_sha256')
    modified['receipt_sha256'] = canonical_sha256(modified)
    (store / 'm1' / 'receipts' / (modified['receipt_id'] + '.json')).write_bytes(canonical_bytes(modified))
    return modified


@pytest.mark.parametrize('field,value', [('revenue', 987654321), ('revenue', True), ('fcf', 'not-a-number'),
                                        ('sector_context_score', 99), ('eps', None)])
def test_rehashed_semantic_input_tampering_is_blocked_by_original_cutoff_replay(tmp_path, field, value):
    receipt = retain(tmp_path)
    tampered = rewrite_receipt(tmp_path, receipt, lambda r: r['input']['raw_fundamentals'].__setitem__(field, value))
    assert sec_m1.load_receipt(tmp_path, tampered['receipt_id'])['receipt_id'] == tampered['receipt_id']
    result = analyze(tmp_path, [tampered])
    assert result['companies']['nvda']['reason_codes'] == ['ORIGINAL_REPLAY_MISMATCH']
    assert not result['candidate_data']['qgv']['data']


def test_exact_byte_corruption_bad_receipt_and_failure_isolation_never_load_latest(tmp_path, monkeypatch):
    broken = retain(tmp_path, 'nvda')
    good = retain(tmp_path, 'amd')
    artifact = broken['inputs']['companyfacts']['artifact_id']
    (tmp_path / 'blobs' / artifact.replace(':', '__')).write_bytes(b' altered exact bytes ')
    monkeypatch.setattr(sec_m1, 'load_latest', lambda *args: pytest.fail('M2 used latest fallback'))
    result = analyze(tmp_path, [broken, good, 'f' * 64])
    assert list(result['candidate_data']['qgv']['data']) == ['amd']
    assert len(result['failures']) == 2
    assert all(r['reason_codes'] == ['RECEIPT_INTEGRITY_FAILURE'] for r in result['failures'])


def test_duplicate_issuer_receipts_are_rejected_instead_of_selecting_latest(tmp_path):
    first = retain(tmp_path)
    second = retain(tmp_path, metrics={'Revenues': (10, 5, 'USD')})
    with pytest.raises(ValueError, match='DUPLICATE_ISSUER'):
        analyze(tmp_path, [first, second])


def conflict_bodies(*, resolve=False, ambiguous_filing=False):
    facts, subs = payloads(metrics={'Revenues': (250, 100, 'USD'), 'OperatingIncomeLoss': (75, None, 'USD')})
    recent = subs['filings']['recent']
    accn = recent['accessionNumber'][0]
    if ambiguous_filing:
        recent['form'].append('10-K')
        recent['filingDate'].append('2025-02-01')
        recent['accessionNumber'].append(accn)
        recent['acceptanceDateTime'].append('2025-02-01T22:00:00Z')
        # Keep older revenue supported by its own unambiguous filing.
        older = '0001045810-24-000778'
        for k, v in {'form': '10-K', 'filingDate': '2024-02-01', 'accessionNumber': older,
                     'acceptanceDateTime': '2024-02-01T20:00:00Z'}.items():
            recent[k].append(v)
        oldrow = facts['facts']['us-gaap']['Revenues']['units']['USD'][1]
        oldrow.update(accn=older, filed='2024-02-01')
    else:
        rows = facts['facts']['us-gaap']['Revenues']['units']['USD']
        rows.append({**rows[0], 'val': 260})
    if resolve:
        resolved = '0001045810-25-000779'
        for k, v in {'form': '10-K/A', 'filingDate': '2025-02-02', 'accessionNumber': resolved,
                     'acceptanceDateTime': '2025-02-02T20:00:00Z'}.items():
            recent[k].append(v)
        rows = facts['facts']['us-gaap']['Revenues']['units']['USD']
        rows.append({**rows[0], 'val': 270, 'accn': resolved, 'filed': '2025-02-02', 'form': '10-K/A'})
    return facts, subs


@pytest.mark.parametrize('ambiguous_filing', [False, True])
def test_unresolved_newer_period_ambiguity_cannot_promote_old_revenue(tmp_path, ambiguous_filing):
    receipt = retain(tmp_path, bodies=conflict_bodies(ambiguous_filing=ambiguous_filing))
    assert receipt['input']['status'] == 'READY'
    assert receipt['input']['raw_fundamentals']['revenue'] == 100
    result = analyze(tmp_path, [receipt])
    assert result['companies']['nvda']['reason_codes'] == ['UNRESOLVED_CURRENT_FACT_AMBIGUITY']
    assert not result['candidate_data']['leaderboard']['data']['rows']


def test_definitive_later_revision_resolves_conflict_without_inferred_parent(tmp_path):
    receipt = retain(tmp_path, bodies=conflict_bodies(resolve=True))
    assert receipt['input']['raw_fundamentals']['revenue'] == 270
    result = analyze(tmp_path, [receipt])
    assert result['companies']['nvda']['status'] == 'CALCULATED'
    assert all(r['parent_accession'] is None for r in result['companies']['nvda']['source']['selected_input_facts'])
    assert any(r['formal_amendment'] for r in result['companies']['nvda']['source']['selected_input_facts'])


def test_old_ambiguity_does_not_block_clear_current_period(tmp_path):
    facts, subs = payloads()
    rows = facts['facts']['us-gaap']['Revenues']['units']['USD']
    rows.append({**rows[1], 'val': 110})
    receipt = retain(tmp_path, bodies=(facts, subs))
    # Q remains measurable; EPS series still supplies a G observation.
    assert analyze(tmp_path, [receipt])['companies']['nvda']['status'] == 'CALCULATED'


def test_input_order_and_retry_clock_do_not_change_semantic_ids(tmp_path):
    first, second = retain(tmp_path), retain(tmp_path, 'amd')
    left = analyze(tmp_path, [first, second])
    right = analyze(tmp_path, [second, first], evaluated_at=AT + timedelta(days=1))
    assert left['candidate_id'] == right['candidate_id']
    assert left['candidate_data'] == right['candidate_data']
    assert left['companies'] == right['companies']
    for snapshot in left['candidate_data']['qgv']['data'].values():
        assert len(snapshot['qgv_snapshot_id'].split('_')[-1]) == 64
    observed = analyze(tmp_path, [first, second], synthetic=False)
    assert observed['candidate_id'] != left['candidate_id']
    assert not observed['synthetic_inputs']
    assert not observed['real_data_verified']
    assert not observed['candidate_data']['qgv']['data']['nvda']['synthetic']


def test_external_transport_prices_credentials_and_legacy_view_pipeline_are_unused(tmp_path, monkeypatch):
    receipt = retain(tmp_path)
    import socket
    import urllib.request
    import investment_system.providers.fred_alfred as fred
    from investment_system.providers.env_price import EnvPriceProvider
    from investment_system.contracts.models import DataStamp
    import investment_system.providers.sec_companyfacts as companyfacts
    from investment_system.qgv.pipeline import AnalysisPipeline
    import investment_system.providers.yahoo_chart as prices
    def forbidden(*args, **kwargs):
        pytest.fail('offline M2 invoked external/provider pipeline')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(fred, '_key', forbidden)
    monkeypatch.setattr(fred, 'api_key_present', forbidden)
    monkeypatch.setattr(EnvPriceProvider, 'enabled', forbidden)
    monkeypatch.setattr(EnvPriceProvider, 'url_template', forbidden)
    monkeypatch.setattr(EnvPriceProvider, 'fetch_symbol', forbidden)
    monkeypatch.setattr(urllib.request, 'urlopen', forbidden)
    monkeypatch.setattr(companyfacts, 'try_fetch_companyfacts', forbidden)
    monkeypatch.setattr(AnalysisPipeline, 'analyze_raw', forbidden)
    for name in ('fetch_chart',):
        if hasattr(prices, name):
            monkeypatch.setattr(prices, name, forbidden)
    monkeypatch.setattr(Path, 'read_text', lambda self, *a, **k: forbidden() if self.name.startswith('.env') else Path.read_bytes(self).decode())
    legacy_available = companyfacts.is_available
    def existing_m1_pit(stamp, cutoff):
        # Only the unmodified M1 converter may call legacy PIT. Its internal
        # non-null DataStamp is never the M2 observational mapper view.
        assert isinstance(stamp, DataStamp) and stamp.published_at is not None
        return legacy_available(stamp, cutoff)
    monkeypatch.setattr(companyfacts, 'is_available', existing_m1_pit)
    assert analyze(tmp_path, [receipt])['companies']['nvda']['status'] == 'CALCULATED'


def test_incomplete_source_store_is_rejected_without_recreating_history(tmp_path):
    receipt = retain(tmp_path)
    history = tmp_path / 'history'
    history.rmdir()
    with pytest.raises(ValueError, match='STORE_NOT_AVAILABLE'):
        analyze(tmp_path, [receipt])
    assert not history.exists()


def test_ready_share_only_input_keeps_both_missing_native_scores_separate(tmp_path):
    receipt = retain(tmp_path, metrics={'CommonStockSharesOutstanding': (10, None, 'shares')})
    assert receipt['input']['status'] == 'READY'
    result = analyze(tmp_path, [receipt])
    native = result['unavailable_snapshots']['nvda']
    assert native['Q_score'] is None and native['G_score'] is None and native['total_score'] is None
    assert len(result['companies']['nvda']['factors']) == 20
    assert result['candidate_data']['leaderboard']['data']['rows'] == []


def test_ambiguous_revision_order_and_clear_later_revision(tmp_path):
    facts, subs = payloads()
    recent = subs['filings']['recent']
    current = facts['facts']['us-gaap']['Revenues']['units']['USD'][0]
    alternate = '0001045810-25-000780'
    for key, value in {'form': '10-K', 'filingDate': '2025-02-01', 'accessionNumber': alternate,
                       'acceptanceDateTime': '2025-02-01T21:00:00Z'}.items():
        recent[key].append(value)
    rows = facts['facts']['us-gaap']['Revenues']['units']['USD']
    rows.append({**current, 'val': 265, 'accn': alternate})
    ambiguous = retain(tmp_path / 'unresolved', bodies=(facts, subs))
    assert ambiguous['input']['raw_fundamentals']['revenue'] == 100
    assert analyze(tmp_path / 'unresolved', [ambiguous])['companies']['nvda']['reason_codes'] == ['UNRESOLVED_CURRENT_FACT_AMBIGUITY']
    last = '0001045810-25-000781'
    for key, value in {'form': '10-K', 'filingDate': '2025-02-03', 'accessionNumber': last,
                       'acceptanceDateTime': '2025-02-03T21:00:00Z'}.items():
        recent[key].append(value)
    rows.append({**current, 'val': 280, 'accn': last, 'filed': '2025-02-03'})
    resolved = retain(tmp_path / 'resolved', bodies=(facts, subs))
    assert resolved['input']['raw_fundamentals']['revenue'] == 280
    assert analyze(tmp_path / 'resolved', [resolved])['companies']['nvda']['status'] == 'CALCULATED'


def test_requested_replay_stamp_and_original_stamp_remain_distinct(tmp_path):
    receipt = retain(tmp_path)
    later = AT + timedelta(days=1)
    result = analyze(tmp_path, [receipt], as_of=later, evaluated_at=later)
    source = result['companies']['nvda']['source']
    replayed = sec_m1.replay_receipt(tmp_path, receipt['receipt_id'], later)
    assert source['requested_stamp'] == replayed['raw_fundamentals']['stamp']
    assert source['original_stamp'] == receipt['input']['raw_fundamentals']['stamp']
    assert source['requested_stamp']['data_stamp_id'] != source['original_stamp']['data_stamp_id']
    factor = result['companies']['nvda']['factors']['fcf_quality']
    assert factor['source_references']['source_stamp'] == source['requested_stamp']


@pytest.mark.parametrize('unsupported', ['widgets_unit', 'unsupported_us_gaap_concept'])
def test_unconsumed_newer_rows_cannot_hide_current_supported_revenue_conflict(tmp_path, unsupported):
    facts, subs = conflict_bodies()
    rows = facts['facts']['us-gaap']['Revenues']['units']['USD']
    rows.append({**rows[1], 'start': '2022-01-01', 'end': '2022-12-31', 'val': 80, 'fy': 2022})
    irrelevant = {**rows[0], 'start': '2024-02-01', 'end': '2025-01-31', 'val': 900}
    if unsupported == 'widgets_unit':
        facts['facts']['us-gaap']['Revenues']['units']['widgets'] = [irrelevant]
    else:
        facts['facts']['us-gaap']['Revenue'] = {'units': {'USD': [irrelevant]}}
    receipt = retain(tmp_path, bodies=(facts, subs))
    assert receipt['input']['raw_fundamentals']['revenue'] == 100
    assert analyze(tmp_path, [receipt])['companies']['nvda']['reason_codes'] == ['UNRESOLVED_CURRENT_FACT_AMBIGUITY']


def test_non_consumed_unit_conflict_does_not_withhold_valid_financial_input(tmp_path):
    facts, subs = payloads()
    revenue = facts['facts']['us-gaap']['Revenues']
    row = revenue['units']['USD'][0]
    revenue['units']['widgets'] = [{**row, 'val': 999}, {**row, 'val': 998}]
    receipt = retain(tmp_path, bodies=(facts, subs))
    assert receipt['input']['raw_fundamentals']['revenue'] == 250
    assert analyze(tmp_path, [receipt])['companies']['nvda']['status'] == 'CALCULATED'


def test_newer_capex_cannot_hide_unresolved_current_cfo_leaf_dependency(tmp_path):
    later = datetime(2026, 3, 1, 10, tzinfo=timezone.utc)
    facts, subs = payloads(metrics={'Revenues': (250, 100, 'USD'), 'OperatingIncomeLoss': (75, None, 'USD'),
                                  'EarningsPerShareDiluted': (5, 2, 'USD/shares'),
                                  'NetCashProvidedByUsedInOperatingActivities': (80, 50, 'USD'),
                                  'PaymentsToAcquirePropertyPlantAndEquipment': (10, None, 'USD')})
    for node in facts['facts']['us-gaap'].values():
        for rows in node['units'].values():
            for row in rows:
                row['filed'] = '2026-02-01'
    subs['filings']['recent']['filingDate'] = ['2026-02-01']
    subs['filings']['recent']['acceptanceDateTime'] = ['2026-02-01T20:00:00Z']
    cfo = facts['facts']['us-gaap']['NetCashProvidedByUsedInOperatingActivities']['units']['USD']
    cfo.append({**cfo[0], 'val': 90})
    capex = facts['facts']['us-gaap']['PaymentsToAcquirePropertyPlantAndEquipment']['units']['USD'][0]
    capex.update(start='2025-01-01', end='2025-12-31')
    receipt = retain(tmp_path, bodies=(facts, subs), acquired_at=later, as_of=later)
    assert receipt['input']['raw_fundamentals']['fcf'] == 40
    result = analyze(tmp_path, [receipt], as_of=later, evaluated_at=later)
    assert result['companies']['nvda']['reason_codes'] == ['UNRESOLVED_CURRENT_FACT_AMBIGUITY']
