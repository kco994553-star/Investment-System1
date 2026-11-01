"""Frozen settings of EXP-STOCK-INDICATOR-DECILES-v1. New for this experiment (nothing ported).

Source of every value: implementation/docs/lab/EXP_STOCK_INDICATOR_DECILES_V1.md sections 1-3 (owner 2026-11-01). These
settings are separate from the operating and forward-validation v3 settings (section 3): no USER_PRESETS, no W0-W3, no
ceil(n/10), no n >= 100 minimum, no top-500 universe, no monthly rebalancing.

Presets come from qgv.qgv_v2.PRESETS (the four fixed presets). 'default' is qgv_v2.DEFAULT_PRESET, which is 'balanced',
so it is an alias and is never scored a second time. settings_sha256() hashes a canonical JSON of settings_dict(); any
change of a value here, of the preset weights in qgv_v2 or of the calc version in v2_factors changes the hash.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json

from ...qgv import qgv_v2, v2_factors

EXPERIMENT_ID = 'EXP-STOCK-INDICATOR-DECILES-v1'
SETTINGS_SCHEMA = 'exp-deciles-settings/1'
SETTINGS_DOC = 'implementation/docs/lab/EXP_STOCK_INDICATOR_DECILES_V1.md'

# ---- populations (nominal issuer market cap in USD at S, class sum) ----
U_A = 'U_A'
U_B = 'U_B'
GROUPS = (U_A, U_B)
CURRENCY = 'USD'
U_A_ENTRY_USD = Decimal('250000000')
U_A_STAY_USD = Decimal('200000000')
U_B_MIN_USD = Decimal('10000000000')
MARKET_CAP_BASIS = 'ISSUER_NOMINAL_CLASS_SUM_AT_S'
# Security types (owner decision 2026-10-30, implementation/docs/expanded_universe/EXPANDED_DEFINITION_20261030.md section
# 1.2), named as universe.expanded_catalog.SECURITY_TYPES: common stock (each class; the issuer is counted once), ADR/ADS
# and REIT are in; ETF, closed-end fund, preferred, warrant, right and unit are out (NOT_ELIGIBLE_SECURITY_TYPE). A type
# outside both lists is not a canonical name and leaves the security UNKNOWN (never excluded).
SECURITY_TYPES_DECISION = ('implementation/docs/expanded_universe/EXPANDED_DEFINITION_20261030.md section 1.2 '
                           '(owner 2026-10-30)')
ELIGIBLE_SECURITY_TYPES = ('COMMON', 'COMMON_CLASS', 'ADR', 'REIT')
EXCLUDED_SECURITY_TYPES = ('ETF', 'CLOSED_END_FUND', 'PREFERRED', 'WARRANT', 'RIGHT', 'UNIT')
ADR_SECURITY_TYPE = 'ADR'
# ADR issuer cap = ordinary shares outstanding / adr_ratio (ordinary shares per ADS) x ADS price; no confirmed ratio -> NA.
ADR_MARKET_CAP_RULE = 'ORDINARY_SHARES_OUTSTANDING_DIV_ADR_RATIO_X_ADS_PRICE_UNCONFIRMED_RATIO_NA'
U_A_RULE = 'ENTRY_250M_STAY_200M_FOR_PREVIOUS_U_A_MEMBERS_FIRST_BUILD_ENTRY'
U_B_RULE = 'MIN_10BN_EACH_EVALUATION_DATE_NO_HYSTERESIS'

# ---- scoring ----
SCORING_POPULATION = 'U_A_AT_S'   # score within the U-A members at S; U-B selects from these same scores
SCORING_CALC_VERSION = v2_factors.CALC_VERSION
if qgv_v2.DEFAULT_PRESET != 'balanced':
    raise RuntimeError('DEFAULT_PRESET_CHANGED')
PRESET_IDS = ('balanced', 'quality', 'growth', 'value')
if set(PRESET_IDS) != set(qgv_v2.PRESETS):
    raise RuntimeError('PRESETS_CHANGED')
DEFAULT_PRESET_ALIAS = 'default'
PRESET_ALIASES = {DEFAULT_PRESET_ALIAS: qgv_v2.DEFAULT_PRESET}
PRESET_WEIGHTS = {p: dict(qgv_v2.PRESETS[p]['weights']) for p in PRESET_IDS}
AXES = ('Q', 'G', 'V')
GATE = qgv_v2.GATE_DEFAULT          # value-trap gate ON (engine default), type weights ON, official inner weights
TYPE_WEIGHTS = True

# ---- strategies: one score per security, higher is better for every one of them ----
STRATEGIES = {
    'AXIS_Q': {'kind': 'AXIS', 'axis': 'Q'},
    'AXIS_G': {'kind': 'AXIS', 'axis': 'G'},
    'AXIS_V': {'kind': 'AXIS', 'axis': 'V'},
    'QGV_BALANCED': {'kind': 'TOTAL', 'preset': 'balanced'},
    'QGV_QUALITY': {'kind': 'TOTAL', 'preset': 'quality'},
    'QGV_GROWTH': {'kind': 'TOTAL', 'preset': 'growth'},
    'QGV_VALUE': {'kind': 'TOTAL', 'preset': 'value'},
}
STRATEGY_IDS = tuple(STRATEGIES)
STRATEGY_ALIASES = {'QGV_DEFAULT': 'QGV_BALANCED'}

# ---- selection ----
DECILE = Decimal('0.10')
MIN_N = 10
ORDER = 'SCORE_DESC_THEN_SECURITY_ID_ASC'
SELECTION_RULE = 'K_FLOOR_N_X_0_10_FIRST_K_AND_LAST_K_OF_ONE_ORDER_NOT_RUN_BELOW_MIN_N'
WEIGHTING = 'EQUAL_WEIGHT_LONG_ONLY_EACH_SIDE'

# ---- schedule and point in time ----
REBALANCE = 'ANNUAL_THIRD_MONDAY_OF_FEBRUARY'
EXECUTION = 'T_OPEN'               # T = first NYSE session on/after the third Monday; never a last-trade substitute
SIGNAL = 'S_SESSION_BEFORE_T'
PIT_LAG_FULL_SESSIONS = 5          # filing usable on the next session after 5 full NYSE sessions after its NY filing date
PIT_USABLE_SESSION = PIT_LAG_FULL_SESSIONS + 1
FILING_DATE_BASIS = 'SEC_FILING_DATE_NEW_YORK'
CALENDAR = 'research.pit_filings.is_session (NYSE rule calendar 2009-2028)'
SCHEDULE_YEARS = tuple(range(2017, 2027))
FIRST_BUNDLE = {'S': '2018-02-16', 'T': '2018-02-20', 'next_T': '2019-02-19'}

# ---- account ----
COST_BPS_PER_SIDE = Decimal('10')
SLIPPAGE_BPS = Decimal('0')
CASH_INTEREST_RATE = Decimal('0')
ADDITIONAL_CONTRIBUTION = Decimal('0')
# Internal notional capital of the ledger: an engine setting, not an owner-set initial capital (owner 11/01 supplementary
# instruction). Results do not depend on it (fractional quantities, proportional costs; checked from 0.01 to 1e9). The
# reported NAV is the index starting at 100 (REPORTED_NAV); the owner's "USD NAV=100만" meant that index.
INTERNAL_NOTIONAL_CAPITAL_USD = Decimal('1000000')
REPORTED_NAV = 'INDEX_BASE_100'
KRW_REQUEST = Decimal('100000000')
KRW_RULE = 'KRW_PERFORMANCE_NOT_COMPUTED_WITHOUT_HISTORICAL_FX'
CASH_RULE = 'DIVIDEND_AND_MERGER_CASH_HELD_UNTIL_NEXT_RESELECTION'
UNFILLED_RULE = 'NO_T_OPEN_UNFILLED_NO_NEXT_RANK_SUBSTITUTION'
UNRESOLVED_EXIT_SCENARIOS = ('LOSS', 'CARRY')
COST_REPORTING = 'BEFORE_AND_AFTER_COST'
# Owner 11/01 decision 3: SPY total return is an ETF auxiliary comparison only; no S&P 500 index total return is claimed.
BENCHMARKS = ('GROUP_EQUAL_WEIGHT_ELIGIBLE', 'SPY_TOTAL_RETURN_ETF_AUXILIARY')
PERFORMANCE_HORIZON_YEARS = (1, 3, 5, 10)   # a horizon longer than the data is null with a reason


def _jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def settings_dict():
    """A fresh JSON-ready copy of every frozen setting (Decimals as strings)."""
    return _jsonable({
        'schema': SETTINGS_SCHEMA, 'experiment_id': EXPERIMENT_ID, 'settings_doc': SETTINGS_DOC,
        'universes': {
            'currency': CURRENCY, 'market_cap_basis': MARKET_CAP_BASIS,
            'security_types': {'decision': SECURITY_TYPES_DECISION, 'eligible': ELIGIBLE_SECURITY_TYPES,
                               'excluded': EXCLUDED_SECURITY_TYPES, 'adr_market_cap_rule': ADR_MARKET_CAP_RULE},
            U_A: {'entry_usd': U_A_ENTRY_USD, 'stay_usd': U_A_STAY_USD, 'rule': U_A_RULE},
            U_B: {'min_usd': U_B_MIN_USD, 'rule': U_B_RULE},
        },
        'scoring': {
            'population': SCORING_POPULATION, 'calc_version': SCORING_CALC_VERSION, 'presets': PRESET_WEIGHTS,
            'preset_aliases': PRESET_ALIASES, 'axes': AXES, 'gate': GATE, 'type_weights': TYPE_WEIGHTS,
        },
        'strategies': STRATEGIES, 'strategy_aliases': STRATEGY_ALIASES,
        'selection': {'decile': DECILE, 'min_n': MIN_N, 'order': ORDER, 'rule': SELECTION_RULE, 'weighting': WEIGHTING},
        'schedule': {'rebalance': REBALANCE, 'signal': SIGNAL, 'execution': EXECUTION, 'years': SCHEDULE_YEARS,
                     'first_bundle': FIRST_BUNDLE, 'calendar': CALENDAR},
        'pit': {'lag_full_sessions': PIT_LAG_FULL_SESSIONS, 'usable_session': PIT_USABLE_SESSION,
                'filing_date_basis': FILING_DATE_BASIS},
        'account': {'cost_bps_per_side': COST_BPS_PER_SIDE, 'slippage_bps': SLIPPAGE_BPS,
                    'cash_interest_rate': CASH_INTEREST_RATE, 'additional_contribution': ADDITIONAL_CONTRIBUTION,
                    'internal_notional_capital_usd': INTERNAL_NOTIONAL_CAPITAL_USD, 'reported_nav': REPORTED_NAV, 'krw_request': KRW_REQUEST, 'krw_rule': KRW_RULE,
                    'cash_rule': CASH_RULE, 'unfilled_rule': UNFILLED_RULE,
                    'unresolved_exit_scenarios': UNRESOLVED_EXIT_SCENARIOS, 'cost_reporting': COST_REPORTING},
        'benchmarks': BENCHMARKS, 'performance_horizon_years': PERFORMANCE_HORIZON_YEARS,
    })


def canonical_json(value=None):
    """Sorted keys, no whitespace, ASCII: the bytes settings_sha256 hashes."""
    return json.dumps(settings_dict() if value is None else _jsonable(value), sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False)


def settings_sha256():
    return hashlib.sha256(canonical_json().encode('ascii')).hexdigest()


def resolve_preset(preset):
    """'default' -> 'balanced'; a fixed preset id -> itself; anything else ValueError('PRESET_INVALID')."""
    preset = PRESET_ALIASES.get(preset, preset)
    if preset not in PRESET_IDS:
        raise ValueError('PRESET_INVALID')
    return preset


def resolve_strategy(strategy):
    """'QGV_DEFAULT' -> 'QGV_BALANCED'; unknown ids ValueError('STRATEGY_INVALID')."""
    strategy = STRATEGY_ALIASES.get(strategy, strategy)
    if strategy not in STRATEGIES:
        raise ValueError('STRATEGY_INVALID')
    return strategy
