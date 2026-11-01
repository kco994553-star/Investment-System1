"""Benchmark tests for EXP-STOCK-INDICATOR-DECILES-v1. Synthetic index levels and prices only."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from investment_system.research.exp_deciles import benchmarks as b
from investment_system.research.exp_deciles import metrics as m
from investment_system.research.exp_deciles.ledger import Rebalance, Settlement, run_ledger

D = Decimal
DAYS = tuple(date(2030, 3, 1) + timedelta(days=i) for i in range(20))
d = DAYS


def px(day, sid, value):
    return dict(date=day, security_id=sid, open=value, close=value, price_basis='RAW')


PRICES = ([px(day, 'A', 10) for day in DAYS] + [px(day, 'B', 20 + i) for i, day in enumerate(DAYS)]
          + [px(day, 'C', 40) for day in DAYS] + [px(day, 'D', 5) for day in DAYS[:6]])


# -- (a) group equal weight -------------------------------------------------------------------------------------
def test_group_equal_weight_is_the_same_ledger_over_all_eligible_names():
    schedule = [Rebalance(d[0], d[1], ['A']), Rebalance(d[8], d[9], ['B'])]
    eligible = {d[0]: ['C', 'A', 'B', 'A'], d[8]: ('B', 'C')}
    result = b.group_equal_weight_benchmark(DAYS, schedule, eligible, PRICES, group='U-B', cost_bps=10,
                                            initial_capital=1000)
    assert result['benchmark_id'] == 'GROUP_EQUAL_WEIGHT' and result['group'] == 'U-B'
    assert result['is_etf'] is False and result['is_sp500_index'] is False
    assert result['eligible_counts'] == {d[0]: 3, d[8]: 2}
    assert [r.selected for r in result['rebalances']] == [('A', 'B', 'C'), ('B', 'C')]
    expected = run_ledger(DAYS, [Rebalance(d[0], d[1], ['A', 'B', 'C']), Rebalance(d[8], d[9], ['B', 'C'])],
                          PRICES, scenario='LOSS', cost_bps=10, initial_capital=1000)
    assert set(result['runs']) == {'LOSS', 'CARRY'}
    assert [r['nav'] for r in result['runs']['LOSS']['daily']] == [r['nav'] for r in expected['daily']]
    run = result['runs']['LOSS']
    assert run['cost_bps'] == 10 and all(f.fee > 0 for f in run['fills'])
    assert {f.session for f in run['fills']} == {d[1], d[9]}  # Same S/T schedule as the strategy.


def test_group_equal_weight_applies_both_termination_scenarios():
    delisting = Settlement('gone', d[6], 'D', 'DELISTING', d[6], 'synthetic evidence record')
    result = b.group_equal_weight_benchmark(DAYS, [(d[0], d[1])], {d[0]: ['A', 'D']}, PRICES, [delisting],
                                            group='U-A', cost_bps=0, initial_capital=1000)
    loss, carry = result['runs']['LOSS'], result['runs']['CARRY']
    assert loss['daily'][6]['nav'] == 500 and carry['daily'][6]['nav'] == 1000
    assert carry['daily'][6]['carry_value'] == 500


def test_group_equal_weight_requires_an_eligible_set_for_every_rebalance():
    with pytest.raises(b.BenchmarkError, match='MISSING_ELIGIBLE_SET'):
        b.group_equal_weight_benchmark(DAYS, [(d[0], d[1]), (d[8], d[9])], {d[0]: ['A']}, PRICES, group='U-A')
    with pytest.raises(b.BenchmarkError, match='INVALID_GROUP_LABEL'):
        b.group_equal_weight_benchmark(DAYS, [(d[0], d[1])], {d[0]: ['A']}, PRICES, group=' ')


# -- (b) external total-return index ----------------------------------------------------------------------------
def tr_rows(levels, *, open_on=None, open_level=None, skip=()):
    rows = []
    for day, level in zip(DAYS, levels):
        if day in skip:
            continue
        row = dict(date=day, total_return_index=level, currency='USD')
        if day == open_on:
            row['open_total_return_index'] = open_level
        rows.append(row)
    return rows


LEVELS = [100 + i for i in range(10)]


SLOT = 'SPY_TOTAL_RETURN_ETF_AUXILIARY'


@pytest.mark.parametrize('label', ['SPY', 'SPY_TR', 'spy total return'])
def test_spy_series_fills_the_etf_auxiliary_slot_and_is_never_named_sp500(label):
    """Owner 11/01 decision 3 (review R2 / SYN-1): the slot is SPY total return as an ETF auxiliary comparison; no
    substitute_for an S&P 500 index slot, no S&P 500 in the name."""
    result = b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100), label=label, claim=SLOT,
                                     entry_date=d[1])
    assert result['is_etf'] is True and result['is_sp500_index'] is False and result['ticker'] == 'SPY'
    assert (result['benchmark_id'], result['role']) == (SLOT, 'ETF_AUXILIARY_COMPARISON')
    assert 'S&P 500' not in result['name'] and 'SP500' not in result['name'].replace(' ', '').upper()
    assert 'substitute_for' not in result and 'ETF_SUBSTITUTE_NOT_INDEX' not in result['flags']


@pytest.mark.parametrize('label,kwargs', [
    ('SP500TR', {}), ('SPXT', {}), ('S&P 500 Total Return', {}), ('S&P 500 TR', {'is_etf': True}),
    ('SP500TR', {'source': 'SPDR S&P 500 Trust daily bars plus distributions'}),
    ('SP500TR', {'source': 'iShares Core S&P 500 NAV with distributions'}),
    ('SP500TR', {'source': 'SPY ETF closes plus SPY distributions'}),
])
@pytest.mark.parametrize('claim', [SLOT, 'OTHER_TR'])
def test_any_series_labelled_as_the_sp500_index_total_return_is_refused(label, kwargs, claim):
    """Review R2 / SYN-1: an SP500TR label (with or without fund text in the source) was published as 'S&P 500 total
    return index'; 'S&P 500 TR' with is_etf was named 'SP500 total return (ETF)'."""
    with pytest.raises(b.BenchmarkError, match='SP500_INDEX_TR_NOT_USED'):
        b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100), label=label, claim=claim,
                                entry_date=d[1], **kwargs)
    with pytest.raises(b.BenchmarkError, match='SP500_INDEX_TR_NOT_USED'):
        b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100), label='SPY', claim='SP500_TR',
                                entry_date=d[1])


@pytest.mark.parametrize('label,kwargs', [
    ('RSP total return', {'is_etf': True}), ('IVV', {}), ('Broad fund X', {'is_etf': True}),
    ('Russell 2000 TR', {}), ('SPDR S&P 500 ETF Trust total return', {}),
])
def test_the_auxiliary_slot_accepts_only_an_spy_etf_series(label, kwargs):
    """Review R2: RSP (equal weight) and any OTHER_TR label filled the slot."""
    with pytest.raises(b.BenchmarkError, match='TR_SERIES_NOT_SPY_ETF'):
        b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100), label=label, claim=SLOT,
                                entry_date=d[1], **kwargs)


def test_an_etf_without_a_known_ticker_is_never_named_from_its_label():
    """Review R2: an ETF without a known ticker took the label base ('SP500 total return (ETF)')."""
    result = b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100),
                                     label='SPDR S&P 500 ETF Trust total return', claim='OTHER_TR', entry_date=d[1])
    assert (result['benchmark_id'], result['name']) == ('ETF_TR:UNIDENTIFIED', 'ETF total return (ticker not identified)')
    rsp = b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100), label='RSP total return',
                                  claim='OTHER_TR', entry_date=d[1], is_etf=True)
    assert (rsp['benchmark_id'], rsp['name'], rsp['role']) == ('ETF_TR:RSP', 'RSP total return (ETF)', 'OTHER_SERIES')


def test_etf_label_cannot_be_declared_not_etf():
    with pytest.raises(b.BenchmarkError, match='ETF_LABEL_DECLARED_NOT_ETF'):
        b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100), label='SPY', claim=SLOT,
                                entry_date=d[1], is_etf=False)
    flagged = b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100), label='Broad fund X',
                                      claim='OTHER_TR', entry_date=d[1], is_etf=True)
    assert flagged['is_etf'] is True and flagged['benchmark_id'] == 'ETF_TR:UNIDENTIFIED'


@pytest.mark.parametrize('label,source', [
    ('Fama-French market', None),
    ('French Mkt-RF', None),
    ('MKT_RF', None),
    ('SPY', 'Ken French data library'),
    ('SPY total return', 'Fama/French factors'),
])
def test_french_market_factor_is_refused_in_the_etf_slot(label, source):
    with pytest.raises(b.BenchmarkError, match='FRENCH_MARKET_NOT_SPY_ETF'):
        b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100), label=label, claim=SLOT,
                                entry_date=d[1], source=source)


def test_french_market_series_is_allowed_only_as_another_labelled_series():
    result = b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100), label='Fama-French market',
                                     claim='OTHER_TR', entry_date=d[1])
    assert result['is_sp500_index'] is False and result['is_french_market'] is True
    assert result['benchmark_id'].startswith('OTHER_TR:') and 'not S&P 500' in result['name']
    with pytest.raises(b.BenchmarkError, match='UNKNOWN_BENCHMARK_CLAIM'):
        b.external_tr_benchmark(tr_rows(LEVELS), label='SPY', claim='SP500', entry_date=d[1])


def test_tr_nav_enters_at_the_t_open_level_and_never_fills_missing_levels():
    rows = tr_rows(LEVELS, open_on=d[1], open_level=D('100.5'), skip=(d[3],))
    result = b.external_tr_benchmark(rows, label='SPY', claim=SLOT, entry_date=d[1], end=d[6],
                                     sessions=DAYS, initial_capital=1000, entry_cost_bps=10)
    assert result['entry_level'] == D('100.5') and result['entry_basis'] == 'OPEN'
    assert [row['date'] for row in result['daily']] == list(d[1:7])
    by_day = {row['date']: row for row in result['daily']}
    expected = D(1000) * D(102) / D('100.5') / D('1.001')
    assert abs(by_day[d[2]]['nav'] - expected) < D('1e-20')
    assert by_day[d[3]]['nav'] is None and by_day[d[3]]['reason'] == 'MISSING_INDEX_LEVEL'
    assert result['status'] == 'INCOMPLETE' and result['reasons'] == ('MISSING_INDEX_LEVEL',)


def test_tr_entry_basis_previous_close_is_flagged_and_missing_open_blocks():
    blocked = b.external_tr_benchmark(tr_rows(LEVELS), label='SPY', claim=SLOT, entry_date=d[1])
    assert blocked['status'] == 'BLOCKED' and blocked['reasons'] == ('MISSING_ENTRY_OPEN_LEVEL',)
    assert blocked['daily'] == []
    previous = b.external_tr_benchmark(tr_rows(LEVELS), label='SPY', claim=SLOT, entry_date=d[1], sessions=DAYS,
                                       entry_basis='PREVIOUS_CLOSE', initial_capital=1000)
    assert previous['entry_level'] == 100 and 'ENTRY_AT_PREVIOUS_CLOSE' in previous['flags']
    assert previous['daily'][0]['nav'] == 1010


def test_previous_close_fallbacks_use_only_the_immediately_preceding_session():
    """Review M3: the entry and end fallbacks took the last close of any age (223 sessions old in the review)."""
    gap = tr_rows(LEVELS, skip=(d[0],))
    blocked = b.external_tr_benchmark(gap, label='SPY', claim=SLOT, entry_date=d[1], sessions=DAYS,
                                      entry_basis='PREVIOUS_CLOSE')
    assert blocked['status'] == 'BLOCKED' and blocked['reasons'] == ('MISSING_PREVIOUS_CLOSE_LEVEL',)
    rows = tr_rows(LEVELS[:5], open_on=d[1], open_level=100)       # closes only up to d[4]
    fresh = b.external_tr_benchmark(rows, label='SPY', claim=SLOT, entry_date=d[1], end=d[5], sessions=DAYS,
                                    end_valuation='OPEN', initial_capital=1000)
    assert fresh['daily'][-1]['valuation'] == 'PREVIOUS_CLOSE' and 'END_AT_PREVIOUS_CLOSE' in fresh['flags']
    assert fresh['daily'][-1]['nav'] == 1040
    stale = b.external_tr_benchmark(rows, label='SPY', claim=SLOT, entry_date=d[1], end=d[9], sessions=DAYS,
                                    end_valuation='OPEN', initial_capital=1000)
    assert stale['daily'][-1]['nav'] is None and stale['daily'][-1]['reason'] == 'MISSING_END_LEVEL'
    assert 'MISSING_END_LEVEL' in stale['reasons'] and 'END_AT_PREVIOUS_CLOSE' not in stale['flags']
    points, started, capital = b.tr_nav_points(stale)
    report = m.series_metrics(points, started_at=started, initial_capital=capital, sessions=DAYS, coverage_end=d[9],
                              final_valuation=stale['daily'][-1]['valuation'])
    assert report['performance']['cumulative_return'].value is None and report['final']['nav_index'] is None


def test_previous_close_entry_anchors_annualization_at_that_close():
    """Review R7: with PREVIOUS_CLOSE entry the return accrues from the S close but CAGR was annualized from T."""
    result = b.external_tr_benchmark(tr_rows(LEVELS), label='SPY', claim=SLOT, entry_date=d[3], sessions=DAYS,
                                     entry_basis='PREVIOUS_CLOSE', initial_capital=1000)
    points, started, _ = b.tr_nav_points(result)
    assert result['entry_level_date'] == d[2] and started == d[2] and points[0].date == d[3]


@pytest.mark.parametrize('rows,reason', [
    ([dict(date=d[1], total_return_index=100, currency='KRW')], 'BENCHMARK_CURRENCY_NOT_USD'),
    ([dict(date=d[1], total_return_index=100)], 'BENCHMARK_CURRENCY_NOT_USD'),
    ([dict(date=d[1], total_return_index=100, currency='USD')] * 2, 'DUPLICATE_INDEX_DATE'),
    ([dict(date=d[1], total_return_index=-1, currency='USD')], 'INVALID_TOTAL_RETURN_INDEX'),
    ([dict(date='2030-03-02', total_return_index=100, currency='USD')], 'INDEX_DATE_MUST_BE_DATE'),
])
def test_tr_rows_are_validated(rows, reason):
    with pytest.raises(b.BenchmarkError, match=reason):
        b.external_tr_benchmark(rows, label='SPY', claim=SLOT, entry_date=d[1])


def test_tr_series_feeds_the_same_metrics():
    result = b.external_tr_benchmark(tr_rows(LEVELS, open_on=d[1], open_level=100), label='SPY', claim=SLOT,
                                     entry_date=d[1], initial_capital=1000)
    points, started, capital = b.tr_nav_points(result)
    report = m.series_metrics(points, started_at=started, initial_capital=capital)
    assert report['performance']['cumulative_return'].value == pytest.approx(109 / 100 - 1)
    assert report['trailing_returns']['1y']['total_return'] == m.Metric(None, 'INSUFFICIENT_HISTORY')


# -- review F8: ETF markers are read in the source text as well --------------------------------------------------
def test_etf_markers_in_the_source_name_the_series_as_that_etf():
    """Review d10 / R2: a series whose source names an ETF is that ETF, never the index."""
    rows = tr_rows(LEVELS, open_on=d[1], open_level=100)
    result = b.external_tr_benchmark(rows, label='Large-cap total return', claim=SLOT, entry_date=d[1],
                                     source='SPY closes plus SPY distributions')
    assert (result['benchmark_id'], result['is_etf']) == (SLOT, True) and 'ETF_NAMED_IN_SOURCE' in result['flags']
    with pytest.raises(b.BenchmarkError, match='ETF_SOURCE_DECLARED_NOT_ETF'):
        b.external_tr_benchmark(rows, label='Large-cap total return', claim='OTHER_TR', entry_date=d[1],
                                is_etf=False, source='closes of IVV')
    fund = b.external_tr_benchmark(rows, label='Large-cap total return', claim='OTHER_TR', entry_date=d[1],
                                   source='iShares Core fund NAV with distributions')
    assert fund['is_etf'] is True and fund['benchmark_id'] == 'ETF_TR:UNIDENTIFIED'
    labelled = b.external_tr_benchmark(rows, label='SPY total return (ETF, synthetic)', claim=SLOT,
                                       entry_date=d[1], is_etf=True, source='synthetic')
    assert (labelled['benchmark_id'], labelled['ticker']) == (SLOT, 'SPY')
