"""Versioned immutable configuration; calculation receives it, performs no I/O.

The loader is the sole official factory. Custom compilation always produces
PREVIEW, regardless of a supplied official label. No save/export is provided.
"""
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re

PILLARS = ('Q', 'G', 'V')

def finite(value):
    try: return type(value) in (int, float) and math.isfinite(value)
    except OverflowError: return False


def validate_type_config(config):
    errors = []
    def err(code):
        if code not in errors: errors.append(code)
    def weights(value):
        if not isinstance(value, dict) or set(value) != set(PILLARS) or any(not finite(v) or v < 0 or v > 100 for v in value.values()):
            err('WEIGHT_INVALID'); return
        if not math.isclose(sum(value.values()), 100, abs_tol=1e-9, rel_tol=0): err('WEIGHT_SUM')
    def rule(value, depth=0):
        if not isinstance(value, dict) or depth > 8: err('RULE_INVALID'); return
        kind = value.get('kind')
        if kind not in ('ramp', 'gated_ramp', 'rank', 'unresolved'): err('RULE_KIND'); return
        if kind in ('ramp', 'gated_ramp', 'rank'):
            if not isinstance(value.get('metric'), str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,95}', value['metric']): err('METRIC_INVALID')
        if kind in ('ramp', 'gated_ramp'):
            low, high = value.get('lower'), value.get('upper')
            if not finite(low) or not finite(high) or low >= high: err('RAMP_BOUNDS')
        if kind == 'gated_ramp' and (not isinstance(value.get('gate_metric'), str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,95}', value['gate_metric'])): err('METRIC_INVALID')
        if kind == 'rank' and (type(value.get('max_rank')) is not int or value['max_rank'] < 1): err('RANK_BOUND')
        if kind == 'unresolved':
            reasons = value.get('reasons')
            if not isinstance(reasons, list) or not reasons or any(not isinstance(r, str) or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,95}', r) for r in reasons): err('UNRESOLVED_REASONS')
            if 'components' in value:
                if not isinstance(value['components'], list): err('RULE_INVALID')
                else:
                    for child in value['components']: rule(child, depth + 1)
    if not isinstance(config, dict): return ('CONFIG_INVALID',)
    if config.get('schema_version') != 1 or type(config.get('schema_version')) is not int: err('SCHEMA_VERSION')
    if not isinstance(config.get('config_version'), str) or not config['config_version']: err('CONFIG_VERSION')
    types = config.get('types'); ids = []
    if not isinstance(types, list) or len(types) > 128: err('TYPES_INVALID'); types = []
    for item in types:
        if not isinstance(item, dict): err('TYPE_INVALID'); continue
        id_ = item.get('id')
        if not isinstance(id_, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', id_): err('TYPE_ID_INVALID')
        elif id_ in ids: err('TYPE_ID_DUPLICATE')
        else: ids.append(id_)
        if not isinstance(item.get('name'), str) or not item['name'].strip() or len(item['name']) > 128: err('TYPE_NAME_INVALID')
        if type(item.get('affects_qgv')) is not bool: err('TYPE_ROLE_INVALID')
        if (item.get('type_role') == 'EXPOSURE_ONLY' or id_ == 'theme') and item.get('affects_qgv'): err('THEME_QGV_FORBIDDEN')
        if item.get('affects_qgv'): weights(item.get('weights'))
        elif 'weights' in item: err('DISPLAY_TYPE_WEIGHTS_FORBIDDEN')
        rule(item.get('rule'))
    fallback = config.get('fallback')
    if not isinstance(fallback, dict): err('FALLBACK_INVALID')
    else:
        if not isinstance(fallback.get('id'), str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', fallback['id']) or not isinstance(fallback.get('name'), str) or not fallback['name'].strip(): err('FALLBACK_INVALID')
        if fallback.get('id') in ids: err('TYPE_ID_DUPLICATE')
        weights(fallback.get('weights'))
    mix = config.get('mixing')
    if not isinstance(mix, dict): err('MIXING_INVALID')
    else:
        threshold, max_types = mix.get('minimum_membership'), mix.get('maximum_types')
        low, high = mix.get('pillar_min'), mix.get('pillar_max')
        if not finite(threshold) or not 0 < threshold <= 1 or type(max_types) is not int or not 1 <= max_types <= 128: err('MIXING_INVALID')
        if not finite(low) or not finite(high) or not 0 <= low < high <= 100 or high <= 0: err('MIXING_INVALID')
        if mix.get('tie_break') != 'CONFIG_ORDER' or mix.get('clamp_then_normalize') is not True: err('MIXING_INVALID')
        pairs = mix.get('exclusive_pairs')
        if not isinstance(pairs, list): err('MIXING_INVALID')
        else:
            for pair in pairs:
                if not isinstance(pair, list) or len(pair) != 2 or pair[0] == pair[1] or any(p not in ids for p in pair): err('EXCLUSIVE_PAIR_INVALID')
    basis = config.get('value_basis')
    if not isinstance(basis, dict) or 'cyclical_type' not in basis or basis.get('cyclical_type') is not None and basis.get('cyclical_type') not in ids: err('VALUE_BASIS_INVALID')
    elif basis.get('cyclical_type') is not None:
        if type(basis.get('normalized_years')) is not int or basis['normalized_years'] < 1 or not isinstance(basis.get('required_metric'), str): err('VALUE_BASIS_INVALID')
    if not isinstance(config.get('themes'), dict) or config['themes'].get('role') != 'EXPOSURE_ONLY': err('THEME_ROLE_INVALID')
    return tuple(errors)


@dataclass(frozen=True)
class TypeConfig:
    payload: str = field(repr=False)
    official: bool = False

    def to_dict(self):
        return json.loads(self.payload)


def _compile(config, official):
    errors = validate_type_config(config)
    if errors: raise ValueError('|'.join(errors))
    try: payload = json.dumps(config, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError): raise ValueError('CONFIG_INVALID') from None
    return TypeConfig(payload, official)


def load_official_type_config():
    """Isolated file access; caller supplies the resulting value to pure engines."""
    return _compile(json.loads(Path(__file__).with_name('type_config_v1.json').read_text()), True)


def compile_custom_config(config):
    """Fresh, immutable device copy. An official status label cannot promote it."""
    if isinstance(config, TypeConfig): config = config.to_dict()
    errors = validate_type_config(config)
    if errors: raise ValueError('|'.join(errors))
    try: config = json.loads(json.dumps(config, allow_nan=False))
    except (ValueError, TypeError, RecursionError): raise ValueError('CONFIG_INVALID') from None
    config['status'] = 'CUSTOM_PREVIEW'
    return _compile(config, False)
