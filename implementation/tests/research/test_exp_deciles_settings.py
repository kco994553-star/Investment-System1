"""EXP-STOCK-INDICATOR-DECILES-v1 frozen settings. Expected values are written by hand from the settings doc sections 1-3."""
from decimal import Decimal
import hashlib
import json

import pytest

from investment_system.qgv import qgv_v2, v2_factors
from investment_system.research.exp_deciles import settings

# Frozen: a deliberate settings (or engine preset / calc version) change must update this pin together with the doc.
SETTINGS_SHA256 = '525dca26a48636bb63715cb3ac968bdafac848cee2ba648d934569b086a38191'


def test_experiment_identity_and_universe_thresholds():
    assert settings.EXPERIMENT_ID == 'EXP-STOCK-INDICATOR-DECILES-v1'
    assert settings.U_A_ENTRY_USD == Decimal('250000000')
    assert settings.U_A_STAY_USD == Decimal('200000000')
    assert settings.U_B_MIN_USD == Decimal('10000000000')
    assert all(isinstance(v, Decimal) for v in (settings.U_A_ENTRY_USD, settings.U_A_STAY_USD, settings.U_B_MIN_USD))
    assert settings.GROUPS == ('U_A', 'U_B')
    assert settings.SCORING_POPULATION == 'U_A_AT_S'


def test_presets_are_the_four_fixed_presets_and_default_is_an_alias():
    # Hand-written from the settings doc (section 1), not read from the engine.
    assert settings.PRESET_WEIGHTS == {
        'balanced': {'Q': 34, 'G': 33, 'V': 33}, 'quality': {'Q': 50, 'G': 25, 'V': 25},
        'growth': {'Q': 30, 'G': 50, 'V': 20}, 'value': {'Q': 25, 'G': 20, 'V': 55}}
    assert settings.PRESET_WEIGHTS == {p: qgv_v2.PRESETS[p]['weights'] for p in qgv_v2.PRESETS}
    assert qgv_v2.DEFAULT_PRESET == 'balanced'
    assert settings.PRESET_ALIASES == {'default': 'balanced'}
    assert 'default' not in settings.PRESET_IDS
    assert settings.resolve_preset('default') == 'balanced'
    with pytest.raises(ValueError, match='PRESET_INVALID'):
        settings.resolve_preset('user-preset/balanced@0.1')   # USER_PRESETS are not this study
    user_axes = [d['axis'] for d in qgv_v2.USER_PRESETS.values()]
    assert settings.PRESET_WEIGHTS['balanced'] not in user_axes


def test_strategies_axes_and_totals_per_preset():
    assert settings.STRATEGY_IDS == ('AXIS_Q', 'AXIS_G', 'AXIS_V', 'QGV_BALANCED', 'QGV_QUALITY', 'QGV_GROWTH', 'QGV_VALUE')
    assert [settings.STRATEGIES[s]['axis'] for s in settings.STRATEGY_IDS[:3]] == ['Q', 'G', 'V']
    assert [settings.STRATEGIES[s]['preset'] for s in settings.STRATEGY_IDS[3:]] == list(settings.PRESET_IDS)
    assert settings.resolve_strategy('QGV_DEFAULT') == 'QGV_BALANCED'
    with pytest.raises(ValueError, match='STRATEGY_INVALID'):
        settings.resolve_strategy('W0')


def test_selection_account_and_pit_constants():
    assert settings.DECILE == Decimal('0.10') and settings.MIN_N == 10
    assert settings.COST_BPS_PER_SIDE == Decimal('10')
    assert settings.SLIPPAGE_BPS == Decimal('0') and settings.CASH_INTEREST_RATE == Decimal('0')
    assert settings.NAV_BASE_USD == Decimal('1000000')
    assert settings.PIT_LAG_FULL_SESSIONS == 5 and settings.PIT_USABLE_SESSION == 6
    assert settings.SCHEDULE_YEARS == tuple(range(2017, 2027))
    assert settings.FIRST_BUNDLE == {'S': '2018-02-16', 'T': '2018-02-20', 'next_T': '2019-02-19'}
    assert settings.SCORING_CALC_VERSION == v2_factors.CALC_VERSION
    assert settings.GATE is True and settings.TYPE_WEIGHTS is True


def test_settings_dict_is_json_with_decimals_as_strings_and_fresh():
    d = settings.settings_dict()
    assert d['universes']['U_A'] == {'entry_usd': '250000000', 'stay_usd': '200000000',
                                     'rule': settings.U_A_RULE}
    assert d['universes']['U_B']['min_usd'] == '10000000000'
    assert d['selection']['decile'] == '0.10' and d['account']['nav_base_usd'] == '1000000'
    assert d['scoring']['population'] == 'U_A_AT_S'
    assert list(d['scoring']['presets']) == list(settings.PRESET_IDS)
    # Security types (owner decision 2026-10-30, EXPANDED_DEFINITION_20261030.md section 1.2) are part of the hash.
    assert d['universes']['security_types'] == {
        'decision': settings.SECURITY_TYPES_DECISION, 'eligible': ['COMMON', 'COMMON_CLASS', 'ADR', 'REIT'],
        'excluded': ['ETF', 'CLOSED_END_FUND', 'PREFERRED', 'WARRANT', 'RIGHT', 'UNIT'],
        'adr_market_cap_rule': settings.ADR_MARKET_CAP_RULE}
    d['universes']['U_A']['entry_usd'] = '1'
    assert settings.settings_dict()['universes']['U_A']['entry_usd'] == '250000000'


def test_settings_sha256_is_canonical_and_pinned():
    text = settings.canonical_json()
    assert '": ' not in text and '", "' not in text      # compact separators
    assert json.loads(text) == settings.settings_dict()
    assert text == json.dumps(settings.settings_dict(), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    digest = settings.settings_sha256()
    assert digest == hashlib.sha256(text.encode('ascii')).hexdigest()
    assert digest == settings.settings_sha256()
    assert digest == SETTINGS_SHA256


def test_settings_sha256_changes_with_any_value(monkeypatch):
    before = settings.settings_sha256()
    monkeypatch.setattr(settings, 'U_A_STAY_USD', Decimal('200000001'))
    assert settings.settings_sha256() != before
    monkeypatch.undo()
    monkeypatch.setattr(settings, 'MIN_N', 11)
    assert settings.settings_sha256() != before
    monkeypatch.undo()
    monkeypatch.setattr(settings, 'ELIGIBLE_SECURITY_TYPES', ('COMMON', 'COMMON_CLASS'))
    assert settings.settings_sha256() != before


def test_package_imports_no_qgv_backtest_network_or_io_modules():
    # The #417/#430 package is not on canonical and Codex's originals stay untouched: ported code only, no import.
    # The CLI (implementation/tools/exp_stock_indicator_deciles.py) is the only IO layer and lives outside the package.
    import ast
    from pathlib import Path

    pkg = Path(settings.__file__).parent
    banned = {'qgv_backtest', 'urllib', 'requests', 'http', 'socket', 'subprocess', 'providers'}
    modules = sorted(p.name for p in pkg.glob('*.py'))
    assert modules == ['__init__.py', 'benchmarks.py', 'handoff.py', 'ledger.py', 'metrics.py', 'pit.py', 'runner.py',
                       'schedule.py', 'scoring.py', 'selection.py', 'settings.py', 'universe.py']
    for name in modules:
        tree = ast.parse((pkg / name).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] + [a.name for a in node.names] if isinstance(node, ast.ImportFrom) else [])
            for imported in names:
                assert not set(imported.split('.')) & banned, (name, imported)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ('open', 'exec', 'eval', '__import__'), (name, node.func.id)
    # the only package file read stays the frozen schedule
    reads = [name for name in modules if 'read_text' in (pkg / name).read_text(encoding='utf-8')
             or 'read_bytes' in (pkg / name).read_text(encoding='utf-8')]
    assert reads == ['schedule.py']
