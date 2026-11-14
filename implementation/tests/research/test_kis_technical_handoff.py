"""New receipt-to-Main boundary; existing indicator arithmetic is not reimplemented."""
from copy import deepcopy
import json
import pytest

from test_adjusted_technical_link import case
from investment_system.research.technical_handoff import prepare_technical


S = '2017-01-06'


def test_existing_adjusted_components_and_raw_pattern_segments_are_separate():
    c = case(); before = deepcopy(c)
    out = prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    assert c == before
    assert out['schema'] == 'kis-technical-handoff/1'
    assert out['publication_scope'] == 'OWNER_PRIVATE_ONLY'
    assert out['context']['signal_day'] == S
    assert out['chart']['basis'] == 'SPLIT_ADJUSTED'
    assert out['chart']['bars'][0]['close'] == '100'
    assert out['chart']['bars'][0]['volume'] == '200'
    assert out['patterns']['basis'] == 'RAW_CLOSE'
    assert len(out['patterns']['result']['segments']) == 2
    assert out['patterns']['rules_scope'] == 'RESEARCH_DEFAULT_NOT_INVESTMENT_SIGNAL'
    assert out['patterns']['volume_scope'] == 'WITHHELD_SCOPE_UNCONFIRMED'
    assert out['patterns']['success_probability'] is None
    by_id = {r['metric_id']: r for r in out['availability']}
    assert by_id['SMA_20']['state'] == 'VALUE'
    assert by_id['RSI_14']['reasons'] == ['ZERO_TOTAL_CHANGE']
    assert by_id['dollar_volume_6m']['value'] is None
    assert 'TRADE_SCOPE_UNCONFIRMED' in by_id['dollar_volume_6m']['reasons']
    assert out['group']['state'] == 'NOT_REQUESTED'
    assert out['group']['rank'] is None


def test_gap_is_never_filled_or_hidden_from_pattern_indices():
    c = case(False)
    missing = c['raw_bars'][50]['date']
    for key in ('raw_bars', 'bars'): del c[key][50]
    out = prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    assert out['sessions']['missing'] == [missing]
    assert missing not in [r['date'] for r in out['chart']['bars']]
    assert out['patterns']['state'] == 'NOT_JUDGEABLE'
    assert 'PRICE_WINDOW_INCOMPLETE' in out['patterns']['reasons']
    assert out['patterns']['result'] is None


def test_evaluation_day_is_not_replaced_by_last_retained_chart_day():
    c = case(False)
    for key in ('raw_bars', 'bars'): c[key].pop()
    c['price_basis_date'] = c['bars'][-1]['date']
    out = prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    assert out['context']['signal_day'] == S
    assert out['context']['chart_observation_day'] < S
    assert out['components']['status'] == 'STALE'
    assert out['patterns']['state'] == 'NOT_JUDGEABLE'
    assert 'SIGNAL_SESSION_MISSING' in out['patterns']['reasons']
    assert all(r['value'] is None for r in out['measures']['metrics'].values())


def test_price_only_indicators_survive_unconfirmed_or_missing_volume():
    c = case(False)
    for key in ('raw_bars', 'bars'):
        for row in c[key]: row['volume'] = None
    out = prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    by_id = {r['metric_id']: r for r in out['availability']}
    assert by_id['momentum_3m']['state'] == 'VALUE'
    assert by_id['SMA_20']['state'] == 'VALUE'
    assert by_id['dollar_volume_6m']['state'] != 'VALUE'
    assert out['patterns']['state'] == 'CALCULATED_RESEARCH'


@pytest.mark.parametrize('change,reason', [
    ('currency', 'INVALID_DAILY_CONTRACT'),
    ('identity', 'IDENTITY_UNCONFIRMED'),
    ('action', 'ACTION_BASIS_UNCONFIRMED'),
])
def test_currency_identity_and_action_evidence_are_not_invented(change, reason):
    c = case(False)
    if change == 'currency':
        c['currency'] = 'EUR'
        with pytest.raises(ValueError, match=reason):
            prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST')
        return
    if change == 'identity': c['identity']['identity_status'] = 'UNKNOWN'
    if change == 'action': c['confirmed_ranges'] = []
    out = prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    assert out['patterns']['state'] == 'NOT_JUDGEABLE'
    assert reason in out['patterns']['reasons']
    assert all(r['state'] != 'VALUE' for r in out['availability'])


def test_future_events_and_bars_do_not_change_earlier_view():
    c = case()
    out = prepare_technical(c, evaluation_day='2016-06-30', series_id='SYNTHETIC:REQUEST')
    assert out['chart']['bars'][-1]['date'] == '2016-06-30'
    assert out['chart']['bars'][0]['close'] == '200'
    assert out['context']['excluded_future_rows'] > 0
    assert out['patterns']['applied_splits'] == []
    assert len(out['patterns']['result']['segments']) == 1


def test_existing_cli_dispatch_calls_the_same_handoff_function():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('kis_cli', Path(__file__).parents[2] / 'tools/kis_retained_calculate.py')
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    args = dict(c=case(False, 20), evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    assert cli.execute(dict(mode='technical-handoff', arguments=args)) == prepare_technical(**args)


def test_final_size_limit_includes_the_result_hash_field(monkeypatch):
    from investment_system.research import technical_handoff as handoff
    args = dict(c=case(False, 20), evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    result = prepare_technical(**args)
    size = len(json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True,
                          separators=(',', ':')).encode())
    monkeypatch.setattr(handoff, 'MAX_BYTES', size - 1)
    with pytest.raises(ValueError, match='TECHNICAL_HANDOFF_TOO_LARGE'):
        prepare_technical(**args)


def test_pattern_execution_is_not_full_warmup_or_a_proven_no_pattern():
    out = prepare_technical(case(False, 14), evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    assert out['patterns']['state'] == 'CALCULATED_RESEARCH'
    seed = out['patterns']['initialization']
    assert seed['minimum_sessions'] == 15
    assert seed['latest_segment_state'] == 'INSUFFICIENT'
    assert seed['segments'][0]['observed_sessions'] == 14
    assert out['patterns']['result']['objects'] == []


def test_main_examples_schema_and_manual_availability_expectations():
    import importlib.util
    from pathlib import Path
    import jsonschema
    root = Path(__file__).parents[2]
    spec = importlib.util.spec_from_file_location('kis_examples', root / 'tools/kis_contract_fixture.py')
    tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
    files = tool.handoff_fixtures()
    import hashlib
    manifest = json.loads((root / 'tests/fixtures/kis-technical-handoff/memory-examples-manifest.json').read_text())
    assert manifest['schema'] == 'synthetic-technical-memory-examples/1'
    assert files['expectations.json']['schema'] == 'synthetic-technical-expectations/1'
    assert manifest['delivery_state'] == 'IN_MEMORY_GENERATOR_VALUES'
    assert set(files) == {f['generated_member_name'] for f in manifest['files']}
    for entry in manifest['files']:
        body = json.dumps(files[entry['generated_member_name']], sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode() + b'\n'
        assert len(body) == entry['bytes']
        assert hashlib.sha256(body).hexdigest() == entry['sha256']
    schema = json.loads((root / 'docs/research/kis-technical-handoff-contract.json').read_text())
    for name, item in files.items():
        if name.endswith('-job.json'):
            jsonschema.validate(item['arguments'], {**schema, '$ref': '#/$defs/arguments'})
        elif name.endswith('-result.json'):
            jsonschema.validate(item, {**schema, '$ref': '#/$defs/result'})
    normal = files['normal-result.json']
    assert normal['components']['adopted_count'] == 12  # 100 sessions: SMA120 alone lacks history.
    assert normal['measures']['adopted_count'] == 1  # Three-month momentum, not six/twelve-month windows.
    assert files['split-result.json']['chart']['bars'][0]['volume'] == '100'
    assert len(files['split-result.json']['patterns']['result']['segments']) == 2
    assert files['missing-session-result.json']['patterns']['state'] == 'NOT_JUDGEABLE'
    assert files['missing-evidence-result.json']['components']['adopted_count'] == 0
    assert files['stale-result.json']['components']['status'] == 'STALE'
    assert files['stale-result.json']['measures']['adopted_count'] == 0


def test_failed_refresh_keeps_original_capture_and_last_success_metadata():
    from investment_system.research.kis_price_bridge import merge_update
    original = case(False, 20)
    kept = merge_update(original, None, evaluation_day=S, failure='SOURCE_FAILURE')['data']
    out = prepare_technical(kept, evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    assert out['context']['update_state'] == 'FAILED'
    assert out['context']['collected_at'] == original['collected_at']
    assert out['context']['last_success_at'] == original['collected_at']
    assert out['components']['status'] == 'STALE'


def test_empty_retained_response_is_missing_and_other_source_is_not_kis():
    c = case(False, 20)
    c['raw_bars'] = []; c['bars'] = []; c['price_basis_date'] = None
    out = prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    assert out['components']['status'] == 'MISSING'
    assert all(r['value'] is None for r in out['availability'])
    assert out['patterns']['state'] == 'NOT_JUDGEABLE'
    c['schema'] = 'retained-daily-price/1'
    with pytest.raises(ValueError, match='KIS_DAILY_CONTRACT_REQUIRED'):
        prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST')


def test_declared_split_reference_is_not_independent_source_document_verification():
    c = case(); before = deepcopy(c)
    out = prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST', include_split_assessment=True)
    proof = out['split_assessment']
    assert c == before
    assert proof['policy_version'] == 'kis-split-evidence/1'
    assert proof['source_document_verification'] == 'NOT_PERFORMED'
    assert proof['full_retained_interval']['state'] == 'COVERED_BY_DECLARED_REFERENCE'
    assert proof['events'][0]['state'] == 'DECLARED_CONFIRMED_WITH_REFERENCE'
    assert proof['events'][0]['source_record_state'] == 'NOT_PROVIDED'
    assert proof['events'][0]['adjustment_applied'] is True
    assert proof['events'][0]['ratio_definition'] == 'NEW_SHARES_PER_OLD_SHARE'
    assert proof['block_reasons'] == []


def test_empty_events_do_not_prove_split_free_history_or_create_global_rolling_gate():
    c = case(False)
    c['confirmed_ranges'] = [dict(**{'from': c['raw_bars'][-20]['date'], 'to': S}, evidence='SYNTHETIC_LAST_20')]
    out = prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST', include_split_assessment=True)
    proof = out['split_assessment']
    assert proof['events'] == []
    assert proof['empty_event_list_is_no_split_evidence'] is False
    assert proof['full_retained_interval']['state'] == 'UNCONFIRMED'
    assert proof['full_retained_interval']['reasons'] == ['ACTION_BASIS_UNCONFIRMED']
    assert out['components']['metrics']['SMA_20']['value'] == 100
    assert out['components']['metrics']['EMA_20']['value'] is None


@pytest.mark.parametrize('field,value,reason', [
    ('ratio', '3', 'SPLIT_RATIO_CONFLICT'),
    ('effective_date', '2016-07-05', 'SPLIT_EFFECTIVE_DATE_CONFLICT'),
    ('symbol', 'OTHER', 'SPLIT_SUBJECT_MISMATCH'),
    ('issuer_id', 'OTHER', 'SPLIT_SUBJECT_MISMATCH'),
    ('security_id', 'OTHER', 'SPLIT_SUBJECT_MISMATCH'),
])
def test_explicit_source_event_conflict_is_rejected_before_adoption(field, value, reason):
    from investment_system.research.technical_handoff import split_readiness
    c = case(); c['issuer_id'] = 'SYNTHETIC:ISSUER'
    c['splits'][0]['source_record'] = {field: value}
    proof = split_readiness(c, evaluation_day=S)
    assert proof['events'][0]['state'] == 'CONFLICT'
    assert reason in proof['block_reasons']
    with pytest.raises(ValueError, match=reason):
        prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST', include_split_assessment=True)


def test_matching_source_metadata_is_not_original_document_confirmation():
    c = case()
    c['splits'][0]['source_record'] = dict(ratio='2.0', effective_date='2016-07-01',
        symbol=c['symbol'], security_id=c['security_id'], source_sha256='1'*64,
        document_location='SYNTHETIC filing paragraph', reviewed_at='2026-11-14T12:00:00Z')
    out = prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST', include_split_assessment=True)
    proof = out['split_assessment']
    assert proof['events'][0]['source_record_state'] == 'SUPPLIED_FIELDS_MATCH'
    assert proof['source_document_verification'] == 'NOT_PERFORMED'
    assert out['components']['metrics']['SMA_20']['value'] == 100


def test_future_conflicting_event_does_not_rebase_or_block_prior_evaluation():
    c = case(); c['splits'][0]['source_record'] = dict(ratio='3')
    out = prepare_technical(c, evaluation_day='2016-06-30', series_id='SYNTHETIC:REQUEST', include_split_assessment=True)
    proof = out['split_assessment']
    assert proof['block_reasons'] == []
    assert proof['events'][0]['state'] == 'EXCLUDED_FUTURE_EVENT'
    assert proof['events'][0]['adjustment_applied'] is False
    assert 'SPLIT_RATIO_CONFLICT' in proof['events'][0]['reasons']
    assert out['components']['metrics']['SMA_20']['value'] == 200


@pytest.mark.parametrize('change,reason', [('provider', 'RAW_DAILY_SOURCE_REQUIRED'),
    ('raw_row', 'RAW_INPUT_ALREADY_ADJUSTED')])
def test_provider_adjustment_is_not_treated_as_raw_or_adjusted_twice(change, reason):
    c = case()
    if change == 'provider': c['source_query']['MODP'] = '1'
    else: c['raw_bars'][0]['price_basis'] = 'SPLIT_ADJUSTED'
    with pytest.raises(ValueError, match=reason):
        prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST', include_split_assessment=True)


def test_raw_split_window_reason_and_independent_adjusted_basis_remain_visible():
    c = case(); c['basis'] = 'RAW'; c['bars'] = deepcopy(c['raw_bars'])
    out = prepare_technical(c, evaluation_day=S, series_id='SYNTHETIC:REQUEST', include_split_assessment=True)
    proof = out['split_assessment']
    assert proof['events'][0]['adjustment_applied'] is False
    assert proof['raw_window_split_dates'] == ['2016-07-01']
    assert 'CORPORATE_ACTION_IN_RAW_WINDOW' in out['measures']['metrics']['momentum_12m']['null_reasons']
    assert out['patterns']['basis'] == 'RAW_CLOSE'


def test_shared_split_assessment_pins_original_record_and_keeps_future_events_separate():
    from investment_system.research.kis_split_evidence import assess_splits
    from investment_system.research.sector_qgv import digest
    c = case(); before = deepcopy(c)
    event = deepcopy(c['splits'][0])
    proof = assess_splits(c, S)
    assert c == before
    assert proof['independently_verified'] is False
    assert proof['confirmed_events'][0]['record'] == event
    assert proof['confirmed_events'][0]['record_hash'] == digest(event)
    assert proof['confirmed_events'][0]['date'] == event['date']
    assert proof['confirmed_events'][0]['ratio'] == '2'
    assert proof['confirmed_events'][0]['independently_verified'] is False
    assert proof['excluded_future_events'] == []
    earlier = assess_splits(c, '2016-06-30')
    assert earlier['confirmed_events'] == []
    assert earlier['excluded_future_events'][0]['record_hash'] == digest(event)
    assert earlier['excluded_future_events'][0]['state'] == 'EXCLUDED_FUTURE_EVENT'


def test_opt_in_assessment_preserves_default_wire_output_and_rejects_nonboolean_option():
    args = dict(c=case(False, 20), evaluation_day=S, series_id='SYNTHETIC:REQUEST')
    legacy = prepare_technical(**args)
    assert prepare_technical(**args, include_split_assessment=False) == legacy
    assert 'split_assessment' not in legacy
    enhanced = prepare_technical(**args, include_split_assessment=True)
    assert {k: v for k, v in enhanced.items() if k not in ('split_assessment', 'result_sha256')} == {
        k: v for k, v in legacy.items() if k != 'result_sha256'}
    assert enhanced['result_sha256'] != legacy['result_sha256']
    with pytest.raises(ValueError, match='INVALID_SPLIT_ASSESSMENT_OPTION'):
        prepare_technical(**args, include_split_assessment='true')


def test_split_metadata_examples_match_manual_expectations_without_changing_frozen_examples():
    import importlib.util
    from pathlib import Path
    import jsonschema
    root = Path(__file__).parents[2]
    spec = importlib.util.spec_from_file_location('kis_split_examples', root / 'tools/kis_contract_fixture.py')
    tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
    expected = json.loads((root / 'tests/fixtures/kis-technical-handoff/split-evidence-expectations.json').read_text())
    assert tool.split_evidence_fixtures()['split-evidence-expectations.json'] == expected
    assert len(expected['cases']) == 13
    assert not any(c['independently_verified'] for c in expected['cases'])
    schema = json.loads((root / 'docs/research/kis-technical-handoff-contract.json').read_text())
    enhanced = prepare_technical(case(), evaluation_day=S, series_id='SYNTHETIC:REQUEST',
                                include_split_assessment=True)
    jsonschema.validate(enhanced, {**schema, '$ref': '#/$defs/result'})
    jsonschema.validate(dict(c=case(), evaluation_day=S, series_id='SYNTHETIC:REQUEST',
                            include_split_assessment=True), {**schema, '$ref': '#/$defs/arguments'})
    assert tool.handoff_fixtures()['normal-result.json'].get('split_assessment') is None

    import hashlib
    manifest = json.loads((root / 'tests/fixtures/kis-technical-handoff/split-evidence-manifest.json').read_text())
    for item in manifest['files']:
        body = (root / 'tests/fixtures/kis-technical-handoff' / item['path']).read_bytes()
        assert len(body) == item['bytes']
        assert hashlib.sha256(body).hexdigest() == item['sha256']
