"""DART ratios share v2 formulae; Korean targets never enter the US issuer pool."""
from datetime import datetime, timezone
import copy


def annual(scale=1):
    return {'state': 'LIVE', 'bsns_year': 2025, 'filed_at': '2026-03-01', 'inputs': {
        'revenue': 200*scale, 'revenue_prev': 180*scale, 'operating_income': 30*scale,
        'net_income': 20*scale, 'eps': 2*scale, 'eps_prev': 1.8*scale,
        'operating_cash_flow': 24*scale, 'capex': -4*scale,
        'cash_and_equivalents': 20*scale, 'equity': 80*scale, 'total_debt': 20*scale,
        'shares': 10, 'operating_income_prev': 25*scale}}


def test_same_ratios_under_currency_scale_and_no_one_year_growth_as_cagr():
    from investment_system.product.dart_qgv2 import annual_metrics
    a = annual_metrics(annual())
    b = annual_metrics(annual(1000))
    assert a == b
    assert a['fcf_to_net_income'] == 1
    assert a['roic'] == 0.29625
    assert a['revenue_cagr_3y'] is None and a['eps_cagr_3y'] is None


def test_korean_target_does_not_contaminate_us_peer_distribution():
    from investment_system.product.dart_qgv2 import reference_score
    universe = {str(i): {'cik': str(i), 'state': 'LIVE', 'profile': 'GENERAL', 'industry_group': None,
                       'metrics': {'roic': i/100, 'fcf_to_net_income': i/10}} for i in range(1, 10)}
    before = copy.deepcopy(universe)
    result = reference_score({'state': 'LIVE', 'annual': annual()}, universe)
    assert universe == before
    assert result['comparison_label'] == '참고 순위'
    assert result['cross_section_size'] == 9
    assert result['axes']['Q']['score'] is None  # 25+20 < 50%: no filled safety/history data
    assert result['axes']['G']['score'] is None
    assert result['reference_only'] is True


def test_optional_v2_projection_preserves_original_backup_schema_and_checks_exact_metrics(tmp_path):
    from tests.test_dart_collection import run
    from tests.dart_fake_opendart import FakeOpenDart
    from investment_system.product import dart_public
    from investment_system.product.dart_qgv2 import metric_projection
    import json
    import pytest
    _, _, out = run(tmp_path, FakeOpenDart())
    payload = json.loads((out / dart_public.FINANCIALS_FILENAME).read_text())
    company = payload['companies']['hanmi']
    assert 'qgv2' not in company
    company['qgv2'] = metric_projection(company)
    assert dart_public.require_financials(payload) is payload
    company['qgv2']['metrics']['fcf_to_net_income'] = 123.0
    with pytest.raises(dart_public.DartPublicError):
        dart_public.require_financials(payload)


def test_workflow_projection_reports_na_and_missing_input_tokens_without_scores(tmp_path, capsys):
    from tests.test_dart_collection import run
    from tests.dart_fake_opendart import FakeOpenDart, FAKE_KEY
    from project_dart_qgv2 import project
    _, _, out = run(tmp_path, FakeOpenDart())
    capsys.readouterr()
    assert project(out) == 0
    printed = capsys.readouterr().out
    assert 'Q_state=NOT_AVAILABLE' in printed and 'G_state=NOT_AVAILABLE' in printed
    assert 'DART_V2_3Y_HISTORY_NOT_COLLECTED' in printed
    assert FAKE_KEY not in printed and 'score=' not in printed
