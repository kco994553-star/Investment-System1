from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math
import pytest
from investment_system.evl.metrics import ReturnPeriod, evaluate_metrics, summarize
from investment_system.evl.pit import PITObservation, PITViolation

D = datetime(2020, 1, 1, tzinfo=timezone.utc)


def periods():
    out = []
    for i, value in enumerate((.1, -.2, .25)):
        start, end = D+timedelta(days=i), D+timedelta(days=i+1)
        out.append(ReturnPeriod(start,end,value,.01,.001,.002,value/2,.1,'USD',
            PITObservation('rf'+str(i),start,'treasury','v1'),
            PITObservation('outcome'+str(i),end,'prices','v1'),
            PITObservation('cpi'+str(i),D+timedelta(days=5),'cpi','v1')))
    return tuple(out)


def evaluate(rows=None):
    return evaluate_metrics(periods() if rows is None else rows,
        evaluation_time=D+timedelta(days=6), periods_per_year=3, tail_fraction=1/3)


def test_hand_calculated_growth_drawdown_and_recovery():
    r = summarize((.1,-.2,.25), periods_per_year=3)
    assert r['total_return'] == pytest.approx(.1)
    assert r['cagr'] == pytest.approx(.1)
    assert r['mdd'] == pytest.approx(.2)
    assert r['calmar'] == pytest.approx(.5)
    assert r['longest_drawdown_periods'] == 1
    assert r['unrecovered_drawdown'] is False


def test_sharpe_sample_variance_and_sortino_all_period_denominator():
    r = summarize((.01,-.01,.02), periods_per_year=12)
    avg = .02/3
    variance = sum((x-avg)**2 for x in (.01,-.01,.02))/2
    assert r['sharpe'] == pytest.approx(avg/math.sqrt(variance)*math.sqrt(12))
    assert r['sortino'] == pytest.approx(avg/math.sqrt(.01**2/3)*math.sqrt(12))


def test_four_views_cost_deflators_and_stamps():
    r = evaluate()
    net = 1.09*.79*1.24
    views = r['views']
    assert views['NET_OF_TRADING_COST_PRE_TAX']['total_return'] == pytest.approx(net-1)
    assert views['REAL_PRE_TAX']['total_return'] == pytest.approx(net/1.002**3-1)
    assert views['RISK_FREE_EXCESS_PRE_TAX']['total_return'] == pytest.approx(net/1.001**3-1)
    assert r['tax_mode'] == 'EXCLUDED' and r['official'] is False
    assert len(r['provenance']) == 3
    assert r['tail_mean_return'] == pytest.approx(-.21)
    assert r['turnover_sum'] == pytest.approx(.3)


def test_initial_wealth_included_and_bankruptcy_supported():
    assert summarize((-.2,.1), periods_per_year=2)['mdd'] == pytest.approx(.2)
    r = summarize((-.5,-1), periods_per_year=2)
    assert r['total_return'] == r['cagr'] == -1
    assert r['mdd'] == 1 and r['unrecovered_drawdown']


def test_undefined_ratios_are_null_not_fake_zero_or_infinity():
    r = summarize((0.,0.), periods_per_year=12)
    assert r['sharpe'] is r['sortino'] is r['calmar'] is None
    assert set(r['undefined']) == {'sharpe','sortino','calmar'}
    assert summarize((.1,), periods_per_year=1)['sharpe'] is None


@pytest.mark.parametrize('values', [(), (float('nan'),), (float('inf'),), (-1.01,), (True,)])
def test_invalid_return_series_blocked(values):
    with pytest.raises(ValueError):
        summarize(values, periods_per_year=12)


def test_future_risk_free_and_unpublished_inflation_rejected():
    rows = periods()
    with pytest.raises(PITViolation):
        evaluate((replace(rows[0], risk_free_stamp=replace(rows[0].risk_free_stamp,available_at=rows[0].end)),)+rows[1:])
    with pytest.raises(PITViolation):
        evaluate_metrics(rows,evaluation_time=D+timedelta(days=4),periods_per_year=3,tail_fraction=.1)


def test_no_missing_or_mixed_currency_alignment():
    rows = periods()
    with pytest.raises(ValueError,match='contiguous'):
        evaluate((rows[0],rows[2]))
    with pytest.raises(ValueError,match='currency'):
        evaluate((rows[0],replace(rows[1],currency='KRW'),rows[2]))


def test_cost_stress_monotonically_reduces_net_wealth():
    baseline = evaluate()['views']['NET_OF_TRADING_COST_PRE_TAX']['total_return']
    stressed = evaluate(tuple(replace(p,trading_cost=p.trading_cost*3) for p in periods()))
    assert stressed['views']['NET_OF_TRADING_COST_PRE_TAX']['total_return'] < baseline
    assert stressed['views']['GROSS_PRE_TAX'] == evaluate()['views']['GROSS_PRE_TAX']


def test_all_positive_benchmark_has_no_downside_capture():
    result = evaluate(tuple(replace(p,benchmark_return=.01) for p in periods()))
    assert result['downside_capture'] is None
