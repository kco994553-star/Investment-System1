"""Canonical port uses the existing kernels without the unmerged 555 engine."""
from importlib.util import find_spec
from pathlib import Path
import importlib.util
import sys


def examples():
    path = Path(__file__).parents[2] / 'tools/kis_contract_fixture.py'
    spec = importlib.util.spec_from_file_location('canonical_kis_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_technical_runtime_exists_independently_of_555():
    assert find_spec('investment_system.research.technical_handoff') is not None
    fixture = examples()
    values = fixture.handoff_fixtures()
    expected = {r['case']: r for r in values['expectations.json']['cases']}
    normal = values['normal-result.json']
    assert normal['components']['metrics']['SMA_20']['value'] == 108.95
    assert normal['components']['metrics']['SMA_120']['value'] is None
    assert normal['measures']['metrics']['momentum_3m']['value'] is not None
    assert normal['measures']['metrics']['dollar_volume_6m']['value'] is None
    assert expected['missing-session']['pattern_state'] == 'NOT_JUDGEABLE'
    assert expected['missing-evidence']['component_adopted'] == 0
    assert expected['stale']['chart_observation_day'] < expected['stale']['signal_day']
    assert 'investment_system.research.qgv_555' not in sys.modules


def test_original_raw_and_confirmed_split_only():
    fixture = examples()
    cases = {r['case']: r for r in fixture.split_evidence_fixtures()['split-evidence-expectations.json']['cases']}
    assert cases['provider-modp1']['error'] == 'RAW_DAILY_SOURCE_REQUIRED'
    assert cases['double-adjusted-bars']['error'] == 'ADJUSTED_ROWS_DO_NOT_MATCH_CONFIRMED_SPLITS'
    assert cases['future-event']['future_count'] == 1
    assert cases['future-event']['adjustment_applied'] == [False]
    assert cases['ratio-conflict']['block_reasons'] == ['SPLIT_RATIO_CONFLICT']
