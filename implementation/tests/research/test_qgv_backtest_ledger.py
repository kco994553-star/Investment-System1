"""Hand-calculated, in-memory ledger examples; these contain no market data."""
from datetime import date
from decimal import Decimal, localcontext

import pytest

from investment_system.research.qgv_backtest.ledger import (
    Dividend, Ledger, LedgerError, Settlement, Split,
)

D = Decimal
S = date(2020, 2, 14)
T = date(2020, 2, 18)
U = date(2020, 2, 19)
V = date(2020, 2, 20)


def close_to(actual, expected):
    assert abs(actual - D(expected)) < D('1e-22')


def test_signal_close_quantities_gap_and_proportional_cash_after_costs():
    ledger = Ledger(D('1000'))
    assert ledger.rebalance(S, ['A', 'B'], 2, {'A': D('10'), 'B': D('20')}) == {'A': D('50'), 'B': D('25')}
    fills = ledger.execute_open(T, {'A': D('20'), 'B': D('40')})
    # Costs included: 2002 requested, so both requested quantities scale 1000/2002.
    close_to(ledger.holdings['A'], '24.97502497502497502497502498')
    close_to(ledger.holdings['B'], '12.48751248751248751248751249')
    close_to(fills[0].quantity / fills[1].quantity, '2')
    assert ledger.cash >= 0
    close_to(sum(f.fee for f in fills), '0.999000999000999000999001')
    close_to(ledger.nav(T, {'A': D('20'), 'B': D('40')}).nav, '999.000999000999000999000999')
    assert ledger.pending['A'] > 0


def test_net_delta_empty_slots_and_sells_before_buys():
    ledger = Ledger(D('1000'), cost_bps=0)
    ledger.rebalance(S, ['A'], 2, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    assert ledger.cash == 500  # Missing second slot remains cash.
    assert ledger.rebalance(U, ['A', 'B'], 2, {'A': D('20'), 'B': D('10')}) == {'A': D('-12.5'), 'B': D('75')}
    fills = ledger.execute_open(V, {'A': D('20'), 'B': D('10')})
    assert [(f.security_id, f.quantity) for f in fills] == [('A', D('-12.5')), ('B', D('75'))]
    assert ledger.cash == 0
    assert ledger.holdings == {'A': D('37.5'), 'B': D('75')}


def test_suspended_sale_is_not_cash_pending_buys_wait_then_fill():
    ledger = Ledger(1000, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    ledger.rebalance(U, ['B'], 1, {'A': D('10'), 'B': D('20')})
    assert ledger.execute_open(V, {'A': None, 'B': D('20')}) == ()
    assert ledger.holdings == {'A': D('100')}
    assert ledger.pending == {'A': D('-100'), 'B': D('50')}
    assert {x.reason for x in ledger.unfilled} == {'UNAVAILABLE_OPEN', 'INSUFFICIENT_CASH'}
    fills = ledger.execute_open(date(2020, 2, 21), {'A': D('10'), 'B': D('20')})
    assert [f.quantity for f in fills] == [D('-100'), D('50')]
    assert ledger.pending == {}


def test_next_regular_decision_cancels_old_remaining_orders():
    ledger = Ledger(1000, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {})
    assert ledger.rebalance(U, ['B'], 1, {'B': D('20')}) == {'B': D('50')}
    assert ledger.cancellations[0].security_id == 'A'
    ledger.execute_open(V, {'A': D('1'), 'B': D('20')})
    assert ledger.holdings == {'B': D('50')}


def test_split_transforms_holdings_and_unfilled_quantity_without_value_change():
    ledger = Ledger(1000, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('20')})  # 50 acquired, 50 still pending.
    ledger.apply_event(Split('split-1', U, 'A', D('2')), U)
    assert ledger.holdings == {'A': D('100')}
    assert ledger.pending == {'A': D('100')}
    assert ledger.nav(U, {'A': D('10')}).nav == 1000
    ledger.apply_event(Split('split-1', U, 'A', D('2')), U)
    assert ledger.holdings['A'] == 100


def test_dividend_receivable_cash_and_reinvestment_lock():
    ledger = Ledger(1000, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('20')})
    dividend = Dividend('div-1', U, 'A', D('2'), V)
    ledger.apply_event(dividend, U)
    assert ledger.nav(U, {'A': D('18')}).nav == 1000  # 900 stock + 100 claim.
    assert ledger.cash == 0
    ledger.settle_events(V)
    assert ledger.cash == ledger.reserved_cash == 100
    assert ledger.receivables == {}
    assert ledger.execute_open(V, {'A': D('18')}) == ()
    ledger.apply_event(dividend, V)
    assert ledger.cash == 100  # Event retry must not pay twice.
    ledger.rebalance(date(2020, 2, 21), ['A'], 1, {'A': D('18')})
    assert ledger.reserved_cash == 0
    ledger.execute_open(date(2020, 2, 24), {'A': D('18')})
    close_to(ledger.cash, '0')


def test_dividend_record_date_quantity_survives_sale_before_pay_date():
    ledger = Ledger(1000, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    ledger.apply_event(Dividend('div', U, 'A', D('1'), V), U)
    ledger.rebalance(U, [], 1, {'A': D('9')})
    ledger.execute_open(V, {'A': D('9')})
    ledger.settle_events(V)
    assert ledger.cash == 1000
    assert ledger.reserved_cash == 100


def test_unconfirmed_delisting_retains_asset_and_blocks_nav_even_with_old_mark():
    ledger = Ledger(1000, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    ledger.apply_event(Settlement('gone', U, 'A', 'CASH_MERGER', None, None), U)
    snapshot = ledger.nav(U, {'A': D('10')})
    assert snapshot.status == 'INCOMPLETE_NAV'
    assert snapshot.nav is None
    assert ledger.holdings == {'A': D('100')}
    with pytest.raises(LedgerError, match='INCOMPLETE_NAV'):
        ledger.rebalance(V, ['B'], 1, {'A': D('10'), 'B': D('20')})


@pytest.mark.parametrize('kind,cash,new_id,ratio,expected', [
    ('CASH_MERGER', D('12'), None, None, {'cash': D('1200'), 'positions': {}}),
    ('STOCK_MERGER', D('2'), 'B', D('.5'), {'cash': D('200'), 'positions': {'B': D('50')}}),
    ('SPINOFF', D('0'), 'B', D('.25'), {'cash': D('0'), 'positions': {'A': D('100'), 'B': D('25')}}),
])
def test_confirmed_corporate_settlement_applies_only_on_settlement_day(kind, cash, new_id, ratio, expected):
    ledger = Ledger(1000, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    event = Settlement('corporate', U, 'A', kind, V, cash, new_id, ratio)
    ledger.apply_event(event, U)
    assert ledger.holdings == {'A': D('100')}
    assert ledger.nav(U, {'A': D('10')}).status == 'INCOMPLETE_NAV'
    ledger.settle_events(V)
    assert ledger.cash == expected['cash']
    assert ledger.holdings == expected['positions']
    ledger.settle_events(V)
    assert ledger.cash == expected['cash']


def test_missing_mark_is_incomplete_never_cached_or_zero_filled():
    ledger = Ledger(100, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    assert ledger.nav(T, {'A': D('10')}).nav == 100
    snapshot = ledger.nav(U, {})
    assert snapshot.nav is None
    assert snapshot.reasons == ('MISSING_MARK:A',)


def test_open_execution_retry_is_idempotent_but_conflicting_input_rejected():
    ledger = Ledger(100, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    original = ledger.execute_open(T, {'A': D('10')})
    assert ledger.execute_open(T, {'A': D('10')}) == original
    assert ledger.holdings == {'A': D('10')}
    with pytest.raises(LedgerError):
        ledger.execute_open(T, {'A': D('20')})
    with pytest.raises(LedgerError):
        ledger.execute_open(S, {'A': D('10')})


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1'])
def test_invalid_initial_cash_rejected(value):
    with pytest.raises(LedgerError):
        Ledger(D(value))


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', '10000'])
def test_invalid_cost_rejected(value):
    with pytest.raises(LedgerError):
        Ledger(100, cost_bps=D(value))


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', '0'])
def test_invalid_open_fails_atomically_before_any_sale(value):
    ledger = Ledger(100, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    ledger.rebalance(U, ['B'], 1, {'A': D('10'), 'B': D('10')})
    with pytest.raises(LedgerError):
        ledger.execute_open(V, {'A': D('10'), 'B': D(value)})
    assert ledger.cash == 0
    assert ledger.holdings == {'A': D('10')}


def test_bad_event_or_conflicting_event_retry_never_mutates_holdings():
    ledger = Ledger(100, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    with pytest.raises(LedgerError):
        ledger.apply_event(Split('bad', U, 'A', D('NaN')), U)
    ledger.apply_event(Split('ok', U, 'A', D('2')), U)
    with pytest.raises(LedgerError):
        ledger.apply_event(Split('ok', U, 'A', D('3')), U)
    assert ledger.holdings['A'] == 20


def test_bad_rebalance_input_does_not_cancel_valid_pending_orders():
    ledger = Ledger(100)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    with pytest.raises(LedgerError):
        ledger.rebalance(U, ['B'], 1, {'B': D('0')})
    assert ledger.pending == {'A': D('10')}
    with pytest.raises(LedgerError):
        ledger.rebalance(U, ['A', 'A'], 2, {'A': D('10')})
    with pytest.raises(LedgerError):
        ledger.rebalance(U, ['A'], 0, {'A': D('10')})


def test_interest_actual_calendar_days_and_retry_cannot_double_accrue():
    ledger = Ledger(1000)
    amount = ledger.accrue_cash_interest(S, date(2020, 2, 17), D('.0365'))
    assert amount == D('.3')  # Three calendar days, including the weekend.
    assert ledger.cash == D('1000.3')
    assert ledger.accrue_cash_interest(S, date(2020, 2, 17), D('.0365')) == D('.3')
    assert ledger.cash == D('1000.3')
    with pytest.raises(LedgerError):
        ledger.accrue_cash_interest(S, T, D('.0365'))
    with pytest.raises(LedgerError):
        ledger.accrue_cash_interest(date(2020, 2, 17), T, D('NaN'))
    assert ledger.cash == D('1000.3')


def test_missing_or_stale_rate_blocks_interest_without_assuming_zero():
    ledger = Ledger(1000)
    with pytest.raises(LedgerError, match='CASH_RATE_UNVERIFIED'):
        ledger.accrue_cash_interest(S, T, None)
    with pytest.raises(LedgerError, match='CASH_RATE_UNVERIFIED'):
        ledger.accrue_cash_interest(S, T, D('.0365'), stale_sessions=6)
    assert ledger.cash == 1000
    assert ledger.accrue_cash_interest(S, T, D('.0365'), stale_sessions=5) == D('.4')


def test_unconfirmed_corporate_action_can_be_resolved_without_losing_asset():
    ledger = Ledger(1000, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    ledger.apply_event(Settlement('gone', U, 'A', 'DELISTING', None, None), U)
    confirmed = Settlement('gone', U, 'A', 'DELISTING', V, D('3'))
    ledger.confirm_settlement(confirmed, V)
    assert ledger.cash == 300
    assert ledger.holdings == {}
    assert ledger.nav(V, {}).nav == 300
    ledger.confirm_settlement(confirmed, V)
    assert ledger.cash == 300


def test_confirmation_cannot_rewrite_already_confirmed_terms():
    ledger = Ledger(1000, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    event = Settlement('gone', U, 'A', 'CASH_MERGER', V, D('12'))
    ledger.apply_event(event, U)
    with pytest.raises(LedgerError):
        ledger.confirm_settlement(Settlement('gone', U, 'A', 'CASH_MERGER', V, D('30')), U)
    assert ledger.holdings == {'A': D('100')}
    assert ledger.cash == 0


def test_recurring_decimal_cash_scaling_never_overdraws_last_buy():
    ledger = Ledger(1)
    ledger.rebalance(S, ['A', 'B'], 2, {'A': D('3'), 'B': D('3')})
    fills = ledger.execute_open(T, {'A': D('7'), 'B': D('7')})
    assert len(fills) == 2
    assert fills[0].quantity == fills[1].quantity
    assert ledger.cash >= 0
    close_to(ledger.cash, '0')


def test_split_scales_suspended_sell_and_retains_no_phantom_cash():
    ledger = Ledger(100, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    ledger.rebalance(U, [], 1, {'A': D('10')})
    ledger.apply_event(Split('split-sell', V, 'A', D('2')), V)
    assert ledger.pending == {'A': D('-20')}
    ledger.execute_open(V, {'A': D('5')}, suspended=['A'])
    assert ledger.cash == 0
    assert ledger.holdings['A'] == 20
    ledger.execute_open(date(2020, 2, 21), {'A': D('5')})
    assert ledger.cash == 100
    assert ledger.holdings == {}


@pytest.mark.parametrize('event', [
    Dividend('bad', U, 'A', D('NaN'), V),
    Dividend('bad', U, 'A', D('1'), T),
    Settlement('bad', U, 'A', 'CASH_MERGER', V, D('Infinity')),
    Settlement('bad', U, 'A', 'STOCK_MERGER', V, D('0'), 'B', D('Infinity')),
    Settlement('bad', U, 'A', 'SPINOFF', T, D('0'), 'B', D('1')),
])
def test_malformed_corporate_terms_rejected_before_mutation(event):
    ledger = Ledger(100, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('10')})
    with pytest.raises(LedgerError):
        ledger.apply_event(event, U)
    assert ledger.cash == 0
    assert ledger.receivables == {}
    assert ledger.holdings == {'A': D('10')}
    assert ledger.nav(U, {'A': D('10')}).nav == 100


def test_split_preserves_all_finite_decimal_quantity_digits():
    ledger = Ledger(1, cost_bps=0)
    ledger.rebalance(S, ['A'], 3, {'A': D('1')})
    ledger.execute_open(T, {'A': D('1')})
    before = ledger.holdings['A']
    ledger.apply_event(Split('precise', U, 'A', D('5')), U)
    with localcontext() as context:
        context.prec = 100
        assert ledger.holdings['A'] / D('5') == before
    ledger.rebalance(U, [], 1, {'A': D('.2')})
    ledger.execute_open(V, {'A': D('.2')})
    assert ledger.holdings == {}


def test_negative_interest_on_entirely_reserved_dividend_cash_keeps_it_reserved():
    ledger = Ledger(100, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('20')})
    ledger.apply_event(Dividend('reserved', U, 'A', D('2'), U), U)
    assert ledger.cash == ledger.reserved_cash == 10
    assert ledger.accrue_cash_interest(U, V, D('-.365')) == D('-.01')
    assert ledger.cash == ledger.reserved_cash == D('9.99')
    assert ledger.execute_open(V, {'A': D('20')}) == ()
    # Retry returns the original accrual without applying another loss.
    assert ledger.accrue_cash_interest(U, V, D('-.365')) == D('-.01')
    assert ledger.cash == ledger.reserved_cash == D('9.99')


def test_negative_interest_loss_is_shared_proportionally_with_reserved_cash():
    ledger = Ledger(100, cost_bps=0)
    ledger.rebalance(S, ['A', 'B'], 2, {'A': D('10'), 'B': D('10')})
    ledger.execute_open(T, {'A': D('10'), 'B': None})
    ledger.apply_event(Dividend('mixed', U, 'A', D('2'), U), U)
    assert ledger.cash == 60
    assert ledger.reserved_cash == 10
    assert ledger.accrue_cash_interest(U, V, D('-.365')) == D('-.06')
    assert ledger.cash == D('59.94')
    assert ledger.reserved_cash == D('9.99')
    fills = ledger.execute_open(V, {'B': D('10')})
    assert fills[0].quantity == D('4.995')  # Spend only 49.95 of remaining cash.
    assert ledger.cash == ledger.reserved_cash == D('9.99')


def test_interest_that_would_exhaust_more_than_all_cash_is_rejected_atomically():
    ledger = Ledger(100)
    with pytest.raises(LedgerError):
        ledger.accrue_cash_interest(S, T, D('-365'))
    assert ledger.cash == 100
    assert ledger.reserved_cash == 0


@pytest.mark.parametrize('rate,expected_interest', [(D('.365'), D('.2')), (D('-.365'), D('-.2'))])
def test_explicit_interest_base_keeps_calendar_split_intervals_simple(rate, expected_interest):
    first = date(2020, 2, 21)
    middle = date(2020, 2, 22)
    last = date(2020, 2, 23)
    whole = Ledger(100)
    assert whole.accrue_cash_interest(first, last, rate, interest_base=D('100')) == expected_interest
    split = Ledger(100)
    first_amount = split.accrue_cash_interest(first, middle, rate, interest_base=D('100'))
    second_amount = split.accrue_cash_interest(middle, last, rate, interest_base=D('100'))
    assert first_amount + second_amount == expected_interest
    assert split.cash == whole.cash
    # Both principal and rate belong to the replay identity.
    with pytest.raises(LedgerError):
        split.accrue_cash_interest(middle, last, rate, interest_base=D('99'))


@pytest.mark.parametrize('principal', [D('NaN'), D('Infinity'), D('-1')])
def test_explicit_interest_base_must_be_finite_nonnegative(principal):
    ledger = Ledger(100)
    with pytest.raises(LedgerError):
        ledger.accrue_cash_interest(U, V, D('.365'), interest_base=principal)
    assert ledger.cash == 100


def test_explicit_base_negative_interest_preserves_reserved_cash_proportion():
    ledger = Ledger(100, cost_bps=0)
    ledger.rebalance(S, ['A'], 1, {'A': D('10')})
    ledger.execute_open(T, {'A': D('20')})
    ledger.apply_event(Dividend('reserved-base', U, 'A', D('2'), U), U)
    ledger.accrue_cash_interest(U, V, D('-.365'), interest_base=D('10'))
    assert ledger.cash == ledger.reserved_cash == D('9.99')
    ledger.accrue_cash_interest(V, date(2020, 2, 21), D('-.365'), interest_base=D('10'))
    assert ledger.cash == ledger.reserved_cash == D('9.98')
