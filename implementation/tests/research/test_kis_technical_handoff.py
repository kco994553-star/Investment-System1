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
