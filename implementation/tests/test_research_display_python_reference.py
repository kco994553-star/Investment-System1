"""Synthetic-only Python reference vectors for the approved chart display contract."""
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'research_display_python_reference.py'
FIXTURE = ROOT / 'tests' / 'fixtures' / 'research_display_python_vectors.json'
CHECKPOINTS = json.loads((ROOT / 'tests' / 'fixtures' / 'technical_research_reference.json').read_text())
INDICATORS = tuple(CHECKPOINTS['expected'])


def reference():
    assert TOOL.is_file(), 'The standalone synthetic Python reference tool is not implemented'
    spec = importlib.util.spec_from_file_location('synthetic_python_reference', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reference_vectors()


def case(name):
    return next(item for item in reference()['cases'] if item['case_id'] == name)


def indicator(item, name):
    return next(value for value in item['expected']['indicators'] if value['indicator_id'] == name)


def test_generator_is_fixed_synthetic_research_contract():
    vectors = reference()
    assert vectors['synthetic'] is True and vectors['role'] == 'RESEARCH_DISPLAY_ONLY'
    assert vectors['display_defaults']['sma_periods'] == [5, 20, 60, 120]
    assert vectors['display_defaults']['optional_sma_period'] == 240
    assert vectors['display_defaults']['include_sma240'] is False
    assert vectors == reference()
    for item in vectors['cases']:
        assert item['synthetic'] is True and item['role'] == 'RESEARCH_DISPLAY_ONLY'
        assert item['expected']['role'] == 'RESEARCH_DISPLAY_ONLY'
        assert item['expected']['state'] == 'INPUT_RESEARCH'
        assert item['expected']['pit_status'] == 'NOT_VERIFIED'
        assert item['input']['options']['includeSma240'] is True
        assert item['input']['options']['priceBasis'] == item['expected']['price_basis']
        assert tuple(value['indicator_id'] for value in item['expected']['indicators']) == INDICATORS
        assert indicator(item, 'SMA_240')['default_visible'] is False
        for n in (5, 20, 60, 120):
            assert indicator(item, f'SMA_{n}')['default_visible'] is True


@pytest.mark.parametrize('name', INDICATORS)
def test_every_existing_talib_checkpoint_agrees(name):
    values = indicator(case('checkpoint_260'), name)['values']
    for index, expected in CHECKPOINTS['expected'][name].items():
        actual = values[int(index)]
        if expected is None:
            assert actual is None
        else:
            assert actual == pytest.approx(expected, rel=1e-11, abs=1e-11)


@pytest.mark.parametrize('name,first', [
    ('SMA_5', 4), ('SMA_20', 19), ('SMA_60', 59), ('SMA_120', 119),
    ('SMA_240', 239), ('EMA_20', 19), ('RSI_14', 14), ('MACD_12_26', 25),
    ('MACD_SIGNAL_9', 33), ('MACD_HISTOGRAM_12_26_9', 33),
    ('BOLL_MIDDLE_20', 19), ('BOLL_UPPER_20_2', 19), ('BOLL_LOWER_20_2', 19),
    ('ATR_14', 14),
])
def test_warmup_null_boundaries_are_transaction_sessions(name, first):
    item = indicator(case('checkpoint_260'), name)
    assert item['values'][:first] == [None] * first
    assert item['unavailable_reasons'][:first] == ['WARMUP'] * first
    assert item['values'][first] is not None
    assert item['unavailable_reasons'][first] is None


def test_linear_vectors_have_hand_computed_ema_macd_atr_bollinger_values():
    rising = case('rising_40')
    assert indicator(rising, 'SMA_20')['values'][19] == 109.5
    assert indicator(rising, 'EMA_20')['values'][19:21] == [109.5, 110.5]
    assert indicator(rising, 'MACD_12_26')['values'][25:] == [7.0] * 15
    assert indicator(rising, 'MACD_SIGNAL_9')['values'][33:] == [7.0] * 7
    assert indicator(rising, 'MACD_HISTOGRAM_12_26_9')['values'][33:] == [0.0] * 7
    assert indicator(rising, 'ATR_14')['values'][14:] == [4.0] * 26
    assert indicator(rising, 'BOLL_UPPER_20_2')['values'][19] == pytest.approx(109.5 + 2 * math.sqrt(33.25))
    assert indicator(rising, 'BOLL_LOWER_20_2')['values'][19] == pytest.approx(109.5 - 2 * math.sqrt(33.25))


def test_flat_and_directional_rsi_never_replace_undefined_with_zero():
    flat = indicator(case('flat_40'), 'RSI_14')
    assert flat['values'][14:] == [None] * 26
    assert flat['unavailable_reasons'][14:] == ['ZERO_TOTAL_CHANGE'] * 26
    assert indicator(case('rising_40'), 'RSI_14')['values'][14:] == [100.0] * 26
    assert indicator(case('falling_40'), 'RSI_14')['values'][14:] == [0.0] * 26
    assert indicator(case('flat_40'), 'MACD_HISTOGRAM_12_26_9')['values'][33:] == [0.0] * 7


@pytest.mark.parametrize('name', ['empty', 'one_session', 'short_14'])
def test_short_histories_keep_long_averages_and_wilder_seed_unavailable(name):
    item = case(name)
    size = len(item['input']['bars'])
    for indicator_id in ('SMA_20', 'SMA_60', 'SMA_120', 'SMA_240', 'EMA_20',
                         'RSI_14', 'MACD_12_26', 'MACD_SIGNAL_9', 'ATR_14'):
        value = indicator(item, indicator_id)
        assert value['values'] == [None] * size
        assert value['unavailable_reasons'] == ['WARMUP'] * size
        assert value['latest_state'] == 'NOT_AVAILABLE'


def test_wilder_recurrence_is_not_a_simple_rolling_average():
    item = case('wilder_recurrence_40')
    assert indicator(item, 'RSI_14')['values'][15] == pytest.approx(81.25)
    assert indicator(item, 'ATR_14')['values'][15] == pytest.approx(4 + 6 / 14)


def test_missing_session_resets_seeds_without_connecting_across_the_gap():
    item = case('missing_session_70')
    for name in ('SMA_20', 'EMA_20', 'RSI_14', 'MACD_12_26', 'ATR_14'):
        assert indicator(item, name)['values'][30] is None
    sma = indicator(item, 'SMA_20')
    assert sma['values'][49] is None and sma['values'][50] is not None
    atr = indicator(item, 'ATR_14')
    assert atr['unavailable_reasons'][30] == 'OHLC_MISSING'
    assert atr['values'][44] is None and atr['values'][45] is not None


def test_adjusted_closes_have_no_raw_ohlc_atr_and_incomplete_session_is_null():
    adjusted = case('adjusted_basis_40')
    assert indicator(adjusted, 'SMA_20')['values'][19] == 109.5 / 2
    atr = indicator(adjusted, 'ATR_14')
    assert atr['values'] == [None] * 40
    assert atr['unavailable_reasons'] == ['OHLC_BASIS_UNCONFIRMED'] * 40
    incomplete = case('incomplete_last_35')
    for name in INDICATORS:
        assert indicator(incomplete, name)['values'][-1] is None


def test_all_index_arrays_are_strict_json_with_matching_availability():
    vectors = reference()
    json.dumps(vectors, allow_nan=False)
    for item in vectors['cases']:
        size = len(item['input']['bars'])
        assert [b['timestamp'] for b in item['input']['bars']] == sorted(b['timestamp'] for b in item['input']['bars'])
        for values in item['expected']['indicators']:
            assert values['role'] == 'RESEARCH_DISPLAY_ONLY'
            assert len(values['values']) == len(values['unavailable_reasons']) == size
            for value, reason in zip(values['values'], values['unavailable_reasons']):
                assert (value is None) == (reason is not None)
                assert value is None or math.isfinite(value)
            expected_state = 'AVAILABLE' if size and values['values'][-1] is not None else 'NOT_AVAILABLE'
            assert values['latest_state'] == expected_state


def test_committed_full_vectors_are_reproducible_without_external_dependencies():
    assert FIXTURE.is_file(), 'The full synthetic cross-language fixture is missing'
    assert json.loads(FIXTURE.read_text()) == reference()


def test_cli_emits_only_the_fixed_synthetic_document():
    completed = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, check=True)
    assert completed.stderr == ''
    assert json.loads(completed.stdout) == reference()


def test_cli_has_no_live_input_option(tmp_path):
    completed = subprocess.run([sys.executable, str(TOOL), '--input', str(tmp_path / 'external.json')],
                               capture_output=True, text=True)
    assert completed.returncode == 2
    assert completed.stdout == '' and 'unrecognized arguments' in completed.stderr
