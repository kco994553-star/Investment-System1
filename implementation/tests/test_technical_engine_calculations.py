"""Synthetic daily-input vectors for the existing engine's three calculations."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from investment_system.technical.daily_input import DailyBar, DailyInputSeries, ExpectedSession, prepare_daily_returns, evaluate_daily_input
from investment_system.technical.engine import TechnicalEngine
from investment_system.technical.engine_calculations import calculate_daily_engine_inputs

START = datetime(2030, 1, 1, 21, tzinfo=timezone.utc)


def series(prices):
    bars = tuple(DailyBar('synthetic-company', 'synthetic-listing', 'SYN', 'USD', 'SYNTHETIC',
                         (START + timedelta(days=i)).date(), START + timedelta(days=i),
                         START + timedelta(days=i), START + timedelta(days=i), True,
                         'RAW_CLOSE', price, None) for i, price in enumerate(prices))
    return DailyInputSeries('synthetic-company', 'synthetic-listing', 'SYN', 'USD', 'SYNTHETIC',
                            'XNYS', 'America/New_York', 'synthetic-source', '1d', 'RAW_CLOSE',
                            START + timedelta(days=len(prices)+2), True, bars,
                            tuple(ExpectedSession(b.session, b.observed_at) for b in bars),
                            'synthetic-calendar', 'CONFIRMED_SYNTHETIC', 'CONFIRMED_SYNTHETIC',
                            tuple(b.session for b in bars), None, ())


@pytest.mark.parametrize('n', [2, 5, 6, 20, 21, 35])
def test_exact_existing_engine_arithmetic_and_adapter_last20(n):
    s = series([100 + (i % 7) * 3 + i for i in range(n)])
    before = deepcopy(s)
    prepared = prepare_daily_returns(s, s.read_at)
    result = calculate_daily_engine_inputs(s, s.read_at)
    rets = prepared.returns
    expected = (sum((r-sum(rets)/len(rets))**2 for r in rets)/len(rets))**0.5
    assert result.state == 'DEMO' and result.prepared == prepared
    assert result.data.population_stddev == expected
    assert result.data.last_return == rets[-1]
    assert result.data.last5_sum == sum(rets[-5:])
    assert result.data.return_count == min(n-1, 20)
    assert result.data.role == 'EXISTING_ENGINE_INPUTS'
    assert (result.prepared.synthetic, result.prepared.pit_status, result.prepared.model_status) == (True, 'NOT_VERIFIED', 'PLACEHOLDER_UNVALIDATED')
    assert s == before


def test_hand_reference_population_divisor_and_short_window():
    # Exactly representable simple returns: +1, -0.5, +1, -0.5.
    s = series([1, 2, 1, 2, 1])
    data = calculate_daily_engine_inputs(s, s.read_at).data
    assert (data.population_stddev, data.last_return, data.last5_sum) == (0.75, -0.5, 1.0)
    short = series([1, 2])
    data = calculate_daily_engine_inputs(short, short.read_at).data
    assert (data.population_stddev, data.last_return, data.last5_sum) == (0.0, 1.0, 1.0)


@pytest.mark.parametrize('prices', [[], [100], [100, None], [100, 0], [100, float('nan')]])
def test_input_failure_preserves_adapter_reason_and_no_values(prices):
    s = series(prices)
    prepared = prepare_daily_returns(s, s.read_at)
    result = calculate_daily_engine_inputs(s, s.read_at)
    assert result.state == 'NOT_AVAILABLE' and result.data is None
    assert result.prepared == prepared and result.prepared.state == 'NOT_AVAILABLE'


@pytest.mark.parametrize('changes', [dict(synthetic=False), dict(basis_status='UNKNOWN'),
                                   dict(corporate_action_status='UNKNOWN'), dict(expected_sessions=None)])
def test_no_real_input_or_validation_bypass(changes):
    s = replace(series([100, 101, 102]), **changes)
    result = calculate_daily_engine_inputs(s, s.read_at)
    assert result.state == 'NOT_AVAILABLE' and result.data is None
    assert result.prepared == prepare_daily_returns(s, s.read_at)


def test_future_bar_excluded_and_future_available_bar_rejected():
    s = series([100, 101, 999])
    cutoff = s.bars[1].observed_at
    s = replace(s, action_covered_sessions=tuple(b.session for b in s.bars[:2]))
    result = calculate_daily_engine_inputs(s, cutoff)
    assert result.prepared.excluded_future_bar_count == 1
    assert result.data.last_return == 101/100-1
    b = replace(s.bars[1], available_at=cutoff+timedelta(seconds=1))
    invalid = replace(s, bars=(s.bars[0], b, s.bars[2]))
    result = calculate_daily_engine_inputs(invalid, cutoff)
    assert result.data is None and result.prepared.reason_codes == ('AVAILABLE_AFTER_AS_OF',)


def test_overflow_is_sanitized_without_leaking_values():
    s = series([1e-300, 1e8, 1])  # finite returns; square overflows in legacy arithmetic
    result = calculate_daily_engine_inputs(s, s.read_at)
    assert result.state == 'NOT_AVAILABLE' and result.data is None
    assert result.prepared.reason_codes == ('CALCULATION_ERROR',)
    assert result.prepared.returns is None and result.prepared.return_count == 0


@pytest.mark.parametrize('prices', [[100, 101, 102], [100, 90, 80], [1, 2, 1, 2, 1]])
def test_engine_outputs_are_unchanged(prices):
    s = series(prices)
    original = evaluate_daily_input(s, s.read_at, engine=TechnicalEngine()).data
    calculate_daily_engine_inputs(s, s.read_at)
    after = evaluate_daily_input(s, s.read_at, engine=TechnicalEngine()).data
    before_fields, after_fields = original.to_dict(), after.to_dict()
    before_fields.pop('technical_snapshot_id'); after_fields.pop('technical_snapshot_id')
    assert before_fields == after_fields


def test_private_result_has_no_serializer_and_repr_omits_calculated_values():
    s = series([1, 2, 1, 2, 1])
    result = calculate_daily_engine_inputs(s, s.read_at)
    assert not hasattr(result, 'to_dict') and not hasattr(result.data, 'to_dict')
    assert '0.75' not in repr(result) and '-0.5' not in repr(result.data)
