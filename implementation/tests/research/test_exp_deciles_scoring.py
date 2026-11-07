"""calc 23.1 scoring of the U-A population for the four presets. Synthetic rows; expected totals computed by hand.

Construction (11 issuers, i = 0..10, one industry group): every Q sub-metric ranks i -> Q = 10i; every G sub-metric ranks
-i -> G = 100 - 10i; EBIT and FCF yields rise with i at one price and zero net debt -> the three V factors that need no
history or realized growth are 10i each -> V = 10i (own history and expectation check NA). No type is recognized, so the
preset weights apply as they are. The value-trap gate drops V for Q industry percentile <= 30 (i <= 3).
"""
import copy
from decimal import Decimal

import pytest

from investment_system.qgv import qgv_v2, v2_factors, v2_scoring
from investment_system.research.exp_deciles import scoring, settings


def sid(i):
    return f'SEC{i:02}'


def row(i):
    metrics = {}
    for fid, spec in v2_scoring.SUBMETRICS['GENERAL'].items():
        for metric, direction in spec:
            metrics[metric] = direction * i if fid.startswith('q_') else -direction * i
    return {'security_id': sid(i), 'cik': str(i + 1).zfill(10), 'state': 'LIVE', 'profile': 'GENERAL', 'sic': '3571',
            'industry_group': 'synthetic', 'fiscal_year_end': '2017-12-31', 'currency': 'USD', 'metrics': metrics,
            'calc_version': v2_factors.CALC_VERSION, 'reason_codes': [],
            'v_inputs_v2': {'currency': 'USD', 'ebit': {'fy_value': 10 + i, 'fy_end': '2017-12-31'},
                            'fcf': {'fy_value': 8 + i, 'fy_end': '2017-12-31'},
                            'total_debt': {'value': 0, 'period_end': '2017-12-31'},
                            'cash_and_equivalents': {'value': 0, 'period_end': '2017-12-31'},
                            'diluted_shares': {'value': 10, 'period_end': '2017-12-31'}, 'revenue_cagr_3y': None}}


def na_row(i, reason='SIC_AS_FILED_NOT_AVAILABLE'):
    return {'security_id': sid(i), 'cik': str(i + 1).zfill(10), 'state': 'NOT_AVAILABLE', 'profile': None, 'sic': None,
            'industry_group': None, 'fiscal_year_end': None, 'currency': None,
            'metrics': dict.fromkeys(v2_factors.METRIC_KEYS), 'v_inputs_v2': v2_factors.empty_v_inputs(),
            'calc_version': v2_factors.CALC_VERSION, 'reason_codes': [reason]}


def universe(n=11):
    rows = {sid(i): row(i) for i in range(n)}
    quotes = {sid(i): {'price': Decimal('10'), 'currency': 'USD', 'price_label': 'PROXY_LAST_TRADE'} for i in range(n)}
    return rows, quotes


def expected_total(i, preset, gated):
    w = settings.PRESET_WEIGHTS[preset]
    q, g, v = 10 * i, 100 - 10 * i, 10 * i
    if gated:
        return (w['Q'] * q + w['G'] * g) / (w['Q'] + w['G'])
    return (w['Q'] * q + w['G'] * g + w['V'] * v) / 100


def test_axes_totals_per_preset_and_gate_match_hand_arithmetic():
    rows, quotes = universe()
    out = scoring.score_population(rows, quotes, population=list(rows))
    for i in range(11):
        sec = out['securities'][sid(i)]
        assert sec['axes'] == pytest.approx({'Q': 10 * i, 'G': 100 - 10 * i, 'V': 10 * i}, rel=1e-12, abs=1e-12)
        gated = i <= 3
        assert sec['value_trap_gate'] is gated
        assert ('VALUE_TRAP_CAUTION' in sec['flags']) is gated
        assert sec['axes']['V'] is not None                                  # the gate keeps the V axis itself
        for preset in settings.PRESET_IDS:
            assert sec['totals'][preset] == pytest.approx(expected_total(i, preset, gated), rel=1e-12, abs=1e-12)
            assert sec['weights'][preset] == pytest.approx({k: float(x) for k, x in settings.PRESET_WEIGHTS[preset].items()})
        assert sec['totals']['default'] == sec['totals']['balanced']
        assert sec['quote_status'] == 'SUPPLIED'
    # Spot values written out: i = 7 -> Q 70, G 30, V 70; i = 2 gated -> Q 20, G 80.
    s7, s2 = out['securities'][sid(7)]['totals'], out['securities'][sid(2)]['totals']
    assert s7['balanced'] == pytest.approx(56.8) and s7['quality'] == pytest.approx(60.0)
    assert s7['growth'] == pytest.approx(50.0) and s7['value'] == pytest.approx(62.0)
    assert s2['balanced'] == pytest.approx(3320 / 67) and s2['quality'] == pytest.approx(40.0)
    assert s2['growth'] == pytest.approx(57.5) and s2['value'] == pytest.approx(2100 / 45)
    assert out['summary']['percentile_population_size'] == 11
    assert out['summary']['totals_available'] == dict.fromkeys(settings.PRESET_IDS, 11)


def test_default_preset_is_computed_once_as_the_balanced_alias(monkeypatch):
    calls, real = [], qgv_v2.score_universe

    def spy(companies, quotes, **kwargs):
        calls.append(kwargs['preset'])
        return real(companies, quotes, **kwargs)

    monkeypatch.setattr(qgv_v2, 'score_universe', spy)
    rows, quotes = universe()
    out = scoring.score_population(rows, quotes, population=list(rows), include_engine=True)
    assert sorted(calls) == sorted(settings.PRESET_IDS) and len(calls) == 4
    assert out['engine']['default'] is out['engine']['balanced']
    assert out['summary']['presets_computed'] == ('balanced', 'quality', 'growth', 'value')
    assert out['summary']['preset_aliases'] == {'default': 'balanced'}


def test_engine_parity_with_a_direct_operating_call():
    rows, quotes = universe()
    out = scoring.score_population(rows, quotes, population=list(rows), include_engine=True)
    companies, _, _ = scoring.prepare_companies({k: rows[k] for k in sorted(rows)},
                                                type_config=scoring.load_official_type_config().to_dict(),
                                                playbook_config=scoring.playbook.load_config())
    priced = {k: {'price': 10.0, 'currency': 'USD', 'month_closes': {}} for k in rows}
    for preset in settings.PRESET_IDS:
        direct = qgv_v2.score_universe(companies, priced, type_config=scoring.load_official_type_config().to_dict(),
                                       parameters=scoring.load_default_dcf_parameters(), preset=preset)
        assert out['engine'][preset] == direct


def test_missing_data_stays_none_with_reasons_and_no_completeness_rule():
    rows, quotes = universe()
    rows[sid(11)] = na_row(11)
    del quotes[sid(7)]                                                      # no S price for SEC07
    quotes[sid(8)] = {'price': Decimal('10'), 'currency': 'USD', 'withheld_reason': 'SPLIT_AFTER_SHARE_COUNT'}
    out = scoring.score_population(rows, quotes, population=list(rows))
    na = out['securities'][sid(11)]
    assert na['axes'] == {'Q': None, 'G': None, 'V': None}
    assert all(v is None for v in na['totals'].values())
    assert all(v is None for v in na['factors'].values())
    assert na['row_reasons'] == ['SIC_AS_FILED_NOT_AVAILABLE'] and na['row_state'] == 'NOT_AVAILABLE'
    assert 'ROW_NOT_AVAILABLE' in na['axis_reasons']['Q'] and 'V_INPUTS_NOT_AVAILABLE' in na['axis_reasons']['V']
    assert na['total_reasons']['balanced'] == 'AXIS_WEIGHT_INSUFFICIENT'
    s7 = out['securities'][sid(7)]
    assert s7['quote_status'] == 'NOT_SUPPLIED' and s7['axes']['V'] is None
    assert 'NO_DEVICE_PRICE' in s7['axis_reasons']['V']
    # Q and G alone carry >= 50% of the weight, so the total exists without V (engine rule, unchanged).
    assert s7['totals']['balanced'] == pytest.approx((34 * 70 + 33 * 30) / 67)
    assert s7['factors']['v_earnings_yield'] is None and s7['factor_reasons']['v_earnings_yield'] == 'NO_DEVICE_PRICE'
    assert out['securities'][sid(8)]['quote_status'] == 'SPLIT_AFTER_SHARE_COUNT'
    assert out['securities'][sid(8)]['axes']['V'] is None
    assert out['summary']['quotes_supplied'] == 9


def test_a_missing_metric_is_not_zero():
    rows, quotes = universe()
    rows[sid(5)]['metrics']['roic'] = None
    out = scoring.score_population(rows, quotes, population=list(rows))
    # q_profitability of SEC05 = gross_profit_to_assets percentile alone (5 of 10 lower) = 50, not a mean with 0.
    assert out['securities'][sid(5)]['factors']['q_profitability'] == pytest.approx(50.0)
    assert rows[sid(5)]['metrics']['roic'] is None


def test_only_the_population_is_scored_and_inputs_are_not_mutated():
    rows, quotes = universe()
    base = scoring.score_population(rows, quotes, population=list(rows))
    extra = dict(rows, OUT=dict(row(99), security_id='OUT', cik='0000000999'))
    original = copy.deepcopy(extra)
    again = scoring.score_population(extra, dict(quotes, OUT={'price': 1, 'currency': 'USD'}), population=list(rows))
    assert again['securities'] == base['securities'] and 'OUT' not in again['securities']
    assert extra == original
    missing = scoring.score_population(rows, quotes, population=list(rows) + ['GHOST'])
    assert missing['securities']['GHOST']['row_reasons'] == ['SCORING_ROW_MISSING']
    assert missing['securities']['GHOST']['totals']['default'] is None
    assert missing['summary']['rows_missing'] == 1


def test_population_errors_are_refused():
    rows, quotes = universe()
    dup = dict(rows, DUP=dict(row(3), security_id='DUP'))
    with pytest.raises(ValueError, match='DUPLICATE_ISSUER_IN_SCORING_POPULATION'):
        scoring.score_population(dup, quotes, population=list(dup))
    stale = dict(rows)
    stale[sid(0)] = dict(rows[sid(0)], calc_version='qgv2-calc/2026-10-15.1')
    with pytest.raises(ValueError, match='CALC_VERSION_MISMATCH'):
        scoring.score_population(stale, quotes, population=list(stale))
    with pytest.raises(ValueError, match='WITHHELD_REASON_INVALID'):
        scoring.score_population(rows, dict(quotes, SEC00={'withheld_reason': 'split'}), population=list(rows))


def test_decimal_and_float_prices_score_identically_and_bad_prices_are_flagged():
    rows, quotes = universe()
    as_float = {k: dict(q, price=10.0) for k, q in quotes.items()}
    assert (scoring.score_population(rows, quotes, population=list(rows))['securities'] ==
            scoring.score_population(rows, as_float, population=list(rows))['securities'])
    bad = dict(quotes, SEC04={'price': Decimal('0'), 'currency': 'USD'}, SEC05={'price': Decimal('10')})
    out = scoring.score_population(rows, bad, population=list(rows))
    assert out['securities'][sid(4)]['quote_status'] == 'QUOTE_PRICE_INVALID'
    assert out['securities'][sid(5)]['quote_status'] == 'QUOTE_CURRENCY_MISSING'
