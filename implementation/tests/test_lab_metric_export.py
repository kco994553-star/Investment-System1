import json
import pytest
from investment_system.research.exp_deciles import lab_diagnostics as lab


def result():
    return {'result_kind': 'SINGLE_COMPANY_METRIC', 'signal_day': '2018-02-16',
            'code_reference': 'a' * 40, 'ev_sales': '2.5', 'symbol': 'SYNTHETIC_ONLY'}


def test_metric_export_is_count_only_without_performance_or_identity_claim():
    out = lab.single_company(result(), source_commit='b' * 40, generated_at='2026-11-04T12:00:00Z')
    r = out['runs'][0]
    assert out['schema_version'] == 'lab-backtest-v2'
    assert r['result_kind'] == 'SINGLE_COMPANY_METRIC' and r['sample']['n_used'] == 1
    assert r['diagnostics'][0]['value'] == 1
    assert r['universe']['point_in_time'] is False
    assert r['equity_curve'] == [] and all(v is None for v in r['metrics'].values())
    assert r['period'] is None and r['costs'] is None
    assert 'SYNTHETIC_ONLY' not in json.dumps(out) and '2.5' not in json.dumps(out)


@pytest.mark.parametrize('change', [{'result_kind': 'BACKTEST'}, {'ev_sales': None}, {'ev_sales': 'NaN'}, {'signal_day': '2018-02-30'}, {'code_reference': 'short'}])
def test_wrong_or_uncomputed_evidence_cannot_be_marked_computed(change):
    with pytest.raises(ValueError):
        lab.single_company({**result(), **change}, source_commit='b' * 40, generated_at='2026-11-04T12:00:00Z')
