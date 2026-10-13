"""S16 13F quarter view and S13 custom type PREVIEW references (synthetic quantities/metrics only)."""
import importlib.util
import json
from pathlib import Path

import pytest

from investment_system.product import thirteenf_quarter as q
from investment_system.product.device_actual_catalog import public_actual_catalog
from investment_system.qgv import type_preview as tp
from investment_system.validation.forward_ledger import IDS

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_MAP = ROOT / 'docs/security_map19_owner/v1_1_cycle_20261008/CURRENT_TARGET_IDENTITY_MAP.json'


def load_tool():
    spec = importlib.util.spec_from_file_location('_t_s16_s13_reference', ROOT / 'tools/s16_s13_reference.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fixture_is_regenerated_from_python_reference():
    tool = load_tool()
    assert (ROOT / 'tests/fixtures/s16_s13_reference_v1.json').read_text() == tool.text()
    with pytest.raises(ValueError, match='SYNTHETIC_ONLY'):
        tool.replay({'synthetic': False, 'operation': 'config_diff', 'input': {}})


def test_target_ids_match_the_forward_ledger_and_type_preview():
    assert tuple(cid for cid, _ in q.TARGET) == IDS == tp.TARGET_IDS


def test_cusips_derived_from_public_isins_match_the_reviewed_identity_map():
    rows = json.loads(IDENTITY_MAP.read_text())['rows']
    reviewed = {}
    for row in rows:
        ids = dict(map(tuple, (row.get('c39_security_identity') or {}).get('identifiers') or []))
        reviewed[row['legacy_company_reference']] = ids.get('CUSIP')
    targets = {t['company_id']: t for t in q.target_securities(public_actual_catalog())}
    for cid, cusip in reviewed.items():
        t = targets[cid]
        if t['cusip'] is not None:
            assert t['cusip'] == cusip, cid
    # Only TEL/Hanmi (not 13F securities) and Eaton (Irish ISIN; CUSIP not in the public catalog) stay unmapped.
    assert {cid: t['reason'] for cid, t in targets.items() if t['cusip'] is None} == {
        'tokyo_electron': 'NOT_13F_SECURITY', 'hanmi': 'NOT_13F_SECURITY', 'etn': 'CUSIP_NOT_IN_PUBLIC_CATALOG'}


def test_missing_report_fields_stay_not_available_and_changes_are_not_summed():
    targets = q.target_securities(public_actual_catalog())
    nvda = next(t['cusip'] for t in targets if t['company_id'] == 'nvda')
    change = lambda key, a, b: {'cusip': nvda, 'security_key': key * 64, 'unit': 'SH', 'kind': 'ADD' if b > a else 'REDUCE',
                                'reported_before': a, 'reported_after': b, 'reported_delta': b - a}
    s = q.summarize_report({'manager_cik': '0000000001', 'previous_quarter': '2026-03-31', 'current_quarter': '2026-06-30',
                            'state': 'LIVE', 'changes': [change('a', 1, 2), change('b', 9, 3)]}, targets)
    row = next(r for r in s['target'] if r['company_id'] == 'nvda')
    assert row['status'] == 'CHANGED' and row['multiple_buckets'] and [c['reported_delta'] for c in row['changes']] == [1, -6]
    assert (s['filed_date'], s['holdings_count'], s['top10_weight']) == (None, None, None)
    assert s['filed_date_reason'] == 'FILING_DATE_NOT_PUBLISHED'
    na = q.summarize_report({'manager_cik': '0000000002', 'previous_quarter': '2026-03-31', 'current_quarter': '2026-06-30',
                             'state': 'NOT_AVAILABLE', 'changes': []}, targets)
    assert {r['status'] for r in na['target']} == {'NOT_AVAILABLE'}


def test_custom_preview_keeps_official_values_and_v_unavailable():
    official_before = json.loads((ROOT / 'src/investment_system/qgv/type_config_v1.json').read_text())
    custom = tp.official_copy()
    custom['types'][0]['weights'] = {'Q': 20, 'G': 60, 'V': 20}
    out = tp.target_type_preview({'data': {'companies': {'nvda': {'metrics': {'revenue_cagr_3y': 0.3}}}}}, None, custom)
    assert [r['company_id'] for r in out['rows']] == list(IDS)
    nvda = next(r for r in out['rows'] if r['company_id'] == 'nvda')
    assert nvda['official']['weights'] == {'Q': 30.0, 'G': 50.0, 'V': 20.0} and nvda['mine']['weights'] == {'Q': 20.0, 'G': 60.0, 'V': 20.0}
    assert nvda['mine']['adjusted_score'] is None and not nvda['types_changed']
    assert [d['path'] for d in out['diff']] == ['types.growth.weights.G', 'types.growth.weights.Q']
    assert json.loads((ROOT / 'src/investment_system/qgv/type_config_v1.json').read_text()) == official_before
    assert official_before['status'] == 'OFFICIAL_PROVISIONAL'


def test_fixture_has_no_price_or_value_fields():
    text = (ROOT / 'tests/fixtures/s16_s13_reference_v1.json').read_text()
    # security_reference.value is an ISIN; type_config has value_basis; reported 13F values and prices are never present.
    for key in ('"price"', '"reported_value"', '"market_value"', '"close"', '"quantity"', '"average_cost"'):
        assert key not in text
