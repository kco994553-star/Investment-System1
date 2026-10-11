"""Adopted DCF default parameters, separate from type_config/1.

dcf_parameters/v1-default (user decision 2026-10-11, kept as history):
explicit 5 years, discount rate 10%, terminal growth 2%, reverse-DCF bracket
-50%..+100%, FCFE per diluted share / cost of equity; explicit growth h null.

dcf_parameters/v1.1-default (user decision 2026-10-11, current default):
the same numbers with fcfe/1.1 and the PROVISIONAL explicit-growth rule
h = clamp(own 3-year revenue CAGR, 0, 0.15). Both are V1_* UNCALIBRATED
defaults: labelled, editable values, not a calibration.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import math
from pathlib import Path

PATH_V1 = Path(__file__).with_name('dcf_parameters_v1_default.json')
PATH = Path(__file__).with_name('dcf_parameters_v1_1_default.json')
CONFIG_VERSION_V1 = 'dcf_parameters/v1-default'
CONFIG_VERSION = 'dcf_parameters/v1.1-default'
STATUS_V1 = 'V1_UNCALIBRATED_DEFAULT'
STATUS = 'V1_1_UNCALIBRATED_DEFAULT'
GROWTH_RULE_KIND = 'REVENUE_CAGR_3Y_CLAMP'
_COMMON = frozenset({
    'schema_version', 'config_version', 'role', 'status', 'decided_at', 'confirmed', 'explicit_years',
    'discount_rate', 'terminal_growth', 'discount_rate_basis', 'cashflow_basis', 'currency',
    'per_share_basis_confirmed', 'share_basis', 'fcfe_definition', 'solver', 'output_version', 'rate_source', 'terminal_source',
})
KEYS_V1 = _COMMON | {'explicit_growth', 'explicit_growth_status'}
KEYS = _COMMON | {'explicit_growth_rule', 'supersedes'}
RULE_KEYS = frozenset({'kind', 'metric', 'lower', 'upper', 'status'})
SOLVER_KEYS = frozenset({'growth_lower', 'growth_upper', 'relative_price_tolerance', 'maximum_iterations'})
# version -> (keys, status, output version, fcfe definition)
_VERSIONS = {
    CONFIG_VERSION_V1: (KEYS_V1, STATUS_V1, 'v1+dcf_v1_default', 'fcfe/1'),
    CONFIG_VERSION: (KEYS, STATUS, 'v1+dcf_v1_1_default', 'fcfe/1.1'),
}


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def valid_growth_rule(rule):
    """True for {kind: REVENUE_CAGR_3Y_CLAMP, metric: revenue_cagr_3y, lower <= upper (finite, > -1), status}."""
    return (isinstance(rule, Mapping) and set(rule) == RULE_KEYS and rule['kind'] == GROWTH_RULE_KIND
            and rule['metric'] == 'revenue_cagr_3y' and rule['status'] == 'PROVISIONAL'
            and _finite(rule['lower']) and _finite(rule['upper']) and -1 < rule['lower'] <= rule['upper'])


def explicit_growth(parameters, revenue_cagr_3y):
    """(h, reason). h = min(upper, max(lower, CAGR)); never invented when the rule or the CAGR is missing."""
    rule = parameters.get('explicit_growth_rule') if isinstance(parameters, Mapping) else None
    if rule is None:
        return None, 'EXPLICIT_GROWTH_UNDECIDED'
    if not valid_growth_rule(rule):
        return None, 'EXPLICIT_GROWTH_RULE_INVALID'
    if not _finite(revenue_cagr_3y):
        return None, 'EXPLICIT_GROWTH_NOT_AVAILABLE'
    return min(rule['upper'], max(rule['lower'], revenue_cagr_3y)), None


def validate_dcf_parameters(p):
    """Return fixed error codes; empty tuple means the document is a valid adopted-default shape (v1 or v1.1)."""
    errors = []
    version = p.get('config_version') if isinstance(p, dict) else None
    if version not in _VERSIONS or set(p) != _VERSIONS[version][0]:
        return ('PARAMETERS_SHAPE',)
    _, status, output_version, fcfe_definition = _VERSIONS[version]
    if p['schema_version'] != 1 or p['role'] != 'RAM_ONLY_RESEARCH':
        errors.append('PARAMETERS_VERSION')
    if p['status'] != status or p['confirmed'] is not True or p['output_version'] != output_version:
        errors.append('PARAMETERS_STATUS')
    if type(p['explicit_years']) is not int or not 1 <= p['explicit_years'] <= 100:
        errors.append('PARAMETERS_YEARS')
    r, g = p['discount_rate'], p['terminal_growth']
    if not _finite(r) or not _finite(g) or r <= -1 or g <= -1 or r <= g:
        errors.append('PARAMETERS_RATES')
    if (p['cashflow_basis'], p['discount_rate_basis'], p['share_basis'], p['fcfe_definition']) != (
            'FCFE_PER_SHARE', 'COST_OF_EQUITY', 'WEIGHTED_AVERAGE_DILUTED', fcfe_definition) or p['per_share_basis_confirmed'] is not True:
        errors.append('PARAMETERS_BASIS')
    if p['currency'] not in ('USD', 'KRW', 'JPY'):
        errors.append('PARAMETERS_CURRENCY')
    if version == CONFIG_VERSION_V1:
        if p['explicit_growth'] is not None or p['explicit_growth_status'] != 'EXPLICIT_GROWTH_UNDECIDED':
            errors.append('PARAMETERS_EXPLICIT_GROWTH')
    elif not valid_growth_rule(p['explicit_growth_rule']) or p['supersedes'] != CONFIG_VERSION_V1:
        errors.append('PARAMETERS_EXPLICIT_GROWTH')
    s = p['solver']
    if not isinstance(s, dict) or set(s) != SOLVER_KEYS or not _finite(s['growth_lower']) or not _finite(s['growth_upper']) \
            or not -1 < s['growth_lower'] < s['growth_upper'] or not _finite(s['relative_price_tolerance']) \
            or not 0 < s['relative_price_tolerance'] < 1 or type(s['maximum_iterations']) is not int or not 1 <= s['maximum_iterations'] <= 10000:
        errors.append('PARAMETERS_SOLVER')
    return tuple(errors)


def _load(path):
    p = json.loads(path.read_text())
    errors = validate_dcf_parameters(p)
    if errors:
        raise ValueError('|'.join(errors))
    return p


def load_default_dcf_parameters():
    """Fresh validated copy of the current adopted defaults (dcf_parameters/v1.1-default)."""
    return _load(PATH)


def load_v1_dcf_parameters():
    """History: the superseded dcf_parameters/v1-default document (explicit growth undecided)."""
    return _load(PATH_V1)
