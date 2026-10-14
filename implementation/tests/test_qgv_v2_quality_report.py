"""The quality report uses validated published inputs; its gaps are not zero-filled."""
import importlib.util
from pathlib import Path

import pytest

from investment_system.qgv.v2_quality_report import report

ROOT = Path(__file__).resolve().parents[1]


def payload():
    spec = importlib.util.spec_from_file_location('qgv2_report_synthetic', ROOT / 'tools/sec_qgv2_reference.py')
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    return ref.base()


def test_report_covers_504_and_keeps_device_value_unavailable():
    value = report(payload())
    assert value['registered_codes'] == 504
    assert value['axes']['Q']['missing_codes'] > 0
    assert value['axes']['Q']['distribution']['count'] + value['axes']['Q']['missing_codes'] == 504
    assert value['V'] == {'state': 'NOT_AVAILABLE', 'reason': 'DEVICE_PRICES_REQUIRED'}
    assert len(value['inspection_candidates']) == 10
    assert all(len(rows) <= 10 for group in value['industry_top10'].values() for rows in group.values())


def test_report_rejects_extra_price_or_modified_scores():
    value = payload()
    value['prices'] = {}
    with pytest.raises(ValueError):
        report(value)
