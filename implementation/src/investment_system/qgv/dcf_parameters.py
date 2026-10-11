"""Adopted DCF default parameters (dcf_parameters/v1-default), separate from type_config/1.

User decision 2026-10-11: explicit 5 years, discount rate 10%, terminal growth
2%, reverse-DCF bracket -50%..+100%, FCFE per diluted share / cost of equity.
Status V1_UNCALIBRATED_DEFAULT: a labelled, editable default, not a calibration.
The explicit-period growth h is not decided and stays null.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

PATH = Path(__file__).with_name('dcf_parameters_v1_default.json')
CONFIG_VERSION = 'dcf_parameters/v1-default'
STATUS = 'V1_UNCALIBRATED_DEFAULT'
KEYS = frozenset({
    'schema_version', 'config_version', 'role', 'status', 'decided_at', 'confirmed', 'explicit_years',
    'discount_rate', 'terminal_growth', 'discount_rate_basis', 'cashflow_basis', 'currency',
    'per_share_basis_confirmed', 'share_basis', 'fcfe_definition', 'explicit_growth', 'explicit_growth_status',
    'solver', 'output_version', 'rate_source', 'terminal_source',
})
SOLVER_KEYS = frozenset({'growth_lower', 'growth_upper', 'relative_price_tolerance', 'maximum_iterations'})


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_dcf_parameters(p):
    """Return fixed error codes; empty tuple means the document is the valid default shape."""
    errors = []
    if not isinstance(p, dict) or set(p) != KEYS:
        return ('PARAMETERS_SHAPE',)
    if p['schema_version'] != 1 or p['config_version'] != CONFIG_VERSION or p['role'] != 'RAM_ONLY_RESEARCH':
        errors.append('PARAMETERS_VERSION')
    if p['status'] != STATUS or p['confirmed'] is not True or p['output_version'] != 'v1+dcf_v1_default':
        errors.append('PARAMETERS_STATUS')
    if type(p['explicit_years']) is not int or not 1 <= p['explicit_years'] <= 100:
        errors.append('PARAMETERS_YEARS')
    r, g = p['discount_rate'], p['terminal_growth']
    if not _finite(r) or not _finite(g) or r <= -1 or g <= -1 or r <= g:
        errors.append('PARAMETERS_RATES')
    if (p['cashflow_basis'], p['discount_rate_basis'], p['share_basis'], p['fcfe_definition']) != (
            'FCFE_PER_SHARE', 'COST_OF_EQUITY', 'WEIGHTED_AVERAGE_DILUTED', 'fcfe/1') or p['per_share_basis_confirmed'] is not True:
        errors.append('PARAMETERS_BASIS')
    if p['currency'] not in ('USD', 'KRW', 'JPY'):
        errors.append('PARAMETERS_CURRENCY')
    if p['explicit_growth'] is not None or p['explicit_growth_status'] != 'EXPLICIT_GROWTH_UNDECIDED':
        errors.append('PARAMETERS_EXPLICIT_GROWTH')
    s = p['solver']
    if not isinstance(s, dict) or set(s) != SOLVER_KEYS or not _finite(s['growth_lower']) or not _finite(s['growth_upper']) \
            or not -1 < s['growth_lower'] < s['growth_upper'] or not _finite(s['relative_price_tolerance']) \
            or not 0 < s['relative_price_tolerance'] < 1 or type(s['maximum_iterations']) is not int or not 1 <= s['maximum_iterations'] <= 10000:
        errors.append('PARAMETERS_SOLVER')
    return tuple(errors)


def load_default_dcf_parameters():
    """Fresh validated copy of the adopted defaults (caller passes it to qgv.dcf)."""
    p = json.loads(PATH.read_text())
    errors = validate_dcf_parameters(p)
    if errors:
        raise ValueError('|'.join(errors))
    return p
