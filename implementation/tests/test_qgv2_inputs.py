"""Python twin of the sec-qgv2.json -> QGV v2 engine-input conversion (qgv/qgv2_inputs.py) == the JS device path.

Parity: tools/qgv2_inputs_parity.js builds the shared cases (tools/qgv_v2_fixture.js payloads, the valid cases of
tests/fixtures/sec_qgv2_vectors_v1.json, synthetic edge variants and, when QGV2_PARITY_REAL_FILE names a published
sec-qgv2.json, that file, read only) and runs the real JS path (SecQgv2.toInputs / Qgv2Inputs.fromInputs / QgvScores.compute
with PlaybookEngine on the page); tools/qgv2_inputs_parity.py runs this twin and qgv_v2.score_universe on the same specs.
The converted records, the engine company records and the engine quote codes must be identical; the engine results must be
identical too (factors, axes, totals, flags, weights, ...), except the DCF reference_range, which keeps the engine vectors'
own 1e-9 tolerance (tools/qgv_v2_node_test.js). Quotes are SYNTHETIC test numbers made up in tools/qgv2_inputs_parity.js.
Nothing is written to disk.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest

from investment_system.qgv import playbook
from investment_system.qgv import qgv2_inputs as qi
from investment_system.qgv.type_config import load_official_type_config

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'tools/qgv2_inputs_parity.js'
_spec = importlib.util.spec_from_file_location('qgv2_inputs_parity', ROOT / 'tools/qgv2_inputs_parity.py')
parity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parity)

TOLERATED = 'reference_range'


def _node(*args, stdin=None):
    p = subprocess.run(['node', str(JS), *args], input=stdin, capture_output=True, text=True, env=dict(os.environ))
    assert p.returncode == 0, p.stderr[-2000:]
    return json.loads(p.stdout)


def diff(a, b, at='', out=None, tolerated=False):
    """Strict JSON-value comparison: bools are not numbers, ints equal floats by value, keys and lengths must match."""
    out = [] if out is None else out
    if isinstance(a, bool) or isinstance(b, bool):
        if a is not b:
            out.append((at, a, b))
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a != b and not (tolerated and abs(a - b) <= max(1e-9, abs(b) * 1e-9)):
            out.append((at, a, b))
    elif type(a) is not type(b):
        out.append((at, a, b))
    elif isinstance(a, dict):
        if set(a) != set(b):
            out.append((at, 'KEYS', sorted(set(a) ^ set(b))))
        else:
            for k in a:
                diff(a[k], b[k], at + '.' + k, out, tolerated or k == TOLERATED)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((at, 'LENGTH', len(a), len(b)))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diff(x, y, f'{at}[{i}]', out, tolerated)
    elif a != b:
        out.append((at, a, b))
    return out


CASES = _node('cases')


def test_cases_cover_the_fixtures_and_the_mapping_branches():
    ids = [c['id'] for c in CASES]
    assert {'light_fixture', 'light_edges', 'light_calc_version', 'light_withdrawn', 'strict_base_valid',
            'strict_calc_version_mixed_population_valid', 'strict_target_withdrawn_valid', 'strict_universe_withdrawn_valid',
            'strict_fixture_missing', 'strict_base_valid_stale_now'} <= set(ids)
    assert len(ids) == len(set(ids))
    real = os.environ.get('QGV2_PARITY_REAL_FILE')
    assert ('real_published_file' in ids) == bool(real and Path(real).exists())


@pytest.mark.parametrize('spec', CASES, ids=lambda c: c['id'])
def test_python_twin_matches_the_js_device_path(spec):
    js = _node('convert', stdin=json.dumps([spec]))[0]
    py = parity.convert(spec)
    for part in ('inputs', 'page_identities', 'companies', 'engine_quote_codes'):
        assert diff(js[part], py[part], part, tolerated=False) == [], (spec['id'], part)
    assert set(js['scores']) == set(py['scores']) == {p['id'] for p in spec['profiles']}
    for profile, rows in js['scores'].items():
        assert set(rows) == set(js['companies'])
        assert diff(rows, py['scores'][profile], profile) == [], (spec['id'], profile)
        for code, r in rows.items():   # factor, axis and total results: exactly equal (no tolerance)
            mine = py['scores'][profile][code]
            assert (r['factors'], r['axes'], r['total'], r['total_reason'], r['flags']) == \
                   (mine['factors'], mine['axes'], mine['total'], mine['total_reason'], mine['flags']), (spec['id'], profile, code)
    # The converted inputs and engine records carry no price-like value; quotes stay in the spec (synthetic, RAM).
    text = json.dumps([py['inputs'], py['companies']])
    for key in ('"price"', '"prices"', '"month_closes"', '"market_cap"', '"marketcap"', '"ev"', '"enterprise_value"'):
        assert key not in text


# ---- direct pins of the mapping rules (synthetic rows) ------------------------------------------------------------
def _row(cik, **extra):
    row = {'cik': cik, 'state': 'LIVE', 'reason_codes': [], 'acquired_at': '2026-10-13T00:00:00Z', 'sic': '3674',
           'industry_group': 'manufacturing_industrial_tech', 'profile': 'GENERAL', 'fiscal_year_end': '2025-12-31',
           'metrics': {'revenue_cagr_3y': 0.15}, 'factors': {'q_profitability': 55.0}, 'axes': {'Q': {'score': 50.0}, 'G': {'score': 40.0}},
           'v_inputs_v2': {'currency': 'USD', 'ebit': {'fy_value': 10.0, 'fy_end': '2025-12-31', 'ttm_value': 12.0, 'ttm_end': '2026-06-30'},
                           'fcf': {'fy_value': 7.0, 'fy_end': '2025-12-31', 'ttm_value': None, 'ttm_end': None},
                           'total_debt': None, 'cash_and_equivalents': {'value': 3.0, 'period_end': '2026-06-30'},
                           'diluted_shares': None, 'ebit_per_share_history': [], 'revenue_cagr_3y': 0.15}}
    row.update(extra)
    return row


def test_flows_withheld_values_and_cross_section_points():
    out = qi.from_inputs({'records': {'NYSE:SYNB': _row('0000000001'), 'NYSE:SYNA': _row('0000000001'), 'NYSE:SYNC': _row('0000000002')},
                          'target': {'syn': _row('0000000002')}})
    a, b, t = out['records']['NYSE:SYNA'], out['records']['NYSE:SYNB'], out['records']['TARGET:syn']
    assert (a['in_cross_section'], b['in_cross_section'], t['in_cross_section']) == (True, False, False)  # one point per CIK
    assert a['v_inputs']['ebit'] == 12.0 and a['periods']['ebit'] == 'TTM 2026-06-30'                  # TTM first
    assert a['v_inputs']['fcf'] == 7.0 and a['periods']['fcf'] == 'FY 2025-12-31'                      # else FY
    # V-STALE-BS / V-SHARES-SCALE values withheld by the publisher stay missing (None / []), never 0 or filled.
    assert (a['v_inputs']['total_debt'], a['v_inputs']['diluted_shares'], a['v_inputs']['ebit_per_share_history']) == (None, None, [])
    assert a['v_inputs']['cash'] == 3.0 and 'total_debt' not in a['periods']


def test_calc_version_mismatch_and_identity_withdrawal():
    v = 'qgv2-calc/2026-10-17.1'
    records = {'NYSE:SYNA': _row('0000000001', calc_version='qgv2-calc/2026-10-15.1'), 'NYSE:SYNB': _row('0000000001', calc_version=v),
               'NYSE:SYNC': _row('0000000002', calc_version=v)}
    target = {'syn': {'cik': '0000000002', 'state': 'NOT_AVAILABLE', 'reason_codes': [qi.WITHDRAWN_REASON], 'fiscal_year_end': None,
                      'detected_at': '2026-10-12T00:00:00Z'}}
    out = qi.from_inputs({'calc_version': v, 'records': records, 'target': target})['records']
    assert out['NYSE:SYNA']['calc_version_mismatch'] is True and out['NYSE:SYNA']['v_inputs'] is None
    assert out['NYSE:SYNB']['in_cross_section'] is True                    # the next same-version code is the CIK's point
    for code in ('NYSE:SYNC', 'TARGET:syn'):
        assert out[code]['identity_withdrawn'] is True and out[code]['state'] == 'WITHDRAWN' and out[code]['na_reasons'] == [qi.WITHDRAWN_REASON]
    companies = qi.engine_companies({'records': out}, {}, load_official_type_config().to_dict())
    assert 'NYSE:SYNA' not in companies and companies['NYSE:SYNB']['memberships']['growth'] == pytest.approx(0.5)


def test_ascii_patterns_and_cyclical_basis():
    out = qi.from_inputs({'records': {'NYSE:SYNA': _row('0000000001', sic='３６７４', fiscal_year_end='2025-12-31')}})['records']
    assert out['NYSE:SYNA']['sic'] is None                                 # JS \\d is ASCII-only
    basis = qi.cyclical_basis({'records': {'NYSE:SYNA': dict(out['NYSE:SYNA'], sic='3674')}}, playbook.load_config())
    assert basis == {'NYSE:SYNA': True}                                    # semiconductors subgroup (PlaybookEngine §6-2)


def test_invalid_file_fails_closed():
    with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
        qi.from_inputs({'records': {'bad code': {}}})
    with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
        qi.light({'kind': 'SEC_QGV2', 'records': {}, 'price': 1})
    with pytest.raises(ValueError, match='SEC_QGV2_INVALID'):
        qi.to_inputs({'kind': 'SEC_QGV2'}, '2026-10-13T00:00:00Z')
