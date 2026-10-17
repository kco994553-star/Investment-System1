"""TYPE-SCOPE (owner instruction 2026-10-17): the same approved type rule for every company with the same eligibility.

The device type weights (qgv-v2.js / qgv_v2.py) now come from each scored row's own published price-free metrics
(`pricefree_memberships`), for Universe codes and TARGET rows alike. These tests pin that the device rule is exactly the
rule the TARGET-only public file `company-types-pricefree.json` applies (company_types.calculate_company_types with
type_config/1), and that no unresolved or price-dependent type is evaluated. Synthetic metric values only.
"""
import json
import re
from pathlib import Path

import pytest

from investment_system.product.public_engine_screens import PRICEFREE_TYPES
from investment_system.qgv import qgv_v2 as v
from investment_system.qgv.company_types import calculate_company_types
from investment_system.qgv.type_config import load_official_type_config

ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads((ROOT / 'tests/fixtures/type_pricefree_memberships_v1.json').read_text())
CONFIG = json.loads((ROOT / 'src/investment_system/qgv/type_config_v1.json').read_text())


def test_vectors_are_for_the_shipped_type_config():
    assert VECTORS['config_version'] == CONFIG['config_version'] == 'type_config/1'
    qgv_types = [t['id'] for t in CONFIG['types'] if t['affects_qgv']]
    for case in VECTORS['cases']:
        assert list(case['memberships']) == qgv_types, case['name']


@pytest.mark.parametrize('case', VECTORS['cases'], ids=lambda c: c['name'])
def test_pricefree_memberships_and_weights_match_the_vectors(case):
    mem = v.pricefree_memberships(case['metrics'], CONFIG)
    assert mem == case['memberships']
    weights, reason, selected = v.type_axis_weights(mem, CONFIG)
    assert (selected, reason) == (case['selected_types'], case['type_reason'])
    assert weights == pytest.approx(case['type_weights'], abs=1e-12)


@pytest.mark.parametrize('case', VECTORS['cases'], ids=lambda c: c['name'])
def test_device_rule_equals_the_target_public_file_rule(case):
    """company-types-pricefree.json (TARGET only) runs calculate_company_types on {revenue_cagr_3y, roic}: for every type it
    publishes, the device derivation gives the identical membership from the same metric value."""
    metrics = {k: case['metrics'].get(k) for k in ('revenue_cagr_3y', 'roic')}
    official = calculate_company_types(metrics=metrics, original_qgv={'Q': None, 'G': None, 'V': None},
                                       config=load_official_type_config())
    device = v.pricefree_memberships(case['metrics'], CONFIG)
    for t in PRICEFREE_TYPES:
        assert device[t] == official['memberships'][t]['membership'], (case['name'], t)


def test_only_approved_pricefree_rules_are_evaluated():
    rules = {t['id']: t['rule'] for t in CONFIG['types'] if t['affects_qgv']}
    evaluated = {tid for tid, r in rules.items() if r['kind'] == 'ramp' and r['metric'] in v.PRICEFREE_TYPE_METRICS}
    assert evaluated == {'growth'}
    # Unresolved (value, quality, cyclical, defensive) and price-dependent (dividend: dividend_yield, leader:
    # sector_marketcap_rank) rules stay null even when such inputs are supplied; the engine itself would score them.
    full = {'revenue_cagr_3y': 0.3, 'roic': 0.5, 'dividend_yield': 0.05, 'dividend_paid_5_consecutive_years': True,
            'sector_marketcap_rank': 1}
    assert {k: x for k, x in v.pricefree_memberships(full, CONFIG).items() if x is not None} == {'growth': 1.0}
    engine = calculate_company_types(metrics=full, original_qgv={'Q': None, 'G': None, 'V': None},
                                     config=load_official_type_config())['memberships']
    assert engine['dividend']['membership'] == 1 and engine['leader']['membership'] == 1


@pytest.mark.parametrize('bad', [True, '0.2', float('nan'), float('inf'), None])
def test_missing_or_invalid_metric_is_null_never_zero(bad):
    assert v.pricefree_memberships({'revenue_cagr_3y': bad}, CONFIG)['growth'] is None
    assert v.pricefree_memberships(None, CONFIG) == {t['id']: None for t in CONFIG['types'] if t['affects_qgv']}


def test_target_status_is_not_an_input():
    """Two rows with the same published metrics get the same memberships and the same weights; nothing in the
    derivation can see whether a row is a TARGET row."""
    import inspect
    assert list(inspect.signature(v.pricefree_memberships).parameters) == ['metrics', 'type_config']
    a = v.pricefree_memberships({'revenue_cagr_3y': 0.25}, CONFIG)
    b = v.pricefree_memberships({'revenue_cagr_3y': 0.25}, CONFIG)
    assert a == b and v.type_axis_weights(a, CONFIG) == v.type_axis_weights(b, CONFIG)


def test_type_scope_id_is_one_constant_tied_to_the_evaluated_rules():
    """Owner decision 2026-10-17 item 4: the device score basis records a type-application scope id; calc_version is kept.

    The id was issued for this metric list and this type_config: changing either (or which rows get memberships) needs a new
    id, so these vectors fail until type_scope is bumped together with them."""
    assert v.TYPE_SCOPE == VECTORS['type_scope']
    assert re.fullmatch(r'qgv2-type-scope/\d{4}-\d{2}-\d{2}\.\d+', v.TYPE_SCOPE)
    assert list(v.PRICEFREE_TYPE_METRICS) == VECTORS['pricefree_type_metrics']
    assert CONFIG['config_version'] == VECTORS['config_version']
    js = (ROOT / 'src/investment_system/product/web_assets/qgv-v2.js').read_text()
    assert re.findall(r"const TYPE_SCOPE='([^']+)'", js) == [v.TYPE_SCOPE]
    assert re.findall(r"const PRICEFREE_TYPE_METRICS=Object\.freeze\(\[([^\]]*)\]\)", js) == ["'revenue_cagr_3y'"]
    from investment_system.qgv.v2_factors import CALC_VERSION
    assert not CALC_VERSION.startswith('qgv2-type-scope/'), 'the scope id is separate from the raw-metric calc_version'


@pytest.mark.parametrize('cagr, growth', [(0.1, 0.0), (0.2, 1.0), (None, None)])
def test_ramp_edges_and_na(cagr, growth):
    """0.10 -> 0, 0.20 -> 1 (the ramp ends), NA stays None, never 0."""
    assert v.pricefree_memberships({'revenue_cagr_3y': cagr}, CONFIG)['growth'] == growth
