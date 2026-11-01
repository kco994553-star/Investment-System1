"""Hand-calculated ledger examples for EXP-STOCK-INDICATOR-DECILES-v1. Synthetic numbers only, no market data."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from investment_system.research.exp_deciles.ledger import (
    DEFAULT_COST_BPS, DEFAULT_INITIAL_CAPITAL, Dividend, Ledger, LedgerError, Rebalance, Settlement,
    SettlementConfirmation, Split, run_ledger, run_scenarios,
)

D = Decimal
# Synthetic consecutive "sessions" (calendar days); no exchange calendar is implied.
DAYS = tuple(date(2030, 3, 1) + timedelta(days=i) for i in range(30))
d = DAYS
EVIDENCE = 'synthetic evidence record'


def px(day, sid, open_, close, **extra):
    return dict(date=day, security_id=sid, open=open_, close=close, price_basis='RAW', **extra)


def flat(sid, value, *, skip=(), days=DAYS):
    return [px(day, sid, value, value) for day in days if day not in skip]


def run(rebalances, prices, events=(), *, scenario='LOSS', cost=0, capital=1000, end=None, days=DAYS):
    return run_ledger(days, rebalances, prices, events, scenario=scenario, cost_bps=cost, initial_capital=capital,
                      end=end)


def row_on(result, day):
    return next(row for row in result['daily'] if row['date'] == day)


def close_to(actual, expected, tol='1e-20'):
    assert abs(D(actual) - D(expected)) < D(tol), (actual, expected)


def qty(result, day):
    return {sid: pos['quantity'] for sid, pos in row_on(result, day)['positions'].items()}


# -- T-only execution, unfilled slots ----------------------------------------------------------------------------
def test_orders_fill_only_at_t_open_and_unfilled_slot_stays_cash_until_next_reselection():
    prices = (flat('A', 10) + flat('C', 30)
              + [px(day, 'B', None if day == d[1] else 20, 20) for day in DAYS])
    rebalances = [Rebalance(d[0], d[1], ['A', 'B']), Rebalance(d[5], d[6], ['A', 'B'])]
    result = run(rebalances, prices)
    first = result['rebalances'][0]
    assert first['targets'] == {'A': D('50'), 'B': D('25')}
    assert [(u.security_id, u.reason, u.requested_quantity) for u in first['unfilled']] == [
        ('B', 'UNAVAILABLE_OPEN', D('25'))]
    # B opens on every later session but is never retried; its slot stays cash until the next reselection.
    for day in d[1:6]:
        assert qty(result, day) == {'A': D('50')}
        assert row_on(result, day)['cash'] == 500
    assert {fill.session for fill in result['fills']} == {d[1], d[6]}
    second = result['rebalances'][1]
    assert second['target_base'] == 1000
    assert [(f.security_id, f.quantity) for f in second['fills']] == [('B', D('25'))]
    assert qty(result, d[6]) == {'A': D('50'), 'B': D('25')}
    assert row_on(result, d[6])['cash'] == 0
    # No next-rank promotion: C is priced throughout and never bought.
    assert all('C' not in row['positions'] for row in result['daily'])


def test_suspended_and_insufficient_cash_reasons_with_slot_cash_held_back():
    prices = ([px(day, 'A', 10, 10, suspended=day == d[1]) for day in DAYS]
              + [px(day, 'B', 20 if day == d[1] else 10, 10) for day in DAYS] + flat('C', 10))
    result = run([Rebalance(d[0], d[1], ['A', 'B', 'C'])], prices, capital=900)
    record = result['rebalances'][0]
    assert record['targets'] == {'A': D('30'), 'B': D('30'), 'C': D('30')}
    reasons = {(u.security_id, u.reason, u.partial) for u in record['unfilled']}
    assert reasons == {('A', 'SUSPENDED', False), ('B', 'INSUFFICIENT_CASH', True), ('C', 'INSUFFICIENT_CASH', True)}
    # A's planned 300 stays cash; B's gap-up cannot use it: B and C share 600 at ratio 600/900.
    assert record['slot_cash_held_back'] == 300
    close_to(row_on(result, d[1])['cash'], '300')
    close_to(qty(result, d[1])['B'], '20')
    close_to(qty(result, d[1])['C'], '20')
    assert 'A' not in qty(result, d[1])


def test_missing_signal_price_is_unfilled_at_s_and_its_slot_stays_cash():
    prices = flat('A', 10, skip=(d[1],)) + [px(d[1], 'A', 12, 12)] + flat('B', 20, skip=(d[0],))
    result = run([Rebalance(d[0], d[1], ['A', 'B'])], prices)
    record = result['rebalances'][0]
    assert [(u.security_id, u.reason, u.session) for u in record['unfilled_at_signal']] == [
        ('B', 'MISSING_SIGNAL_PRICE', d[0])]
    assert record['slot_cash_held_back_at_signal'] == 500
    # A's S-locked 50 shares cost 600 at the T open; only A's own 500 slot is available.
    close_to(qty(result, d[1])['A'], D(500) / D(12))
    close_to(row_on(result, d[1])['cash'], '500')


def test_s_locked_targets_sells_first_then_buys_and_cost_ten_bp_per_side():
    prices = flat('A', 10) + flat('B', 20)
    rebalances = [Rebalance(d[0], d[1], ['A']), Rebalance(d[3], d[4], ['B'])]
    result = run(rebalances, prices, cost=10)
    buy = result['rebalances'][0]['fills'][0]
    # 100 requested at 10 costs 1001 with fees, so the buy scales by 1000/1001.
    close_to(buy.quantity, D(100) * D(1000) / D(1001))
    close_to(buy.fee, buy.gross * D('0.001'))
    second = result['rebalances'][1]
    assert [f.quantity < 0 for f in second['fills']] == [True, False]
    sell, buy_b = second['fills']
    close_to(sell.fee, sell.gross * D('0.001'))
    close_to(buy_b.fee, buy_b.gross * D('0.001'))
    close_to(second['costs'], sell.fee + buy_b.fee)
    close_to(result['total_costs'], sum((f.fee for f in result['fills']), D(0)))
    zero = run(rebalances, prices, cost=0)
    assert all(f.fee == 0 for f in zero['fills'])
    assert row_on(zero, d[10])['nav'] == 1000
    assert row_on(result, d[10])['nav'] < 1000


def test_defaults_are_usd_one_million_and_ten_bp():
    assert DEFAULT_INITIAL_CAPITAL == D('1000000')
    assert DEFAULT_COST_BPS == D('10')
    result = run_ledger(DAYS, [Rebalance(d[0], d[1], ['A'])], flat('A', 10), scenario='LOSS')
    assert result['initial_capital'] == D('1000000') and result['cost_bps'] == D('10')
    assert result['currency'] == 'USD' and result['cash_interest'] == 'ZERO'
    assert row_on(result, d[0])['nav'] == D('1000000')


# -- reserved corporate-action cash -----------------------------------------------------------------------------
def test_settlement_cash_between_s_and_t_is_reserved_and_cannot_fund_buys():
    merger = Settlement('m1', d[5], 'A', 'CASH_MERGER', d[5], EVIDENCE, d[5], D('12'))
    prices = flat('A', 10, skip=DAYS[5:]) + flat('B', 20)
    rebalances = [Rebalance(d[0], d[1], ['A']), Rebalance(d[4], d[6], ['B']), Rebalance(d[8], d[9], ['B'])]
    for scenario in ('LOSS', 'CARRY'):
        result = run(rebalances, prices, [merger], scenario=scenario)
        day5 = row_on(result, d[5])
        assert day5['cash'] == day5['reserved_cash'] == 1200
        assert day5['positions'] == {}
        second = result['rebalances'][1]
        assert {(u.security_id, u.reason, u.partial) for u in second['unfilled']} == {
            ('A', 'UNSETTLED_CORPORATE_ACTION', False), ('B', 'INSUFFICIENT_CASH', False)}
        assert second['fills'] == ()
        assert row_on(result, d[7])['cash'] == row_on(result, d[7])['reserved_cash'] == 1200
        third = result['rebalances'][2]
        assert third['released_reserved_cash'] == 1200 and third['target_base'] == 1200
        assert qty(result, d[9]) == {'B': D('60')}
        assert row_on(result, d[9])['cash'] == 0


def test_settlement_cash_received_before_s_is_released_at_reselection():
    merger = Settlement('m2', d[2], 'A', 'CASH_MERGER', d[2], EVIDENCE, d[3], D('11'))
    prices = flat('A', 10, skip=DAYS[2:]) + flat('B', 20)
    result = run([Rebalance(d[0], d[1], ['A']), Rebalance(d[5], d[6], ['B'])], prices, [merger])
    assert row_on(result, d[2])['receivables'] == 1100 and row_on(result, d[2])['cash'] == 0
    assert row_on(result, d[3])['reserved_cash'] == 1100
    assert row_on(result, d[4])['spendable_cash'] == 0
    assert result['rebalances'][1]['released_reserved_cash'] == 1100
    assert qty(result, d[6]) == {'B': D('55')}


def test_dividend_receivable_then_reserved_cash_reinvested_only_at_next_reselection():
    prices = flat('A', 10, skip=DAYS[2:]) + flat('A', 9, days=DAYS[2:]) + flat('B', 20)
    dividend = Dividend('div1', d[2], 'A', D('1'), d[3])
    result = run([Rebalance(d[0], d[1], ['A']), Rebalance(d[5], d[6], ['A', 'B'])], prices, [dividend])
    ex_day = row_on(result, d[2])
    assert ex_day['nav'] == 1000 and ex_day['receivables'] == 100 and ex_day['cash'] == 0
    for day in d[3:6]:
        assert row_on(result, day)['cash'] == row_on(result, day)['reserved_cash'] == 100
    second = result['rebalances'][1]
    assert second['released_reserved_cash'] == 100 and second['target_base'] == 1000
    close_to(qty(result, d[6])['A'], D(500) / D(9))
    assert qty(result, d[6])['B'] == 25
    close_to(row_on(result, d[6])['cash'], '0')


def test_dividend_paid_between_s_and_t_is_reserved_and_cannot_fund_t_buys():
    prices = flat('A', 10, skip=DAYS[5:]) + flat('A', 9, days=DAYS[5:]) + flat('B', 20)
    dividend = Dividend('div2', d[5], 'A', D('1'), d[5])
    result = run([Rebalance(d[0], d[1], ['A']), Rebalance(d[4], d[5], ['B'])], prices, [dividend])
    record = result['rebalances'][1]
    # Sale gives 900 plus 100 dividend cash, but only 900 is spendable: B fills 45 of 50.
    close_to(qty(result, d[5])['B'], '45')
    assert [(u.security_id, u.reason, u.partial) for u in record['unfilled']] == [('B', 'INSUFFICIENT_CASH', True)]
    assert row_on(result, d[5])['reserved_cash'] == 100
    close_to(row_on(result, d[5])['cash'], '100')
    assert row_on(result, d[5])['nav'] == 1000


def test_dividend_without_pay_date_pays_on_ex_date_with_flag():
    result = run([Rebalance(d[0], d[1], ['A'])], flat('A', 10), [Dividend('div3', d[3], 'A', D('0.5'))])
    day = row_on(result, d[3])
    assert 'DIVIDEND_PAY_DATE_ASSUMED_EX_DATE:div3' in day['flags']
    assert day['cash'] == day['reserved_cash'] == 50
    assert day['nav'] == 1050


# -- zero interest ----------------------------------------------------------------------------------------------
def test_cash_interest_is_zero_and_other_modes_are_rejected():
    result = run([Rebalance(d[0], d[1], ['A'])], [px(day, 'A', None, 10) for day in DAYS])
    assert all(row['cash'] == 1000 and row['nav'] == 1000 for row in result['daily'])
    assert result['fills'] == ()
    with pytest.raises(LedgerError, match='UNSUPPORTED_CASH_INTEREST_MODE'):
        Ledger(scenario='LOSS', cash_interest='RATE_ROWS')
    with pytest.raises(LedgerError, match='UNSUPPORTED_CASH_INTEREST_MODE'):
        run_ledger(DAYS, [Rebalance(d[0], d[1], ['A'])], flat('A', 10), scenario='LOSS', cash_interest='H15')


# -- splits ------------------------------------------------------------------------------------------------------
def test_split_adjusts_quantity_on_effective_date_without_double_counting_raw_prices():
    prices = flat('A', 10, skip=DAYS[3:]) + flat('A', 5, days=DAYS[3:])
    result = run([Rebalance(d[0], d[1], ['A'])], prices, [Split('s1', d[3], 'A', D('2'))])
    assert qty(result, d[2]) == {'A': D('100')} and qty(result, d[3]) == {'A': D('200')}
    assert all(row['nav'] == 1000 for row in result['daily'])


def test_split_during_price_gap_rebases_the_stale_mark():
    prices = flat('A', 10, days=DAYS[:3]) + flat('A', 5, days=DAYS[6:])
    result = run([Rebalance(d[0], d[1], ['A'])], prices, [Split('s2', d[4], 'A', D('2'))])
    day = row_on(result, d[4])
    assert day['positions']['A']['price'] == 5 and day['positions']['A']['stale']
    assert 'STALE_MARK:A' in day['flags']
    assert all(row['nav'] == 1000 for row in result['daily'])


def test_split_between_s_and_t_scales_the_pending_order():
    prices = flat('A', 10, skip=DAYS[2:]) + flat('A', 5, days=DAYS[2:])
    result = run([Rebalance(d[1], d[2], ['A'])], prices, [Split('s3', d[2], 'A', D('2'))])
    assert result['rebalances'][0]['targets'] == {'A': D('100')}
    assert qty(result, d[2]) == {'A': D('200')}
    assert row_on(result, d[2])['cash'] == 0


# -- stale marks are not terminations ---------------------------------------------------------------------------
def test_missing_price_is_a_stale_mark_never_a_loss_or_carry_and_never_traded_later():
    prices = flat('A', 10, days=DAYS[:3]) + flat('A', 7, days=DAYS[12:]) + flat('B', 10)
    rebalances = [Rebalance(d[0], d[1], ['A', 'B']), Rebalance(d[6], d[7], ['B'])]
    runs = run_scenarios(DAYS, rebalances, prices, (), cost_bps=0, initial_capital=1000)
    for scenario, result in runs.items():
        for day in d[3:12]:
            row = row_on(result, day)
            assert 'STALE_MARK:A' in row['flags']
            assert row['positions']['A']['state'] == 'HELD' and row['positions']['A']['price'] == 10
            assert not any(flag.startswith(('LOSS_SCENARIO', 'CARRY_SCENARIO')) for flag in row['flags'])
            assert row['carry_value'] == 0
        second = result['rebalances'][1]
        assert second['stale_signal_marks'] == ('A',)
        # The unsold stale name is not cash, so B's top-up has nothing to spend.
        assert {(u.security_id, u.reason) for u in second['unfilled']} == {
            ('A', 'UNAVAILABLE_OPEN'), ('B', 'INSUFFICIENT_CASH')}
        assert qty(result, d[13])['A'] == 50  # Not sold later when prices return.
        assert row_on(result, d[13])['positions']['A']['stale'] is False
    assert [r['nav'] for r in runs['LOSS']['daily']] == [r['nav'] for r in runs['CARRY']['daily']]


# -- termination scenarios --------------------------------------------------------------------------------------
def _termination_case(events, extra_rebalance=None, more_prices=()):
    prices = flat('A', 10, skip=DAYS[2:]) + [px(d[2], 'A', 9, 8)] + flat('B', 10) + list(more_prices)
    rebalances = [Rebalance(d[0], d[1], ['A', 'B'])] + ([extra_rebalance] if extra_rebalance else [])
    return run_scenarios(DAYS, rebalances, prices, events, cost_bps=0, initial_capital=1000)


def test_unconfirmed_termination_loss_zero_carry_last_price_from_available_date_only():
    delisting = Settlement('del1', d[4], 'A', 'DELISTING', d[5], EVIDENCE)
    runs = _termination_case([delisting])
    for scenario, result in runs.items():
        for day in d[3:5]:  # Effective but not yet evidenced: only a stale mark.
            row = row_on(result, day)
            assert row['nav'] == 900 and 'STALE_MARK:A' in row['flags']
            assert row['positions']['A']['state'] == 'HELD'
        row = row_on(result, d[5])
        assert row['positions']['A']['quantity'] == 50  # Legal quantity kept in both scenarios.
        assert 'TERMINATION_UNCONFIRMED:del1:' + scenario in row['events']
    loss, carry = runs['LOSS'], runs['CARRY']
    for day in d[5:]:
        assert row_on(loss, day)['nav'] == 500 and row_on(loss, day)['positions']['A']['value'] == 0
        assert 'LOSS_SCENARIO:A' in row_on(loss, day)['flags']
        assert row_on(carry, day)['nav'] == 900 and row_on(carry, day)['carry_value'] == 400
        assert row_on(carry, day)['positions']['A']['price'] == 8
        assert row_on(carry, day)['cash'] == 0  # CARRY is never cash.
        assert 'CARRY_SCENARIO:A' in row_on(carry, day)['flags']


def test_carry_asset_is_never_sold_cashed_or_reinvested_at_reselection():
    delisting = Settlement('del2', d[4], 'A', 'DELISTING', d[4], EVIDENCE)
    runs = _termination_case([delisting], Rebalance(d[7], d[8], ['A', 'B', 'C']), flat('C', 10))
    carry = runs['CARRY']
    record = carry['rebalances'][1]
    assert record['frozen_positions'] == {'A': 'CARRY'}
    assert record['carry_value_excluded'] == 400
    assert record['target_base'] == 500 and record['nav_at_signal'] == 900
    assert 'A' not in record['orders']
    assert [(u.security_id, u.reason) for u in record['unfilled_at_signal']] == [('A', 'UNSETTLED_CORPORATE_ACTION')]
    assert all(fill.security_id != 'A' for fill in record['fills'])
    after = row_on(carry, d[8])
    assert after['positions']['A']['state'] == 'CARRY' and after['positions']['A']['quantity'] == 50
    assert after['carry_value'] == 400
    # A's slot (500/3) stays cash; B and C restore to 500/3 each. Nothing came from the carry asset.
    close_to(after['cash'], D(500) / 3)
    close_to(after['nav'], '900')
    loss_after = row_on(runs['LOSS'], d[8])
    close_to(loss_after['nav'], '500')
    assert loss_after['positions']['A']['quantity'] == 50


def test_later_confirmation_replaces_scenario_value_from_its_own_date_without_backdating():
    delisting = Settlement('del3', d[4], 'A', 'DELISTING', d[4], EVIDENCE)
    confirmation = SettlementConfirmation('del3', d[9], EVIDENCE, d[6], D('3'))
    runs = _termination_case([delisting, confirmation])
    for day in d[4:9]:
        assert row_on(runs['LOSS'], day)['nav'] == 500
        assert row_on(runs['CARRY'], day)['nav'] == 900
    for scenario, result in runs.items():
        row = row_on(result, d[9])
        assert row['positions'] == {'B': {**row['positions']['B']}} and 'A' not in row['positions']
        # Terms say pay on d[6], but they are known only on d[9]: cash arrives on d[9], reserved.
        assert row['cash'] == row['reserved_cash'] == 150
        assert row['nav'] == 650
        assert 'SETTLEMENT_CONFIRMED:del3' in row['events']
    assert [r['nav'] for r in runs['LOSS']['daily'][9:]] == [r['nav'] for r in runs['CARRY']['daily'][9:]]


def test_confirmed_termination_settles_by_its_terms_identically_in_both_scenarios():
    merger = Settlement('m3', d[4], 'A', 'CASH_MERGER', d[3], EVIDENCE, d[6], D('12'))
    repeat = SettlementConfirmation('m3', d[7], EVIDENCE, d[6], D('12'))  # Identical terms: no second payment.
    runs = _termination_case([merger, repeat])
    assert [r['nav'] for r in runs['LOSS']['daily']] == [r['nav'] for r in runs['CARRY']['daily']]
    result = runs['LOSS']
    assert row_on(result, d[3])['positions']['A']['state'] == 'HELD'  # Evidenced early, effective later.
    row = row_on(result, d[4])
    assert 'A' not in row['positions'] and row['receivables'] == 600 and row['nav'] == 1100
    assert row_on(result, d[6])['cash'] == row_on(result, d[6])['reserved_cash'] == 600


def test_stock_merger_delivers_new_shares_on_activation_and_cash_leg_reserved():
    merger = Settlement('m4', d[4], 'A', 'STOCK_MERGER', d[4], EVIDENCE, d[5], D('1'), 'N', D('0.5'))
    runs = _termination_case([merger], more_prices=flat('N', 20, days=DAYS[4:]))
    for result in runs.values():
        row = row_on(result, d[4])
        assert qty(result, d[4]) == {'B': D('50'), 'N': D('25')}
        assert row['nav'] == 500 + 500 + 50
        assert row_on(result, d[5])['reserved_cash'] == 50


def test_received_stock_without_any_price_marks_the_day_incomplete_not_zero():
    merger = Settlement('m5', d[4], 'A', 'STOCK_MERGER', d[4], EVIDENCE, d[4], D('0'), 'N', D('1'))
    result = _termination_case([merger], more_prices=flat('N', 20, days=DAYS[6:]))['LOSS']
    for day in d[4:6]:
        assert row_on(result, day)['nav'] is None
        assert row_on(result, day)['reasons'] == ('UNPRICED_POSITION:N',)
    assert row_on(result, d[6])['nav'] == 1000 + 500
    assert result['status'] == 'INCOMPLETE_NAV'


def test_unconfirmed_spinoff_is_flagged_and_confirmation_credits_shares_from_its_date():
    spinoff = Settlement('sp1', d[3], 'A', 'SPINOFF', d[3], EVIDENCE)
    confirmation = SettlementConfirmation('sp1', d[5], EVIDENCE, d[3], D('0'), 'S', D('0.5'))
    prices = flat('A', 10) + flat('S', 4)
    result = run([Rebalance(d[0], d[1], ['A'])], prices, [spinoff, confirmation])
    assert 'SPINOFF_TERMS_UNCONFIRMED:sp1' in row_on(result, d[3])['flags']
    assert qty(result, d[4]) == {'A': D('100')}
    assert qty(result, d[5]) == {'A': D('100'), 'S': D('50')}
    assert row_on(result, d[5])['nav'] == 1200


# -- outputs and scenario helper --------------------------------------------------------------------------------
def test_daily_and_rebalance_outputs_carry_the_required_fields():
    result = run([Rebalance(d[0], d[1], ['A'])], flat('A', 10), cost=10)
    row = row_on(result, d[1])
    for key in ('date', 'nav', 'status', 'cash', 'reserved_cash', 'receivables', 'carry_value', 'market_value',
                'positions', 'fills', 'costs', 'flags'):
        assert key in row
    assert set(row['positions']['A']) >= {'quantity', 'price', 'value', 'state'}
    assert row['fills'] and row['costs'] == row['fills'][0].fee
    assert row_on(result, d[2])['fills'] == () and row_on(result, d[2])['costs'] == 0
    record = result['rebalances'][0]
    for key in ('signal_date', 'execution_date', 'selected', 'orders', 'fills', 'unfilled', 'costs',
                'nav_at_signal', 'target_base', 'open_nav_before_trades', 'execution_status'):
        assert key in record
    assert record['execution_status'] == 'EXECUTED' and record['open_nav_before_trades'] == 1000


def test_run_scenarios_uses_the_same_selections_for_both():
    rebalances = [Rebalance(d[0], d[1], ['A'])]
    runs = run_scenarios(DAYS, rebalances, flat('A', 10), (), cost_bps=0, initial_capital=1000)
    assert set(runs) == {'LOSS', 'CARRY'}
    assert runs['LOSS']['rebalances'][0]['selected'] == runs['CARRY']['rebalances'][0]['selected'] == ('A',)
    with pytest.raises(LedgerError, match='SCENARIO_IS_SET_BY_RUN_SCENARIOS'):
        run_scenarios(DAYS, rebalances, flat('A', 10), scenario='LOSS')


def test_rebalance_whose_t_is_after_the_run_end_cancels_its_orders():
    result = run([Rebalance(d[0], d[1], ['A']), Rebalance(d[5], d[6], ['B'])], flat('A', 10) + flat('B', 10),
                 end=d[5])
    record = result['rebalances'][1]
    assert record['execution_status'] == 'AFTER_RUN_END'
    assert set(record['cancelled_orders']) == {'A', 'B'}
    assert qty(result, d[5]) == {'A': D('100')}


@pytest.mark.parametrize('rows,reason', [
    ([dict(date=d[0], security_id='A', open=10, close=10)], 'PRICE_BASIS_NOT_RAW'),
    ([dict(date=d[0], security_id='A', open=10, close=10, price_basis='ADJUSTED')], 'PRICE_BASIS_NOT_RAW'),
    ([px(d[0], 'A', 10, 10, currency='KRW')], 'PRICE_CURRENCY_NOT_USD'),
    ([px(d[0], 'A', 10, 10), px(d[0], 'A', 10, 10)], 'DUPLICATE_PRICE_KEY'),
    ([px(d[0], 'A', 10, 'NaN')], 'INVALID_PRICE'),
    ([px(d[0], 'A', 0, 10)], 'INVALID_PRICE'),
])
def test_price_rows_must_be_raw_usd_and_valid(rows, reason):
    with pytest.raises(LedgerError, match=reason):
        run([Rebalance(d[0], d[1], ['A'])], rows)


@pytest.mark.parametrize('rebalances,reason', [
    ([Rebalance(d[1], d[1], ['A'])], 'EXECUTION_MUST_FOLLOW_SIGNAL'),
    ([Rebalance(d[0], d[3], ['A']), Rebalance(d[2], d[4], ['A'])], 'REBALANCES_OVERLAP_OR_UNORDERED'),
    ([Rebalance(d[0], d[1], ['A', 'A'])], 'DUPLICATE_SELECTED_SECURITY'),
    ([Rebalance(d[0], date(2031, 1, 1), ['A'])], 'REBALANCE_DATE_NOT_A_SESSION'),
    ([], 'NO_REBALANCE'),
])
def test_invalid_rebalance_schedules_are_rejected(rebalances, reason):
    with pytest.raises(LedgerError, match=reason):
        run(rebalances, flat('A', 10))


@pytest.mark.parametrize('kwargs,reason', [
    (dict(scenario='BOTH'), 'UNKNOWN_SCENARIO'),
    (dict(scenario='LOSS', cost_bps=10000), 'INVALID_COST_BPS'),
    (dict(scenario='LOSS', cost_bps=-1), 'INVALID_COST_BPS'),
    (dict(scenario='LOSS', initial_cash=0), 'INVALID_INITIAL_CASH'),
])
def test_invalid_ledger_settings_are_rejected(kwargs, reason):
    with pytest.raises(LedgerError, match=reason):
        Ledger(**kwargs)


@pytest.mark.parametrize('events,reason', [
    ([Settlement('x', d[3], 'A', 'DELISTING', d[3], '')], 'SETTLEMENT_EVIDENCE_REQUIRED'),
    ([Settlement('x', d[3], 'A', 'BANKRUPTCY', d[3], EVIDENCE)], 'UNKNOWN_SETTLEMENT_KIND'),
    ([SettlementConfirmation('x', d[3], EVIDENCE, d[3], D('1'))], 'CONFIRMATION_WITHOUT_SETTLEMENT'),
    ([Settlement('x', d[3], 'A', 'CASH_MERGER', d[3], EVIDENCE, d[2], D('1'))], 'SETTLEMENT_PRECEDES_EFFECTIVE_DATE'),
    ([Settlement('x', d[3], 'A', 'CASH_MERGER', d[3], EVIDENCE, d[4], D('1'), 'N', D('1'))], 'UNEXPECTED_STOCK_TERMS'),
    ([Dividend('x', d[3], 'A', D('1'), d[2])], 'PAY_DATE_PRECEDES_EX_DATE'),
    ([Split('x', d[3], 'A', D('2')), Split('x', d[4], 'A', D('2'))], 'DUPLICATE_EVENT_ID'),
    ([Settlement('x', d[3], 'A', 'CASH_MERGER', d[3], EVIDENCE, None, None),
      SettlementConfirmation('x', d[5], EVIDENCE, d[5], D('1'), 'N', D('1'))], 'UNEXPECTED_STOCK_TERMS'),
])
def test_invalid_corporate_action_inputs_are_rejected(events, reason):
    with pytest.raises(LedgerError, match=reason):
        run([Rebalance(d[0], d[1], ['A'])], flat('A', 10), events)


def test_daily_position_detail_can_be_dropped_without_changing_totals():
    rebalances = [Rebalance(d[0], d[1], ['A', 'B'])]
    prices = flat('A', 10) + flat('B', 20)
    full = run(rebalances, prices, cost=10)
    lean = run_ledger(DAYS, rebalances, prices, scenario='LOSS', cost_bps=10, initial_capital=1000,
                      daily_positions=False)
    assert all(row['positions'] is None for row in lean['daily'])
    assert [r['nav'] for r in lean['daily']] == [r['nav'] for r in full['daily']]
    assert [r['flags'] for r in lean['daily']] == [r['flags'] for r in full['daily']]


# -- review F1: entitlement fixed at the effective date, delivered at activation (never back-dated) ----------------
def _spinoff_prices():
    """Parent P trades at 100 until the ex/effective date d[3], then ex-distribution at 80; child C (one per P) at 20."""
    rows = []
    for day in DAYS[:12]:
        parent = D('100') if day < d[3] else D('80')
        rows.append(px(day, 'P', parent, parent))
        rows.append(px(day, 'Q', D('100'), D('100')))
        if day >= d[3]:
            rows.append(px(day, 'C', D('20'), D('20')))
    return rows


def test_spinoff_entitlement_is_the_holding_at_the_effective_date_when_t_falls_before_the_evidence():
    # Effective d[3], evidence only on d[6]; the reselection S d[4] -> T d[5] lies between them (review d2).
    spin = Settlement('SP1', d[3], 'P', 'SPINOFF', d[6], EVIDENCE, d[3], D('0'), 'C', D('1'))

    def final(rebalances):
        result = run_ledger(DAYS[:12], rebalances, _spinoff_prices(), [spin], scenario='LOSS', cost_bps=0,
                            initial_capital=D('1000'))
        return result, result['daily'][-1]

    # A: P held over the ex-date and sold at the ex-distribution T open; the ex-date holder still gets 10 C.
    held, last = final([Rebalance(d[0], d[1], ('P',)), Rebalance(d[4], d[5], ('Q',))])
    assert last['nav'] == 1000 and qty(held, d[11]) == {'Q': D('8'), 'C': D('10')}
    assert qty(held, d[5]) == {'Q': D('8')}                 # nothing is delivered before the evidence date
    assert 'SETTLEMENT_APPLIED:SP1' in row_on(held, d[6])['events']
    # B: P bought at the ex-distribution T open is not entitled: no C, no double count.
    bought, last = final([Rebalance(d[0], d[1], ('Q',)), Rebalance(d[4], d[5], ('P',))])
    assert last['nav'] == 1000 and qty(bought, d[11]) == {'P': D('12.5')}


def test_terminating_event_applies_to_the_effective_date_holding_less_later_sales():
    # A is delisted effective d[3] with evidence on d[6]; an OTC-like open on d[5] sells it at the reselection.
    prices = flat('A', 10, days=DAYS[:12]) + flat('B', 10, days=DAYS[:12])
    delist = Settlement('DL1', d[3], 'A', 'DELISTING', d[6], EVIDENCE)
    runs = run_scenarios(DAYS[:12], [Rebalance(d[0], d[1], ['A']), Rebalance(d[4], d[5], ['B'])], prices, [delist],
                         cost_bps=0, initial_capital=1000)
    for scenario, result in runs.items():
        row = row_on(result, d[6])
        assert 'HOLDING_CHANGED_AFTER_EFFECTIVE_DATE:DL1' in row['flags']
        assert qty(result, d[11]) == {'B': D('100')} and row_on(result, d[11])['nav'] == 1000   # sold: no CARRY too
    # Bought after the effective date: the purchase is void at activation (no phantom CARRY asset).
    runs = run_scenarios(DAYS[:12], [Rebalance(d[0], d[1], ['B']), Rebalance(d[4], d[5], ['A'])], prices, [delist],
                         cost_bps=0, initial_capital=1000)
    for result in runs.values():
        assert 'A' not in qty(result, d[6]) and row_on(result, d[6])['nav'] == 0
        assert 'HOLDING_CHANGED_AFTER_EFFECTIVE_DATE:DL1' in row_on(result, d[6])['flags']


# -- review F5: per-security conflicts, never a refusal of every portfolio -------------------------------------
def test_merger_plus_form_25_and_a_split_after_delisting_do_not_refuse_a_portfolio_that_never_held_them():
    days = DAYS[:10]
    prices = flat('Q', 10, days=days)
    merger = Settlement('M-1', d[3], 'M', 'CASH_MERGER', d[3], EVIDENCE, d[4], D('50'))
    form25 = Settlement('M-2', d[5], 'M', 'DELISTING', d[5], EVIDENCE)
    delist = Settlement('Z-1', d[3], 'Z', 'DELISTING', d[3], EVIDENCE)
    otc_split = Split('Z-2', d[6], 'Z', D('0.1'))
    result = run_ledger(days, [Rebalance(d[0], d[1], ('Q',))], prices, [merger, form25, delist, otc_split],
                        scenario='LOSS', cost_bps=0, initial_capital=1000)
    assert result['status'] == 'COMPLETE' and result['conflicts'] == ()
    assert 'TERMINATION_SUPPORTING_EVIDENCE:M-2' in row_on(result, d[5])['events']
    assert 'SPLIT_IGNORED_NO_POSITION:Z-2' in row_on(result, d[6])['events']
    assert all(row['nav'] == 1000 for row in result['daily'][1:])


def test_open_termination_is_settled_by_a_later_terminating_event_with_terms():
    delist = Settlement('DL', d[4], 'A', 'DELISTING', d[4], EVIDENCE)
    merger = Settlement('MG', d[4], 'A', 'CASH_MERGER', d[7], EVIDENCE, d[8], D('7'))
    runs = _termination_case([delist, merger])
    assert row_on(runs['LOSS'], d[6])['nav'] == 500 and row_on(runs['CARRY'], d[6])['nav'] == 900
    for result in runs.values():
        row = row_on(result, d[7])
        assert 'TERMINATION_SETTLED_BY:DL:MG' in row['events'] and 'A' not in row['positions']
        assert row['receivables'] == 350 and row['nav'] == 850
        assert row_on(result, d[8])['cash'] == row_on(result, d[8])['reserved_cash'] == 350
    assert [r['nav'] for r in runs['LOSS']['daily'][7:]] == [r['nav'] for r in runs['CARRY']['daily'][7:]]


def test_contradicting_terms_are_recorded_on_that_security_and_change_nothing():
    applied = Settlement('x', d[3], 'A', 'DELISTING', d[3], EVIDENCE, d[4], D('1'))
    contradict = SettlementConfirmation('x', d[5], EVIDENCE, d[4], D('2'))
    result = run([Rebalance(d[0], d[1], ['A'])], flat('A', 10), [applied, contradict])
    assert result['conflicts'] == ({'session': d[5], 'event_id': 'x', 'security_id': 'A',
                                    'reason': 'CONFIRMED_TERMS_CONTRADICT_SETTLEMENT'},)
    assert 'SETTLEMENT_CONFLICT:x' in row_on(result, d[5])['flags'] and row_on(result, d[5])['cash'] == 100
    partial = Settlement('y', d[3], 'A', 'DELISTING', d[3], EVIDENCE, d[4], None)
    late = SettlementConfirmation('y', d[5], EVIDENCE, d[5], D('2'))
    runs = run_scenarios(DAYS, [Rebalance(d[0], d[1], ['A'])], flat('A', 10), [partial, late], cost_bps=0,
                         initial_capital=1000)
    assert runs['LOSS']['conflicts'][0]['reason'] == 'CONFIRMED_TERMS_CONTRADICT_SETTLEMENT'
    assert row_on(runs['LOSS'], d[9])['nav'] == 0 and row_on(runs['CARRY'], d[9])['nav'] == 1000   # still unconfirmed
    other = Settlement('z', d[6], 'A', 'CASH_MERGER', d[6], EVIDENCE, d[7], D('3'))
    result = run([Rebalance(d[0], d[1], ['A'])], flat('A', 10), [applied, other])
    assert result['conflicts'][0]['reason'] == 'TERMINATION_TERMS_DIFFER_FROM_APPLIED_TERMS'
    assert row_on(result, d[9])['cash'] == 100      # the first terms stand, no second payment


def test_split_of_a_frozen_carry_position_keeps_its_value():
    delist = Settlement('del5', d[4], 'A', 'DELISTING', d[4], EVIDENCE)
    reverse = Split('rs', d[6], 'A', D('0.1'))
    carry = _termination_case([delist, reverse])['CARRY']
    row = row_on(carry, d[6])
    assert 'SPLIT_ON_TERMINATED_SECURITY:rs' in row['flags']
    assert row['positions']['A']['quantity'] == 5 and row['positions']['A']['price'] == 80
    assert row['carry_value'] == 400 and row['nav'] == 900


# -- ADR dividend depositary fee (owner task, as in the preserved Codex research ledger c68af2c0) ------------------
def test_adr_dividend_depositary_fee_is_deducted_and_recorded_as_an_instrument_fee():
    dividend = Dividend('adr-div', d[3], 'A', D('0.50'), d[5], depositary_fee_per_share=D('0.05'))
    result = run([Rebalance(d[0], d[1], ['A'])], flat('A', 10), [dividend])
    assert row_on(result, d[3])['receivables'] == D('45')            # 100 ADS x (0.50 - 0.05)
    assert 'DEPOSITARY_FEE:adr-div' in row_on(result, d[3])['events']
    assert row_on(result, d[5])['cash'] == row_on(result, d[5])['reserved_cash'] == 45
    assert result['instrument_fees'] == ({'session': d[3], 'event_id': 'adr-div', 'security_id': 'A',
                                          'kind': 'DEPOSITARY_FEE', 'quantity': D('100'), 'fee_per_share': D('0.05'),
                                          'amount': D('5.00')},)
    assert result['total_instrument_fees'] == 5 and result['total_costs'] == 0     # not a trading cost
    plain = run([Rebalance(d[0], d[1], ['A'])], flat('A', 10), [Dividend('div', d[3], 'A', D('0.50'), d[5])])
    assert plain['instrument_fees'] == () and row_on(plain, d[3])['receivables'] == 50
    with pytest.raises(LedgerError, match='ADR_FEE_EXCEEDS_DIVIDEND'):
        run([Rebalance(d[0], d[1], ['A'])], flat('A', 10),
            [Dividend('bad', d[3], 'A', D('0.05'), d[5], depositary_fee_per_share=D('0.06'))])



# -- review F4: terminal valuation at an open --------------------------------------------------------------------
def test_terminal_open_valuation_marks_opens_trades_nothing_and_keeps_loss_carry():
    prices = ([px(day, 'A', 10, 10) for day in DAYS[:6]] + [px(d[6], 'A', 12, 15)]
              + [px(day, 'B', 10, 10) for day in DAYS[:6]])
    delisting = Settlement('dl', d[3], 'B', 'DELISTING', d[3], EVIDENCE)
    rebalances = [Rebalance(d[0], d[1], ['A', 'B']), Rebalance(d[5], d[6], ['A'])]
    runs = run_scenarios(DAYS[:7], rebalances, prices, [delisting], cost_bps=0, initial_capital=1000, end=d[6],
                         end_valuation='OPEN')
    for scenario, result in runs.items():
        last = result['daily'][-1]
        assert (last['date'], last['valuation'], result['end_valuation']) == (d[6], 'OPEN', 'OPEN')
        assert last['positions']['A']['price'] == 12 and last['fills'] == ()
        assert result['rebalances'][1]['execution_status'] == 'AFTER_RUN_END'      # T == end: no trade
    assert runs['LOSS']['daily'][-1]['nav'] == 600 and runs['CARRY']['daily'][-1]['nav'] == 1100
    stale = run_ledger(DAYS[:7], rebalances[:1], [px(day, 'A', None if day == d[6] else 10, 10) for day in DAYS[:7]],
                       scenario='LOSS', cost_bps=0, initial_capital=1000, end=d[6], end_valuation='OPEN')
    assert 'STALE_MARK:A' in stale['daily'][-1]['flags'] and stale['daily'][-1]['nav'] == 1000
    with pytest.raises(LedgerError, match='END_NOT_A_SESSION'):
        run_ledger(DAYS[:7], rebalances[:1], prices, scenario='LOSS', end=date(2031, 1, 1), end_valuation='OPEN')
